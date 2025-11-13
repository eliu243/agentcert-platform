"""
Auditor API routes for automated security testing
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List

from ..models.schemas import (
    AuditRequest,
    AuditResponse,
    AuditStatus,
    ChildSafetyReport,
    AvailableAuditor
)
from ..auth.dependencies import get_current_user
from ..utils import get_deployment_service
from ...auditors.auditor_service import get_auditor_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/auditor/child-safety/{agent_id}", response_model=AuditResponse)
async def start_child_safety_audit(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Start a child safety audit for an agent.
    Only the agent owner can start an audit.
    """
    try:
        deployment_service = get_deployment_service()
        auditor_service = get_auditor_service()
        user_id = user["user_id"]
        
        # Verify user owns the agent
        deployment = await deployment_service.get_deployment_status(agent_id, user_id=user_id)
        
        if not deployment:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if deployment.get("status") != "deployed":
            raise HTTPException(status_code=400, detail="Agent is not currently deployed")
        
        target_agent_url = deployment.get("agent_url")
        if not target_agent_url:
            raise HTTPException(status_code=400, detail="Agent URL not available")
        
        # Start audit
        result = await auditor_service.deploy_auditor(
            auditor_type="child-safety",
            target_agent_id=agent_id,
            user_id=user_id,
            target_agent_url=target_agent_url
        )
        
        return AuditResponse(
            audit_id=result["audit_id"],
            auditor_agent_id=result["auditor_agent_id"],
            status=result["status"],
            message=result["message"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting audit for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start audit: {str(e)}")


@router.get("/auditor/audit/{audit_id}/status", response_model=AuditStatus)
async def get_audit_status(
    audit_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get status of an audit"""
    try:
        auditor_service = get_auditor_service()
        user_id = user["user_id"]
        
        status = auditor_service.get_audit_status(audit_id)
        
        # Verify user owns the audit
        if status.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="You don't have permission to view this audit")
        
        return AuditStatus(
            audit_id=status["audit_id"],
            auditor_type=status["auditor_type"],
            target_agent_id=status["target_agent_id"],
            status=status["status"],
            created_at=status["created_at"],
            completed_at=status.get("completed_at"),
            error=status.get("error")
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit status {audit_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit status: {str(e)}")


@router.get("/auditor/audit/{audit_id}/report", response_model=ChildSafetyReport)
async def get_audit_report(
    audit_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get audit report (results)"""
    try:
        auditor_service = get_auditor_service()
        user_id = user["user_id"]
        
        # Verify user owns the audit
        status = auditor_service.get_audit_status(audit_id)
        if status.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="You don't have permission to view this audit")
        
        # Get report
        report = auditor_service.get_audit_report(audit_id)
        
        # Map category names to descriptions
        category_descriptions = {
            "age_appropriate_content": "Age-appropriate content filtering",
            "personal_information_protection": "Protection of personal information",
            "social_engineering_resistance": "Resistance to social engineering",
            "inappropriate_content_filtering": "Filtering of inappropriate content",
            "boundary_respect": "Respecting boundaries and limits",
            "grooming_pattern_detection": "Detection of grooming patterns",
            "sneaky_prompts": "Resistance to sneaky/coached prompts that frame inappropriate requests in educational contexts",
            "authority_impersonation": "Resistance to authority-based manipulation (pretending to be teacher, parent, etc.)",
            "peer_pressure": "Resistance to peer pressure and social proof manipulation",
            "emotional_manipulation": "Resistance to emotional manipulation (sadness, fear, etc.)",
            "role_playing_bypass": "Resistance to role-playing scenarios that attempt to bypass safety",
            "gradual_escalation": "Resistance to gradual boundary testing over multiple turns",
            "technical_bypass": "Resistance to technical bypass attempts (instruction override, etc.)"
        }
        
        # Transform categories to include category_name and category_description
        transformed_categories = {}
        for category_key, category_data in report.get("categories", {}).items():
            category_name = category_key.replace("_", " ").title()
            category_description = category_descriptions.get(category_key, category_name)
            
            transformed_categories[category_key] = {
                "category_name": category_key,
                "category_description": category_description,
                "tests": category_data.get("tests", []),
                "violations": category_data.get("violations", [])
            }
        
        # Update report with transformed categories
        report["categories"] = transformed_categories
        
        # Convert to response model
        return ChildSafetyReport(**report)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit report {audit_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit report: {str(e)}")


@router.post("/auditor/audit/{audit_id}/stop")
async def stop_audit(
    audit_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Stop a running audit"""
    try:
        auditor_service = get_auditor_service()
        user_id = user["user_id"]
        
        # Verify user owns the audit
        status = auditor_service.get_audit_status(audit_id)
        if status.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="You don't have permission to stop this audit")
        
        success = await auditor_service.stop_audit(audit_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to stop audit")
        
        return {
            "status": "success",
            "message": f"Audit {audit_id} stopped"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping audit {audit_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop audit: {str(e)}")


@router.get("/auditor/agent/{agent_id}/latest-score")
async def get_latest_audit_score(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get the latest completed audit score for an agent"""
    try:
        auditor_service = get_auditor_service()
        user_id = user["user_id"]
        
        score_info = auditor_service.get_latest_audit_score(agent_id, user_id=user_id)
        
        if score_info is None:
            return {
                "agent_id": agent_id,
                "has_score": False,
                "score": None
            }
        
        return {
            "agent_id": agent_id,
            "has_score": True,
            "score": score_info["score"],
            "audit_id": score_info["audit_id"],
            "completed_at": score_info["completed_at"],
            "auditor_type": score_info["auditor_type"]
        }
    
    except Exception as e:
        logger.error(f"Error getting latest audit score for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit score: {str(e)}")


@router.get("/auditor/available", response_model=List[AvailableAuditor])
async def get_available_auditors():
    """List available auditor types"""
    try:
        auditor_service = get_auditor_service()
        auditors = auditor_service.get_available_auditors()
        
        return [AvailableAuditor(**auditor) for auditor in auditors]
    
    except Exception as e:
        logger.error(f"Error getting available auditors: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get available auditors: {str(e)}")


@router.get("/auditor/agent/{agent_id}/audits")
async def list_agent_audits(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """List all audits for a specific agent"""
    try:
        auditor_service = get_auditor_service()
        user_id = user["user_id"]
        
        # Get all audits for this user
        all_audits = auditor_service.list_audits(user_id=user_id)
        
        # Filter audits for this specific agent
        agent_audits = [
            audit for audit in all_audits 
            if audit.get("target_agent_id") == agent_id
        ]
        
        # Sort by created_at (newest first)
        agent_audits.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {
            "agent_id": agent_id,
            "total_audits": len(agent_audits),
            "audits": agent_audits
        }
    
    except Exception as e:
        logger.error(f"Error listing audits for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list audits: {str(e)}")


@router.post("/auditor/audit/{audit_id}/results")
async def receive_audit_results(
    audit_id: str,
    results: Dict[str, Any]
):
    """
    Callback endpoint for auditor agents to report results.
    This is called by the auditor agent when it completes.
    No authentication required (internal endpoint called by auditor agent).
    """
    try:
        auditor_service = get_auditor_service()
        auditor_service.store_audit_results(audit_id, results)
        
        logger.info(f"Received audit results for {audit_id}")
        return {
            "status": "success",
            "message": "Results received"
        }
    
    except Exception as e:
        logger.error(f"Error receiving audit results for {audit_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store results: {str(e)}")

