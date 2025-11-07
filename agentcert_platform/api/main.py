#!/usr/bin/env python3
"""
AgentCert Platform - Main API Server
"""

import os
import logging
from fastapi import FastAPI
from .routes import deploy, test, results

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AgentCert Platform API",
    description="Backend API for AI agent security testing",
    version="1.0.0"
)

# Note: Security features (CORS, authentication, rate limiting) disabled for development
# Add security middleware in production

# Include routers
app.include_router(deploy.router, prefix="/api", tags=["deployment"])
app.include_router(test.router, prefix="/api", tags=["testing"])
app.include_router(results.router, prefix="/api", tags=["results"])


@app.on_event("startup")
async def startup_event():
    """Log deployment configuration on startup"""
    use_ec2 = os.getenv("USE_EC2", "false").lower() == "true"
    
    print("=" * 60)
    print("🚀 AgentCert Platform API Starting")
    print("=" * 60)
    
    if use_ec2:
        print("✅ EC2 Deployment Mode: ENABLED")
        print(f"   USE_EC2={os.getenv('USE_EC2')}")
        print(f"   AWS_REGION={os.getenv('AWS_REGION', 'us-east-1')}")
        print(f"   EC2_INSTANCE_TYPE={os.getenv('EC2_INSTANCE_TYPE', 't3.micro')}")
        print(f"   EC2_KEY_NAME={os.getenv('EC2_KEY_NAME', 'agentcert-key')}")
        print(f"   EC2_SG_NAME={os.getenv('EC2_SG_NAME', 'agentcert-agents')}")
        print(f"   Registry URL={os.getenv('NEST_REGISTRY_URL', 'http://registry.chat39.com:6900')}")
        
        # Verify AWS credentials
        try:
            import boto3
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            print(f"   AWS Account: {identity.get('Account')}")
            print(f"   AWS User/Role: {identity.get('Arn')}")
        except Exception as e:
            print(f"   ⚠️  Warning: AWS credentials check failed: {e}")
    else:
        print("💻 EC2 Deployment Mode: DISABLED (Local mode)")
        print(f"   USE_EC2={os.getenv('USE_EC2', 'not set')}")
        print("   Set USE_EC2=true to enable EC2 deployment")
    
    print("=" * 60)
    
    # Also log via logger
    logger.info("=" * 60)
    logger.info("AgentCert Platform API Starting")
    if use_ec2:
        logger.info("EC2 Deployment Mode: ENABLED")
    else:
        logger.info("EC2 Deployment Mode: DISABLED (Local mode)")
    logger.info("=" * 60)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AgentCert Platform API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


def main():
    """Main entry point for running the API server"""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

