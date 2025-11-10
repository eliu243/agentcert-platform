"""
Stress Test Service - Tests agents with malicious prompts
"""

import asyncio
import httpx
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import sys
from pathlib import Path

# Add config path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .malicious_prompts import load_malicious_prompts
from .response_analyzer import analyze_response

logger = logging.getLogger(__name__)


class StressTestService:
    """Service for running stress tests on deployed agents"""
    
    def __init__(self):
        self.active_tests: Dict[str, Dict[str, Any]] = {}  # In-memory storage
        self.results_storage: Dict[str, Dict[str, Any]] = {}  # Test results
    
    async def run_stress_test(self, agent_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run stress test on a deployed agent.
        
        Args:
            agent_id: Agent ID to test
            user_id: Optional user ID (for user-scoped deployments)
        
        Returns:
            Dictionary with test results
        """
        test_id = f"test-{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Starting stress test {test_id} for agent {agent_id}")
        
        # Get agent info (from deployment service)
        agent_info = await self._get_agent_info(agent_id, user_id=user_id)
        if not agent_info:
            raise ValueError(f"Agent {agent_id} not found or not registered")
        
        # For Phase 1: If agent is registered but not deployed, we'll test locally
        agent_url = agent_info.get("agent_url")
        repo_path = agent_info.get("repo_path")
        
        if not agent_url and not repo_path:
            raise ValueError(f"Agent {agent_id} has no deployment info")
        
        # Mark test as running
        self.active_tests[test_id] = {
            "test_id": test_id,
            "agent_id": agent_id,
            "status": "running",
            "started_at": datetime.now().isoformat()
        }
        
        try:
            # Load malicious prompts
            prompts = load_malicious_prompts()
            
            # Run tests
            test_results = []
            for i, prompt_data in enumerate(prompts, 1):
                logger.info(f"[{i}/{len(prompts)}] Testing: {prompt_data['category']}")
                
                # Test the agent via HTTP
                if not agent_url:
                    raise ValueError(f"Agent {agent_id} is not deployed (no agent_url)")
                
                result = await self._test_prompt(
                    agent_url,
                    prompt_data,
                    f"{test_id}-{i}"
                )
                test_results.append(result)
            
            # Get A2A logs from agent (if deployed)
            a2a_logs = {}
            if agent_url:
                a2a_logs = await self._get_a2a_logs(agent_url)
            else:
                logger.info("Skipping A2A logs retrieval (agent not deployed)")
            
            # Calculate security score
            passed_tests = sum(1 for r in test_results if r.get("passed", False))
            failed_tests = len(test_results) - passed_tests
            security_score = (passed_tests / len(test_results) * 100) if test_results else 0
            
            # Extract violations
            violations = []
            for result in test_results:
                if not result.get("passed", False) and result.get("violations"):
                    violations.append({
                        "test_id": result.get("test_id", ""),
                        "category": result.get("category", ""),
                        "severity": result.get("severity", "medium"),
                        "prompt": result.get("prompt", ""),
                        "agent_response": result.get("agent_response", "")[:500],
                        "description": ", ".join(result.get("violations", []))
                    })
            
            # Prepare final results
            final_results = {
                "test_id": test_id,
                "agent_id": agent_id,
                "status": "completed",
                "security_score": security_score,
                "total_tests": len(test_results),
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "violations": violations,
                "test_results": test_results,
                "a2a_logs": a2a_logs,
                "completed_at": datetime.now().isoformat()
            }
            
            # Store results in both places
            self.results_storage[test_id] = final_results
            
            # Also store in ResultsService (use shared instance from results route)
            try:
                from ..api.routes.results import results_service
                results_service.store_results(agent_id, final_results)
            except Exception as e:
                logger.warning(f"Could not store results in ResultsService: {e}")
            
            # Update active test status
            self.active_tests[test_id]["status"] = "completed"
            
            return {
                "test_id": test_id,
                "agent_id": agent_id,
                "status": "completed",
                "total_tests": len(prompts),
                "results": test_results
            }
        
        except Exception as e:
            logger.error(f"Stress test failed: {e}")
            self.active_tests[test_id]["status"] = "failed"
            self.active_tests[test_id]["error"] = str(e)
            raise
    
    async def _test_prompt(
        self,
        agent_url: str,
        prompt_data: Dict[str, Any],
        conversation_id: str
    ) -> Dict[str, Any]:
        """Test a single malicious prompt"""
        try:
            # Ensure agent_url has /a2a endpoint
            if not agent_url.endswith('/a2a'):
                if agent_url.endswith('/'):
                    a2a_url = f"{agent_url}a2a"
                else:
                    a2a_url = f"{agent_url}/a2a"
            else:
                a2a_url = agent_url
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    a2a_url,
                    json={
                        "content": {
                            "text": prompt_data["prompt"],
                            "type": "text"
                        },
                        "role": "user",
                        "conversation_id": conversation_id
                    }
                )
                
                if response.status_code != 200:
                    return {
                        "test_id": prompt_data["id"],
                        "status": "error",
                        "error": f"HTTP {response.status_code}"
                    }
                
                # Parse response
                response_data = response.json()
                agent_response = self._extract_response_text(response_data)
                
                # Analyze response for violations
                analysis = analyze_response(agent_response, prompt_data)
                
                return {
                    "test_id": prompt_data["id"],
                    "category": prompt_data["category"],
                    "prompt": prompt_data["prompt"],
                    "agent_response": agent_response[:500],  # Truncate
                    "passed": analysis["passed"],
                    "violations": analysis["violations"],
                    "severity": analysis["severity"]
                }
        
        except Exception as e:
            logger.error(f"Error testing prompt: {e}")
            return {
                "test_id": prompt_data["id"],
                "status": "error",
                "error": str(e)
            }
    
    def _extract_response_text(self, response_data: Any) -> str:
        """Extract response text from NEST A2A response"""
        if isinstance(response_data, dict):
            if "content" in response_data:
                content = response_data["content"]
                if isinstance(content, dict) and "text" in content:
                    return content["text"]
                elif isinstance(content, str):
                    return content
            return str(response_data)
        return str(response_data)
    
    async def _get_a2a_logs(self, agent_url: str) -> Dict[str, Any]:
        """Get A2A logs from agent"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try to get logs endpoint (if implemented)
                response = await client.get(f"{agent_url}/logs/a2a?time_window_hours=1")
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass
        
        return {}
    
    async def _get_agent_info(self, agent_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get agent info from deployment service"""
        try:
            # Import the same instance used by the deploy route
            from ..api.utils import get_deployment_service
            deployment_service = get_deployment_service()
            # user_id is optional - if not provided, it won't verify ownership
            # but since we already verify in the route, this should work
            deployment_info = await deployment_service.get_deployment_status(agent_id, user_id=user_id)
            return deployment_info
        except Exception as e:
            logger.error(f"Failed to get agent info for {agent_id}: {e}")
            return None
    
    async def _get_agent_url(self, agent_id: str) -> Optional[str]:
        """Get agent URL from deployment service (deprecated - use _get_agent_info)"""
        agent_info = await self._get_agent_info(agent_id)
        return agent_info.get("agent_url") if agent_info else None
    
    async def get_test_status(self, agent_id: str) -> Dict[str, Any]:
        """Get status of stress test for an agent"""
        # Find active test for agent
        for test_id, test_info in self.active_tests.items():
            if test_info["agent_id"] == agent_id:
                return test_info
        
        # Check if results exist
        for test_id, results in self.results_storage.items():
            if results["agent_id"] == agent_id:
                return {
                    "test_id": test_id,
                    "agent_id": agent_id,
                    "status": "completed",
                    "results_available": True
                }
        
        raise ValueError(f"No test found for agent {agent_id}")
    
    async def analyze_with_grader(self, agent_id: str, test_id: str):
        """Trigger LLM grader analysis (called in background)"""
        from ..grader.llm_grader import LLMGrader
        from ..grader.scorer import ResultsService
        
        if test_id not in self.results_storage:
            logger.warning(f"Test results not found for {test_id}")
            return
        
        test_data = self.results_storage[test_id]
        
        grader = LLMGrader()
        analysis = await grader.analyze(
            stress_test_results=test_data["test_results"],
            a2a_logs=test_data["a2a_logs"]
        )
        
        # Store analysis results
        test_data["grader_analysis"] = analysis
        test_data["security_score"] = analysis.get("security_score", 0.0)
        
        # Calculate test statistics
        test_results = test_data["test_results"]
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.get("passed", False))
        failed_tests = total_tests - passed_tests
        
        # Extract violations from test_results (already in correct format)
        # Don't use violations from LLM grader as they might be in wrong format
        violations = []
        for result in test_results:
            if not result.get("passed", False) and result.get("violations"):
                violations.append({
                    "test_id": result.get("test_id", ""),
                    "category": result.get("category", ""),
                    "severity": result.get("severity", "medium"),
                    "prompt": result.get("prompt", ""),
                    "agent_response": result.get("agent_response", "")[:500],
                    "description": ", ".join(result.get("violations", []))
                })
        
        # Prepare final results
        final_results = {
            "test_id": test_id,
            "agent_id": agent_id,
            "security_score": analysis.get("security_score", 0.0),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "violations": violations,  # Use properly formatted violations
            "test_results": test_results,
            "a2a_logs": test_data.get("a2a_logs", {}),
            "completed_at": test_data.get("completed_at")
        }
        
        # Store in ResultsService (use shared instance from results route)
        try:
            from ..api.routes.results import results_service
            results_service.store_results(agent_id, final_results)
        except Exception as e:
            logger.warning(f"Could not store results in ResultsService: {e}")

