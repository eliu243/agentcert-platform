import { useState } from 'react';

const ViolationDetail = ({ violation }) => {
  const [expanded, setExpanded] = useState(false);

  if (!violation) return null;

  const severityColors = {
    critical: 'bg-red-900/30 border-red-700 text-red-300',
    high: 'bg-orange-900/30 border-orange-700 text-orange-300',
    medium: 'bg-yellow-900/30 border-yellow-700 text-yellow-300',
    low: 'bg-blue-900/30 border-blue-700 text-blue-300'
  };

  const severityColor = severityColors[violation.severity] || severityColors.medium;

  return (
    <div className={`border rounded-lg p-4 ${severityColor}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className="px-2 py-1 bg-slate-800/50 rounded text-xs font-medium">
              {violation.severity?.toUpperCase() || 'MEDIUM'}
            </span>
            <span className="text-sm text-gray-400">
              {violation.category?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </span>
          </div>
          <p className="text-sm mb-3">{violation.description}</p>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-gray-400 hover:text-white transition-colors ml-4"
        >
          <svg
            className={`w-5 h-5 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {expanded && (
        <div className="mt-4 space-y-3 pt-4 border-t border-slate-700/50">
          <div>
            <p className="text-xs font-medium text-gray-400 mb-1">Test Message:</p>
            <div className="bg-slate-900/50 rounded p-3 text-sm text-gray-300">
              {violation.test_message || violation.prompt}
            </div>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-400 mb-1">Agent Response:</p>
            <div className="bg-slate-900/50 rounded p-3 text-sm text-gray-300 max-h-48 overflow-y-auto">
              {violation.agent_response}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ViolationDetail;

