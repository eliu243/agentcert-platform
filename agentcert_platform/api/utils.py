"""
Shared utilities for API routes
"""

import os
import logging
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from agentcert_platform.deployment.deployer import DeploymentService

logger = logging.getLogger(__name__)

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

