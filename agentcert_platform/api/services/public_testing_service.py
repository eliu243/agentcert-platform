"""
Public testing service for crowdsourced agent testing
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PublicTestingService:
    """Service for managing public agents and vulnerability reports"""
    
    def __init__(self):
        """Initialize public testing service with in-memory storage"""
        # In-memory storage for public agents
        # Structure: {agent_id: {owner_user_id, owner_username, github_repo, description, is_public, created_at, test_count, security_score}}
        self.public_agents: Dict[str, Dict[str, Any]] = {}
        
        # In-memory storage for vulnerability reports
        # Structure: List of {agent_id, reporter_user_id, reporter_username, category, severity, prompt, agent_response, description, timestamp, status}
        self.vulnerability_reports: List[Dict[str, Any]] = []
    
    def make_agent_public(
        self,
        agent_id: str,
        owner_user_id: str,
        owner_username: str,
        github_repo: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make an agent publicly available for testing.
        
        Args:
            agent_id: Agent identifier
            owner_user_id: User ID of agent owner
            owner_username: Username of agent owner
            github_repo: GitHub repository URL
            description: Optional description of the agent
        
        Returns:
            Dictionary with agent public status
        """
        self.public_agents[agent_id] = {
            "agent_id": agent_id,
            "owner_user_id": owner_user_id,
            "owner_username": owner_username,
            "github_repo": github_repo,
            "description": description,
            "is_public": True,
            "created_at": datetime.now().isoformat(),
            "test_count": 0,
            "security_score": None
        }
        
        logger.info(f"Agent {agent_id} made public by {owner_username}")
        return self.public_agents[agent_id]
    
    def make_agent_private(self, agent_id: str, owner_user_id: str) -> bool:
        """
        Make an agent private (remove from public testing).
        
        Args:
            agent_id: Agent identifier
            owner_user_id: User ID of agent owner (for verification)
        
        Returns:
            True if successful, False if agent not found or not owned by user
        """
        if agent_id not in self.public_agents:
            return False
        
        if self.public_agents[agent_id]["owner_user_id"] != owner_user_id:
            return False
        
        self.public_agents[agent_id]["is_public"] = False
        logger.info(f"Agent {agent_id} made private by {owner_user_id}")
        return True
    
    def get_public_agents(self) -> List[Dict[str, Any]]:
        """
        Get all publicly available agents.
        
        Returns:
            List of public agent dictionaries
        """
        return [
            agent for agent in self.public_agents.values()
            if agent.get("is_public", False)
        ]
    
    def is_agent_public(self, agent_id: str) -> bool:
        """
        Check if an agent is public.
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            True if agent is public, False otherwise
        """
        if agent_id not in self.public_agents:
            return False
        return self.public_agents[agent_id].get("is_public", False)
    
    def get_agent_owner(self, agent_id: str) -> Optional[str]:
        """
        Get the owner user ID of an agent.
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Owner user ID if found, None otherwise
        """
        if agent_id not in self.public_agents:
            return None
        return self.public_agents[agent_id].get("owner_user_id")
    
    def increment_test_count(self, agent_id: str) -> None:
        """
        Increment the test count for an agent.
        
        Args:
            agent_id: Agent identifier
        """
        if agent_id in self.public_agents:
            self.public_agents[agent_id]["test_count"] = \
                self.public_agents[agent_id].get("test_count", 0) + 1
    
    def add_vulnerability_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a vulnerability report.
        
        Args:
            report: Dictionary containing report data
        
        Returns:
            The added report with generated report_id
        """
        report_id = f"report-{len(self.vulnerability_reports) + 1}"
        report["report_id"] = report_id
        report["timestamp"] = datetime.now().isoformat()
        report["status"] = "open"  # Default status: "open" or "addressed"
        
        self.vulnerability_reports.append(report)
        logger.info(f"Vulnerability report {report_id} added for agent {report.get('agent_id')}")
        
        return report
    
    def get_vulnerability_reports(
        self,
        agent_id: str,
        owner_user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get vulnerability reports for an agent (owner only).
        
        Args:
            agent_id: Agent identifier
            owner_user_id: User ID of agent owner (for verification)
        
        Returns:
            List of vulnerability reports
        """
        # Verify ownership
        if agent_id not in self.public_agents:
            return []
        
        if self.public_agents[agent_id]["owner_user_id"] != owner_user_id:
            return []
        
        # Filter reports for this agent (only return open reports by default)
        return [
            report for report in self.vulnerability_reports
            if report.get("agent_id") == agent_id and report.get("status") != "addressed"
        ]
    
    def mark_report_addressed(
        self,
        report_id: str,
        agent_id: str,
        owner_user_id: str
    ) -> bool:
        """
        Mark a vulnerability report as addressed.
        
        Args:
            report_id: Report identifier
            agent_id: Agent identifier
            owner_user_id: User ID of agent owner (for verification)
        
        Returns:
            True if successful, False if report not found or not owned by user
        """
        # Verify ownership
        if agent_id not in self.public_agents:
            return False
        
        if self.public_agents[agent_id]["owner_user_id"] != owner_user_id:
            return False
        
        # Find and update the report
        for report in self.vulnerability_reports:
            if report.get("report_id") == report_id and report.get("agent_id") == agent_id:
                report["status"] = "addressed"
                report["addressed_at"] = datetime.now().isoformat()
                logger.info(f"Report {report_id} marked as addressed by {owner_user_id}")
                return True
        
        return False
    
    def update_agent_security_score(
        self,
        agent_id: str,
        security_score: Optional[float]
    ) -> None:
        """
        Update the security score for an agent.
        
        Args:
            agent_id: Agent identifier
            security_score: Security score (0-100) or None
        """
        if agent_id in self.public_agents:
            self.public_agents[agent_id]["security_score"] = security_score


# Global service instance
_public_testing_service: Optional[PublicTestingService] = None


def get_public_testing_service() -> PublicTestingService:
    """Get or create public testing service instance"""
    global _public_testing_service
    if _public_testing_service is None:
        _public_testing_service = PublicTestingService()
    return _public_testing_service

