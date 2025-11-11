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
                        "agent_response": result.get("agent_response", "")[:500],  # Extracted text for display
                        "raw_response": result.get("raw_response"),  # Include raw response with metadata
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
                
                # Log the raw response for debugging
                logger.info(f"=== A2A Response Debug ===")
                logger.info(f"Response type: {type(response_data)}")
                if isinstance(response_data, dict):
                    logger.info(f"Response keys: {list(response_data.keys())}")
                    # Log ALL values to understand the structure
                    # Helper function to check if string looks like UUID
                    def looks_like_uuid(s):
                        import re
                        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                        return bool(re.match(uuid_pattern, s.strip(), re.IGNORECASE)) if isinstance(s, str) else False
                    
                    for key, value in response_data.items():
                        if isinstance(value, str):
                            is_uuid_val = looks_like_uuid(value)
                            logger.info(f"  {key}: '{value}' (type: str, length: {len(value)}, looks_like_uuid: {is_uuid_val})")
                        elif isinstance(value, dict):
                            logger.info(f"  {key}: {{dict with keys: {list(value.keys())}}}")
                            # Log nested dict values
                            for nested_key, nested_value in value.items():
                                if isinstance(nested_value, str):
                                    is_uuid_nested = looks_like_uuid(nested_value)
                                    logger.info(f"    {nested_key}: '{nested_value}' (type: str, length: {len(nested_value)}, looks_like_uuid: {is_uuid_nested})")
                                else:
                                    logger.info(f"    {nested_key}: {type(nested_value)}")
                        elif isinstance(value, list):
                            logger.info(f"  {key}: [list with {len(value)} items]")
                            if len(value) > 0:
                                logger.info(f"    First item type: {type(value[0])}")
                                if isinstance(value[0], dict):
                                    logger.info(f"    First item keys: {list(value[0].keys())}")
                                elif isinstance(value[0], str):
                                    is_uuid_list = looks_like_uuid(value[0])
                                    logger.info(f"    First item: '{value[0]}' (looks_like_uuid: {is_uuid_list})")
                        else:
                            logger.info(f"  {key}: {type(value)}")
                    
                    # Also log as JSON for structure
                    import json
                    try:
                        response_str = json.dumps(response_data, indent=2)
                        logger.info(f"Full response as JSON:\n{response_str}")
                    except Exception as e:
                        logger.info(f"Could not serialize response as JSON: {e}")
                else:
                    logger.info(f"Response (non-dict): {response_data}")
                logger.info(f"=== End A2A Response Debug ===")
                
                agent_response = self._extract_response_text(response_data)
                
                # Validate extracted response - reject UUIDs immediately
                if agent_response:
                    if self._is_uuid(agent_response.strip()):
                        logger.error(f"ERROR: Initial extraction returned UUID (rejecting): {agent_response}")
                        agent_response = ""
                    else:
                        logger.info(f"Initial extraction successful (first 100 chars): {agent_response[:100]}")
                else:
                    logger.warning(f"No response extracted from initial extraction")
                
                # If extraction returned empty or was a UUID, try aggressive extraction
                if not agent_response or agent_response.strip() == '':
                    logger.warning(f"Trying aggressive extraction. Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'not a dict'}")
                    agent_response = self._extract_response_text_aggressive(response_data)
                    # Validate again - reject UUIDs
                    if agent_response and self._is_uuid(agent_response.strip()):
                        logger.error(f"Aggressive extraction returned UUID (rejecting): {agent_response}")
                        agent_response = ""
                
                # If still empty, try finding any text
                if not agent_response or agent_response.strip() == '':
                    logger.warning(f"Trying _find_any_text as last resort")
                    agent_response = self._find_any_text(response_data)
                    # Validate again - reject UUIDs
                    if agent_response and self._is_uuid(agent_response.strip()):
                        logger.error(f"_find_any_text returned UUID (rejecting): {agent_response}")
                        agent_response = ""
                
                # Final validation: ensure we have actual text, not a UUID or dict representation
                if agent_response:
                    stripped = agent_response.strip()
                    # Final UUID check
                    if self._is_uuid(stripped):
                        logger.error(f"Final validation: Response is a UUID: {stripped}")
                        agent_response = ""
                    # Check if it looks like a Python dict representation
                    elif stripped.startswith('{') and ("'conversation_id'" in stripped or (stripped.count("'") > stripped.count('"') and 'conversation_id' in stripped)):
                        logger.error(f"Response appears to be Python dict representation: {stripped[:100]}")
                        # Try to parse and re-extract
                        try:
                            import ast
                            parsed = ast.literal_eval(stripped)
                            if isinstance(parsed, dict):
                                agent_response = self._extract_response_text_aggressive(parsed)
                                if agent_response and self._is_uuid(agent_response.strip()):
                                    agent_response = ""
                                if not agent_response:
                                    agent_response = self._find_any_text(parsed)
                                    if agent_response and self._is_uuid(agent_response.strip()):
                                        agent_response = ""
                        except:
                            pass
                
                # If we still don't have proper text after all attempts, log extensively
                if not agent_response or agent_response.strip() == '':
                    logger.error(f"CRITICAL: All extraction methods failed or returned UUIDs")
                    logger.error(f"Response data type: {type(response_data)}")
                    if isinstance(response_data, dict):
                        logger.error(f"Response keys: {list(response_data.keys())}")
                        # Try to show all string values in the response
                        import json
                        try:
                            logger.error(f"Full response structure: {json.dumps(response_data, indent=2)}")
                        except:
                            logger.error(f"Response (non-serializable): {response_data}")
                    agent_response = "[Unable to extract response text - response may contain only UUIDs/metadata]"
                
                # FINAL VALIDATION: Never store a UUID as the response
                # If agent_response is a UUID, it means extraction failed
                if agent_response and self._is_uuid(agent_response.strip()):
                    logger.error(f"CRITICAL ERROR: Attempted to store UUID as agent_response: {agent_response}")
                    logger.error(f"This should never happen - all UUID checks should have caught this!")
                    logger.error(f"Response data was: {response_data}")
                    # Don't store the UUID - store an error message instead
                    agent_response = "[Error: Response extraction returned UUID instead of text - see server logs]"
                
                # Analyze response for violations (even if it's an error message)
                analysis = analyze_response(agent_response, prompt_data)
                
                # Store both the extracted text (for display) and the raw response (for export)
                return {
                    "test_id": prompt_data["id"],
                    "category": prompt_data["category"],
                    "prompt": prompt_data["prompt"],
                    "agent_response": agent_response[:500] if agent_response else "",  # Truncated extracted text for display
                    "raw_response": response_data,  # Store full raw NEST response with all metadata (conversation_id, role, type, etc.)
                    "passed": analysis["passed"],
                    "violations": analysis["violations"],
                    "severity": analysis["severity"]
                }
        
        except Exception as e:
            logger.error(f"Error testing prompt: {e}")
            return {
                "test_id": prompt_data["id"],
                "status": "error",
                "error": str(e),
                "raw_response": None  # No raw response on error
            }
    
    def _find_any_text(self, response_data: Any) -> str:
        """Aggressively search for any text content in the response"""
        if isinstance(response_data, str):
            # If it's a string but looks like a Python dict representation, try to parse it
            if response_data.strip().startswith('{') and not response_data.strip().startswith('{"'):
                # Might be a Python dict string, try to evaluate or parse
                try:
                    import json
                    # Try to convert Python dict string to JSON
                    import ast
                    parsed = ast.literal_eval(response_data)
                    if isinstance(parsed, dict):
                        return self._extract_response_text(parsed)
                except:
                    pass
            return response_data
        
        if isinstance(response_data, dict):
            # Try to find the longest string value that's not metadata
            metadata_fields = {"conversation_id", "conversationId", "role", "type", "timestamp", "id", "test_id"}
            candidates = []
            
            def search_dict(obj, depth=0):
                if depth > 5:
                    return
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key not in metadata_fields:
                            if isinstance(value, str) and len(value.strip()) > 3:
                                stripped = value.strip()
                                
                                # STRICT UUID detection - reject anything that looks like a UUID
                                # UUID pattern: 8-4-4-4-12 hex digits with hyphens
                                import re
                                uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                                is_uuid = bool(re.match(uuid_pattern, stripped, re.IGNORECASE))
                                
                                # Reject if it's a UUID
                                if is_uuid:
                                    continue
                                
                                # Check if it looks like actual text
                                has_letters = any(c.isalpha() for c in stripped)
                                has_spaces = ' ' in stripped
                                word_count = len(stripped.split())
                                is_numeric_only = stripped.replace('.', '').replace('-', '').replace(' ', '').isdigit()
                                starts_with_brace = stripped.startswith('{') or stripped.startswith('[')
                                is_hex_only = bool(re.match(r'^[0-9a-f-]+$', stripped, re.IGNORECASE)) and len(stripped) > 20
                                
                                # It's likely text if:
                                # - Has letters AND (has spaces OR multiple words OR is longer than 20 chars)
                                # - AND is not purely numeric
                                # - AND doesn't start with brace (not a JSON string)
                                # - AND is not hex-only (which might be a hash)
                                if (has_letters and 
                                    (has_spaces or word_count > 1 or len(stripped) > 20) and 
                                    not is_numeric_only and
                                    not starts_with_brace and
                                    not is_hex_only):
                                    candidates.append((len(stripped), stripped))
                            elif isinstance(value, (dict, list)):
                                search_dict(value, depth + 1)
                elif isinstance(obj, list):
                    for item in obj:
                        search_dict(item, depth + 1)
            
            search_dict(response_data)
            
            if candidates:
                # Return the longest candidate
                candidates.sort(reverse=True, key=lambda x: x[0])
                return candidates[0][1]
            
            # If no candidates found, try to extract from content field more aggressively
            if "content" in response_data:
                content = response_data["content"]
                if isinstance(content, str) and content.strip():
                    return content.strip()
                elif isinstance(content, dict):
                    # Recursively search in content
                    result = self._find_any_text(content)
                    if result and not result.startswith('{'):
                        return result
        
        # Last resort: return empty string (don't return Python dict representation)
        return ""
    
    def _extract_response_text_aggressive(self, response_data: Any) -> str:
        """More aggressive extraction that handles edge cases"""
        if isinstance(response_data, str):
            # Reject if it's a UUID
            if self._is_uuid(response_data.strip()):
                return ""
            # If it's already a string but looks like a dict representation, try to parse it
            if response_data.strip().startswith('{'):
                try:
                    import json
                    parsed = json.loads(response_data)
                    extracted = self._extract_response_text(parsed)
                    # Reject if extracted value is a UUID
                    if extracted and not self._is_uuid(extracted):
                        return extracted
                except:
                    pass
            return response_data
        
        if isinstance(response_data, dict):
            # Check all possible text fields, including nested ones
            # Order matters - check most common formats first
            text_fields = [
                ["content", "text"],  # Most common: {content: {text: "..."}}
                ["content", 0, "text"],  # content as array: {content: [{text: "..."}]}
                ["message", "content", "text"],  # Nested message
                ["response", "content", "text"],  # Nested response
                ["data", "content", "text"],  # Nested data
                ["result", "content", "text"],  # Nested result
                ["output", "content", "text"],  # Nested output
                ["choices", 0, "message", "content"],  # OpenAI-style: {choices: [{message: {content: "..."}}]}
                ["choices", 0, "message", "content", "text"],  # OpenAI-style with text
                ["messages", 0, "content"],  # Messages array
                ["messages", 0, "content", "text"],  # Messages with text
                ["text"],  # Direct text field
                ["message"],  # Direct message field
                ["response"],  # Direct response field
                ["answer"],  # Direct answer field
                ["output"],  # Direct output field
                ["body"],  # HTTP body
                ["data"],  # Direct data field
            ]
            
            for field_path in text_fields:
                try:
                    value = response_data
                    for field in field_path:
                        if isinstance(value, list) and isinstance(field, int):
                            if field < len(value):
                                value = value[field]
                            else:
                                value = None
                                break
                        elif isinstance(value, dict):
                            value = value.get(field)
                        else:
                            value = None
                            break
                    
                    if isinstance(value, str) and value.strip():
                        stripped = value.strip()
                        # Reject if it's a UUID
                        if not self._is_uuid(stripped):
                            return stripped
                except (KeyError, TypeError, IndexError):
                    continue
        
        return ""
    
    def _is_uuid(self, text: str) -> bool:
        """Check if a string is a UUID"""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, text.strip(), re.IGNORECASE))
    
    def _extract_response_text(self, response_data: Any) -> str:
        """Extract response text from NEST A2A response"""
        if isinstance(response_data, dict):
            # Check for nested content.text (common in NEST/A2A responses)
            if "content" in response_data:
                content = response_data["content"]
                if isinstance(content, dict) and "text" in content:
                    text = str(content["text"])
                    # Reject if it's a UUID
                    if text and not self._is_uuid(text):
                        return text
                elif isinstance(content, str):
                    # Reject if it's a UUID
                    if content and not self._is_uuid(content):
                        return content
                # Handle content as array (some responses have content as list)
                elif isinstance(content, list) and len(content) > 0:
                    # Look for text in first item
                    first_item = content[0]
                    if isinstance(first_item, dict) and "text" in first_item:
                        text = str(first_item["text"])
                        # Reject if it's a UUID
                        if text and not self._is_uuid(text):
                            return text
                    elif isinstance(first_item, str):
                        # Reject if it's a UUID
                        if first_item and not self._is_uuid(first_item):
                            return first_item
            
            # Check for direct text field
            if "text" in response_data:
                text = str(response_data["text"])
                # Reject if it's a UUID
                if text and not self._is_uuid(text):
                    return text
            
            # Check for message field
            if "message" in response_data:
                message = response_data["message"]
                if isinstance(message, str) and message:
                    # Reject if it's a UUID
                    if not self._is_uuid(message):
                        return message
                elif isinstance(message, dict):
                    # Recursively extract from message
                    extracted = self._extract_response_text(message)
                    if extracted and not self._is_uuid(extracted):
                        return extracted
            
            # Check for response field
            if "response" in response_data:
                response = response_data["response"]
                if isinstance(response, str) and response:
                    # Reject if it's a UUID
                    if not self._is_uuid(response):
                        return response
                elif isinstance(response, dict):
                    extracted = self._extract_response_text(response)
                    if extracted and not self._is_uuid(extracted):
                        return extracted
            
            # Check for answer field
            if "answer" in response_data:
                answer = response_data["answer"]
                # Reject if it's a UUID
                if isinstance(answer, str) and answer and not self._is_uuid(answer):
                    return answer
            
            # Check for output field
            if "output" in response_data:
                output = response_data["output"]
                # Reject if it's a UUID
                if isinstance(output, str) and output and not self._is_uuid(output):
                    return output
            
            # Last resort: try to find any string field that looks like content
            # Skip ALL metadata fields (including conversation_id, message_id, etc. which are often UUIDs)
            metadata_fields = {
                "conversation_id", "conversationId", "conversation_id", 
                "role", "type", "timestamp", "id", "message_id", "msg_id",
                "request_id", "requestId", "session_id", "sessionId",
                "user_id", "userId", "agent_id", "agentId"
            }
            for key, value in response_data.items():
                # Skip metadata fields
                if key in metadata_fields:
                    continue
                # Skip any field that looks like it contains a UUID
                if isinstance(value, str):
                    # Always reject UUIDs, even if not in metadata_fields
                    if self._is_uuid(value):
                        continue
                    if value and len(value) > 5:
                        # Check if it looks like actual text (not a hash, not just hex)
                        # Must have letters (not just hex digits) and be meaningful
                        if any(c.isalpha() and c not in 'abcdef' for c in value.lower()) or ' ' in value:
                            return value
                elif isinstance(value, dict):
                    # Recursively check nested dict
                    extracted = self._extract_response_text(value)
                    if extracted and not self._is_uuid(extracted):
                        return extracted
                elif isinstance(value, list):
                    # Check list items
                    for item in value:
                        if isinstance(item, str) and not self._is_uuid(item) and len(item) > 5:
                            if any(c.isalpha() and c not in 'abcdef' for c in item.lower()) or ' ' in item:
                                return item
                        elif isinstance(item, dict):
                            extracted = self._extract_response_text(item)
                            if extracted and not self._is_uuid(extracted):
                                return extracted
            
            # Don't return JSON representation or string representation of dict
            # (that would show as a hash to the user)
            # Return empty and let the caller handle it with more aggressive extraction methods
            logger.debug(f"Could not extract text from response. Keys: {list(response_data.keys())}")
            return ""
        
        # If it's already a string, validate it
        if isinstance(response_data, str):
            # Reject if it's a UUID
            if self._is_uuid(response_data.strip()):
                return ""
            return response_data
        
        # For other types, don't convert to string representation (avoids dict representation)
        # Return empty and let caller handle it
        return ""
    
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
                    "agent_response": result.get("agent_response", "")[:500],  # Extracted text for display
                    "raw_response": result.get("raw_response"),  # Include raw response with metadata
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

