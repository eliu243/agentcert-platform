import { useState, useEffect } from 'react';
import DeploymentForm from './components/DeploymentForm';
import TestRunner from './components/TestRunner';
import ResultsDashboard from './components/ResultsDashboard';
import DeploymentsList from './components/DeploymentsList';

function App() {
  const [currentAgentId, setCurrentAgentId] = useState('');
  const [activeTab, setActiveTab] = useState('deploy'); // 'deploy', 'deployments', 'test', 'results'
  const [deploymentComplete, setDeploymentComplete] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [deploymentsKey, setDeploymentsKey] = useState(0); // Key to force refresh deployments list

  // Load dark mode preference from localStorage
  useEffect(() => {
    const savedDarkMode = localStorage.getItem('darkMode') === 'true';
    setDarkMode(savedDarkMode);
    if (savedDarkMode) {
      document.documentElement.classList.add('dark');
    }
  }, []);

  // Toggle dark mode
  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', newDarkMode.toString());
    if (newDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  const handleDeploymentSuccess = (deploymentResult) => {
    setCurrentAgentId(deploymentResult.agent_id);
    setDeploymentComplete(true);
    // Refresh deployments list
    setDeploymentsKey(prev => prev + 1);
    // Automatically switch to test tab after successful deployment
    setActiveTab('test');
  };

  const handleTestComplete = (agentId) => {
    // Automatically switch to results tab after test completes
    setActiveTab('results');
  };

  const handleRefreshResults = () => {
    // This can be used to trigger a refresh if needed
  };

  const handleAgentSelected = (agentId) => {
    setCurrentAgentId(agentId);
    // Switch to test tab when an agent is selected
    setActiveTab('test');
  };

  const handleDeploymentDeleted = (agentId) => {
    // If the deleted agent is the current one, clear it
    if (currentAgentId === agentId) {
      setCurrentAgentId('');
      // Switch to deployments tab
      setActiveTab('deployments');
    }
    // Refresh deployments list
    setDeploymentsKey(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">AgentCert Platform</h1>
            <div className="flex items-center gap-4">
              {currentAgentId && (
                <div className="text-sm text-gray-600 dark:text-gray-300">
                  Agent ID: <span className="font-mono font-semibold">{currentAgentId}</span>
                </div>
              )}
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                aria-label="Toggle dark mode"
              >
                {darkMode ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('deploy')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'deploy'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              Deploy Agent
            </button>
            <button
              onClick={() => setActiveTab('deployments')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'deployments'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              Deployments
            </button>
            <button
              onClick={() => setActiveTab('test')}
              disabled={!currentAgentId}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'test'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
              } ${!currentAgentId ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              Run Test
            </button>
            <button
              onClick={() => setActiveTab('results')}
              disabled={!currentAgentId}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'results'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
              } ${!currentAgentId ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              View Results
            </button>
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'deploy' && (
          <div>
            <DeploymentForm onDeploymentSuccess={handleDeploymentSuccess} />
          </div>
        )}

        {activeTab === 'deployments' && (
          <div>
            <DeploymentsList
              key={deploymentsKey}
              onAgentSelected={handleAgentSelected}
              onDeploymentDeleted={handleDeploymentDeleted}
            />
          </div>
        )}

        {activeTab === 'test' && (
          <div>
            {currentAgentId ? (
              <TestRunner agentId={currentAgentId} onTestComplete={handleTestComplete} />
            ) : (
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
                <p className="text-yellow-800 dark:text-yellow-200">
                  Please deploy an agent first before running tests.
                </p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'results' && (
          <div>
            {currentAgentId ? (
              <ResultsDashboard agentId={currentAgentId} onRefresh={handleRefreshResults} />
            ) : (
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
                <p className="text-yellow-800 dark:text-yellow-200">
                  Please deploy an agent and run tests first to view results.
                </p>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-12 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-sm text-gray-500 dark:text-gray-400">
            AgentCert Platform - AI Agent Security Testing & Certification
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
