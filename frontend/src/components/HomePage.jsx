import { useAuth } from '../contexts/AuthContext';
import { login } from '../services/auth';

const HomePage = ({ onNavigateToDeploy }) => {
  const { authenticated } = useAuth();

  const handleGetStarted = () => {
    if (authenticated) {
      // If authenticated, navigate to deploy tab
      if (onNavigateToDeploy) {
        onNavigateToDeploy();
      }
    } else {
      login();
    }
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="text-center">
          <div className="mb-8 overflow-visible" style={{ paddingBottom: '0.2em' }}>
            <h1 
              className="text-7xl font-extrabold gradient-text mb-4 tracking-tight"
            >
              AgentCert
            </h1>
            <div className="h-1 w-32 bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 mx-auto rounded-full"></div>
          </div>
          <p className="text-2xl text-gray-300 mb-4 max-w-3xl mx-auto font-light">
            Orchestration Platform for AI Agent Deployment & Security Testing
          </p>
          <p className="text-lg text-gray-400 mb-12 max-w-2xl mx-auto">
            Deploy your agents to real cloud environments, stress test them with malicious prompts, and get comprehensive insights and security performance metrics on their behavior.
          </p>
          <button
            onClick={handleGetStarted}
            className="inline-flex items-center gap-3 px-10 py-5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-lg font-bold rounded-xl transition-all shadow-2xl hover:shadow-cyan-500/50 hover:scale-105 transform duration-200"
          >
            {authenticated ? 'Go to Dashboard' : 'Get Started with GitHub'}
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        </div>
      </div>

      {/* Features Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <h2 className="text-4xl font-bold text-center text-white mb-4">
          Platform Capabilities
        </h2>
        <p className="text-center text-gray-400 mb-16 text-lg">Orchestrate, deploy, test, and analyze your AI agents in the cloud</p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-8 hover:border-cyan-500/50 transition-all hover:shadow-xl hover:shadow-cyan-500/10 hover:scale-105 transform duration-200">
            <div className="w-14 h-14 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center mb-6 shadow-lg">
              <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-white mb-3">
              Cloud Orchestration
            </h3>
            <p className="text-gray-300 leading-relaxed">
              Seamlessly orchestrate agent deployments to real cloud environments. Deploy directly from GitHub repositories with automated infrastructure provisioning and configuration.
            </p>
          </div>

          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-8 hover:border-purple-500/50 transition-all hover:shadow-xl hover:shadow-purple-500/10 hover:scale-105 transform duration-200">
            <div className="w-14 h-14 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl flex items-center justify-center mb-6 shadow-lg">
              <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-white mb-3">
              Stress Testing
            </h3>
            <p className="text-gray-300 leading-relaxed">
              Run comprehensive stress tests with malicious prompts and real-world attack scenarios. Test your agents against data exfiltration, prompt injection, and other security vulnerabilities in a controlled cloud environment.
            </p>
          </div>

          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-8 hover:border-blue-500/50 transition-all hover:shadow-xl hover:shadow-blue-500/10 hover:scale-105 transform duration-200">
            <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-cyan-600 rounded-xl flex items-center justify-center mb-6 shadow-lg">
              <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-white mb-3">
              Performance Metrics
            </h3>
            <p className="text-gray-300 leading-relaxed">
              Get comprehensive insights and security performance metrics on your agent's behavior. AI-powered analysis provides detailed violation reports, security scores (0-100), and behavioral analytics.
            </p>
          </div>

          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-8 hover:border-amber-500/50 transition-all hover:shadow-xl hover:shadow-amber-500/10 hover:scale-105 transform duration-200">
            <div className="w-14 h-14 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl flex items-center justify-center mb-6 shadow-lg">
              <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-white mb-3">
              Real Cloud Environment
            </h3>
            <p className="text-gray-300 leading-relaxed">
              Deploy your agents to real cloud infrastructure (AWS EC2) for authentic testing. Automated provisioning, configuration, and NEST infrastructure integration make deployment effortless.
            </p>
          </div>

          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-8 hover:border-red-500/50 transition-all hover:shadow-xl hover:shadow-red-500/10 hover:scale-105 transform duration-200">
            <div className="w-14 h-14 bg-gradient-to-br from-red-500 to-pink-600 rounded-xl flex items-center justify-center mb-6 shadow-lg">
              <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-white mb-3">
              Security Insights
            </h3>
            <p className="text-gray-300 leading-relaxed">
              Get detailed security insights and behavioral analysis. Identify vulnerabilities, track performance metrics, and understand how your agent responds to various attack vectors.
            </p>
          </div>

          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-8 hover:border-indigo-500/50 transition-all hover:shadow-xl hover:shadow-indigo-500/10 hover:scale-105 transform duration-200">
            <div className="w-14 h-14 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center mb-6 shadow-lg">
              <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-white mb-3">
              Comprehensive Analytics
            </h3>
            <p className="text-gray-300 leading-relaxed">
              Access detailed analytics dashboards with test results, A2A communication logs, performance metrics, security scores, and behavioral insights. Export data as JSON for further analysis.
            </p>
          </div>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="bg-slate-900/50 backdrop-blur-sm py-20 border-y border-slate-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl font-bold text-center text-white mb-4">
            How It Works
          </h2>
          <p className="text-center text-gray-400 mb-16 text-lg">Simple, secure, and efficient</p>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="text-center group">
              <div className="w-20 h-20 bg-gradient-to-br from-cyan-500 to-blue-600 text-white rounded-2xl flex items-center justify-center text-3xl font-bold mx-auto mb-6 shadow-lg group-hover:scale-110 transition-transform duration-200">
                1
              </div>
              <h3 className="text-xl font-bold text-white mb-3">
                Deploy to Cloud
              </h3>
              <p className="text-gray-300 text-sm leading-relaxed">
                Select a repository from GitHub and orchestrate deployment to real cloud infrastructure. Automated provisioning and configuration handled seamlessly.
              </p>
            </div>
            <div className="text-center group">
              <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-600 text-white rounded-2xl flex items-center justify-center text-3xl font-bold mx-auto mb-6 shadow-lg group-hover:scale-110 transition-transform duration-200">
                2
              </div>
              <h3 className="text-xl font-bold text-white mb-3">
                Stress Test
              </h3>
              <p className="text-gray-300 text-sm leading-relaxed">
                Execute comprehensive stress tests with malicious prompts and real-world attack scenarios in your cloud-deployed environment.
              </p>
            </div>
            <div className="text-center group">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-cyan-600 text-white rounded-2xl flex items-center justify-center text-3xl font-bold mx-auto mb-6 shadow-lg group-hover:scale-110 transition-transform duration-200">
                3
              </div>
              <h3 className="text-xl font-bold text-white mb-3">
                Get Insights
              </h3>
              <p className="text-gray-300 text-sm leading-relaxed">
                Receive comprehensive insights and security performance metrics on your agent's behavior. AI-powered analysis identifies vulnerabilities and tracks performance.
              </p>
            </div>
            <div className="text-center group">
              <div className="w-20 h-20 bg-gradient-to-br from-amber-500 to-orange-600 text-white rounded-2xl flex items-center justify-center text-3xl font-bold mx-auto mb-6 shadow-lg group-hover:scale-110 transition-transform duration-200">
                4
              </div>
              <h3 className="text-xl font-bold text-white mb-3">
                Analyze & Optimize
              </h3>
              <p className="text-gray-300 text-sm leading-relaxed">
                Review detailed analytics, security scores, and behavioral metrics. Use insights to optimize your agent's security and performance.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="bg-gradient-to-br from-cyan-600/20 via-blue-600/20 to-purple-600/20 backdrop-blur-md border border-cyan-500/30 rounded-3xl p-16 text-center shadow-2xl">
          <h2 className="text-4xl font-bold text-white mb-6">
            Ready to Deploy & Test Your AI Agents?
          </h2>
          <p className="text-xl text-gray-300 mb-10">
            Orchestrate cloud deployments, stress test your agents, and get comprehensive performance metrics—all in one platform.
          </p>
          <button
            onClick={handleGetStarted}
            className="inline-flex items-center gap-3 px-10 py-5 bg-white text-slate-900 text-lg font-bold rounded-xl hover:bg-gray-100 transition-all shadow-2xl hover:scale-105 transform duration-200"
          >
            {authenticated ? 'Go to Dashboard' : 'Get Started with GitHub'}
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        </div>
      </div>

      {/* Footer - only show when embedded in authenticated view */}
      {authenticated && (
        <footer className="bg-slate-900/80 backdrop-blur-md border-t border-slate-800/50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <p className="text-center text-sm text-gray-400">
              AgentCert Platform - AI Agent Security Testing & Certification
            </p>
          </div>
        </footer>
      )}
    </div>
  );
};

export default HomePage;

