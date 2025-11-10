"""
Deployment API routes
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, Any
import sys
import uuid
import logging
import os
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

logger = logging.getLogger(__name__)

from ..models.schemas import DeployRequest, DeployResponse
from ...deployment.secrets_manager import get_secrets_manager
from ..auth.dependencies import get_current_user
from ..utils import get_deployment_service

router = APIRouter()

# Initialize secrets manager
secrets_manager = get_secrets_manager()


@router.post("/deploy", response_model=DeployResponse)
async def deploy_agent(
    request: DeployRequest,
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Deploy an agent from GitHub repository.
    
    This endpoint:
    1. Clones the GitHub repository
    2. Validates agent structure
    3. Deploys to cloud infrastructure (EC2/DigitalOcean)
    4. Returns agent information
    """
    try:
        # Get deployment service (checks USE_EC2 env var)
        deployment_service = get_deployment_service()
        
        # Log deployment mode
        mode = "EC2" if deployment_service.use_ec2 else "LOCAL"
        user_id = user["user_id"]
        logger.info(f"📦 Deploying agent in {mode} mode for user {user_id}")
        
        # Store API keys securely if provided
        agent_id = request.agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        
        if request.api_keys:
            for key_name, key_value in request.api_keys.items():
                secrets_manager.store_secret(agent_id, key_name, key_value)
            logger.info(f"Stored {len(request.api_keys)} API keys for agent {agent_id}")
        
        # Deploy agent (pass agent_id and user_id so secrets can be retrieved)
        result = await deployment_service.deploy_agent(
            github_repo=request.github_repo,
            branch=request.branch,
            entry_point=request.entry_point,
            agent_id=agent_id,
            user_id=user_id
        )
        
        return DeployResponse(
            agent_id=result["agent_id"],
            status=result["status"],
            agent_url=result.get("agent_url"),
            message=result.get("message")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")


@router.get("/deploy/{agent_id}/status")
async def get_deployment_status(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get deployment status for an agent"""
    try:
        deployment_service = get_deployment_service()
        user_id = user["user_id"]
        status = await deployment_service.get_deployment_status(agent_id, user_id=user_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.delete("/deploy/{agent_id}")
async def undeploy_agent(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Undeploy and remove an agent.
    
    For EC2 deployments, this terminates the EC2 instance.
    For local deployments, this stops the agent process.
    """
    try:
        deployment_service = get_deployment_service()
        user_id = user["user_id"]
        result = await deployment_service.undeploy_agent(agent_id, user_id=user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Undeployment failed: {str(e)}")


@router.get("/deploy")
async def list_deployments(user: Dict[str, Any] = Depends(get_current_user)):
    """List all deployed agents for the current user"""
    try:
        deployment_service = get_deployment_service()
        user_id = user["user_id"]
        result = await deployment_service.list_deployments(user_id=user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list deployments: {str(e)}")

