import { useState, useEffect } from 'react';
import { listPublicAgents, testAgent } from '../services/api';
import VulnerabilityReportModal from './VulnerabilityReportModal';
import LoadingSpinner from './LoadingSpinner';

const PublicTesting = () => {
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [message, setMessage] = useState('');
  const [conversation, setConversation] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingAgents, setLoadingAgents] = useState(true);
  const [error, setError] = useState(null);
  const [showReportModal, setShowReportModal] = useState(false);

  useEffect(() => {
    loadPublicAgents();
  }, []);

  const loadPublicAgents = async () => {
    setLoadingAgents(true);
    setError(null);
    try {
      const data = await listPublicAgents();
      setAgents(data);
    } catch (err) {
      setError(err.message || 'Failed to load public agents');
    } finally {
      setLoadingAgents(false);
    }
  };

  const handleSelectAgent = (agent) => {
    setSelectedAgent(agent);
    setConversation([]);
    setConversationId(null);
    setMessage('');
  };

  const handleTestAgent = async () => {
    if (!message.trim() || !selectedAgent || loading) return;

    setLoading(true);
    setError(null);
    const userMessage = message.trim();
    setMessage('');

    try {
      const response = await testAgent(
        selectedAgent.agent_id,
        userMessage,
        conversationId
      );

      // Update conversation ID if this is a new conversation
      if (!conversationId && response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      setConversation((prev) => [
        ...prev,
        { role: 'user', content: userMessage },
        { role: 'agent', content: response.agent_response }
      ]);
    } catch (err) {
      setError(err.message || 'Failed to test agent');
    } finally {
      setLoading(false);
    }
  };

  const handleReportVulnerability = () => {
    if (conversation.length === 0) return;

    const lastUserMessage = conversation
      .filter((m) => m.role === 'user')
      .pop();
    const lastAgentResponse = conversation
      .filter((m) => m.role === 'agent')
      .pop();

    if (lastUserMessage && lastAgentResponse) {
      setShowReportModal(true);
    }
  };

  const getLastUserMessage = () => {
    const lastUser = conversation.filter((m) => m.role === 'user').pop();
    return lastUser ? lastUser.content : '';
  };

  const getLastAgentResponse = () => {
    const lastAgent = conversation.filter((m) => m.role === 'agent').pop();
    return lastAgent ? lastAgent.content : '';
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">Crowdsourced Agent Testing</h1>
        <p className="text-gray-400">
          Test publicly available agents and help find security vulnerabilities
        </p>
      </div>

      {error && (
        <div className="mb-4 bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Agent List */}
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-white">Available Agents</h2>
            <button
              onClick={loadPublicAgents}
              className="text-cyan-400 hover:text-cyan-300 text-sm"
              disabled={loadingAgents}
            >
              {loadingAgents ? 'Loading...' : 'Refresh'}
            </button>
          </div>

          {loadingAgents ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : agents.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <p>No public agents available</p>
              <p className="text-sm mt-2">Agents will appear here when owners make them public</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {agents.map((agent) => (
                <div
                  key={agent.agent_id}
                  onClick={() => handleSelectAgent(agent)}
                  className={`p-3 rounded-lg cursor-pointer transition-colors ${
                    selectedAgent?.agent_id === agent.agent_id
                      ? 'bg-cyan-600/30 border border-cyan-500'
                      : 'bg-slate-700/50 hover:bg-slate-700 border border-slate-600/50'
                  }`}
                >
                  <div className="font-semibold text-white text-sm">{agent.agent_id}</div>
                  <div className="text-xs text-gray-400 mt-1">
                    by {agent.owner_username}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {agent.test_count} tests
                    {agent.security_score !== null && (
                      <span className="ml-2">
                        • Score: {agent.security_score?.toFixed(1)}
                      </span>
                    )}
                  </div>
                  {agent.description && (
                    <div className="text-xs text-gray-400 mt-2 italic">
                      {agent.description}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Chat Interface */}
        <div className="md:col-span-2 bg-slate-800/50 rounded-lg p-4 border border-slate-700/50 flex flex-col">
          {selectedAgent ? (
            <>
              <div className="mb-4 pb-4 border-b border-slate-700/50">
                <h2 className="text-xl font-bold text-white">{selectedAgent.agent_id}</h2>
                <p className="text-sm text-gray-400">
                  Testing agent by {selectedAgent.owner_username}
                </p>
                {selectedAgent.description && (
                  <p className="text-sm text-gray-300 mt-2">{selectedAgent.description}</p>
                )}
              </div>

              {/* Conversation */}
              <div className="flex-1 overflow-y-auto mb-4 space-y-3 min-h-[400px] max-h-[500px]">
                {conversation.length === 0 ? (
                  <div className="text-center text-gray-400 py-12">
                    <p>Start a conversation with this agent</p>
                    <p className="text-sm mt-2">Try testing for vulnerabilities like jailbreaks or prompt injection</p>
                  </div>
                ) : (
                  conversation.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg ${
                        msg.role === 'user'
                          ? 'bg-cyan-600/20 ml-8 border border-cyan-500/30'
                          : 'bg-slate-700/50 mr-8 border border-slate-600/50'
                      }`}
                    >
                      <div className="text-xs text-gray-400 mb-1">
                        {msg.role === 'user' ? 'You' : 'Agent'}
                      </div>
                      <div className="text-white whitespace-pre-wrap">{msg.content}</div>
                    </div>
                  ))
                )}
                {loading && (
                  <div className="text-center text-gray-400 py-2">
                    <LoadingSpinner />
                  </div>
                )}
              </div>

              {/* Message Input */}
              <div className="space-y-2">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleTestAgent();
                      }
                    }}
                    placeholder="Type a test message..."
                    className="flex-1 bg-slate-700 text-white p-3 rounded-lg border border-slate-600 focus:border-cyan-500 focus:outline-none"
                    disabled={loading}
                  />
                  <button
                    onClick={handleTestAgent}
                    disabled={loading || !message.trim()}
                    className="bg-cyan-600 px-6 py-3 rounded-lg text-white font-semibold hover:bg-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {loading ? 'Sending...' : 'Send'}
                  </button>
                </div>

                {/* Report Vulnerability Button */}
                {conversation.length > 0 && (
                  <button
                    onClick={handleReportVulnerability}
                    className="w-full bg-red-600/20 hover:bg-red-600/30 border border-red-600/50 text-red-300 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                  >
                    Report Vulnerability
                  </button>
                )}
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-center text-gray-400 py-12">
              <div>
                <p className="text-lg mb-2">Select an agent to start testing</p>
                <p className="text-sm">Choose an agent from the list to begin</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Vulnerability Report Modal */}
      {selectedAgent && (
        <VulnerabilityReportModal
          isOpen={showReportModal}
          onClose={() => setShowReportModal(false)}
          agentId={selectedAgent.agent_id}
          prompt={getLastUserMessage()}
          agentResponse={getLastAgentResponse()}
        />
      )}
    </div>
  );
};

export default PublicTesting;

