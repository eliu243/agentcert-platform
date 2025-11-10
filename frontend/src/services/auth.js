/**
 * Authentication service for GitHub OAuth
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TOKEN_STORAGE_KEY = 'agentcert_auth_token';

/**
 * Get stored authentication token
 */
export const getToken = () => {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
};

/**
 * Store authentication token
 */
export const setToken = (token) => {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
};

/**
 * Remove authentication token
 */
export const removeToken = () => {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
};

/**
 * Check if user is authenticated
 */
export const isAuthenticated = () => {
  return !!getToken();
};

/**
 * Initiate GitHub OAuth login
 * Redirects user to backend login endpoint which redirects to GitHub
 */
export const login = () => {
  window.location.href = `${API_BASE_URL}/api/auth/login`;
};

/**
 * Handle OAuth callback
 * Extracts token from URL and stores it
 */
export const handleCallback = () => {
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  const error = urlParams.get('error');
  
  if (error) {
    throw new Error(error);
  }
  
  if (token) {
    setToken(token);
    // Remove token from URL
    window.history.replaceState({}, document.title, window.location.pathname);
    return token;
  }
  
  return null;
};

/**
 * Logout user
 */
export const logout = async () => {
  try {
    const token = getToken();
    if (token) {
      // Call logout endpoint
      await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
    }
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    // Always remove token
    removeToken();
  }
};

/**
 * Get current user information
 */
export const getCurrentUser = async () => {
  try {
    const token = getToken();
    if (!token) {
      return null;
    }
    
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        // Token is invalid, remove it
        removeToken();
        return null;
      }
      throw new Error('Failed to get user information');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Get current user error:', error);
    return null;
  }
};

/**
 * Get user's GitHub repositories
 */
export const getUserRepos = async () => {
  try {
    const token = getToken();
    if (!token) {
      throw new Error('Not authenticated');
    }
    
    const response = await fetch(`${API_BASE_URL}/api/auth/repos`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        removeToken();
        throw new Error('Not authenticated');
      }
      throw new Error('Failed to fetch repositories');
    }
    
    const data = await response.json();
    return data.repos || [];
  } catch (error) {
    console.error('Get user repos error:', error);
    throw error;
  }
};

