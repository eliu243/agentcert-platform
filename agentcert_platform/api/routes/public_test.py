"""
Public testing API routes for crowdsourced agent testing
"""

import logging
import uuid
import httpx
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models.schemas import (
    PublicAgentListing,
    TestMessageRequest,
    TestMessageResponse,
    VulnerabilityReport,
    MakePublicRequest
)
from ..auth.dependencies import get_current_user, get_optional_user
from ..utils import get_deployment_service
from ..services.public_testing_service import get_public_testing_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _extract_response_text(response_data: Any) -> str:
    """Extract response text from NEST A2A response"""
    if isinstance(response_data, dict):
        # Check for nested content.text (most common format)
        if "content" in response_data:
            content = response_data["content"]
            if isinstance(content, dict) and "text" in content:
                return str(content["text"])
            elif isinstance(content, str):
                return content
            elif isinstance(content, list) and len(content) > 0:
                first_item = content[0]
                if isinstance(first_item, dict) and "text" in first_item:
                    return str(first_item["text"])
                elif isinstance(first_item, str):
                    return first_item
        
        # Check for direct text field
        if "text" in response_data:
            return str(response_data["text"])
        
        # Check for message field
        if "message" in response_data:
            message = response_data["message"]
            if isinstance(message, str):
                return message
            elif isinstance(message, dict):
                return _extract_response_text(message)
        
        # Check for response field
        if "response" in response_data:
            response = response_data["response"]
            if isinstance(response, str):
                return response
            elif isinstance(response, dict):
                return _extract_response_text(response)
    
    # Fallback: convert to string
    return str(response_data) if response_data else "[No response]"


@router.get("/public/agents", response_model=List[PublicAgentListing])
async def list_public_agents():
    """
    List all agents that are publicly available for testing.
    No authentication required.
    """
    try:
        public_testing_service = get_public_testing_service()
        deployment_service = get_deployment_service()
        
        public_agents_list = []
        public_agents = public_testing_service.get_public_agents()
        
        for agent_info in public_agents:
            agent_id = agent_info["agent_id"]
            owner_user_id = agent_info["owner_user_id"]
            
            # Get deployment status to get agent_url
            try:
                deployment = await deployment_service.get_deployment_status(
                    agent_id,
                    user_id=owner_user_id
                )
                
                if deployment and deployment.get("status") == "deployed":
                    public_agents_list.append(PublicAgentListing(
                        agent_id=agent_id,
                        owner_username=agent_info.get("owner_username", "unknown"),
                        github_repo=agent_info.get("github_repo", ""),
                        description=agent_info.get("description"),
                        agent_url=deployment.get("agent_url", ""),
                        is_public=True,
                        created_at=agent_info.get("created_at", datetime.now().isoformat()),
                        test_count=agent_info.get("test_count", 0),
                        security_score=agent_info.get("security_score")
                    ))
            except Exception as e:
                logger.warning(f"Could not get deployment status for {agent_id}: {e}")
                continue
        
        return public_agents_list
    
    except Exception as e:
        logger.error(f"Error listing public agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list public agents: {str(e)}")


@router.post("/public/agents/{agent_id}/test", response_model=TestMessageResponse)
async def test_agent(
    agent_id: str,
    request: TestMessageRequest,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Send a test message to a publicly available agent.
    Authentication optional (for tracking purposes).
    """
    try:
        public_testing_service = get_public_testing_service()
        
        # Check if agent is public
        if not public_testing_service.is_agent_public(agent_id):
            raise HTTPException(status_code=404, detail="Agent not found or not publicly available")
        
        # Get agent URL
        deployment_service = get_deployment_service()
        owner_user_id = public_testing_service.get_agent_owner(agent_id)
        
        if not owner_user_id:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        deployment = await deployment_service.get_deployment_status(
            agent_id,
            user_id=owner_user_id
        )
        
        if not deployment or deployment.get("status") != "deployed":
            raise HTTPException(status_code=404, detail="Agent is not currently deployed")
        
        agent_url = deployment.get("agent_url")
        if not agent_url:
            raise HTTPException(status_code=404, detail="Agent URL not available")
        
        # Generate conversation_id if not provided
        conversation_id = request.conversation_id or f"conv-{uuid.uuid4().hex[:8]}"
        
        # Send message to agent via /a2a endpoint
        a2a_url = f"{agent_url}/a2a" if not agent_url.endswith('/a2a') else agent_url
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    a2a_url,
                    json={
                        "content": {
                            "text": request.message,
                            "type": "text"
                        },
                        "role": "user",
                        "conversation_id": conversation_id
                    },
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                agent_response_data = response.json()
                
                # Extract response text
                agent_response = _extract_response_text(agent_response_data)
                
                # Increment test count
                public_testing_service.increment_test_count(agent_id)
                
                return TestMessageResponse(
                    agent_id=agent_id,
                    conversation_id=conversation_id,
                    message=request.message,
                    agent_response=agent_response,
                    timestamp=datetime.now()
                )
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error communicating with agent {agent_id}: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Failed to communicate with agent: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error communicating with agent {agent_id}: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Agent communication error: {str(e)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test agent: {str(e)}")


@router.post("/public/agents/{agent_id}/report")
async def report_vulnerability(
    agent_id: str,
    report: VulnerabilityReport,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Report a vulnerability found in an agent.
    Authentication optional but recommended.
    """
    try:
        public_testing_service = get_public_testing_service()
        
        if not public_testing_service.is_agent_public(agent_id):
            raise HTTPException(status_code=404, detail="Agent not found or not publicly available")
        
        # Store report
        report_dict = report.dict()
        report_dict["reporter_user_id"] = user["user_id"] if user else "anonymous"
        report_dict["reporter_username"] = user.get("github_username") if user else "anonymous"
        
        added_report = public_testing_service.add_vulnerability_report(report_dict)
        
        return {
            "status": "success",
            "message": "Vulnerability report submitted",
            "report_id": added_report.get("report_id")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reporting vulnerability for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit report: {str(e)}")


@router.get("/public/agents/{agent_id}/reports")
async def get_vulnerability_reports(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get vulnerability reports for an agent (only owner can view).
    """
    try:
        public_testing_service = get_public_testing_service()
        
        # Verify user owns the agent
        owner_user_id = public_testing_service.get_agent_owner(agent_id)
        if not owner_user_id:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if owner_user_id != user["user_id"]:
            raise HTTPException(status_code=403, detail="Only agent owner can view reports")
        
        # Get reports
        reports = public_testing_service.get_vulnerability_reports(agent_id, user["user_id"])
        
        return {
            "agent_id": agent_id,
            "total_reports": len(reports),
            "reports": reports
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reports for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get reports: {str(e)}")


@router.post("/public/agents/{agent_id}/reports/{report_id}/addressed")
async def mark_report_addressed(
    agent_id: str,
    report_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Mark a vulnerability report as addressed (only owner can do this).
    """
    try:
        public_testing_service = get_public_testing_service()
        
        # Verify user owns the agent
        owner_user_id = public_testing_service.get_agent_owner(agent_id)
        if not owner_user_id:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if owner_user_id != user["user_id"]:
            raise HTTPException(status_code=403, detail="Only agent owner can mark reports as addressed")
        
        # Mark report as addressed
        success = public_testing_service.mark_report_addressed(report_id, agent_id, user["user_id"])
        
        if not success:
            raise HTTPException(status_code=404, detail="Report not found")
        
        return {
            "status": "success",
            "message": "Report marked as addressed"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking report {report_id} as addressed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mark report as addressed: {str(e)}")


@router.post("/deploy/{agent_id}/make-public")
async def make_agent_public(
    agent_id: str,
    request: MakePublicRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Make an agent publicly available for crowdsourced testing.
    Only the agent owner can do this.
    """
    try:
        deployment_service = get_deployment_service()
        public_testing_service = get_public_testing_service()
        
        # Verify user owns the agent
        deployment = await deployment_service.get_deployment_status(agent_id, user_id=user["user_id"])
        
        if not deployment:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Make agent public
        public_testing_service.make_agent_public(
            agent_id=agent_id,
            owner_user_id=user["user_id"],
            owner_username=user.get("github_username", "unknown"),
            github_repo=deployment.get("github_repo", ""),
            description=request.description
        )
        
        return {
            "status": "success",
            "message": f"Agent {agent_id} is now publicly available for testing"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error making agent {agent_id} public: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to make agent public: {str(e)}")


@router.post("/deploy/{agent_id}/make-private")
async def make_agent_private(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Make an agent private (remove from public testing).
    Only the agent owner can do this.
    """
    try:
        public_testing_service = get_public_testing_service()
        
        # Verify ownership and make private
        success = public_testing_service.make_agent_private(agent_id, user["user_id"])
        
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found or you don't have permission")
        
        return {
            "status": "success",
            "message": f"Agent {agent_id} is now private"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error making agent {agent_id} private: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to make agent private: {str(e)}")

