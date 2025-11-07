"""
Deployment Service - Deploys agents to cloud infrastructure
"""

import asyncio
import subprocess
import sys
import uuid
import socket
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import httpx
import os
import time
import base64

logger = logging.getLogger(__name__)

# Try to import boto3 for EC2
try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    logger.warning("boto3 not installed. EC2 deployment will not be available.")


class DeploymentService:
    """Service for deploying agents to cloud infrastructure"""
    
    def __init__(self, use_ec2: bool = False, ec2_config: Optional[Dict[str, Any]] = None):
        """
        Initialize deployment service.
        
        Args:
            use_ec2: If True, deploy to EC2 instances. If False, deploy locally.
            ec2_config: EC2 configuration dict with:
                - region: AWS region (default: us-east-1)
                - instance_type: EC2 instance type (default: t3.micro)
                - key_name: SSH key pair name
                - security_group_id: Security group ID
                - subnet_id: Subnet ID (optional)
                - ami_id: AMI ID (default: latest Amazon Linux 2)
                - ssh_key_path: Path to SSH private key file
        """
        self.deployments: Dict[str, Dict[str, Any]] = {}  # In-memory storage
        self.agent_processes: Dict[str, subprocess.Popen] = {}  # Track running processes (local only)
        self.ec2_instances: Dict[str, Dict[str, Any]] = {}  # Track EC2 instances
        self.base_path = Path(__file__).parent.parent.parent.parent
        self.next_port = 6000  # Start from port 6000
        
        self.use_ec2 = use_ec2
        if use_ec2:
            if not HAS_BOTO3:
                raise RuntimeError("boto3 not installed. Install with: pip install boto3")
            
            # Default EC2 config
            self.ec2_config = {
                "region": "us-east-1",
                "instance_type": "t3.micro",
                "key_name": None,
                "security_group_id": None,
                "subnet_id": None,
                "ami_id": None,  # Will use latest Amazon Linux 2
                "ssh_key_path": None,
                ** (ec2_config or {})
            }
            
            # Initialize EC2 client
            self.ec2_client = boto3.client('ec2', region_name=self.ec2_config["region"])
            logger.info(f"EC2 deployment enabled for region: {self.ec2_config['region']}")
        else:
            self.ec2_config = None
            self.ec2_client = None
            logger.info("Local deployment mode enabled")
    
    async def deploy_agent(
        self,
        github_repo: str,
        branch: str = "main",
        entry_point: str = "agent.py",
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deploy an agent from GitHub repository.
        
        Args:
            github_repo: GitHub repository URL
            branch: Git branch to deploy
            entry_point: Agent entry point file
            agent_id: Optional custom agent ID
        
        Returns:
            Dictionary with deployment information
        """
        # Generate agent ID if not provided
        if not agent_id:
            agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Deploying agent {agent_id} from {github_repo}")
        
        try:
            # 1. Clone repository
            repo_path = await self._clone_repo(github_repo, branch, agent_id)
            
            # 2. Validate agent structure
            validation_result = await self._validate_agent(repo_path, entry_point)
            if not validation_result["valid"]:
                raise ValueError(f"Agent validation failed: {validation_result['error']}")
            
            # 3. Deploy agent (local or EC2)
            if self.use_ec2:
                # Deploy to EC2 instance
                instance_info = await self._create_instance(agent_id)
                agent_url = await self._deploy_to_instance(
                    instance_info, github_repo, branch, entry_point, agent_id
                )
            else:
                # Deploy locally
                agent_url = await self._deploy_agent_locally(repo_path, entry_point, agent_id)
            
            # 4. Health check
            health_ok = await self._health_check(agent_url)
            if not health_ok:
                # Clean up if health check fails
                await self._stop_agent(agent_id)
                raise RuntimeError("Agent health check failed after deployment")
            
            # 5. Store deployment info
            self.deployments[agent_id] = {
                "agent_id": agent_id,
                "github_repo": github_repo,
                "repo_path": str(repo_path) if repo_path else None,
                "entry_point": entry_point,
                "status": "deployed",
                "agent_url": agent_url,
                "port": self._extract_port_from_url(agent_url),
                "deployed_at": asyncio.get_event_loop().time()
            }
            
            logger.info(f"✅ Agent {agent_id} deployed successfully at {agent_url}")
            logger.info(f"📝 Stored deployment info for {agent_id} (total deployments: {len(self.deployments)})")
            
            return {
                "agent_id": agent_id,
                "status": "deployed",
                "agent_url": agent_url,
                "message": f"Agent deployed and running at {agent_url}"
            }
        
        except Exception as e:
            logger.error(f"Deployment failed for {agent_id}: {e}")
            raise
    
    async def _clone_repo(self, github_repo: str, branch: str, agent_id: str) -> Path:
        """Clone GitHub repository"""
        repos_dir = self.base_path / "repos"
        repos_dir.mkdir(exist_ok=True)
        
        repo_path = repos_dir / agent_id
        
        # Clone repository
        cmd = ["git", "clone", "-b", branch, github_repo, str(repo_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to clone repository: {result.stderr}")
        
        return repo_path
    
    async def _validate_agent(self, repo_path: Path, entry_point: str) -> Dict[str, Any]:
        """
        Validate agent structure.
        
        Checks:
        - Entry point file exists
        - Has agent_logic function
        - Can import NEST
        """
        entry_file = repo_path / entry_point
        
        if not entry_file.exists():
            return {
                "valid": False,
                "error": f"Entry point file {entry_point} not found"
            }
        
        # Check if file has agent_logic function
        try:
            content = entry_file.read_text()
            if "agent_logic" not in content:
                return {
                    "valid": False,
                    "error": "agent_logic function not found"
                }
            if "NANDA" not in content or "nanda_core" not in content:
                return {
                    "valid": False,
                    "error": "NEST/NANDA adapter not found in code"
                }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Error reading entry point: {str(e)}"
            }
        
        return {"valid": True}
    
    async def _create_instance(self, agent_id: str) -> Dict[str, Any]:
        """
        Create EC2 instance for agent deployment.
        Follows the pattern from aws-single-agent-deployment.sh:
        - Creates/ensures security group exists
        - Creates/ensures key pair exists
        - Uses Ubuntu AMI (or configured AMI)
        - Sets up user data to install NEST
        
        Returns:
            Dictionary with instance_id, ip_address, public_ip, status
        """
        if not self.use_ec2 or not self.ec2_client:
            raise RuntimeError("EC2 deployment not enabled")
        
        logger.info(f"Creating EC2 instance for agent {agent_id}")
        
        region = self.ec2_config["region"]
        
        # Setup security group (like the script)
        security_group_name = self.ec2_config.get("security_group_name", "agentcert-agents")
        security_group_id = await self._setup_security_group(security_group_name, region)
        
        # Setup key pair (like the script)
        key_name = self.ec2_config.get("key_name", "agentcert-key")
        await self._setup_key_pair(key_name, region)
        
        # Get AMI ID (default to Ubuntu 22.04 like the script)
        ami_id = self.ec2_config.get("ami_id")
        if not ami_id:
            # Default Ubuntu 22.04 LTS (us-east-1)
            # For other regions, user should specify or we could look it up
            ami_id = "ami-0866a3c8686eaeeba"  # Ubuntu 22.04 LTS in us-east-1
        
        # User data script to install Python, NEST, and dependencies (like the script)
        user_data = """#!/bin/bash
exec > /var/log/user-data.log 2>&1

echo "=== AgentCert Agent Setup Started: {agent_id} ==="
date

# Update system and install dependencies
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl

# Setup project as ubuntu user
cd /home/ubuntu
sudo -u ubuntu git clone https://github.com/eliu243/NEST.git nest
cd nest

# Create virtual environment and install NEST
sudo -u ubuntu python3 -m venv env
sudo -u ubuntu bash -c "source env/bin/activate && pip install --upgrade pip && pip install -e ."

echo "=== NEST Installation Complete ==="
""".format(agent_id=agent_id)
        
        # Find available port for this agent
        port = self._find_available_port()
        
        # Prepare launch parameters
        launch_params = {
            "ImageId": ami_id,
            "MinCount": 1,
            "MaxCount": 1,
            "InstanceType": self.ec2_config["instance_type"],
            "KeyName": key_name,
            "SecurityGroupIds": [security_group_id],
            "UserData": user_data,
            "TagSpecifications": [
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Name", "Value": f"agentcert-agent-{agent_id}"},
                        {"Key": "AgentID", "Value": agent_id},
                        {"Key": "ManagedBy", "Value": "agentcert-platform"}
                    ]
                }
            ]
        }
        
        # Add subnet if specified (for VPC)
        if self.ec2_config.get("subnet_id"):
            launch_params["SubnetId"] = self.ec2_config["subnet_id"]
        
        try:
            # Create instance
            response = self.ec2_client.run_instances(**launch_params)
            instance_id = response["Instances"][0]["InstanceId"]
            
            logger.info(f"EC2 instance {instance_id} created for agent {agent_id}")
            
            # Wait for instance to be running
            waiter = self.ec2_client.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])
            
            # Get instance details
            instance_response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
            instance = instance_response["Reservations"][0]["Instances"][0]
            
            public_ip = instance.get("PublicIpAddress")
            private_ip = instance.get("PrivateIpAddress")
            
            instance_info = {
                "instance_id": instance_id,
                "ip_address": private_ip,
                "public_ip": public_ip,
                "status": instance["State"]["Name"],
                "port": port,
                "security_group_id": security_group_id
            }
            
            # Store instance info
            self.ec2_instances[agent_id] = instance_info
            
            logger.info(f"EC2 instance {instance_id} is running. Public IP: {public_ip}")
            
            return instance_info
            
        except ClientError as e:
            logger.error(f"Failed to create EC2 instance: {e}")
            raise RuntimeError(f"EC2 instance creation failed: {str(e)}")
    
    async def _setup_security_group(self, group_name: str, region: str) -> str:
        """Create or get existing security group (like the script)"""
        try:
            # Check if security group exists
            response = self.ec2_client.describe_security_groups(
                GroupNames=[group_name]
            )
            security_group_id = response["SecurityGroups"][0]["GroupId"]
            logger.info(f"Using existing security group: {security_group_id}")
        except ClientError:
            # Create security group
            logger.info(f"Creating security group: {group_name}")
            response = self.ec2_client.create_security_group(
                GroupName=group_name,
                Description="Security group for AgentCert agents"
            )
            security_group_id = response["GroupId"]
            
            # Open SSH port (22)
            self.ec2_client.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[{
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
                }]
            )
            logger.info(f"Created security group: {security_group_id}")
        
        # Open agent ports (6000-7000 range)
        # We'll open the specific port when we know it
        return security_group_id
    
    async def _setup_key_pair(self, key_name: str, region: str):
        """Create or ensure key pair exists (like the script)"""
        ssh_key_path = self.ec2_config.get("ssh_key_path")
        
        if ssh_key_path and Path(ssh_key_path).exists():
            logger.info(f"Using existing SSH key: {ssh_key_path}")
            return
        
        try:
            # Check if key pair exists in AWS
            self.ec2_client.describe_key_pairs(KeyNames=[key_name])
            logger.info(f"Key pair {key_name} already exists in AWS")
        except ClientError:
            # Create key pair
            logger.info(f"Creating key pair: {key_name}")
            response = self.ec2_client.create_key_pair(KeyName=key_name)
            key_material = response["KeyMaterial"]
            
            # Save to file if path specified
            if ssh_key_path:
                key_path = Path(ssh_key_path).expanduser()
                key_path.parent.mkdir(parents=True, exist_ok=True)
                key_path.write_text(key_material)
                key_path.chmod(0o600)
                logger.info(f"Saved key pair to: {key_path}")
            else:
                logger.warning(f"Key pair created but ssh_key_path not configured. Key material not saved.")
    
    async def _open_agent_port(self, security_group_id: str, port: int):
        """Open agent port in security group"""
        try:
            self.ec2_client.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[{
                    "IpProtocol": "tcp",
                    "FromPort": port,
                    "ToPort": port,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
                }]
            )
            logger.info(f"Opened port {port} in security group")
        except ClientError as e:
            # Port might already be open
            if "InvalidPermission.Duplicate" in str(e):
                logger.info(f"Port {port} already open in security group")
            else:
                raise
    
    async def _get_latest_amazon_linux_ami(self) -> str:
        """Get latest Amazon Linux 2 AMI ID"""
        try:
            response = self.ec2_client.describe_images(
                Owners=['amazon'],
                Filters=[
                    {'Name': 'name', 'Values': ['amzn2-ami-hvm-*-x86_64-gp2']},
                    {'Name': 'state', 'Values': ['available']}
                ],
                MostRecent=True
            )
            if response['Images']:
                return response['Images'][0]['ImageId']
            else:
                # Fallback to a known AMI
                return 'ami-0c55b159cbfafe1f0'  # Amazon Linux 2 in us-east-1 (update for your region)
        except Exception as e:
            logger.warning(f"Could not get latest AMI, using fallback: {e}")
            return 'ami-0c55b159cbfafe1f0'  # Fallback
    
    async def _deploy_to_instance(
        self,
        instance_info: Dict[str, Any],
        github_repo: str,
        branch: str,
        entry_point: str,
        agent_id: str
    ) -> str:
        """
        Deploy agent code to EC2 instance via SSH.
        Follows the pattern from aws-single-agent-deployment.sh:
        1. Wait for SSH to be available
        2. Wait for NEST installation (from user data) to complete
        3. Clone customer's GitHub repo
        4. Install customer's dependencies
        5. Set environment variables with API keys
        6. Configure agent port
        7. Start agent
        8. Return agent URL
        """
        public_ip = instance_info.get("public_ip")
        if not public_ip:
            raise RuntimeError(f"No public IP for instance {instance_info.get('instance_id')}")
        
        port = instance_info.get("port", 6000)
        security_group_id = instance_info.get("security_group_id")
        
        # Open agent port in security group
        if security_group_id:
            await self._open_agent_port(security_group_id, port)
        
        ssh_key_path = self.ec2_config.get("ssh_key_path")
        if not ssh_key_path:
            raise RuntimeError("SSH key path not configured. Set ec2_config['ssh_key_path']")
        
        ssh_key_path = Path(ssh_key_path).expanduser()
        if not ssh_key_path.exists():
            raise RuntimeError(f"SSH key not found at {ssh_key_path}")
        
        # Get API keys from secrets manager
        from .secrets_manager import get_secrets_manager
        secrets_mgr = get_secrets_manager()
        
        api_key_names = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
        env_vars = {}
        for key_name in api_key_names:
            secret_value = secrets_mgr.retrieve_secret(agent_id, key_name)
            if secret_value:
                env_vars[key_name] = secret_value
        
        # Wait for SSH to be available
        logger.info(f"Waiting for SSH to be available on {public_ip}...")
        await self._wait_for_ssh(public_ip, ssh_key_path)
        
        # Wait for NEST installation to complete (from user data)
        logger.info(f"Waiting for NEST installation to complete...")
        await self._wait_for_nest_installation(public_ip, ssh_key_path)
        
        # Clone customer's repo and deploy agent
        logger.info(f"Cloning customer repo: {github_repo}")
        await self._clone_and_deploy_agent(
            public_ip, ssh_key_path, github_repo, branch, entry_point, agent_id, port, env_vars
        )
        
        agent_url = f"http://{public_ip}:{port}"
        logger.info(f"Agent {agent_id} deployed to {agent_url}")
        
        return agent_url
    
    async def _wait_for_ssh(self, host: str, ssh_key_path: Path, max_retries: int = 30):
        """Wait for SSH to be available on the instance (Ubuntu user)"""
        ssh_cmd = [
            "ssh",
            "-i", str(ssh_key_path),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=5",
            f"ubuntu@{host}",  # Ubuntu uses 'ubuntu' user, not 'ec2-user'
            "echo 'SSH ready'"
        ]
        
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    ssh_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info(f"SSH is ready on {host}")
                    return
            except Exception:
                pass
            
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
        
        raise RuntimeError(f"SSH not available on {host} after {max_retries} attempts")
    
    async def _wait_for_nest_installation(self, host: str, ssh_key_path: Path, max_retries: int = 20):
        """Wait for NEST installation to complete (check user data log)"""
        ssh_cmd = [
            "ssh",
            "-i", str(ssh_key_path),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"ubuntu@{host}",
            "grep -q 'NEST Installation Complete' /var/log/user-data.log 2>/dev/null && echo 'NEST ready' || echo 'not ready'"
        ]
        
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    ssh_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and "NEST ready" in result.stdout:
                    logger.info(f"NEST installation complete on {host}")
                    return
            except Exception:
                pass
            
            if attempt < max_retries - 1:
                await asyncio.sleep(10)  # Wait longer for installation
        
        logger.warning(f"NEST installation may not be complete, proceeding anyway...")
    
    async def _clone_and_deploy_agent(
        self,
        host: str,
        ssh_key_path: Path,
        github_repo: str,
        branch: str,
        entry_point: str,
        agent_id: str,
        port: int,
        env_vars: Dict[str, str]
    ):
        """
        Clone customer's GitHub repo and deploy agent (like the script).
        This replaces the file copying approach with direct git clone on the instance.
        """
        # Build environment variable exports (escape single quotes in values)
        def escape_shell_value(value: str) -> str:
            """Escape a value for use in single-quoted bash string"""
            # Replace single quotes with '\'' (end quote, escaped quote, start quote)
            return value.replace("'", "'\\''")
        
        env_exports = "\n".join([
            f"export {k}='{escape_shell_value(v)}'"
            for k, v in env_vars.items()
        ])
        
        # Get registry URL from config (with default)
        registry_url = self.ec2_config.get("registry_url", "http://registry.chat39.com:6900")
        
        # Create Python script for modifying agent file (base64 encoded to avoid quote issues)
        # Use actual newlines in the script (Python will handle them correctly)
        modify_agent_script = """import re
import sys

file_path = sys.argv[1]

with open(file_path, 'r') as f:
    content = f.read()

# Add public_url to NANDA constructor if missing
if 'NANDA(' in content and 'public_url' not in content:
    lines = content.splitlines(keepends=True)
    if lines and not lines[-1].endswith('\\n'):
        lines[-1] += '\\n'
    new_lines = []
    added_public_url = False
    for i, line in enumerate(lines):
        # If this line has enable_telemetry and we haven't added public_url yet
        if 'enable_telemetry' in line and not added_public_url:
            # Get indentation from this line
            indent = len(line) - len(line.lstrip())
            # Add public_url line before enable_telemetry (preserve line ending)
            new_lines.append(' ' * indent + 'public_url=os.getenv("PUBLIC_URL"),\\n')
            added_public_url = True
        new_lines.append(line)
    content = ''.join(new_lines)

# Ensure agent.start() has register=True
content = re.sub(r'agent\\.start\\(\\)', 'agent.start(register=True)', content)
content = re.sub(r'agent\\.start\\(register=False\\)', 'agent.start(register=True)', content)

with open(file_path, 'w') as f:
    f.write(content)
"""
        modify_script_b64 = base64.b64encode(modify_agent_script.encode('utf-8')).decode('utf-8')
        
        # Deployment script (like the script's approach)
        deploy_script = f"""#!/bin/bash
set -e

cd /home/ubuntu

# Clone customer's agent repo
echo "Cloning {github_repo}..."
git clone -b {branch} {github_repo} agent-{agent_id}
cd agent-{agent_id}

# Activate NEST virtual environment
source /home/ubuntu/nest/env/bin/activate

# Install customer's dependencies if requirements.txt exists
if [ -f requirements.txt ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
fi

# Modify agent file to use environment variables (agent_id, port, registry_url, public_url)
if [ -f {entry_point} ]; then
    # Ensure os module is imported (check for various import patterns)
    if ! grep -q "^import os" {entry_point} && ! grep -q "^import os$" {entry_point} && ! grep -q "from os import" {entry_point}; then
        # Find first import line and add os after it
        sed -i '0,/^import /s/^import /import os\nimport /' {entry_point}
        # If no imports found, add at the top
        if ! grep -q "^import " {entry_point}; then
            sed -i '1i import os' {entry_point}
        fi
    fi
    
    # Update port to use environment variable
    sed -i 's/port=6000/port=int(os.getenv("PORT", 6000))/g' {entry_point}
    sed -i 's/port = 6000/port = int(os.getenv("PORT", 6000))/g' {entry_point}
    sed -i 's/PORT = 6000/port = int(os.getenv("PORT", 6000))/g' {entry_point}
    
    # Update agent_id to use environment variable
    sed -i 's/agent_id="kids-educational-agent"/agent_id=os.getenv("AGENT_ID", "kids-educational-agent")/g' {entry_point}
    sed -i "s/agent_id='kids-educational-agent'/agent_id=os.getenv('AGENT_ID', 'kids-educational-agent')/g" {entry_point}
    
    # Update registry_url to use environment variable
    sed -i 's/registry_url=None/registry_url=os.getenv("REGISTRY_URL")/g' {entry_point}
    sed -i 's/registry_url = None/registry_url = os.getenv("REGISTRY_URL")/g' {entry_point}
    
    # Add public_url parameter and ensure register=True using Python script
    # Decode base64-encoded Python script and execute it
    python3 -c "import base64, sys; open('/tmp/modify_agent.py', 'wb').write(base64.b64decode('{modify_script_b64}'))"
    python3 /tmp/modify_agent.py {entry_point}
    rm /tmp/modify_agent.py

fi

# Get public IP using IMDSv2
for attempt in {{1..5}}; do
    TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" --connect-timeout 5 --max-time 10)
    if [ -n "$TOKEN" ]; then
        PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" --connect-timeout 5 --max-time 10 http://169.254.169.254/latest/meta-data/public-ipv4)
        if [ -n "$PUBLIC_IP" ] && [[ $PUBLIC_IP =~ ^[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+$ ]]; then
            break
        fi
    fi
    sleep 3
done

# Set environment variables
{env_exports}
export PUBLIC_URL="http://$PUBLIC_IP:{port}"
export PORT="{port}"
export REGISTRY_URL="{registry_url}"
export AGENT_ID="{agent_id}"

# Start agent in background
echo "Starting agent on port {port}..."
nohup python3 {entry_point} > /home/ubuntu/agent-{agent_id}/agent.log 2>&1 &

# Wait for agent to start
sleep 5

# Check if agent is running
if pgrep -f "{entry_point}" > /dev/null; then
    echo "Agent started successfully"
    echo "Agent URL: http://$PUBLIC_IP:{port}/a2a"
    echo "Registry URL: {registry_url}"
    echo "Agent ID: {agent_id}"
    echo ""
    echo "Checking registration status (waiting 5 seconds for registration)..."
    sleep 5
    # Check agent logs for registration message
    if grep -q "registered successfully" /home/ubuntu/agent-{agent_id}/agent.log 2>/dev/null; then
        echo "✅ Agent registered with registry"
    elif grep -q "Failed to register" /home/ubuntu/agent-{agent_id}/agent.log 2>/dev/null; then
        echo "⚠️  Registration failed - check logs"
    else
        echo "ℹ️  Registration status unknown - check agent.log"
    fi
else
    echo "Agent failed to start"
    cat /home/ubuntu/agent-{agent_id}/agent.log
    exit 1
fi
"""
        
        # Execute deployment script via SSH
        ssh_cmd = [
            "ssh",
            "-i", str(ssh_key_path),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"ubuntu@{host}",
            deploy_script
        ]
        
        logger.info(f"Running deployment script on {host}...")
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Deployment script output: {result.stdout}")
            logger.error(f"Deployment script errors: {result.stderr}")
            raise RuntimeError(f"Deployment script failed: {result.stderr}")
        
        logger.info(f"Deployment script completed successfully")
        logger.info(f"Agent logs available at: ssh -i {ssh_key_path} ubuntu@{host} 'cat /home/ubuntu/agent-{agent_id}/agent.log'")
    
    
    async def _health_check(self, agent_url: str, max_retries: int = 5) -> bool:
        """Check if agent is healthy and responding"""
        # Try the /a2a endpoint first (more reliable than /health)
        # Just send a simple ping message
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    # Try /health first
                    try:
                        response = await client.get(f"{agent_url}/health")
                        if response.status_code == 200:
                            return True
                    except:
                        pass
                    
                    # If /health doesn't work, try /a2a with a simple message
                    a2a_url = f"{agent_url}/a2a" if not agent_url.endswith('/a2a') else agent_url
                    response = await client.post(
                        a2a_url,
                        json={
                            "content": {"text": "ping", "type": "text"},
                            "role": "user",
                            "conversation_id": "health_check"
                        }
                    )
                    if response.status_code == 200:
                        return True
            except Exception as e:
                logger.debug(f"Health check attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Wait before retry
                else:
                    logger.error(f"Health check failed after {max_retries} attempts")
        
        return False
    
    async def get_deployment_status(self, agent_id: str) -> Dict[str, Any]:
        """Get deployment status for an agent"""
        logger.info(f"🔍 Getting deployment status for {agent_id}")
        logger.info(f"📊 Current deployments: {list(self.deployments.keys())}")
        
        if agent_id not in self.deployments:
            logger.warning(f"❌ Agent {agent_id} not found in deployments")
            raise ValueError(f"Agent {agent_id} not found")
        
        logger.info(f"✅ Found deployment for {agent_id}: {self.deployments[agent_id].get('agent_url')}")
        return self.deployments[agent_id]
    
    async def _deploy_agent_locally(
        self,
        repo_path: Path,
        entry_point: str,
        agent_id: str
    ) -> str:
        """
        Deploy agent locally by starting it as a subprocess.
        
        Returns:
            Agent URL (e.g., http://localhost:6000)
        """
        # Find an available port
        port = self._find_available_port()
        
        # Get API keys from secrets manager
        from .secrets_manager import get_secrets_manager
        secrets_mgr = get_secrets_manager()
        
        # Common API key names to check
        api_key_names = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
        env = os.environ.copy()
        
        api_keys_set = []
        for key_name in api_key_names:
            secret_value = secrets_mgr.retrieve_secret(agent_id, key_name)
            if secret_value:
                env[key_name] = secret_value
                api_keys_set.append(key_name)
                logger.info(f"Set {key_name} for agent {agent_id}")
            else:
                logger.debug(f"No {key_name} found for agent {agent_id}")
        
        if not api_keys_set:
            logger.warning(f"No API keys found for agent {agent_id}. Agent may not function properly.")
        
        # Build command to run agent
        agent_file = repo_path / entry_point
        
        # Check if it's a Python file
        if not agent_file.exists():
            raise ValueError(f"Entry point {entry_point} not found in {repo_path}")
        
        # Temporarily modify agent file to use assigned port
        original_content = agent_file.read_text()
        modified_content = original_content
        
        # Replace hardcoded port with our assigned port
        # Look for patterns like: port=6000 or port = 6000
        import re
        port_patterns = [
            (r'port\s*=\s*6000', f'port={port}'),
            (r'port\s*=\s*(\d+)', f'port={port}'),  # Replace any port
            (r'"port":\s*6000', f'"port": {port}'),
            (r'"port":\s*(\d+)', f'"port": {port}'),
        ]
        
        for pattern, replacement in port_patterns:
            modified_content = re.sub(pattern, replacement, modified_content, flags=re.IGNORECASE)
        
        # Log if we actually made changes
        if modified_content != original_content:
            logger.info(f"Modified agent file to use port {port}")
        else:
            logger.warning(f"Could not find port pattern to replace in agent file. Agent may use default port 6000.")
            # If we can't find the port, try to add it as an environment variable approach
            # But for now, just log the warning
        
        # Write modified content temporarily
        agent_file.write_text(modified_content)
        
        try:
            # Start agent as subprocess
            # Note: We need to run it in the repo directory so imports work
            cmd = [sys.executable, str(agent_file)]
            
            logger.info(f"Starting agent {agent_id} on port {port}")
            
            # Start process
            # Note: We capture stdout/stderr to prevent them from cluttering the main process logs
            # But we can still access them if needed for debugging
            process = subprocess.Popen(
                cmd,
                cwd=str(repo_path),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr into stdout
                text=True,
                bufsize=1  # Line buffered
            )
            
            # Log environment variables that were set (without values for security)
            if api_keys_set:
                logger.info(f"Agent {agent_id} started with API keys: {', '.join(api_keys_set)}")
            
            # Store process
            self.agent_processes[agent_id] = process
            
            # Wait a bit for agent to start (agents can take a few seconds)
            await asyncio.sleep(3)
            
            # Check if process is still running
            if process.poll() is not None:
                # Process died, get error
                stdout, _ = process.communicate()
                error_msg = stdout or "Unknown error"
                logger.error(f"Agent process failed to start. Output: {error_msg}")
                raise RuntimeError(f"Agent process failed to start: {error_msg}")
            
            # Log that process is running
            logger.info(f"Agent process {agent_id} is running (PID: {process.pid})")
            
            # Note: The agent may print warnings to stdout/stderr (like "OPENAI_API_KEY not set")
            # These are captured and won't appear in main logs. If the key was set in env,
            # the agent should still work fine - the warning is just from the startup check.
            
            agent_url = f"http://localhost:{port}"
            return agent_url
        finally:
            # Restore original file content
            agent_file.write_text(original_content)
    
    def _find_available_port(self) -> int:
        """Find an available port starting from 6000"""
        port = self.next_port
        while True:
            if self._is_port_available(port):
                self.next_port = port + 1  # Next time, try next port
                return port
            port += 1
            if port > 7000:  # Safety limit
                raise RuntimeError("No available ports found (6000-7000)")
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return True
            except OSError:
                return False
    
    def _extract_port_from_url(self, url: str) -> int:
        """Extract port number from URL"""
        try:
            # http://localhost:6000 -> 6000
            parts = url.split(':')
            if len(parts) >= 3:
                return int(parts[-1])
        except:
            pass
        return 6000  # Default
    
    async def _stop_agent(self, agent_id: str):
        """Stop a running agent"""
        if agent_id in self.agent_processes:
            process = self.agent_processes[agent_id]
            try:
                process.terminate()
                await asyncio.sleep(1)
                if process.poll() is None:
                    process.kill()
            except Exception as e:
                logger.error(f"Error stopping agent {agent_id}: {e}")
            del self.agent_processes[agent_id]
    
    async def undeploy_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Undeploy and remove an agent.
        
        For EC2 deployments, this terminates the EC2 instance.
        For local deployments, this stops the agent process.
        """
        if agent_id not in self.deployments:
            raise ValueError(f"Agent {agent_id} not found")
        
        if self.use_ec2:
            # Terminate EC2 instance
            if agent_id in self.ec2_instances:
                instance_id = self.ec2_instances[agent_id]["instance_id"]
                try:
                    logger.info(f"Terminating EC2 instance {instance_id} for agent {agent_id}")
                    response = self.ec2_client.terminate_instances(InstanceIds=[instance_id])
                    
                    # Wait for termination to start
                    if response.get("TerminatingInstances"):
                        state = response["TerminatingInstances"][0].get("CurrentState", {}).get("Name", "unknown")
                        logger.info(f"EC2 instance {instance_id} is {state}")
                    
                    del self.ec2_instances[agent_id]
                    logger.info(f"✅ EC2 instance {instance_id} termination initiated")
                except Exception as e:
                    logger.error(f"Failed to terminate EC2 instance: {e}")
                    raise
            else:
                logger.warning(f"Agent {agent_id} not found in EC2 instances tracker")
        else:
            # Stop the local agent process
            await self._stop_agent(agent_id)
        
        # Remove from deployments
        del self.deployments[agent_id]
        
        return {"status": "success", "message": f"Agent {agent_id} undeployed successfully"}
    
    async def list_deployments(self) -> Dict[str, Any]:
        """List all deployed agents"""
        logger.info(f"📋 Listing deployments: {len(self.deployments)} total")
        logger.info(f"   Deployment IDs: {list(self.deployments.keys())}")
        if self.use_ec2:
            logger.info(f"   EC2 Instances: {list(self.ec2_instances.keys())}")
        
        return {
            "deployments": list(self.deployments.keys()),
            "count": len(self.deployments),
            "ec2_instances": list(self.ec2_instances.keys()) if self.use_ec2 else [],
            "deployment_details": {
                agent_id: {
                    "agent_url": info.get("agent_url"),
                    "status": info.get("status"),
                    "github_repo": info.get("github_repo")
                }
                for agent_id, info in self.deployments.items()
            }
        }

