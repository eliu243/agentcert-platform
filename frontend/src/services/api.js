import axios from 'axios';
import { getToken } from './auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add authentication interceptor
api.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle 401 responses (unauthorized)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token is invalid or expired, redirect to login
      const token = getToken();
      if (token) {
        // Clear invalid token
        localStorage.removeItem('agentcert_auth_token');
        // Redirect to login page
        window.location.href = '/';
      }
    }
    return Promise.reject(error);
  }
);

/**
 * Deploy an agent from GitHub repository
 * @param {string} githubRepo - GitHub repository URL
 * @param {string} branch - Git branch (default: "main")
 * @param {string} entryPoint - Entry point file (default: "agent.py")
 * @param {Object} apiKeys - API keys object (e.g., {OPENAI_API_KEY: "sk-..."})
 * @param {string} agentId - Custom agent ID/name (optional, auto-generated if not provided)
 * @returns {Promise} Deployment response
 */
export const deployAgent = async (githubRepo, branch = 'main', entryPoint = 'agent.py', apiKeys = null, agentId = null) => {
  try {
    const payload = {
      github_repo: githubRepo,
      branch: branch,
      entry_point: entryPoint,
    };
    
    if (agentId) {
      payload.agent_id = agentId;
    }
    
    if (apiKeys && Object.keys(apiKeys).length > 0) {
      payload.api_keys = apiKeys;
    }
    
    const response = await api.post('/api/deploy', payload);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Deployment failed');
  }
};

/**
 * Get deployment status for an agent
 * @param {string} agentId - Agent ID
 * @returns {Promise} Deployment status
 */
export const getDeploymentStatus = async (agentId) => {
  try {
    const response = await api.get(`/api/deploy/${agentId}/status`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to get deployment status');
  }
};

/**
 * List all deployments
 * @returns {Promise} List of deployments
 */
export const listDeployments = async () => {
  try {
    const response = await api.get('/api/deploy');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to list deployments');
  }
};

/**
 * Undeploy an agent
 * @param {string} agentId - Agent ID
 * @returns {Promise} Undeployment response
 */
export const undeployAgent = async (agentId) => {
  try {
    const response = await api.delete(`/api/deploy/${agentId}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to undeploy agent');
  }
};

/**
 * Run stress test on a deployed agent
 * @param {string} agentId - Agent ID
 * @returns {Promise} Test response
 */
export const runStressTest = async (agentId) => {
  try {
    const response = await api.post(`/api/test/${agentId}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Stress test failed');
  }
};

/**
 * Get test status for an agent
 * @param {string} agentId - Agent ID
 * @returns {Promise} Test status
 */
export const getTestStatus = async (agentId) => {
  try {
    const response = await api.get(`/api/test/${agentId}/status`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to get test status');
  }
};

/**
 * Get test results for an agent
 * @param {string} agentId - Agent ID
 * @returns {Promise} Test results
 */
export const getResults = async (agentId) => {
  try {
    const response = await api.get(`/api/results/${agentId}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to get results');
  }
};

/**
 * Get test results summary for an agent
 * @param {string} agentId - Agent ID
 * @returns {Promise} Test results summary
 */
export const getResultsSummary = async (agentId) => {
  try {
    const response = await api.get(`/api/results/${agentId}/summary`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to get results summary');
  }
};

/**
 * Health check
 * @returns {Promise} Health status
 */
export const healthCheck = async () => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    throw new Error('Health check failed');
  }
};

/**
 * Get platform configuration
 * @returns {Promise} Platform configuration (deployment mode, etc.)
 */
export const getConfig = async () => {
  try {
    const response = await api.get('/api/config');
    return response.data;
  } catch (error) {
    throw new Error('Failed to get configuration');
  }
};

/**
 * List all publicly available agents for testing
 * @returns {Promise} List of public agents
 */
export const listPublicAgents = async () => {
  try {
    const response = await api.get('/api/public/agents');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to list public agents');
  }
};

/**
 * Send a test message to a public agent
 * @param {string} agentId - Agent ID
 * @param {string} message - Test message
 * @param {string} conversationId - Optional conversation ID for multi-turn conversations
 * @returns {Promise} Agent response
 */
export const testAgent = async (agentId, message, conversationId = null) => {
  try {
    const payload = { message };
    if (conversationId) {
      payload.conversation_id = conversationId;
    }
    const response = await api.post(`/api/public/agents/${agentId}/test`, payload);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to test agent');
  }
};

/**
 * Report a vulnerability found in an agent
 * @param {string} agentId - Agent ID
 * @param {Object} report - Vulnerability report object
 * @returns {Promise} Report submission response
 */
export const reportVulnerability = async (agentId, report) => {
  try {
    const payload = {
      agent_id: agentId,
      ...report
    };
    const response = await api.post(`/api/public/agents/${agentId}/report`, payload);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to report vulnerability');
  }
};

/**
 * Get vulnerability reports for an agent (owner only)
 * @param {string} agentId - Agent ID
 * @returns {Promise} Vulnerability reports
 */
export const getVulnerabilityReports = async (agentId) => {
  try {
    const response = await api.get(`/api/public/agents/${agentId}/reports`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to get vulnerability reports');
  }
};

/**
 * Make an agent publicly available for testing
 * @param {string} agentId - Agent ID
 * @param {string} description - Optional description
 * @returns {Promise} Response
 */
export const makeAgentPublic = async (agentId, description = null) => {
  try {
    const payload = {};
    if (description) {
      payload.description = description;
    }
    const response = await api.post(`/api/deploy/${agentId}/make-public`, payload);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to make agent public');
  }
};

/**
 * Make an agent private (remove from public testing)
 * @param {string} agentId - Agent ID
 * @returns {Promise} Response
 */
export const makeAgentPrivate = async (agentId) => {
  try {
    const response = await api.post(`/api/deploy/${agentId}/make-private`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to make agent private');
  }
};

/**
 * Mark a vulnerability report as addressed
 * @param {string} agentId - Agent ID
 * @param {string} reportId - Report ID
 * @returns {Promise} Response
 */
export const markReportAddressed = async (agentId, reportId) => {
  try {
    const response = await api.post(`/api/public/agents/${agentId}/reports/${reportId}/addressed`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to mark report as addressed');
  }
};

/**
 * Start a child safety audit for an agent
 * @param {string} agentId - Agent ID to audit
 * @returns {Promise} Audit response with audit_id
 */
export const startChildSafetyAudit = async (agentId) => {
  try {
    const response = await api.post(`/api/auditor/child-safety/${agentId}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to start audit');
  }
};

/**
 * Get status of an audit
 * @param {string} auditId - Audit ID
 * @returns {Promise} Audit status
 */
export const getAuditStatus = async (auditId) => {
  try {
    const response = await api.get(`/api/auditor/audit/${auditId}/status`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to get audit status');
  }
};

/**
 * Get audit report (results)
 * @param {string} auditId - Audit ID
 * @returns {Promise} Audit report
 */
export const getAuditReport = async (auditId) => {
  try {
    const response = await api.get(`/api/auditor/audit/${auditId}/report`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to get audit report');
  }
};

/**
 * Stop a running audit
 * @param {string} auditId - Audit ID
 * @returns {Promise} Response
 */
export const stopAudit = async (auditId) => {
  try {
    const response = await api.post(`/api/auditor/audit/${auditId}/stop`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to stop audit');
  }
};

/**
 * Get list of available auditors
 * @returns {Promise} List of available auditors
 */
export const getAvailableAuditors = async () => {
  try {
    const response = await api.get('/api/auditor/available');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to get available auditors');
  }
};

/**
 * List all audits for an agent
 * @param {string} agentId - Agent ID
 * @returns {Promise} List of audits for the agent
 */
export const listAgentAudits = async (agentId) => {
  try {
    const response = await api.get(`/api/auditor/agent/${agentId}/audits`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to list audits');
  }
};

