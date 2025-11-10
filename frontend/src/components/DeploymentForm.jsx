import { useState } from 'react';
import { deployAgent } from '../services/api';
import LoadingSpinner from './LoadingSpinner';
import StatusBadge from './StatusBadge';

const DeploymentForm = ({ onDeploymentSuccess }) => {
  const [githubRepo, setGithubRepo] = useState('');
  const [branch, setBranch] = useState('main');
  const [entryPoint, setEntryPoint] = useState('agent.py');
  const [apiKeys, setApiKeys] = useState([]); // Array of { key: string, value: string }
  const [selectedApiKeyType, setSelectedApiKeyType] = useState('');
  const [customKeyName, setCustomKeyName] = useState('');
  const [isDeploying, setIsDeploying] = useState(false);
  const [deploymentStatus, setDeploymentStatus] = useState(null);
  const [error, setError] = useState(null);
  const [showApiKeys, setShowApiKeys] = useState(false);

  // Predefined API key options
  const apiKeyOptions = [
    { value: 'OPENAI_API_KEY', label: 'OpenAI API Key', placeholder: 'sk-...' },
    { value: 'ANTHROPIC_API_KEY', label: 'Anthropic API Key', placeholder: 'sk-ant-...' },
    { value: 'GOOGLE_API_KEY', label: 'Google API Key', placeholder: 'AIza...' },
    { value: 'COHERE_API_KEY', label: 'Cohere API Key', placeholder: 'co-...' },
    { value: 'HUGGINGFACE_API_KEY', label: 'Hugging Face API Key', placeholder: 'hf_...' },
    { value: 'AZURE_OPENAI_API_KEY', label: 'Azure OpenAI API Key', placeholder: '...' },
    { value: 'PALM_API_KEY', label: 'Google PaLM API Key', placeholder: '...' },
    { value: 'CUSTOM', label: 'Custom API Key', placeholder: 'Enter custom key name' },
  ];

  const handleAddApiKey = () => {
    if (!selectedApiKeyType) return;

    if (selectedApiKeyType === 'CUSTOM') {
      // For custom keys, we need a name
      if (!customKeyName.trim()) {
        setError('Please enter a custom API key name');
        return;
      }
      // Check if key already exists
      if (apiKeys.some(k => k.key === customKeyName.trim())) {
        setError(`API key "${customKeyName.trim()}" already added`);
        return;
      }
      setApiKeys([...apiKeys, { key: customKeyName.trim(), value: '' }]);
      setCustomKeyName('');
    } else {
      // Check if key already exists
      if (apiKeys.some(k => k.key === selectedApiKeyType)) {
        setError(`API key "${selectedApiKeyType}" already added`);
        return;
      }
      const selectedOption = apiKeyOptions.find(opt => opt.value === selectedApiKeyType);
      setApiKeys([...apiKeys, { key: selectedApiKeyType, value: '', placeholder: selectedOption?.placeholder || '' }]);
    }
    setSelectedApiKeyType('');
    setError(null);
  };

  const handleApiKeyValueChange = (keyName, value) => {
    setApiKeys(apiKeys.map(k => k.key === keyName ? { ...k, value } : k));
  };

  const handleRemoveApiKey = (keyName) => {
    setApiKeys(apiKeys.filter(k => k.key !== keyName));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsDeploying(true);
    setError(null);
    setDeploymentStatus(null);

    try {
      // Collect all API keys (filter out empty ones)
      const allApiKeys = {};
      
      apiKeys.forEach((item) => {
        if (item.key && item.value) {
          allApiKeys[item.key] = item.value;
        }
      });

      const result = await deployAgent(
        githubRepo,
        branch,
        entryPoint,
        Object.keys(allApiKeys).length > 0 ? allApiKeys : null
      );

      setDeploymentStatus(result);
      if (onDeploymentSuccess) {
        onDeploymentSuccess(result);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsDeploying(false);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 transition-colors">
      <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-6">Deploy Agent</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* GitHub Repository URL */}
        <div>
          <label htmlFor="githubRepo" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            GitHub Repository URL *
          </label>
          <input
            type="text"
            id="githubRepo"
            value={githubRepo}
            onChange={(e) => setGithubRepo(e.target.value)}
            required
            placeholder="https://github.com/username/repo.git"
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:focus:border-blue-400"
          />
        </div>

        {/* Branch */}
        <div>
          <label htmlFor="branch" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Branch
          </label>
          <input
            type="text"
            id="branch"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            placeholder="main"
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:focus:border-blue-400"
          />
        </div>

        {/* Entry Point */}
        <div>
          <label htmlFor="entryPoint" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Entry Point
          </label>
          <input
            type="text"
            id="entryPoint"
            value={entryPoint}
            onChange={(e) => setEntryPoint(e.target.value)}
            placeholder="agent.py"
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:focus:border-blue-400"
          />
        </div>

        {/* API Keys Section */}
        <div>
          <button
            type="button"
            onClick={() => setShowApiKeys(!showApiKeys)}
            className="flex items-center justify-between w-full text-left text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 hover:text-gray-900 dark:hover:text-white"
          >
            <span>API Keys (Optional)</span>
            <span>{showApiKeys ? '−' : '+'}</span>
          </button>

          {showApiKeys && (
            <div className="space-y-4 pl-4 border-l-2 border-gray-200 dark:border-gray-600">
              {/* Add API Key Dropdown */}
              <div className="space-y-2">
                <label htmlFor="apiKeyType" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Select API Key Type
                </label>
                <div className="flex gap-2">
                  <select
                    id="apiKeyType"
                    value={selectedApiKeyType}
                    onChange={(e) => {
                      setSelectedApiKeyType(e.target.value);
                      setError(null);
                    }}
                    className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:focus:border-blue-400"
                  >
                    <option value="">Choose an API key...</option>
                    {apiKeyOptions
                      .filter(option => {
                        // For predefined options, filter out already added ones
                        if (option.value !== 'CUSTOM') {
                          return !apiKeys.some(k => k.key === option.value);
                        }
                        // Always show CUSTOM option
                        return true;
                      })
                      .map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                  </select>
                  <button
                    type="button"
                    onClick={handleAddApiKey}
                    disabled={!selectedApiKeyType}
                    className="px-4 py-2 bg-blue-600 dark:bg-blue-700 text-white rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 disabled:bg-gray-400 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
                  >
                    Add
                  </button>
                </div>

                {/* Custom Key Name Input (only show when CUSTOM is selected) */}
                {selectedApiKeyType === 'CUSTOM' && (
                  <div>
                    <label htmlFor="customKeyName" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Custom API Key Name
                    </label>
                    <input
                      type="text"
                      id="customKeyName"
                      value={customKeyName}
                      onChange={(e) => setCustomKeyName(e.target.value)}
                      placeholder="e.g., MY_CUSTOM_API_KEY"
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:focus:border-blue-400"
                    />
                  </div>
                )}
              </div>

              {/* Display Added API Keys */}
              {apiKeys.length > 0 && (
                <div className="space-y-3">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Added API Keys ({apiKeys.length})
                  </p>
                  {apiKeys.map((apiKey) => {
                    const option = apiKeyOptions.find(opt => opt.value === apiKey.key);
                    const displayLabel = option ? option.label : apiKey.key;
                    const placeholder = apiKey.placeholder || option?.placeholder || 'Enter API key value';
                    
                    return (
                      <div key={apiKey.key} className="flex gap-2 items-start">
                        <div className="flex-1">
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            {displayLabel}
                          </label>
                          <input
                            type="password"
                            value={apiKey.value}
                            onChange={(e) => handleApiKeyValueChange(apiKey.key, e.target.value)}
                            placeholder={placeholder}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:focus:border-blue-400"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveApiKey(apiKey.key)}
                          className="mt-6 px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700 transition-colors text-sm font-medium"
                          title="Remove API key"
                        >
                          Remove
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}

              {apiKeys.length === 0 && (
                <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                  No API keys added yet. Select an API key type above to add one.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {/* Deployment Status */}
        {deploymentStatus && (
          <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md">
            <div className="flex items-center gap-2 mb-2">
              <StatusBadge status={deploymentStatus.status} />
              <span className="text-sm font-medium text-green-800 dark:text-green-200">
                Agent ID: {deploymentStatus.agent_id}
              </span>
            </div>
            {deploymentStatus.agent_url && (
              <p className="text-sm text-green-700 dark:text-green-300">
                Agent URL: <span className="font-mono">{deploymentStatus.agent_url}</span>
              </p>
            )}
            {deploymentStatus.message && (
              <p className="text-sm text-green-700 dark:text-green-300 mt-1">{deploymentStatus.message}</p>
            )}
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isDeploying || !githubRepo}
          className="w-full px-6 py-3 bg-blue-600 dark:bg-blue-700 text-white rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 disabled:bg-gray-400 dark:disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
        >
          {isDeploying ? (
            <>
              <LoadingSpinner size="sm" />
              <span>Deploying...</span>
            </>
          ) : (
            'Deploy Agent'
          )}
        </button>
      </form>
    </div>
  );
};

export default DeploymentForm;

