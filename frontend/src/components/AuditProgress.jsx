import { useState, useEffect } from 'react';
import { getAuditStatus, stopAudit } from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const AuditProgress = ({ auditId, onComplete, onError }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stopping, setStopping] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (auditId) {
      const interval = setInterval(() => {
        loadStatus();
      }, 2000); // Poll every 2 seconds

      loadStatus();

      return () => clearInterval(interval);
    }
  }, [auditId]);

  const loadStatus = async () => {
    try {
      const data = await getAuditStatus(auditId);
      setStatus(data);
      setLoading(false);

      if (data.status === 'completed') {
        if (onComplete) {
          onComplete(auditId);
        }
      } else if (data.status === 'failed' || data.status === 'stopped') {
        if (onError) {
          onError(data.error || 'Audit failed');
        }
      }
    } catch (err) {
      setError(err.message || 'Failed to load audit status');
      setLoading(false);
      if (onError) {
        onError(err.message);
      }
    }
  };

  const handleStop = async () => {
    if (!window.confirm('Are you sure you want to stop this audit?')) {
      return;
    }

    setStopping(true);
    try {
      await stopAudit(auditId);
      await loadStatus();
    } catch (err) {
      setError(err.message || 'Failed to stop audit');
    } finally {
      setStopping(false);
    }
  };

  if (loading && !status) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner />
      </div>
    );
  }

  if (error && !status) {
    return (
      <div className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded-lg">
        {error}
      </div>
    );
  }

  if (!status) {
    return null;
  }

  const statusColors = {
    deploying: 'text-yellow-400',
    running: 'text-cyan-400',
    completed: 'text-green-400',
    failed: 'text-red-400',
    stopped: 'text-gray-400'
  };

  return (
    <div className="space-y-6">
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">Audit in Progress</h2>
            <p className="text-gray-400">Audit ID: {auditId}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-lg font-semibold ${statusColors[status.status] || 'text-gray-400'}`}>
              {status.status?.toUpperCase() || 'UNKNOWN'}
            </span>
            {status.status === 'running' && (
              <button
                onClick={handleStop}
                disabled={stopping}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {stopping ? 'Stopping...' : 'Stop Audit'}
              </button>
            )}
          </div>
        </div>

        {status.status === 'running' && (
          <div className="mt-4">
            <div className="flex items-center gap-2 text-cyan-400">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-cyan-400"></div>
              <span className="text-sm">Audit is running... This may take a few minutes.</span>
            </div>
          </div>
        )}

        {status.error && (
          <div className="mt-4 bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded-lg">
            <p className="font-medium">Error:</p>
            <p className="text-sm">{status.error}</p>
          </div>
        )}

        <div className="mt-4 text-sm text-gray-400">
          <p>Started: {new Date(status.created_at).toLocaleString()}</p>
          {status.completed_at && (
            <p>Completed: {new Date(status.completed_at).toLocaleString()}</p>
          )}
        </div>
      </div>

      {status.status === 'running' && (
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Testing Categories</h3>
          <div className="space-y-3">
            {[
              'Age-appropriate content',
              'Personal information protection',
              'Social engineering resistance',
              'Inappropriate content filtering',
              'Boundary respect',
              'Grooming pattern detection'
            ].map((category, idx) => (
              <div key={idx} className="flex items-center gap-3">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-cyan-400"></div>
                <span className="text-gray-300">{category}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditProgress;

