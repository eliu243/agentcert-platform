import { useState, useEffect } from 'react';
import { getAvailableAuditors, startChildSafetyAudit } from '../services/api';
import Modal from './Modal';
import LoadingSpinner from './LoadingSpinner';

const AuditorSelectionModal = ({ isOpen, onClose, agentId, onAuditStarted }) => {
  const [auditors, setAuditors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadAuditors();
    }
  }, [isOpen]);

  const loadAuditors = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAvailableAuditors();
      setAuditors(data);
    } catch (err) {
      setError(err.message || 'Failed to load auditors');
    } finally {
      setLoading(false);
    }
  };

  const handleStartAudit = async (auditorType) => {
    setStarting(true);
    setError(null);
    try {
      let result;
      if (auditorType === 'child-safety') {
        result = await startChildSafetyAudit(agentId);
      } else {
        throw new Error(`Unknown auditor type: ${auditorType}`);
      }
      
      if (onAuditStarted) {
        onAuditStarted(result.audit_id);
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to start audit');
    } finally {
      setStarting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Select Auditor">
      <div className="space-y-4">
        {loading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner />
          </div>
        ) : error ? (
          <div className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded-lg">
            {error}
          </div>
        ) : auditors.length === 0 ? (
          <div className="text-gray-400 text-center py-8">
            No auditors available
          </div>
        ) : (
          <div className="space-y-4">
            {auditors.map((auditor) => (
              <div
                key={auditor.type}
                className="bg-slate-700/50 border border-slate-600 rounded-lg p-6 hover:border-cyan-500/50 transition-colors"
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-xl font-bold text-white mb-2">{auditor.name}</h3>
                    <p className="text-gray-300 text-sm mb-2">{auditor.description}</p>
                    {auditor.target_age_range && (
                      <p className="text-cyan-400 text-sm font-medium">
                        Target Age Range: {auditor.target_age_range}
                      </p>
                    )}
                  </div>
                </div>
                
                {auditor.categories && auditor.categories.length > 0 && (
                  <div className="mb-4">
                    <p className="text-gray-400 text-sm font-medium mb-2">Test Categories:</p>
                    <div className="flex flex-wrap gap-2">
                      {auditor.categories.map((category, idx) => (
                        <span
                          key={idx}
                          className="px-3 py-1 bg-slate-600/50 text-gray-300 text-xs rounded-full"
                        >
                          {category}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                <button
                  onClick={() => handleStartAudit(auditor.type)}
                  disabled={starting}
                  className="w-full px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {starting ? 'Starting Audit...' : 'Start Audit'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
};

export default AuditorSelectionModal;

