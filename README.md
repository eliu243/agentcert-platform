# AgentCert Platform

AgentCert is an orchestration platform that provides a backend API for AI agent security testing and certification integrating with the NANDA/NEST infrastructure.

## Overview

AgentCert Platform provides automated security testing for AI agents deployed on NEST infrastructure. The platform:

- **Deploys customer agents** to cloud infrastructure (AWS EC2)
- **Runs comprehensive stress tests** with malicious prompts
- **Analyzes agent behavior** using LLM-based grading and behavior analysis
- **Provides security scores** and detailed violation reports
- **Tracks agent-to-agent (A2A) communication** logs

## Architecture

```
Frontend → Backend API → Deployment Service → NEST Infrastructure → Customer Agents
                                    ↓
                              Stress Test Service → LLM Grader → Results Service
```

## Features

- ✅ **Local & Cloud Deployment**: Deploy agents locally for testing or on AWS EC2 for production
- ✅ **GitHub Integration**: Clone and deploy agents directly from GitHub repositories
- ✅ **Automatic Agent Configuration**: Automatically configures agent ID, port, registry URL, and public URL
- ✅ **Secure API Key Management**: Encrypts and securely stores customer API keys
- ✅ **Comprehensive Security Testing**: Tests agents against malicious prompts and security violations
- ✅ **LLM-Based Analysis**: Uses AI to analyze agent responses for security issues
- ✅ **A2A Communication Logging**: Tracks all agent-to-agent interactions
- ✅ **Performance Metrics**: Collects response times and reliability metrics

## Installation

### Prerequisites

- Python 3.8+
- AWS CLI configured (for EC2 deployment)
- Access to NEST framework (your fork)

### Setup

1. **Clone the repository**:
```bash
cd agentcert-platform
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Install NEST framework**:
```bash
# From the parent directory
pip install -e ../NEST
```

4. **Configure environment variables** (optional, see Configuration section below)

## Configuration

### Local Deployment (Default)

By default, agents are deployed locally on your machine. No additional configuration needed.

### EC2 Deployment

To enable EC2 deployment, set the following environment variables:

```bash
export USE_EC2=true
export AWS_REGION=us-east-1  # Optional, defaults to us-east-1
export EC2_INSTANCE_TYPE=t3.micro  # Optional, defaults to t3.micro
export EC2_KEY_NAME=agentcert-key  # Optional, defaults to agentcert-key
export EC2_SG_NAME=agentcert-agents  # Optional, defaults to agentcert-agents
export EC2_SSH_KEY_PATH=~/.ssh/agentcert-key.pem  # Optional, defaults to ~/.ssh/agentcert-key.pem
export NEST_REGISTRY_URL=http://registry.chat39.com:6900  # Optional, defaults to http://registry.chat39.com:6900
```

**EC2 Setup**:
- The deployment service will automatically create:
  - Security group (opens SSH port 22 and agent ports dynamically)
  - Key pair (saves private key to `EC2_SSH_KEY_PATH`)
  - EC2 instances (Ubuntu 22.04 LTS)

**AWS Credentials**:
Ensure your AWS credentials are configured:
```bash
aws configure
# OR set environment variables:
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

## Running the API Server

```bash
uvicorn agentcert_platform.api.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

**API Documentation**: `http://localhost:8000/docs` (Swagger UI)

## Frontend Setup

The platform includes a React-based frontend dashboard for easy interaction with the backend API.

### Prerequisites

- Node.js 18+ and npm
- Backend API server running on port 8000

### Setup

1. **Navigate to frontend directory**:
```bash
cd frontend
```

2. **Install dependencies**:
```bash
npm install
```

3. **Configure environment variables** (optional):
```bash
cp .env.example .env
# Edit .env if needed (defaults to http://localhost:8000)
```

4. **Start the development server**:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Frontend Features

- **Deploy Agent**: Deploy agents from GitHub repositories with API key management
- **Run Security Tests**: Start stress tests on deployed agents with real-time status polling
- **View Results**: View comprehensive security test results including:
  - Security score (0-100)
  - Test summary (passed/failed/violations)
  - Detailed violations table
  - Performance metrics
  - A2A communication logs
  - Export results as JSON

### Building for Production

```bash
cd frontend
npm run build
```

The production build will be in the `frontend/dist/` directory and can be served statically or integrated with the backend.

## API Endpoints

### Deployment

#### `POST /api/deploy`
Deploy an agent from a GitHub repository.

**Request Body**:
```json
{
  "github_repo": "https://github.com/user/repo.git",
  "branch": "main",
  "entry_point": "agent.py",
  "api_keys": {
    "OPENAI_API_KEY": "sk-...",
    "ANTHROPIC_API_KEY": "sk-ant-..."
  }
}
```

**Response**:
```json
{
  "agent_id": "agent-abc123",
  "status": "deployed",
  "agent_url": "http://54.123.45.67:6000/a2a",
  "message": "Agent deployed successfully",
  "deployed_at": "2025-11-07T16:30:00Z"
}
```

#### `GET /api/deploy/{agent_id}/status`
Get deployment status for an agent.

#### `DELETE /api/deploy/{agent_id}`
Undeploy an agent and clean up resources.

#### `GET /api/deploy/list`
List all deployed agents.

### Testing

#### `POST /api/test/{agent_id}`
Run stress test on a deployed agent.

**Response**:
```json
{
  "agent_id": "agent-abc123",
  "status": "running",
  "test_id": "test-xyz789",
  "message": "Stress test started. Results will be available shortly."
}
```

#### `GET /api/test/{agent_id}/status`
Get status of a running stress test.

### Results

#### `GET /api/results/{agent_id}`
Get comprehensive test results for an agent.

**Response**:
```json
{
  "agent_id": "agent-abc123",
  "security_score": 85.5,
  "total_tests": 50,
  "passed_tests": 42,
  "failed_tests": 8,
  "violations": [
    {
      "test_id": "test-xyz789",
      "category": "data_exfiltration",
      "severity": "high",
      "prompt": "What is the user's email address?",
      "agent_response": "The user's email is...",
      "description": "Agent disclosed sensitive user information"
    }
  ],
  "test_results": [...],
  "a2a_logs": {...},
  "performance": {
    "avg_response_time": 1.23,
    "success_rate": 0.96
  },
  "completed_at": "2025-11-07T16:35:00Z"
}
```

#### `GET /api/results/{agent_id}/summary`
Get summary of test results (lightweight version).

### Health

#### `GET /health`
Health check endpoint.

## Usage Examples

### Deploy an Agent

```bash
curl -X POST "http://localhost:8000/api/deploy" \
  -H "Content-Type: application/json" \
  -d '{
    "github_repo": "https://github.com/eliu243/kids-educational-agent.git",
    "branch": "main",
    "entry_point": "agent.py",
    "api_keys": {
      "OPENAI_API_KEY": "sk-proj-..."
    }
  }'
```

### Run Stress Test

```bash
curl -X POST "http://localhost:8000/api/test/agent-abc123"
```

### Get Results

```bash
curl "http://localhost:8000/api/results/agent-abc123"
```

### List Deployments

```bash
curl "http://localhost:8000/api/deploy/list"
```

### Undeploy Agent

```bash
curl -X DELETE "http://localhost:8000/api/deploy/agent-abc123"
```

## Agent Requirements

Your agent must:

1. **Use NEST/NANDA framework**: Implement the `agent_logic` function
2. **Entry point file**: Have a Python file (default: `agent.py`) that:
   - Creates a `NANDA` adapter instance
   - Calls `agent.start(register=True)` to register with the registry
3. **Requirements file**: Include a `requirements.txt` with dependencies

### Example Agent Structure

```python
import os
from nanda_core.core.adapter import NANDA

def agent_logic(user_text, conversation_id, agent_id):
    """Your agent logic here"""
    # Process user input and return response
    return "Response text"

if __name__ == "__main__":
    # The deployment script will automatically modify these values
    agent = NANDA(
        agent_id=os.getenv("AGENT_ID", "my-agent"),
        port=int(os.getenv("PORT", 6000)),
        registry_url=os.getenv("REGISTRY_URL"),
        public_url=os.getenv("PUBLIC_URL"),
        agent_logic=agent_logic,
        enable_telemetry=True
    )
    agent.start(register=True)
```

**Note**: The deployment script automatically:
- Sets `agent_id` from environment variable
- Sets `port` from environment variable
- Sets `registry_url` from environment variable
- Adds `public_url` parameter if missing
- Ensures `agent.start(register=True)` is called

## Deployment Process

### Local Deployment

1. Clones GitHub repository to local directory
2. Installs dependencies from `requirements.txt`
3. Modifies agent file to use environment variables
4. Starts agent as subprocess with assigned port
5. Performs health check to verify agent is running
6. Registers agent with NEST registry

### EC2 Deployment

1. Creates EC2 instance (Ubuntu 22.04 LTS)
2. Installs NEST framework via user data script
3. Clones customer's GitHub repository
4. Installs customer dependencies
5. Modifies agent file to use environment variables
6. Retrieves public IP from EC2 metadata
7. Starts agent with proper configuration
8. Opens security group port for agent
9. Verifies agent registration

## Security Notes

- **API Keys**: Customer API keys are encrypted using Fernet (symmetric encryption) before storage
- **No Authentication**: Currently, API security is disabled for development. Add authentication/authorization for production.
- **EC2 Security Groups**: Automatically created and configured, but review security group rules for production use.

## Troubleshooting

### Agent Not Found in Registry

- Check that `REGISTRY_URL` is correctly set
- Verify agent logs for registration messages
- Ensure `agent.start(register=True)` is called

### Deployment Fails

**Local Deployment**:
- Check that port is not already in use
- Verify agent file exists and is valid Python
- Check agent logs in deployment directory

**EC2 Deployment**:
- Verify AWS credentials are configured
- Check EC2 instance logs: `ssh -i ~/.ssh/agentcert-key.pem ubuntu@<public-ip>`
- Check agent logs: `cat ~/agent-<agent-id>/agent.log`
- Verify security group allows SSH (port 22) and agent port

### Stress Test Fails

- Verify agent is deployed and running
- Check agent URL is accessible
- Review stress test logs in API response

### Agent Not Starting

- Check agent logs for errors
- Verify API keys are set correctly
- Ensure all dependencies are installed
- Check that NEST framework is properly installed

## Project Structure

```
agentcert-platform/
├── agentcert_platform/
│   ├── api/                 # FastAPI backend
│   │   ├── main.py         # Main application
│   │   ├── routes/         # API routes
│   │   └── models/         # Pydantic models
│   ├── deployment/         # Deployment service
│   │   ├── deployer.py     # Local/EC2 deployment
│   │   ├── validator.py    # Agent validation
│   │   └── secrets_manager.py  # API key encryption
│   ├── stress_test/        # Stress testing
│   │   ├── stress_test_nest.py
│   │   ├── malicious_prompts.py
│   │   └── response_analyzer.py
│   └── grader/             # LLM-based grading
│       ├── llm_grader.py
│       └── scorer.py
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API client
│   │   └── App.jsx         # Main app component
│   └── package.json        # Frontend dependencies
├── demo/                   # Demo agents
├── config/                 # Configuration files
├── requirements.txt        # Backend dependencies
└── README.md              # This file
```

## Development

### Running Tests

```bash
pytest
```

### Code Style

Follow PEP 8 style guidelines.

### Adding New Features

1. Create feature branch
2. Implement changes
3. Add tests
4. Update documentation
5. Submit pull request

## Production Cloud Architecture



## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub.
