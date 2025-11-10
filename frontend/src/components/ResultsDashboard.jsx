import { useState, useEffect } from 'react';
import { getResults } from '../services/api';
import StatusBadge from './StatusBadge';
import LoadingSpinner from './LoadingSpinner';

const ResultsDashboard = ({ agentId, onRefresh }) => {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showA2ALogs, setShowA2ALogs] = useState(false);
  const [showFullResponse, setShowFullResponse] = useState({});

  useEffect(() => {
    if (agentId) {
      loadResults();
    }
  }, [agentId]);

  const loadResults = async () => {
    if (!agentId) {
      setError('No agent ID provided');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await getResults(agentId);
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    loadResults();
    if (onRefresh) {
      onRefresh();
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400';
    if (score >= 50) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getScoreBgColor = (score) => {
    if (score >= 80) return 'bg-green-100 dark:bg-green-900/20 border-green-300 dark:border-green-700';
    if (score >= 50) return 'bg-yellow-100 dark:bg-yellow-900/20 border-yellow-300 dark:border-yellow-700';
    return 'bg-red-100 dark:bg-red-900/20 border-red-300 dark:border-red-700';
  };

  const toggleFullResponse = (violationId) => {
    setShowFullResponse({
      ...showFullResponse,
      [violationId]: !showFullResponse[violationId],
    });
  };

  const exportResults = () => {
    if (!results) return;

    const dataStr = JSON.stringify(results, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `agentcert-results-${agentId}-${new Date().toISOString()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
        <div className="flex justify-center items-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
          <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          <button
            onClick={handleRefresh}
            className="mt-4 px-4 py-2 bg-red-600 dark:bg-red-700 text-white rounded-md hover:bg-red-700 dark:hover:bg-red-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
        <p className="text-gray-500 dark:text-gray-400 text-center py-12">No results available</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-white">Test Results</h2>
        <div className="flex gap-2">
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 text-sm transition-colors"
          >
            Refresh
          </button>
          <button
            onClick={exportResults}
            className="px-4 py-2 bg-blue-600 dark:bg-blue-700 text-white rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 text-sm transition-colors"
          >
            Export JSON
          </button>
        </div>
      </div>

      {/* Security Score */}
      <div className={`mb-6 p-6 rounded-lg border-2 transition-colors ${getScoreBgColor(results.security_score)}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Security Score</p>
            <p className={`text-5xl font-bold ${getScoreColor(results.security_score)}`}>
              {results.security_score.toFixed(1)}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">out of 100</p>
          </div>
          <StatusBadge
            status={
              results.security_score >= 80
                ? 'Excellent'
                : results.security_score >= 50
                ? 'Moderate'
                : 'Poor'
            }
          />
        </div>
      </div>

      {/* Test Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 transition-colors">
          <p className="text-sm font-medium text-blue-700 dark:text-blue-300 mb-1">Total Tests</p>
          <p className="text-2xl font-bold text-blue-900 dark:text-blue-200">{results.total_tests}</p>
        </div>
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 transition-colors">
          <p className="text-sm font-medium text-green-700 dark:text-green-300 mb-1">Passed</p>
          <p className="text-2xl font-bold text-green-900 dark:text-green-200">{results.passed_tests}</p>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 transition-colors">
          <p className="text-sm font-medium text-red-700 dark:text-red-300 mb-1">Failed</p>
          <p className="text-2xl font-bold text-red-900 dark:text-red-200">{results.failed_tests}</p>
        </div>
        <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4 transition-colors">
          <p className="text-sm font-medium text-orange-700 dark:text-orange-300 mb-1">Violations</p>
          <p className="text-2xl font-bold text-orange-900 dark:text-orange-200">{results.violations.length}</p>
        </div>
      </div>

      {/* Performance Metrics */}
      {results.performance && (
        <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg transition-colors">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-3">Performance Metrics</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {results.performance.avg_response_time && (
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Average Response Time</p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">
                  {results.performance.avg_response_time.toFixed(2)}s
                </p>
              </div>
            )}
            {results.performance.success_rate && (
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Success Rate</p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">
                  {(results.performance.success_rate * 100).toFixed(1)}%
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Violations Table */}
      {results.violations && results.violations.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-3">Security Violations</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Severity
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Prompt
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Response
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Description
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {results.violations.map((violation, index) => (
                  <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                    <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">{violation.category}</td>
                    <td className="px-4 py-3 text-sm">
                      <StatusBadge status={violation.severity} />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300 max-w-xs">
                      <div className="truncate">{violation.prompt}</div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300 max-w-xs">
                      <div>
                        {showFullResponse[`${violation.test_id}-${index}`] ? (
                          <div>
                            <div className="mb-1">{violation.agent_response}</div>
                            <button
                              onClick={() => toggleFullResponse(`${violation.test_id}-${index}`)}
                              className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-xs"
                            >
                              Show less
                            </button>
                          </div>
                        ) : (
                          <div>
                            <div className="truncate">{violation.agent_response}</div>
                            {violation.agent_response.length > 50 && (
                              <button
                                onClick={() => toggleFullResponse(`${violation.test_id}-${index}`)}
                                className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-xs mt-1"
                              >
                                Show more
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">{violation.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* A2A Logs */}
      {results.a2a_logs && Object.keys(results.a2a_logs).length > 0 && (
        <div className="mb-6">
          <button
            onClick={() => setShowA2ALogs(!showA2ALogs)}
            className="flex items-center justify-between w-full text-left text-lg font-semibold text-gray-800 dark:text-white mb-3 hover:text-gray-900 dark:hover:text-gray-200"
          >
            <span>A2A Communication Logs</span>
            <span>{showA2ALogs ? '−' : '+'}</span>
          </button>
          {showA2ALogs && (
            <div className="p-4 bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-lg transition-colors">
              <pre className="text-xs text-gray-700 dark:text-gray-300 overflow-x-auto">
                {JSON.stringify(results.a2a_logs, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Completed At */}
      {results.completed_at && (
        <div className="text-sm text-gray-500 dark:text-gray-400 text-center">
          Test completed at: {new Date(results.completed_at).toLocaleString()}
        </div>
      )}
    </div>
  );
};

export default ResultsDashboard;

