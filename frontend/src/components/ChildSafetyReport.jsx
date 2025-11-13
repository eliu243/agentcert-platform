import { useState, useEffect } from 'react';
import { getAuditReport } from '../services/api';
import LoadingSpinner from './LoadingSpinner';
import ViolationDetail from './ViolationDetail';

const ChildSafetyReport = ({ auditId }) => {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedCategories, setExpandedCategories] = useState(new Set());
  const [selectedConversation, setSelectedConversation] = useState(null);

  useEffect(() => {
    if (auditId) {
      loadReport();
    }
  }, [auditId]);

  const loadReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAuditReport(auditId);
      setReport(data);
    } catch (err) {
      setError(err.message || 'Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const toggleCategory = (categoryName) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(categoryName)) {
      newExpanded.delete(categoryName);
    } else {
      newExpanded.add(categoryName);
    }
    setExpandedCategories(newExpanded);
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getScoreBgColor = (score) => {
    if (score >= 80) return 'bg-green-900/20 border-green-700/50';
    if (score >= 50) return 'bg-yellow-900/20 border-yellow-700/50';
    return 'bg-red-900/20 border-red-700/50';
  };

  const handleExportJSON = () => {
    if (!report) return;
    
    // Create a clean JSON export
    const exportData = {
      audit_id: report.audit_id,
      target_agent_url: report.target_agent_url,
      started_at: report.started_at,
      completed_at: report.completed_at,
      overall_score: report.overall_score,
      status: report.status,
      categories: report.categories,
      conversations: report.conversations,
      recommendations: report.recommendations,
      exported_at: new Date().toISOString()
    };
    
    // Convert to JSON string with pretty formatting
    const jsonString = JSON.stringify(exportData, null, 2);
    
    // Create a blob and download
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `child-safety-audit-${report.audit_id}-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

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

  if (!report) {
    return <div className="text-gray-400">No report data available</div>;
  }

  const score = report.overall_score ?? 0;
  const totalViolations = Object.values(report.categories || {}).reduce(
    (sum, cat) => sum + (cat.violations?.length || 0),
    0
  );

  const categoryNames = {
    age_appropriate_content: 'Age-Appropriate Content',
    personal_information_protection: 'Personal Information Protection',
    social_engineering_resistance: 'Social Engineering Resistance',
    inappropriate_content_filtering: 'Inappropriate Content Filtering',
    boundary_respect: 'Boundary Respect',
    grooming_pattern_detection: 'Grooming Pattern Detection'
  };

  return (
    <div className="space-y-6">
      {/* Header with Export Button */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-3xl font-bold text-white">Child Safety Audit Report</h1>
        <button
          onClick={handleExportJSON}
          className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-md text-sm transition-colors font-medium flex items-center gap-2 shadow-sm hover:shadow-md"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Export as JSON
        </button>
      </div>

      {/* Overall Score */}
      <div className={`${getScoreBgColor(score)} border rounded-lg p-8 text-center`}>
        <h2 className="text-3xl font-bold text-white mb-2">Child Safety Score</h2>
        <div className={`text-6xl font-bold ${getScoreColor(score)} mb-4`}>
          {score.toFixed(1)}/100
        </div>
        <p className="text-gray-400">
          {totalViolations} violation{totalViolations !== 1 ? 's' : ''} found across {Object.keys(report.categories || {}).length} categories
        </p>
      </div>

      {/* Category Breakdown */}
      <div className="space-y-4">
        <h3 className="text-2xl font-bold text-white">Category Breakdown</h3>
        {Object.entries(report.categories || {}).map(([categoryName, categoryData]) => {
          const categoryDisplayName = categoryNames[categoryName] || categoryName;
          const violations = categoryData.violations || [];
          const tests = categoryData.tests || [];
          const passed = tests.length - violations.length;
          const categoryScore = tests.length > 0 ? (passed / tests.length) * 100 : 0;
          const isExpanded = expandedCategories.has(categoryName);

          return (
            <div key={categoryName} className="bg-slate-800/50 border border-slate-700 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex-1">
                  <h4 className="text-lg font-semibold text-white mb-2">{categoryDisplayName}</h4>
                  <div className="flex items-center gap-4 text-sm text-gray-400">
                    <span>{tests.length} tests</span>
                    <span className={violations.length > 0 ? 'text-red-400' : 'text-green-400'}>
                      {violations.length} violation{violations.length !== 1 ? 's' : ''}
                    </span>
                    <span>Score: {categoryScore.toFixed(0)}%</span>
                  </div>
                </div>
                <button
                  onClick={() => toggleCategory(categoryName)}
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  <svg
                    className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>

              {/* Progress Bar */}
              <div className="mb-4">
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      categoryScore >= 80 ? 'bg-green-500' : categoryScore >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${categoryScore}%` }}
                  />
                </div>
              </div>

              {/* Violations */}
              {violations.length > 0 && (
                <div className="mb-4">
                  <h5 className="text-sm font-medium text-red-400 mb-2">Violations Found:</h5>
                  <div className="space-y-2">
                    {violations.map((violation, idx) => (
                      <ViolationDetail key={idx} violation={violation} />
                    ))}
                  </div>
                </div>
              )}

              {/* Expanded Details */}
              {isExpanded && (
                <div className="mt-4 pt-4 border-t border-slate-700/50 space-y-3">
                  <h5 className="text-sm font-medium text-gray-400 mb-2">Test Details:</h5>
                  {tests.map((test, idx) => (
                    <div key={idx} className="bg-slate-900/50 rounded p-3 text-sm">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-gray-400">Test {test.test_number}:</span>
                        {test.analysis?.has_violation ? (
                          <span className="px-2 py-0.5 bg-red-900/50 text-red-300 rounded text-xs">
                            Violation
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 bg-green-900/50 text-green-300 rounded text-xs">
                            Passed
                          </span>
                        )}
                      </div>
                      <p className="text-gray-300 mb-1">
                        <span className="text-gray-500">Q:</span> {test.message}
                      </p>
                      <p className="text-gray-300">
                        <span className="text-gray-500">A:</span> {test.agent_response}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Conversations */}
      {report.conversations && report.conversations.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-2xl font-bold text-white">Conversation Logs</h3>
          <div className="space-y-2">
            {report.conversations.map((conv, idx) => (
              <div key={idx} className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-400">
                    {categoryNames[conv.category] || conv.category}
                  </span>
                  <button
                    onClick={() => setSelectedConversation(selectedConversation === idx ? null : idx)}
                    className="text-cyan-400 hover:text-cyan-300 text-sm"
                  >
                    {selectedConversation === idx ? 'Hide' : 'Show'} Conversation
                  </button>
                </div>
                {selectedConversation === idx && conv.history && (
                  <div className="mt-3 space-y-2 max-h-96 overflow-y-auto">
                    {conv.history.map((msg, msgIdx) => (
                      <div key={msgIdx} className="bg-slate-900/50 rounded p-3 text-sm">
                        <p className="text-cyan-400 mb-1">User: {msg.user}</p>
                        <p className="text-gray-300">Agent: {msg.agent}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {report.recommendations && report.recommendations.length > 0 && (
        <div className="bg-blue-900/20 border border-blue-700/50 rounded-lg p-6">
          <h3 className="text-xl font-bold text-white mb-4">Recommendations</h3>
          <ul className="space-y-2">
            {report.recommendations.map((rec, idx) => (
              <li key={idx} className="text-gray-300 flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default ChildSafetyReport;

