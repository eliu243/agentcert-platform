import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Deploy an agent from GitHub repository
 * @param {string} githubRepo - GitHub repository URL
 * @param {string} branch - Git branch (default: "main")
 * @param {string} entryPoint - Entry point file (default: "agent.py")
 * @param {Object} apiKeys - API keys object (e.g., {OPENAI_API_KEY: "sk-..."})
 * @returns {Promise} Deployment response
 */
export const deployAgent = async (githubRepo, branch = 'main', entryPoint = 'agent.py', apiKeys = null) => {
  try {
    const payload = {
      github_repo: githubRepo,
      branch: branch,
      entry_point: entryPoint,
    };
    
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

