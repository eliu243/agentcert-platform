import { useState, useEffect } from 'react';
import { listDeployments, undeployAgent } from '../services/api';
import StatusBadge from './StatusBadge';
import LoadingSpinner from './LoadingSpinner';

const DeploymentsList = ({ onRunTest, onViewResults, onDeploymentDeleted }) => {
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deletingAgents, setDeletingAgents] = useState(new Set());

  useEffect(() => {
    loadDeployments(true);
  }, []);

  const loadDeployments = async (showLoading = false) => {
    if (showLoading) {
      setLoading(true);
    }
    setError(null);

    try {
      const data = await listDeployments();
      // Convert deployment_details object to array
      const deploymentsArray = Object.entries(data.deployment_details || {}).map(([agentId, details]) => ({
        agent_id: agentId,
        ...details,
      }));
      setDeployments(deploymentsArray);
    } catch (err) {
      setError(err.message);
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  };

  const handleDelete = async (agentId) => {
    const confirmed = window.confirm(
      `Are you sure you want to remove agent "${agentId}"?\n\nThis will:\n- Terminate the agent instance\n- Clean up all resources\n- Remove the deployment\n\nThis action cannot be undone.`
    );
    
    if (!confirmed) {
      return;
    }

    setDeletingAgents(prev => new Set(prev).add(agentId));

    try {
      await undeployAgent(agentId);
      // Reload deployments list to ensure consistency (show loading)
      await loadDeployments(true);
      
      if (onDeploymentDeleted) {
        onDeploymentDeleted(agentId);
      }
    } catch (err) {
      setError(err.message);
      // Still reload to get latest state
      await loadDeployments(true);
    } finally {
      setDeletingAgents(prev => {
        const newSet = new Set(prev);
        newSet.delete(agentId);
        return newSet;
      });
    }
  };

  const handleRunTest = (agentId) => {
    if (onRunTest) {
      onRunTest(agentId);
    }
  };

  const handleViewResults = (agentId) => {
    if (onViewResults) {
      onViewResults(agentId);
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl shadow-lg p-6 transition-colors">
        <div className="flex justify-center items-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    );
  }

  if (error && deployments.length === 0) {
    return (
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl shadow-lg p-6 transition-colors">
        <div className="p-4 bg-red-900/20 border border-red-700/50 rounded-md">
          <p className="text-sm text-red-200">{error}</p>
          <button
            onClick={() => loadDeployments(true)}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl shadow-lg p-6 transition-colors">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">Deployed Agents</h2>
        <button
          onClick={() => loadDeployments(true)}
          className="px-4 py-2 bg-slate-700 text-gray-300 rounded-md hover:bg-slate-600 text-sm transition-colors"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-yellow-900/20 border border-yellow-700/50 rounded-md">
          <p className="text-sm text-yellow-200">{error}</p>
        </div>
      )}

      {deployments.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-400 text-lg mb-2">No agents deployed yet</p>
          <p className="text-sm text-gray-500">
            Deploy your first agent using the "Deploy Agent" tab
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {deployments.map((deployment) => (
            <div
              key={deployment.agent_id}
              className="border border-slate-700/50 rounded-lg p-4 hover:bg-slate-700/30 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-3">
                    <h3 className="text-lg font-semibold text-white">
                      {deployment.agent_id}
                    </h3>
                    <StatusBadge status={deployment.status || 'deployed'} />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium text-gray-300">GitHub Repository:</span>
                      <p className="text-gray-400 font-mono text-xs mt-1 break-all">
                        <a
                          href={deployment.github_repo || '#'}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-cyan-400 hover:underline"
                          onClick={(e) => {
                            if (!deployment.github_repo) {
                              e.preventDefault();
                            }
                          }}
                        >
                          {deployment.github_repo || 'N/A'}
                        </a>
                      </p>
                    </div>

                    <div>
                      <span className="font-medium text-gray-300">Branch:</span>
                      <p className="text-gray-400 mt-1 font-mono">
                        {deployment.branch || 'main'}
                      </p>
                    </div>

                    <div>
                      <span className="font-medium text-gray-300">Entry Point:</span>
                      <p className="text-gray-400 mt-1 font-mono">
                        {deployment.entry_point || 'agent.py'}
                      </p>
                    </div>

                    {deployment.agent_url && (
                      <div>
                        <span className="font-medium text-gray-300">Agent URL:</span>
                        <p className="text-gray-400 font-mono text-xs mt-1 break-all">
                          <a
                            href={deployment.agent_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-cyan-400 hover:underline"
                          >
                            {deployment.agent_url}
                          </a>
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex flex-col gap-2 ml-4">
                  <button
                    onClick={() => handleRunTest(deployment.agent_id)}
                    className="px-4 py-2 bg-cyan-600 text-white rounded-md hover:bg-cyan-700 text-sm transition-colors font-medium"
                  >
                    Run Test
                  </button>
                  <button
                    onClick={() => handleViewResults(deployment.agent_id)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm transition-colors font-medium"
                  >
                    View Results
                  </button>
                  <button
                    onClick={() => handleDelete(deployment.agent_id)}
                    disabled={deletingAgents.has(deployment.agent_id)}
                    className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-sm transition-colors flex items-center justify-center gap-2"
                  >
                    {deletingAgents.has(deployment.agent_id) ? (
                      <>
                        <LoadingSpinner size="sm" />
                        <span>Removing...</span>
                      </>
                    ) : (
                      'Remove'
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {deployments.length > 0 && (
        <div className="mt-6 text-sm text-gray-400 text-center">
          Total: {deployments.length} deployed agent{deployments.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
};

export default DeploymentsList;

