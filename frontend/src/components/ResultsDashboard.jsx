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
  const [showFullPrompt, setShowFullPrompt] = useState({});

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
    if (score >= 80) return 'text-green-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getScoreBgColor = (score) => {
    if (score >= 80) return 'bg-green-900/20 border-green-700/50';
    if (score >= 50) return 'bg-yellow-900/20 border-yellow-700/50';
    return 'bg-red-900/20 border-red-700/50';
  };

  const toggleFullResponse = (violationId) => {
    setShowFullResponse({
      ...showFullResponse,
      [violationId]: !showFullResponse[violationId],
    });
  };

  const toggleFullPrompt = (violationId) => {
    setShowFullPrompt({
      ...showFullPrompt,
      [violationId]: !showFullPrompt[violationId],
    });
  };

  // Extract clean text from agent response (handles JSON objects, nested structures, etc.)
  // This function extracts text but does NOT remove agent ID prefixes - those are removed only for display
  const extractResponseText = (response) => {
    // Handle null/undefined
    if (!response && response !== '') return '';
    
    // If response is already a plain string (most common case after backend processing),
    // use it directly - preserve all content including agent ID prefixes
    if (typeof response === 'string') {
      const trimmed = response.trim();
      // If it's empty, return empty (don't try to extract from empty)
      if (!trimmed) return '';
      
      // If it's a plain string without JSON structure, return it as-is (with agent ID if present)
      if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
        return trimmed;
      }
      
      // It's a JSON-like string, will be handled by extractText below
    }
    
    // Helper function to recursively extract text from objects
    const extractText = (obj, depth = 0) => {
      // Prevent infinite recursion
      if (depth > 10) return '';
      
      // If it's already a plain string, return it
      if (typeof obj === 'string') {
        const trimmed = obj.trim();
        // If it looks like JSON, try to parse it
        if ((trimmed.startsWith('{') || trimmed.startsWith('[')) && depth === 0) {
          try {
            const parsed = JSON.parse(trimmed);
            return extractText(parsed, depth + 1);
          } catch (e) {
            // Not valid JSON - might be a Python dict string or malformed
            // Try to extract text using regex
            const patterns = [
              /"content"\s*:\s*\{[^}]*"text"\s*:\s*"((?:[^"\\]|\\.)*)"/,
              /"content"\s*:\s*"((?:[^"\\]|\\.)*)"/,
              /"text"\s*:\s*"((?:[^"\\]|\\.)*)"/,
              /'content'\s*:\s*\{[^}]*'text'\s*:\s*'((?:[^'\\]|\\.)*)'/,
              /'text'\s*:\s*'((?:[^'\\]|\\.)*)'/,
            ];
            
            for (const pattern of patterns) {
              const match = trimmed.match(pattern);
              if (match && match[1]) {
                let extracted = match[1]
                  .replace(/\\n/g, '\n')
                  .replace(/\\t/g, '\t')
                  .replace(/\\r/g, '\r')
                  .replace(/\\"/g, '"')
                  .replace(/\\'/g, "'")
                  .replace(/\\\\/g, '\\');
                if (extracted.trim().length > 0) {
                  return extracted;
                }
              }
            }
            // If extraction fails, return the original string (better than empty)
            return trimmed;
          }
        }
        return trimmed;
      }
      
      // If it's not an object, convert to string
      if (typeof obj !== 'object' || obj === null) {
        return String(obj);
      }
      
      // Handle arrays - look for text in array items
      if (Array.isArray(obj)) {
        // If array has one item, extract from that item
        if (obj.length === 1) {
          return extractText(obj[0], depth + 1);
        }
        // If array has multiple items, try to find text in each
        const texts = obj.map(item => extractText(item, depth + 1)).filter(t => t && t.trim());
        if (texts.length > 0) {
          return texts.join('\n');
        }
        return '';
      }
      
      // Handle objects - look for common text fields
      // Priority order: content.text > content (if string) > text > message > response
      // IMPORTANT: Extract text FIRST before checking/removing metadata
      
      // Check for nested content.text (common in NEST/A2A responses)
      // This is the most common format: { content: { text: "..." }, conversation_id: "...", role: "..." }
      if (obj.content !== undefined && obj.content !== null) {
        if (typeof obj.content === 'string') {
          // content is a direct string
          return obj.content;
        }
        if (typeof obj.content === 'object') {
          // content is an object - look for text field
          if (obj.content.text !== undefined && typeof obj.content.text === 'string') {
            return obj.content.text;
          }
          // Check if content is an array
          if (Array.isArray(obj.content)) {
            const contentTexts = obj.content
              .map(item => {
                if (typeof item === 'string') return item;
                if (item && typeof item === 'object' && item.text !== undefined && typeof item.text === 'string') {
                  return item.text;
                }
                return null;
              })
              .filter(t => t);
            if (contentTexts.length > 0) {
              return contentTexts.join('\n');
            }
          }
        }
      }
      
      // Check for direct text field (second priority)
      if (obj.text !== undefined && typeof obj.text === 'string') {
        return obj.text;
      }
      
      // Check for message field
      if (obj.message !== undefined) {
        const messageText = extractText(obj.message, depth + 1);
        if (messageText && messageText.trim()) return messageText;
      }
      
      // Check for response field
      if (obj.response !== undefined) {
        const responseText = extractText(obj.response, depth + 1);
        if (responseText && responseText.trim()) return responseText;
      }
      
      // Check for answer field
      if (obj.answer !== undefined && typeof obj.answer === 'string') {
        return obj.answer;
      }
      
      // Check for output field
      if (obj.output !== undefined && typeof obj.output === 'string') {
        return obj.output;
      }
      
      // Check for body field
      if (obj.body !== undefined && typeof obj.body === 'string') {
        return obj.body;
      }
      
      // Check for data field
      if (obj.data !== undefined) {
        const dataText = extractText(obj.data, depth + 1);
        if (dataText && dataText.trim()) return dataText;
      }
      
      // If no obvious text field, remove ALL metadata and see what's left
      const cleaned = { ...obj };
      // Remove ALL common metadata fields aggressively
      const metadataFields = [
        'conversation_id', 'conversationId', 'conversation_id',
        'role', 'type', 'timestamp', 'id', 'test_id',
        'status', 'error', 'passed', 'violations', 'severity',
        'category', 'prompt', 'description', 'agent_id',
        'created_at', 'updated_at', 'createdAt', 'updatedAt',
        'metadata', 'headers', 'request_id', 'requestId'
      ];
      metadataFields.forEach(field => delete cleaned[field]);
      
      // Get remaining keys after cleaning
      const keys = Object.keys(cleaned);
      
      // If only one field remains and it's a string, use it
      if (keys.length === 1) {
        const value = cleaned[keys[0]];
        if (typeof value === 'string' && value.trim()) {
          return value.trim();
        }
        // Try to extract from the single field
        if (typeof value === 'object' && value !== null) {
          const extracted = extractText(value, depth + 1);
          if (extracted) return extracted;
        }
      }
      
      // If multiple fields remain, prioritize text-containing fields
      // Check content/text fields first (already checked above, but double-check cleaned object)
      const textFields = ['content', 'text', 'message', 'response', 'answer', 'output', 'data', 'body'];
      for (const field of textFields) {
        if (cleaned[field]) {
          const extracted = extractText(cleaned[field], depth + 1);
          if (extracted && extracted.trim()) {
            return extracted.trim();
          }
        }
      }
      
      // Last resort: find the longest string value that doesn't look like metadata
      const stringValues = [];
      for (const key of keys) {
        const value = cleaned[key];
        if (typeof value === 'string' && value.trim().length > 5) {
          // Skip if it looks like metadata (UUIDs, IDs, etc.)
          const looksLikeMetadata = /^[a-f0-9-]{36}$/i.test(value.trim()) || // UUID
                                   /^\d{10,}$/.test(value.trim()) || // Timestamp
                                   value.trim().length < 10;
          
          if (!looksLikeMetadata) {
            stringValues.push({ value: value.trim(), length: value.trim().length });
          }
        } else if (typeof value === 'object' && value !== null) {
          // Try to extract from nested object
          const extracted = extractText(value, depth + 1);
          if (extracted && extracted.trim()) {
            stringValues.push({ value: extracted.trim(), length: extracted.trim().length });
          }
        }
      }
      
      // Return the longest string value (most likely to be the actual response)
      if (stringValues.length > 0) {
        stringValues.sort((a, b) => b.length - a.length);
        return stringValues[0].value;
      }
      
      // If we can't find any text in object, try to return a cleaned JSON representation
      // This ensures we show something rather than empty
      try {
        const cleaned = { ...obj };
        // Remove metadata fields
        const metadataFields = ['conversation_id', 'conversationId', 'role', 'type', 'timestamp', 'id'];
        metadataFields.forEach(field => delete cleaned[field]);
        
        // If there's anything left, return it as JSON string
        if (Object.keys(cleaned).length > 0) {
          return JSON.stringify(cleaned, null, 2);
        }
      } catch (e) {
        // If JSON operations fail, fall through
      }
      
      // Last resort: return string representation of the object
      return String(obj);
    };
    
    // Extract text first
    let extracted = '';
    if (typeof response === 'string') {
      const trimmed = response.trim();
      if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
        // It's a JSON string, try to parse and extract
        try {
          const parsed = JSON.parse(trimmed);
          extracted = extractText(parsed);
        } catch (e) {
          // Not valid JSON, use as-is
          extracted = trimmed;
        }
      } else {
        // Plain string
        extracted = trimmed;
      }
    } else {
      // For objects, use extractText
      extracted = extractText(response);
    }
    
    // Return extracted text WITHOUT removing agent ID prefix
    // Agent ID prefix will be removed only for display
    return extracted || '';
  };

  // Helper function to clean agent ID prefix for display only
  // This preserves the full metadata in the exported JSON
  const cleanAgentIdForDisplay = (text) => {
    if (!text || typeof text !== 'string') return text;
    // Remove patterns like [agent-73b2b38c] or [agent-xxxxx-xxxx] from the start
    // Pattern: [agent- followed by alphanumeric and hyphens, then ]
    return text
      .replace(/^\[agent-[a-z0-9][a-z0-9-]*\]\s*/i, '')  // [agent-xxxxx] at start
      .replace(/^\(agent-[a-z0-9][a-z0-9-]*\)\s*/i, '')  // (agent-xxxxx) at start
      .replace(/^agent-[a-z0-9][a-z0-9-]*:\s*/i, '')     // agent-xxxxx: at start
      .trim();
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
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl shadow-lg p-6 transition-colors">
        <div className="flex justify-center items-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl shadow-lg p-6 transition-colors">
        <div className="p-4 bg-red-900/20 border border-red-700/50 rounded-md">
          <p className="text-sm text-red-200">{error}</p>
          <button
            onClick={handleRefresh}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl shadow-lg p-6 transition-colors">
        <p className="text-gray-400 text-center py-12">No results available</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl shadow-lg p-6 transition-colors">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">Test Results</h2>
        <div className="flex gap-2">
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-slate-700 text-gray-300 rounded-md hover:bg-slate-600 text-sm transition-colors"
          >
            Refresh
          </button>
          <button
            onClick={exportResults}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm transition-colors"
          >
            Export JSON
          </button>
        </div>
      </div>

      {/* Security Score */}
      <div className={`mb-6 p-6 rounded-lg border-2 transition-colors ${getScoreBgColor(results.security_score)}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-300 mb-1">Security Score</p>
            <p className={`text-5xl font-bold ${getScoreColor(results.security_score)}`}>
              {results.security_score.toFixed(1)}
            </p>
            <p className="text-sm text-gray-400 mt-1">out of 100</p>
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
        <div className="bg-blue-900/20 border border-blue-700/50 rounded-lg p-4 transition-colors">
          <p className="text-sm font-medium text-blue-300 mb-1">Total Tests</p>
          <p className="text-2xl font-bold text-blue-200">{results.total_tests}</p>
        </div>
        <div className="bg-green-900/20 border border-green-700/50 rounded-lg p-4 transition-colors">
          <p className="text-sm font-medium text-green-300 mb-1">Passed</p>
          <p className="text-2xl font-bold text-green-200">{results.passed_tests}</p>
        </div>
        <div className="bg-red-900/20 border border-red-700/50 rounded-lg p-4 transition-colors">
          <p className="text-sm font-medium text-red-300 mb-1">Failed</p>
          <p className="text-2xl font-bold text-red-200">{results.failed_tests}</p>
        </div>
        <div className="bg-orange-900/20 border border-orange-700/50 rounded-lg p-4 transition-colors">
          <p className="text-sm font-medium text-orange-300 mb-1">Violations</p>
          <p className="text-2xl font-bold text-orange-200">{results.violations.length}</p>
        </div>
      </div>

      {/* Performance Metrics */}
      {results.performance && (
        <div className="mb-6 p-4 bg-slate-700/50 border border-slate-600 rounded-lg transition-colors">
          <h3 className="text-lg font-semibold text-white mb-3">Performance Metrics</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {results.performance.avg_response_time && (
              <div>
                <p className="text-sm font-medium text-gray-300">Average Response Time</p>
                <p className="text-xl font-bold text-white">
                  {results.performance.avg_response_time.toFixed(2)}s
                </p>
              </div>
            )}
            {results.performance.success_rate && (
              <div>
                <p className="text-sm font-medium text-gray-300">Success Rate</p>
                <p className="text-xl font-bold text-white">
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
          <h3 className="text-lg font-semibold text-white mb-3">Security Violations</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-700">
              <thead className="bg-slate-700/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Severity
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Prompt
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Response
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Description
                  </th>
                </tr>
              </thead>
              <tbody className="bg-slate-800/50 divide-y divide-slate-700">
                {results.violations.map((violation, index) => (
                  <tr key={index} className="hover:bg-slate-700/30 transition-colors">
                    <td className="px-4 py-3 text-sm text-white">{violation.category}</td>
                    <td className="px-4 py-3 text-sm">
                      <StatusBadge status={violation.severity} />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300 max-w-xs">
                      <div>
                        {showFullPrompt[`${violation.test_id}-${index}`] ? (
                          <div>
                            <div className="mb-1 whitespace-pre-wrap break-words text-gray-200">{violation.prompt}</div>
                            <button
                              onClick={() => toggleFullPrompt(`${violation.test_id}-${index}`)}
                              className="text-cyan-400 hover:text-cyan-300 text-xs font-medium"
                            >
                              Show less
                            </button>
                          </div>
                        ) : (
                          <div>
                            <div className="truncate text-gray-300">{violation.prompt}</div>
                            {violation.prompt && violation.prompt.length > 50 && (
                              <button
                                onClick={() => toggleFullPrompt(`${violation.test_id}-${index}`)}
                                className="text-cyan-400 hover:text-cyan-300 text-xs mt-1 font-medium"
                              >
                                Show more
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300 max-w-xs">
                      <div>
                        {(() => {
                          // Extract and clean the response text
                          const rawResponse = violation.agent_response;
                          let responseText = extractResponseText(rawResponse);
                          const violationId = `${violation.test_id}-${index}`;
                          
                          // If extraction returned empty, try fallback approaches
                          if (!responseText || responseText.trim() === '') {
                            if (rawResponse) {
                              // If rawResponse is a string, use it directly (backend should have cleaned it)
                              if (typeof rawResponse === 'string' && rawResponse.trim()) {
                                responseText = rawResponse.trim();
                              } 
                              // If it's an object, try to extract any meaningful content
                              else if (typeof rawResponse === 'object' && rawResponse !== null) {
                                // Try JSON stringify and extract again
                                try {
                                  const stringified = JSON.stringify(rawResponse, null, 2);
                                  responseText = extractResponseText(stringified);
                                  // If still empty, show the stringified version but clean it
                                  if (!responseText || responseText.trim() === '') {
                                    // Remove metadata fields from JSON
                                    const cleaned = JSON.parse(stringified);
                                    delete cleaned.conversation_id;
                                    delete cleaned.conversationId;
                                    delete cleaned.role;
                                    delete cleaned.type;
                                    delete cleaned.timestamp;
                                    delete cleaned.id;
                                    responseText = JSON.stringify(cleaned, null, 2);
                                  }
                                } catch (e) {
                                  // If JSON.stringify fails, just show the object as string
                                  responseText = String(rawResponse);
                                }
                              } else {
                                // Fallback to string representation
                                responseText = String(rawResponse);
                              }
                            }
                          }
                          
                          // Final fallback - show something useful
                          const rawDisplayText = (responseText && responseText.trim()) 
                            ? responseText.trim() 
                            : (rawResponse ? String(rawResponse) : 'No response available');
                          
                          // Clean agent ID prefix ONLY for display (preserves full metadata in export)
                          const displayText = cleanAgentIdForDisplay(rawDisplayText);
                          
                          return showFullResponse[violationId] ? (
                            <div>
                              <div className="mb-1 whitespace-pre-wrap break-words text-gray-200">{displayText}</div>
                              <button
                                onClick={() => toggleFullResponse(violationId)}
                                className="text-cyan-400 hover:text-cyan-300 text-xs font-medium"
                              >
                                Show less
                              </button>
                            </div>
                          ) : (
                            <div>
                              <div className="truncate text-gray-300">{displayText}</div>
                              {displayText && displayText.length > 50 && displayText !== 'No response available' && (
                                <button
                                  onClick={() => toggleFullResponse(violationId)}
                                  className="text-cyan-400 hover:text-cyan-300 text-xs mt-1 font-medium"
                                >
                                  Show more
                                </button>
                              )}
                            </div>
                          );
                        })()}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">{violation.description}</td>
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
            className="flex items-center justify-between w-full text-left text-lg font-semibold text-white mb-3 hover:text-gray-200"
          >
            <span>A2A Communication Logs</span>
            <span>{showA2ALogs ? '−' : '+'}</span>
          </button>
          {showA2ALogs && (
            <div className="p-4 bg-slate-700/50 border border-slate-600 rounded-lg transition-colors">
              <pre className="text-xs text-gray-300 overflow-x-auto">
                {JSON.stringify(results.a2a_logs, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Completed At */}
      {results.completed_at && (
        <div className="text-sm text-gray-400 text-center">
          Test completed at: {new Date(results.completed_at).toLocaleString()}
        </div>
      )}
    </div>
  );
};

export default ResultsDashboard;

