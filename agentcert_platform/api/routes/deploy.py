"""
Deployment API routes
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
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
from ...deployment.deployer import DeploymentService
from ...deployment.secrets_manager import get_secrets_manager

router = APIRouter()

# Deployment service singleton
_deployment_service = None
_initialized_mode = None

def get_deployment_service():
    """
    Get deployment service instance (true singleton).
    
    The service is initialized once based on USE_EC2 at startup.
    It persists across requests to maintain deployment tracking.
    """
    global _deployment_service, _initialized_mode
    
    # Only initialize once - don't re-initialize if mode changes
    # This preserves in-memory deployments across requests
    if _deployment_service is None:
        use_ec2 = os.getenv("USE_EC2", "false").lower() == "true"
        _initialized_mode = use_ec2
        
        if use_ec2:
            ec2_config = {
                "region": os.getenv("AWS_REGION", "us-east-1"),
                "instance_type": os.getenv("EC2_INSTANCE_TYPE", "t3.micro"),
                "key_name": os.getenv("EC2_KEY_NAME", "agentcert-key"),
                "security_group_name": os.getenv("EC2_SG_NAME", "agentcert-agents"),
                "ami_id": os.getenv("EC2_AMI_ID"),  # Optional
                "ssh_key_path": os.getenv("EC2_SSH_KEY_PATH", "~/.ssh/agentcert-key.pem"),
                "subnet_id": os.getenv("EC2_SUBNET_ID"),  # Optional
                "registry_url": os.getenv("NEST_REGISTRY_URL", "http://registry.chat39.com:6900"),  # Default registry
            }
            logger.info(f"🚀 EC2 deployment enabled: {ec2_config}")
            logger.info(f"   USE_EC2={os.getenv('USE_EC2')}")
            _deployment_service = DeploymentService(use_ec2=True, ec2_config=ec2_config)
        else:
            logger.info("💻 Local deployment mode")
            logger.info(f"   USE_EC2={os.getenv('USE_EC2', 'not set')}")
            _deployment_service = DeploymentService(use_ec2=False)
    
    return _deployment_service

# Initialize on module load
deployment_service = get_deployment_service()
secrets_manager = get_secrets_manager()


@router.post("/deploy", response_model=DeployResponse)
async def deploy_agent(request: DeployRequest, background_tasks: BackgroundTasks):
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
        logger.info(f"📦 Deploying agent in {mode} mode")
        
        # Store API keys securely if provided
        agent_id = request.agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        
        if request.api_keys:
            for key_name, key_value in request.api_keys.items():
                secrets_manager.store_secret(agent_id, key_name, key_value)
            logger.info(f"Stored {len(request.api_keys)} API keys for agent {agent_id}")
        
        # Deploy agent (pass agent_id so secrets can be retrieved)
        result = await deployment_service.deploy_agent(
            github_repo=request.github_repo,
            branch=request.branch,
            entry_point=request.entry_point,
            agent_id=agent_id
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
async def get_deployment_status(agent_id: str):
    """Get deployment status for an agent"""
    try:
        deployment_service = get_deployment_service()
        status = await deployment_service.get_deployment_status(agent_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Agent not found: {str(e)}")


@router.delete("/deploy/{agent_id}")
async def undeploy_agent(agent_id: str):
    """
    Undeploy and remove an agent.
    
    For EC2 deployments, this terminates the EC2 instance.
    For local deployments, this stops the agent process.
    """
    try:
        deployment_service = get_deployment_service()
        result = await deployment_service.undeploy_agent(agent_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Undeployment failed: {str(e)}")


@router.get("/deploy")
async def list_deployments():
    """List all deployed agents"""
    try:
        deployment_service = get_deployment_service()
        result = await deployment_service.list_deployments()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list deployments: {str(e)}")

