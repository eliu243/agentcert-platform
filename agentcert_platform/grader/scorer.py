"""
Results Service - Manages and retrieves test results

Note: This file should be renamed to results_service.py for clarity,
but keeping scorer.py for now to match the import in routes/results.py
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ResultsService:
    """Service for managing and retrieving test results"""
    
    def __init__(self):
        # In-memory storage (in production, use database)
        self.results: Dict[str, Dict[str, Any]] = {}
    
    async def get_results(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete test results for an agent.
        
        Args:
            agent_id: Agent ID
        
        Returns:
            Dictionary with all results
        """
        # Find results for this agent
        for test_id, result in self.results.items():
            if result.get("agent_id") == agent_id:
                return result
        
        return None
    
    async def get_summary(self, agent_id: str) -> Dict[str, Any]:
        """Get summary of results (lightweight)"""
        results = await self.get_results(agent_id)
        
        if not results:
            return {
                "agent_id": agent_id,
                "status": "no_results"
            }
        
        return {
            "agent_id": agent_id,
            "security_score": results.get("security_score", 0),
            "total_tests": results.get("total_tests", 0),
            "passed_tests": results.get("passed_tests", 0),
            "failed_tests": results.get("failed_tests", 0),
            "violations_count": len(results.get("violations", [])),
            "status": "completed"
        }
    
    def store_results(self, agent_id: str, results: Dict[str, Any]):
        """Store test results"""
        test_id = results.get("test_id", f"test-{agent_id}")
        self.results[test_id] = results

