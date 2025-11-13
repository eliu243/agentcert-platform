import { useState, useEffect } from 'react';
import { listDeployments, undeployAgent, makeAgentPublic, makeAgentPrivate, listPublicAgents, getVulnerabilityReports, getLatestAuditScore } from '../services/api';
import StatusBadge from './StatusBadge';
import LoadingSpinner from './LoadingSpinner';

const DeploymentsList = ({ onViewReports, onStartAudit, onViewAuditReports, onDeploymentDeleted }) => {
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deletingAgents, setDeletingAgents] = useState(new Set());
  const [publicAgents, setPublicAgents] = useState(new Set());
  const [togglingPublic, setTogglingPublic] = useState(new Set());
  const [agentsWithReports, setAgentsWithReports] = useState(new Set());
  const [auditScores, setAuditScores] = useState(new Map()); // Map of agent_id -> {score, has_score}

  useEffect(() => {
    loadDeployments(true);
    loadPublicAgents();
  }, []);

  useEffect(() => {
    // Check for agents with reports (even if private now) and fetch audit scores
    const checkForReportsAndScores = async () => {
      const agentsWithReportsSet = new Set();
      const scoresMap = new Map();
      
      for (const deployment of deployments) {
        // Check for vulnerability reports
        try {
          const reports = await getVulnerabilityReports(deployment.agent_id);
          if (reports && reports.total_reports > 0) {
            agentsWithReportsSet.add(deployment.agent_id);
          }
        } catch (err) {
          // Silently fail - agent might not have reports or might not be accessible
        }
        
        // Fetch latest audit score
        try {
          const scoreData = await getLatestAuditScore(deployment.agent_id);
          if (scoreData && scoreData.has_score) {
            scoresMap.set(deployment.agent_id, {
              score: scoreData.score,
              audit_id: scoreData.audit_id,
              completed_at: scoreData.completed_at,
              auditor_type: scoreData.auditor_type
            });
          }
        } catch (err) {
          // Silently fail - agent might not have audit scores
        }
      }
      
      setAgentsWithReports(agentsWithReportsSet);
      setAuditScores(scoresMap);
    };
    
    if (deployments.length > 0) {
      checkForReportsAndScores();
    }
  }, [deployments]);

  const loadPublicAgents = async () => {
    try {
      const publicAgentsList = await listPublicAgents();
      const publicSet = new Set(publicAgentsList.map(a => a.agent_id));
      setPublicAgents(publicSet);
    } catch (err) {
      // Silently fail - public agents list is optional
      console.error('Failed to load public agents:', err);
    }
  };

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

  const handleViewReports = (agentId) => {
    if (onViewReports) {
      onViewReports(agentId);
    }
  };

  const handleStartAudit = (agentId) => {
    if (onStartAudit) {
      onStartAudit(agentId);
    }
  };

  const handleViewAuditReports = (agentId) => {
    if (onViewAuditReports) {
      onViewAuditReports(agentId);
    }
  };

  const handleMakePublic = async (agentId) => {
    setTogglingPublic(prev => new Set(prev).add(agentId));
    try {
      await makeAgentPublic(agentId);
      await loadPublicAgents();
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to make agent public');
    } finally {
      setTogglingPublic(prev => {
        const newSet = new Set(prev);
        newSet.delete(agentId);
        return newSet;
      });
    }
  };

  const handleMakePrivate = async (agentId) => {
    setTogglingPublic(prev => new Set(prev).add(agentId));
    try {
      await makeAgentPrivate(agentId);
      await loadPublicAgents();
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to make agent private');
    } finally {
      setTogglingPublic(prev => {
        const newSet = new Set(prev);
        newSet.delete(agentId);
        return newSet;
      });
    }
  };

  const isPublic = (agentId) => publicAgents.has(agentId);

  const formatAuditorType = (auditorType) => {
    if (!auditorType) return 'Audit';
    // Convert "child-safety" -> "Child Safety"
    return auditorType
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
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
                  <div className="flex items-center gap-3 mb-3 flex-wrap">
                    <h3 className="text-lg font-semibold text-white">
                      {deployment.agent_id}
                    </h3>
                    <StatusBadge status={deployment.status || 'deployed'} />
                    {isPublic(deployment.agent_id) && (
                      <span className="px-2 py-1 bg-green-600/20 text-green-400 text-xs rounded border border-green-600/50">
                        Public
                      </span>
                    )}
                    {auditScores.has(deployment.agent_id) && (() => {
                      const scoreData = auditScores.get(deployment.agent_id);
                      const auditorName = formatAuditorType(scoreData.auditor_type);
                      return (
                        <span className={`px-3 py-1 text-sm font-semibold rounded border ${
                          scoreData.score >= 80
                            ? 'bg-green-600/20 text-green-400 border-green-600/50'
                            : scoreData.score >= 60
                            ? 'bg-yellow-600/20 text-yellow-400 border-yellow-600/50'
                            : 'bg-red-600/20 text-red-400 border-red-600/50'
                        }`}>
                          {auditorName} score: {Math.round(scoreData.score)}
                        </span>
                      );
                    })()}
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
                    onClick={() => handleStartAudit(deployment.agent_id)}
                    className="px-4 py-2 bg-emerald-600 text-white rounded-md hover:bg-emerald-700 text-sm transition-colors font-medium shadow-sm hover:shadow-md"
                  >
                    Run Audit
                  </button>
                  <button
                    onClick={() => handleViewAuditReports(deployment.agent_id)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm transition-colors font-medium shadow-sm hover:shadow-md"
                  >
                    View Audit Reports
                  </button>
                  <button
                    onClick={() => handleViewReports(deployment.agent_id)}
                    disabled={!isPublic(deployment.agent_id) && !agentsWithReports.has(deployment.agent_id)}
                    className={`px-4 py-2 text-white rounded-md text-sm transition-colors font-medium shadow-sm hover:shadow-md ${
                      isPublic(deployment.agent_id) || agentsWithReports.has(deployment.agent_id)
                        ? 'bg-violet-600 hover:bg-violet-700'
                        : 'bg-slate-600 opacity-50 cursor-not-allowed'
                    }`}
                    title={
                      !isPublic(deployment.agent_id) && !agentsWithReports.has(deployment.agent_id)
                        ? 'Make agent public to view vulnerability reports'
                        : 'View vulnerability reports from crowdsourced testing'
                    }
                  >
                    View Public Reports
                  </button>
                  <button
                    onClick={() => handleDelete(deployment.agent_id)}
                    disabled={deletingAgents.has(deployment.agent_id)}
                    className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-sm transition-colors flex items-center justify-center gap-2 shadow-sm hover:shadow-md"
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
              
              {/* Public/Private Toggle at bottom left */}
              <div className="mt-4 flex items-center gap-3">
                <label className="flex items-center gap-3 cursor-pointer">
                  <span className="text-sm text-gray-300">
                    {togglingPublic.has(deployment.agent_id) ? (
                      <span className="flex items-center gap-2">
                        <LoadingSpinner size="sm" />
                        <span>Updating...</span>
                      </span>
                    ) : (
                      <>
                        <span className={isPublic(deployment.agent_id) ? 'text-green-400 font-medium' : 'text-gray-400'}>
                          {isPublic(deployment.agent_id) ? 'Public' : 'Private'}
                        </span>
                        <span className="text-gray-500 ml-1">
                          {isPublic(deployment.agent_id) ? '(visible to others)' : '(only you can see)'}
                        </span>
                      </>
                    )}
                  </span>
                  <div className="relative inline-block w-14 h-7">
                    <input
                      type="checkbox"
                      checked={isPublic(deployment.agent_id)}
                      onChange={() => {
                        if (isPublic(deployment.agent_id)) {
                          handleMakePrivate(deployment.agent_id);
                        } else {
                          handleMakePublic(deployment.agent_id);
                        }
                      }}
                      disabled={togglingPublic.has(deployment.agent_id)}
                      className="sr-only peer"
                    />
                    <div className="w-14 h-7 bg-slate-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-green-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[4px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed"></div>
                  </div>
                </label>
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

