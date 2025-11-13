"""
Pydantic models for API requests and responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class DeployRequest(BaseModel):
    """Request model for agent deployment"""
    github_repo: str = Field(..., description="GitHub repository URL")
    branch: Optional[str] = Field(default="main", description="Git branch to deploy")
    entry_point: Optional[str] = Field(default="agent.py", description="Agent entry point file")
    agent_id: Optional[str] = Field(default=None, description="Custom agent ID (auto-generated if not provided)")
    api_keys: Optional[Dict[str, str]] = Field(
        default=None,
        description="API keys needed by the agent (e.g., {'OPENAI_API_KEY': 'sk-...'}). "
                   "These are encrypted and stored securely."
    )


class DeployResponse(BaseModel):
    """Response model for agent deployment"""
    agent_id: str
    status: str
    agent_url: Optional[str] = None
    message: Optional[str] = None
    deployed_at: datetime = Field(default_factory=datetime.now)


class TestRequest(BaseModel):
    """Request model for stress test"""
    agent_id: str = Field(..., description="Agent ID to test")
    test_config: Optional[Dict[str, Any]] = Field(default=None, description="Optional test configuration")


class TestResponse(BaseModel):
    """Response model for stress test"""
    agent_id: str
    status: str  # "running", "completed", "failed"
    test_id: Optional[str] = None
    message: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.now)


class Violation(BaseModel):
    """Security violation model"""
    test_id: str
    category: str
    severity: str  # "critical", "high", "medium"
    prompt: str
    agent_response: str
    description: str


class ResultsResponse(BaseModel):
    """Response model for test results"""
    agent_id: str
    security_score: float = Field(..., ge=0, le=100, description="Security score 0-100")
    total_tests: int
    passed_tests: int
    failed_tests: int
    violations: List[Violation]
    test_results: List[Dict[str, Any]]
    a2a_logs: Optional[Dict[str, Any]] = None
    traces: Optional[List[Dict[str, Any]]] = None
    performance: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None


class PublicAgentListing(BaseModel):
    """Public agent listing for crowdsourced testing"""
    agent_id: str
    owner_username: str
    github_repo: str
    description: Optional[str] = None
    agent_url: str
    is_public: bool = True
    created_at: str
    test_count: int = 0
    security_score: Optional[float] = None


class TestMessageRequest(BaseModel):
    """Request to send a test message to an agent"""
    message: str = Field(..., min_length=1, max_length=2000, description="Test message to send to agent")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID for multi-turn conversations")


class TestMessageResponse(BaseModel):
    """Response from agent"""
    agent_id: str
    conversation_id: str
    message: str
    agent_response: str
    timestamp: datetime = Field(default_factory=datetime.now)


class VulnerabilityReport(BaseModel):
    """Report of a vulnerability found"""
    agent_id: str
    category: str = Field(..., description="Vulnerability category (jailbreak, data_leak, inappropriate_content, prompt_injection, etc.)")
    severity: str = Field(..., description="Severity level (critical, high, medium, low)")
    prompt: str = Field(..., description="The prompt that triggered the vulnerability")
    agent_response: str = Field(..., description="The agent's response")
    description: str = Field(..., description="Description of the vulnerability")


class MakePublicRequest(BaseModel):
    """Request to make an agent public"""
    description: Optional[str] = Field(default=None, description="Optional description of the agent")


# Auditor schemas
class AuditRequest(BaseModel):
    """Request to start an audit"""
    auditor_type: str = Field(..., description="Type of auditor (e.g., 'child-safety')")


class AuditResponse(BaseModel):
    """Response from starting an audit"""
    audit_id: str
    auditor_agent_id: str
    status: str
    message: str


class AuditStatus(BaseModel):
    """Status of an audit"""
    audit_id: str
    auditor_type: str
    target_agent_id: str
    status: str  # "deploying", "running", "completed", "failed", "stopped"
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


class CategoryViolation(BaseModel):
    """Violation found in a category"""
    category: str
    severity: str  # "critical", "high", "medium", "low"
    test_message: str
    agent_response: str
    description: str


class CategoryResult(BaseModel):
    """Results for a test category"""
    category_name: str
    category_description: str
    tests: List[Dict[str, Any]]
    violations: List[CategoryViolation]


class ChildSafetyReport(BaseModel):
    """Child safety audit report"""
    audit_id: str
    target_agent_url: str
    started_at: str
    completed_at: Optional[str] = None
    overall_score: Optional[float] = Field(None, ge=0, le=100, description="Safety score 0-100")
    status: str
    categories: Dict[str, CategoryResult]
    conversations: List[Dict[str, Any]]
    recommendations: Optional[List[str]] = None


class AvailableAuditor(BaseModel):
    """Available auditor type"""
    type: str
    name: str
    description: str
    target_age_range: Optional[str] = None
    categories: List[str]

