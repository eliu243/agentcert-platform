import { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import DeploymentForm from './components/DeploymentForm';
import DeploymentsList from './components/DeploymentsList';
import HomePage from './components/HomePage';
import ProfileDropdown from './components/ProfileDropdown';
import ProtectedRoute from './components/ProtectedRoute';
import PublicTesting from './components/PublicTesting';
import VulnerabilityReports from './components/VulnerabilityReports';
import AuditorSelectionModal from './components/AuditorSelectionModal';
import AuditProgress from './components/AuditProgress';
import ChildSafetyReport from './components/ChildSafetyReport';
import AuditReportsList from './components/AuditReportsList';

function AppContent() {
  const { authenticated, loading, user, reloadUser } = useAuth();
  const [activeTab, setActiveTab] = useState('home'); // 'home', 'deploy', 'deployments'
  const [deploymentsKey, setDeploymentsKey] = useState(0); // Key to force refresh deployments list
  const [deploymentsView, setDeploymentsView] = useState('list'); // 'list', 'reports', 'audit-progress', 'audit-report', 'audit-reports-list'
  const [selectedAgentId, setSelectedAgentId] = useState(null);
  const [showAuditorModal, setShowAuditorModal] = useState(false);
  const [auditAgentId, setAuditAgentId] = useState(null);
  const [currentAuditId, setCurrentAuditId] = useState(null);

  // Set dark mode as default on mount (always enabled)
  useEffect(() => {
    document.documentElement.classList.add('dark');
    // Ensure it stays dark even if something tries to remove it
    const observer = new MutationObserver(() => {
      if (!document.documentElement.classList.contains('dark')) {
        document.documentElement.classList.add('dark');
      }
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });
    return () => observer.disconnect();
  }, []);

  const handleDeploymentSuccess = (deploymentResult) => {
    // Refresh deployments list
    setDeploymentsKey(prev => prev + 1);
    // Switch to deployments tab after successful deployment
    setActiveTab('deployments');
    setDeploymentsView('list');
  };

  const handleViewReports = (agentId) => {
    setSelectedAgentId(agentId);
    setDeploymentsView('reports');
  };

  const handleStartAudit = (agentId) => {
    setAuditAgentId(agentId);
    setShowAuditorModal(true);
  };

  const handleAuditStarted = (auditId) => {
    setCurrentAuditId(auditId);
    setShowAuditorModal(false);
    setDeploymentsView('audit-progress');
  };

  const handleAuditComplete = (auditId) => {
    setCurrentAuditId(auditId);
    setDeploymentsView('audit-report');
  };

  const handleAuditError = (error) => {
    console.error('Audit error:', error);
    // Could show error message or go back to list
  };

  const handleViewAuditReports = (agentId) => {
    setSelectedAgentId(agentId);
    setDeploymentsView('audit-reports-list');
  };

  const handleViewAudit = (auditId) => {
    setCurrentAuditId(auditId);
    setDeploymentsView('audit-report');
  };


  const handleBackToDeployments = () => {
    setDeploymentsView('list');
    setSelectedAgentId(null);
    // Refresh deployments list when going back
    setDeploymentsKey(prev => prev + 1);
  };

  const handleDeploymentDeleted = (agentId) => {
    // If the deleted agent is being viewed, go back to list
    if (selectedAgentId === agentId) {
      setDeploymentsView('list');
      setSelectedAgentId(null);
    }
    // Refresh deployments list
    setDeploymentsKey(prev => prev + 1);
  };

  const handleLoginSuccess = () => {
    reloadUser();
    // Stay on home page after login, user can navigate to dashboard
    setActiveTab('home');
  };

  // Show loading while checking authentication
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto"></div>
          <p className="mt-4 text-gray-300">Loading...</p>
        </div>
      </div>
    );
  }

  // Show home page if not authenticated
  if (!authenticated) {
    return (
      <div className="min-h-screen bg-slate-950">
        {/* Header */}
        <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-800/50 shadow-lg overflow-visible">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 overflow-visible">
            <div className="flex items-center justify-between overflow-visible">
              <div className="overflow-visible" style={{ paddingBottom: '0.15em', minHeight: 'fit-content' }}>
                <h1 
                  className="text-4xl font-extrabold gradient-text cursor-pointer hover:scale-105 transition-transform"
                  onClick={() => {
                    setActiveTab('home');
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                >
                  AgentCert
                </h1>
              </div>
              <div className="flex items-center gap-4">
                <ProfileDropdown onLoginSuccess={handleLoginSuccess} />
              </div>
            </div>
          </div>
        </header>

        {/* Navigation Tabs */}
        <div className="bg-slate-900/60 backdrop-blur-sm border-b border-slate-800/50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <nav className="flex space-x-8">
              <button
                onClick={() => {
                  setActiveTab('home');
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                className={`py-4 px-1 border-b-2 font-semibold text-sm transition-all ${
                  activeTab === 'home'
                    ? 'border-cyan-400 text-cyan-400'
                    : 'border-transparent text-gray-400 hover:text-cyan-300 hover:border-cyan-300/50'
                }`}
              >
                Home
              </button>
              <button
                onClick={() => setActiveTab('public-testing')}
                className={`py-4 px-1 border-b-2 font-semibold text-sm transition-all ${
                  activeTab === 'public-testing'
                    ? 'border-cyan-400 text-cyan-400'
                    : 'border-transparent text-gray-400 hover:text-cyan-300 hover:border-cyan-300/50'
                }`}
              >
                Public Testing
              </button>
            </nav>
          </div>
        </div>

        {/* Main Content */}
        <main className={activeTab === 'home' ? '' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8'}>
          {activeTab === 'home' && (
            <HomePage onNavigateToDeploy={() => setActiveTab('public-testing')} />
          )}
          {activeTab === 'public-testing' && <PublicTesting />}
        </main>

        {/* Footer */}
        <footer className="bg-slate-900/80 backdrop-blur-md border-t border-slate-800/50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <p className="text-center text-sm text-gray-400">
              AgentCert Platform - AI Agent Security Testing & Certification
            </p>
          </div>
        </footer>
      </div>
    );
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-slate-950">
        {/* Header */}
        <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-800/50 shadow-lg sticky top-0 z-50 overflow-visible">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 overflow-visible">
            <div className="flex items-center justify-between overflow-visible">
              <div className="overflow-visible" style={{ paddingBottom: '0.15em', minHeight: 'fit-content' }}>
                <h1 
                  className="text-4xl font-extrabold gradient-text cursor-pointer hover:scale-105 transition-transform"
                  onClick={() => {
                    setActiveTab('home');
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                >
                  AgentCert
                </h1>
              </div>
              <div className="flex items-center gap-4">
                <ProfileDropdown onLoginSuccess={handleLoginSuccess} />
              </div>
            </div>
          </div>
        </header>

      {/* Navigation Tabs */}
      <div className="bg-slate-900/60 backdrop-blur-sm border-b border-slate-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8">
            <button
              onClick={() => {
                setActiveTab('home');
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              className={`py-4 px-1 border-b-2 font-semibold text-sm transition-all ${
                activeTab === 'home'
                  ? 'border-cyan-400 text-cyan-400'
                  : 'border-transparent text-gray-400 hover:text-cyan-300 hover:border-cyan-300/50'
              }`}
            >
              Home
            </button>
            <button
              onClick={() => setActiveTab('deploy')}
              className={`py-4 px-1 border-b-2 font-semibold text-sm transition-all ${
                activeTab === 'deploy'
                  ? 'border-cyan-400 text-cyan-400'
                  : 'border-transparent text-gray-400 hover:text-cyan-300 hover:border-cyan-300/50'
              }`}
            >
              Deploy Agent
            </button>
            <button
              onClick={() => {
                setActiveTab('deployments');
                setDeploymentsView('list');
              }}
              className={`py-4 px-1 border-b-2 font-semibold text-sm transition-all ${
                activeTab === 'deployments'
                  ? 'border-cyan-400 text-cyan-400'
                  : 'border-transparent text-gray-400 hover:text-cyan-300 hover:border-cyan-300/50'
              }`}
            >
              Deployments
            </button>
            <button
              onClick={() => setActiveTab('public-testing')}
              className={`py-4 px-1 border-b-2 font-semibold text-sm transition-all ${
                activeTab === 'public-testing'
                  ? 'border-cyan-400 text-cyan-400'
                  : 'border-transparent text-gray-400 hover:text-cyan-300 hover:border-cyan-300/50'
              }`}
            >
              Public Testing
            </button>
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className={activeTab === 'home' ? '' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8'}>
        {activeTab === 'home' && (
          <HomePage onNavigateToDeploy={() => setActiveTab('deploy')} />
        )}

        {activeTab === 'deploy' && (
          <div>
            <DeploymentForm onDeploymentSuccess={handleDeploymentSuccess} />
          </div>
        )}

        {activeTab === 'deployments' && (
          <div>
            {deploymentsView === 'list' && (
              <DeploymentsList
                key={deploymentsKey}
                onViewReports={handleViewReports}
                onStartAudit={handleStartAudit}
                onViewAuditReports={handleViewAuditReports}
                onDeploymentDeleted={handleDeploymentDeleted}
              />
            )}
            {deploymentsView === 'reports' && selectedAgentId && (
              <div>
                <button
                  onClick={handleBackToDeployments}
                  className="mb-6 flex items-center gap-2 px-4 py-2 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50 rounded-lg text-gray-300 hover:text-white transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  Back to Deployments
                </button>
                <VulnerabilityReports agentId={selectedAgentId} />
              </div>
            )}
            {deploymentsView === 'audit-progress' && currentAuditId && (
              <div>
                <button
                  onClick={handleBackToDeployments}
                  className="mb-6 flex items-center gap-2 px-4 py-2 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50 rounded-lg text-gray-300 hover:text-white transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  Back to Deployments
                </button>
                <AuditProgress
                  auditId={currentAuditId}
                  onComplete={handleAuditComplete}
                  onError={handleAuditError}
                />
              </div>
            )}
            {deploymentsView === 'audit-report' && currentAuditId && (
              <div>
                <button
                  onClick={() => {
                    if (selectedAgentId) {
                      setDeploymentsView('audit-reports-list');
                    } else {
                      handleBackToDeployments();
                    }
                  }}
                  className="mb-6 flex items-center gap-2 px-4 py-2 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50 rounded-lg text-gray-300 hover:text-white transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  Back
                </button>
                <ChildSafetyReport auditId={currentAuditId} />
              </div>
            )}
            {deploymentsView === 'audit-reports-list' && selectedAgentId && (
              <div>
                <button
                  onClick={handleBackToDeployments}
                  className="mb-6 flex items-center gap-2 px-4 py-2 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50 rounded-lg text-gray-300 hover:text-white transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  Back to Deployments
                </button>
                <AuditReportsList agentId={selectedAgentId} onViewAudit={handleViewAudit} />
              </div>
            )}
          </div>
        )}

        {/* Auditor Selection Modal */}
        <AuditorSelectionModal
          isOpen={showAuditorModal}
          onClose={() => {
            setShowAuditorModal(false);
            setAuditAgentId(null);
          }}
          agentId={auditAgentId}
          onAuditStarted={handleAuditStarted}
        />

        {activeTab === 'public-testing' && (
          <PublicTesting />
        )}
      </main>

      {/* Footer - Only show on dashboard tabs, not on home page (home page has its own footer) */}
      {activeTab !== 'home' && (
        <footer className="bg-slate-900/80 backdrop-blur-md border-t border-slate-800/50 mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <p className="text-center text-sm text-gray-400">
              AgentCert Platform - AI Agent Security Testing & Certification
            </p>
          </div>
        </footer>
      )}
      </div>
    </ProtectedRoute>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
