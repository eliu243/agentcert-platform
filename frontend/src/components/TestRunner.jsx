import { useState, useEffect, useRef } from 'react';
import { runStressTest, getTestStatus } from '../services/api';
import LoadingSpinner from './LoadingSpinner';
import StatusBadge from './StatusBadge';

const TestRunner = ({ agentId, onTestComplete }) => {
  const [testAgentId, setTestAgentId] = useState(agentId || '');
  const [isRunning, setIsRunning] = useState(false);
  const [testStatus, setTestStatus] = useState(null);
  const [error, setError] = useState(null);
  const pollingIntervalRef = useRef(null);

  useEffect(() => {
    // Set agent ID from prop if provided
    if (agentId) {
      setTestAgentId(agentId);
    }
  }, [agentId]);

  useEffect(() => {
    // Cleanup polling on unmount
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const startPolling = (agentId) => {
    // Clear any existing polling
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    // Start polling every 3 seconds
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const status = await getTestStatus(agentId);
        setTestStatus(status);

        // Check if test is completed
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(pollingIntervalRef.current);
          setIsRunning(false);
          
          if (status.status === 'completed' && onTestComplete) {
            onTestComplete(agentId);
          }
        }
      } catch (err) {
        console.error('Error polling test status:', err);
        // Don't stop polling on error, just log it
      }
    }, 3000);
  };

  const handleStartTest = async () => {
    if (!testAgentId) {
      setError('Please enter an agent ID');
      return;
    }

    setIsRunning(true);
    setError(null);
    setTestStatus(null);

    try {
      const result = await runStressTest(testAgentId);
      setTestStatus(result);
      
      // Start polling for status updates
      startPolling(testAgentId);
    } catch (err) {
      setError(err.message);
      setIsRunning(false);
    }
  };

  const handleStopPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    setIsRunning(false);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
      <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6">Run Security Test</h2>
      
      <div className="space-y-4">
        {/* Agent ID Input */}
        <div>
          <label htmlFor="testAgentId" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Agent ID *
          </label>
          <input
            type="text"
            id="testAgentId"
            value={testAgentId}
            onChange={(e) => setTestAgentId(e.target.value)}
            required
            placeholder="agent-abc123"
            disabled={isRunning}
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:focus:border-blue-400 disabled:bg-gray-100 dark:disabled:bg-gray-700 disabled:cursor-not-allowed"
          />
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {/* Test Status */}
        {testStatus && (
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
            <div className="flex items-center gap-2 mb-2">
              <StatusBadge status={testStatus.status} />
              {testStatus.test_id && (
                <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                  Test ID: {testStatus.test_id}
                </span>
              )}
            </div>
            {testStatus.message && (
              <p className="text-sm text-blue-700 dark:text-blue-300">{testStatus.message}</p>
            )}
            {testStatus.total_tests && (
              <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                Total tests: {testStatus.total_tests}
              </p>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2">
          {!isRunning ? (
            <button
              onClick={handleStartTest}
              disabled={!testAgentId}
              className="flex-1 px-6 py-3 bg-blue-600 dark:bg-blue-700 text-white rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 disabled:bg-gray-400 dark:disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
            >
              Run Security Test
            </button>
          ) : (
            <>
              <button
                onClick={handleStopPolling}
                className="px-6 py-3 bg-red-600 dark:bg-red-700 text-white rounded-md hover:bg-red-700 dark:hover:bg-red-600 flex items-center justify-center gap-2 transition-colors"
              >
                Stop Polling
              </button>
              <div className="flex-1 px-6 py-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md flex items-center justify-center gap-2">
                <LoadingSpinner size="sm" />
                <span className="text-blue-800 dark:text-blue-200">Test running...</span>
              </div>
            </>
          )}
        </div>

        {/* Polling Info */}
        {isRunning && (
          <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
            Polling for test status updates every 3 seconds...
          </p>
        )}
      </div>
    </div>
  );
};

export default TestRunner;

