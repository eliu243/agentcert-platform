"""
Auditor Service - Manages auditor agent deployments and audit tracking
"""

import os
import sys
import uuid
import logging
import asyncio
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from ..api.utils import get_deployment_service
from ..deployment.secrets_manager import get_secrets_manager

logger = logging.getLogger(__name__)


class AuditorService:
    """Service for managing auditor deployments and audits"""
    
    def __init__(self):
        self.audits: Dict[str, Dict[str, Any]] = {}  # In-memory storage
        self.auditor_agents: Dict[str, Dict[str, Any]] = {}  # Track deployed auditor agents
        # auditor_service.py is in agentcert_platform/auditors/, so parent is the auditors directory
        self.auditor_repo_path = Path(__file__).parent
    
    async def deploy_auditor(
        self,
        auditor_type: str,
        target_agent_id: str,
        user_id: str,
        target_agent_url: str
    ) -> Dict[str, Any]:
        """
        Deploy an auditor agent to test a target agent.
        
        Args:
            auditor_type: Type of auditor (e.g., "child-safety")
            target_agent_id: ID of the target agent to test
            user_id: User ID who requested the audit
            target_agent_url: URL of the target agent
        
        Returns:
            Dictionary with audit_id and auditor deployment info
        """
        # Generate audit ID
        audit_id = f"audit-{uuid.uuid4().hex[:8]}"
        
        # Map auditor type to directory name
        # "child-safety" -> "child_safety_auditor"
        auditor_type_to_dir = {
            "child-safety": "child_safety_auditor"
        }
        
        auditor_dir_name = auditor_type_to_dir.get(auditor_type, auditor_type.replace("-", "_") + "_auditor")
        
        # Get auditor path
        auditor_path = self.auditor_repo_path / auditor_dir_name
        logger.info(f"Looking for auditor at: {auditor_path}")
        if not auditor_path.exists():
            raise ValueError(f"Auditor type '{auditor_type}' not found (looked for directory: {auditor_dir_name})")
        
        # Get deployment service
        deployment_service = get_deployment_service()
        
        # Generate auditor agent ID
        auditor_agent_id = f"auditor-{auditor_type}-{audit_id}"
        
        # Get platform callback URL (where auditor reports results)
        platform_base_url = os.getenv("PLATFORM_BASE_URL", "http://localhost:8000")
        platform_callback_url = f"{platform_base_url}/api/auditor/audit/{audit_id}/results"
        
        # Store audit info
        self.audits[audit_id] = {
            "audit_id": audit_id,
            "auditor_type": auditor_type,
            "target_agent_id": target_agent_id,
            "target_agent_url": target_agent_url,
            "user_id": user_id,
            "auditor_agent_id": auditor_agent_id,
            "status": "deploying",
            "created_at": datetime.now().isoformat(),
            "results": None
        }
        
        try:
            # Prepare environment variables for auditor
            # The auditor needs to know:
            # - Target agent URL
            # - Platform callback URL
            # - Audit ID
            # - API keys (if needed for LLM)
            
            # Get secrets manager for API keys
            secrets_manager = get_secrets_manager()
            
            # Check if we have OpenAI API key stored globally or for this user
            openai_key = os.getenv("OPENAI_API_KEY")  # Can be set globally
            if not openai_key:
                # Try to get from secrets (could be stored per-user or globally)
                try:
                    openai_key = secrets_manager.get_secret("global", "OPENAI_API_KEY")
                except:
                    pass
            
            # Deploy auditor agent using deployment service
            # We'll deploy it from the local auditor directory
            # For this, we need to create a temporary git repo or use file path
            # Since deployment service expects a GitHub repo, we'll need to adapt
            
            # For now, we'll deploy the auditor in standalone mode
            # This means it runs as a background process, not as a NEST agent
            # This is simpler and works for both local and EC2
            
            logger.info(f"Deploying auditor {auditor_agent_id} for audit {audit_id}")
            
            # Start auditor in standalone mode as background task
            auditor_process = await self._start_auditor_standalone(
                auditor_path=auditor_path,
                auditor_type=auditor_type,
                audit_id=audit_id,
                target_agent_url=target_agent_url,
                platform_callback_url=platform_callback_url,
                openai_key=openai_key
            )
            
            # Store auditor info
            self.auditor_agents[auditor_agent_id] = {
                "auditor_agent_id": auditor_agent_id,
                "audit_id": audit_id,
                "process": auditor_process,
                "status": "running"
            }
            
            self.audits[audit_id]["status"] = "running"
            
            return {
                "audit_id": audit_id,
                "auditor_agent_id": auditor_agent_id,
                "status": "running",
                "message": f"Auditor deployed and audit started"
            }
        
        except Exception as e:
            logger.error(f"Error deploying auditor: {e}")
            self.audits[audit_id]["status"] = "failed"
            self.audits[audit_id]["error"] = str(e)
            raise
    
    async def _start_auditor_standalone(
        self,
        auditor_path: Path,
        auditor_type: str,
        audit_id: str,
        target_agent_url: str,
        platform_callback_url: str,
        openai_key: Optional[str]
    ):
        """Start auditor in standalone mode as background process"""
        
        # Set up environment variables
        env = os.environ.copy()
        env["STANDALONE_MODE"] = "true"
        env["TARGET_AGENT_URL"] = target_agent_url
        env["PLATFORM_CALLBACK_URL"] = platform_callback_url
        env["AUDIT_ID"] = audit_id
        if openai_key:
            env["OPENAI_API_KEY"] = openai_key
        
        # Run auditor script
        agent_script = auditor_path / "agent.py"
        if not agent_script.exists():
            raise ValueError(f"Auditor agent script not found: {agent_script}")
        
        # Start process
        process = subprocess.Popen(
            [sys.executable, str(agent_script)],
            env=env,
            cwd=str(auditor_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        logger.info(f"Started auditor process {process.pid} for audit {audit_id}")
        return process
    
    def get_audit_status(self, audit_id: str) -> Dict[str, Any]:
        """Get status of an audit"""
        if audit_id not in self.audits:
            raise ValueError(f"Audit {audit_id} not found")
        
        audit = self.audits[audit_id].copy()
        
        # Check if auditor process is still running
        if audit.get("auditor_agent_id"):
            auditor_agent_id = audit["auditor_agent_id"]
            if auditor_agent_id in self.auditor_agents:
                auditor_info = self.auditor_agents[auditor_agent_id]
                process = auditor_info.get("process")
                if process and process.poll() is not None:
                    # Process finished
                    if audit["status"] == "running":
                        audit["status"] = "completed" if audit.get("results") else "failed"
        
        return audit
    
    def get_audit_report(self, audit_id: str) -> Dict[str, Any]:
        """Get audit report (results)"""
        if audit_id not in self.audits:
            raise ValueError(f"Audit {audit_id} not found")
        
        audit = self.audits[audit_id]
        
        if not audit.get("results"):
            raise ValueError(f"Audit {audit_id} has no results yet")
        
        return audit["results"]
    
    def store_audit_results(self, audit_id: str, results: Dict[str, Any]):
        """Store audit results (called by callback endpoint)"""
        if audit_id not in self.audits:
            logger.warning(f"Received results for unknown audit {audit_id}")
            return
        
        self.audits[audit_id]["results"] = results
        self.audits[audit_id]["status"] = "completed"
        self.audits[audit_id]["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"Stored results for audit {audit_id}")
    
    async def stop_audit(self, audit_id: str) -> bool:
        """Stop a running audit"""
        if audit_id not in self.audits:
            raise ValueError(f"Audit {audit_id} not found")
        
        audit = self.audits[audit_id]
        
        # Stop auditor process
        if audit.get("auditor_agent_id"):
            auditor_agent_id = audit["auditor_agent_id"]
            if auditor_agent_id in self.auditor_agents:
                auditor_info = self.auditor_agents[auditor_agent_id]
                process = auditor_info.get("process")
                if process:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except:
                        process.kill()
                    logger.info(f"Stopped auditor process for audit {audit_id}")
        
        audit["status"] = "stopped"
        return True
    
    def list_audits(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List audits, optionally filtered by user"""
        audits_list = list(self.audits.values())
        
        if user_id:
            audits_list = [a for a in audits_list if a.get("user_id") == user_id]
        
        return audits_list
    
    def get_available_auditors(self) -> List[Dict[str, Any]]:
        """Get list of available auditor types"""
        auditors = []
        
        # Check for child-safety auditor
        child_safety_path = self.auditor_repo_path / "child_safety_auditor"
        logger.info(f"Checking for child safety auditor at: {child_safety_path}")
        logger.info(f"Path exists: {child_safety_path.exists()}")
        if child_safety_path.exists():
            auditors.append({
                "type": "child-safety",
                "name": "Child Safety Auditor",
                "description": "Tests agents for child safety compliance (ages 8-13)",
                "target_age_range": "8-13 years",
                "categories": [
                    "Age-appropriate content",
                    "Personal information protection",
                    "Social engineering resistance",
                    "Inappropriate content filtering",
                    "Boundary respect",
                    "Grooming pattern detection"
                ]
            })
            logger.info("Child Safety Auditor found and added to available auditors")
        else:
            logger.warning(f"Child Safety Auditor not found at {child_safety_path}")
        
        logger.info(f"Returning {len(auditors)} available auditors")
        return auditors


# Singleton instance
_auditor_service = None


def get_auditor_service() -> AuditorService:
    """Get auditor service singleton"""
    global _auditor_service
    if _auditor_service is None:
        _auditor_service = AuditorService()
        logger.info(f"Initialized AuditorService with auditor_repo_path: {_auditor_service.auditor_repo_path}")
    return _auditor_service

