import { useState, useEffect } from 'react';
import { listAgentAudits, getAuditReport } from '../services/api';
import LoadingSpinner from './LoadingSpinner';
import ChildSafetyReport from './ChildSafetyReport';

const AuditReportsList = ({ agentId, onViewAudit }) => {
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedAuditId, setSelectedAuditId] = useState(null);

  useEffect(() => {
    if (agentId) {
      loadAudits();
    }
  }, [agentId]);

  const loadAudits = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listAgentAudits(agentId);
      setAudits(data.audits || []);
    } catch (err) {
      setError(err.message || 'Failed to load audits');
    } finally {
      setLoading(false);
    }
  };

  const handleViewAudit = (auditId) => {
    if (onViewAudit) {
      onViewAudit(auditId);
    } else {
      setSelectedAuditId(auditId);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'text-green-400';
      case 'running':
        return 'text-cyan-400';
      case 'failed':
        return 'text-red-400';
      case 'stopped':
        return 'text-gray-400';
      default:
        return 'text-yellow-400';
    }
  };

  if (selectedAuditId) {
    return (
      <div>
        <button
          onClick={() => setSelectedAuditId(null)}
          className="mb-6 flex items-center gap-2 px-4 py-2 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50 rounded-lg text-gray-300 hover:text-white transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Audit List
        </button>
        <ChildSafetyReport auditId={selectedAuditId} />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded-lg">
        {error}
      </div>
    );
  }

  if (audits.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400 text-lg mb-2">No audits found for this agent</p>
        <p className="text-sm text-gray-500">
          Run an audit using the "Audit with Child Safety Auditor" button
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">Audit Reports</h2>
        <button
          onClick={loadAudits}
          className="px-4 py-2 bg-slate-700 text-gray-300 rounded-md hover:bg-slate-600 text-sm transition-colors"
        >
          Refresh
        </button>
      </div>

      {audits.map((audit) => (
        <div
          key={audit.audit_id}
          className="bg-slate-800/50 border border-slate-700 rounded-lg p-6 hover:border-cyan-500/50 transition-colors"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h3 className="text-lg font-semibold text-white">
                  {audit.auditor_type === 'child-safety' ? 'Child Safety Audit' : audit.auditor_type}
                </h3>
                <span className={`text-sm font-medium ${getStatusColor(audit.status)}`}>
                  {audit.status?.toUpperCase() || 'UNKNOWN'}
                </span>
              </div>
              <div className="text-sm text-gray-400 space-y-1">
                <p>Audit ID: {audit.audit_id}</p>
                <p>Started: {new Date(audit.created_at).toLocaleString()}</p>
                {audit.completed_at && (
                  <p>Completed: {new Date(audit.completed_at).toLocaleString()}</p>
                )}
                {audit.results && audit.results.overall_score !== null && (
                  <p className="text-cyan-400 font-medium">
                    Safety Score: {audit.results.overall_score.toFixed(1)}/100
                  </p>
                )}
              </div>
              {audit.error && (
                <div className="mt-2 text-sm text-red-400">
                  Error: {audit.error}
                </div>
              )}
            </div>
            <div className="ml-4">
              {audit.status === 'completed' && audit.results ? (
                <button
                  onClick={() => handleViewAudit(audit.audit_id)}
                  className="px-4 py-2 bg-cyan-600 text-white rounded-md hover:bg-cyan-700 text-sm transition-colors font-medium"
                >
                  View Report
                </button>
              ) : audit.status === 'running' ? (
                <button
                  onClick={() => handleViewAudit(audit.audit_id)}
                  className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 text-sm transition-colors font-medium"
                >
                  View Progress
                </button>
              ) : (
                <span className="text-gray-500 text-sm">No report available</span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default AuditReportsList;

