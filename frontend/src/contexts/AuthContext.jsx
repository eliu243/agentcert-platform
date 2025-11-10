import { createContext, useContext, useState, useEffect } from 'react';
import { getToken, getCurrentUser, isAuthenticated, handleCallback } from '../services/auth';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  const checkAuth = async () => {
    setLoading(true);
    try {
      if (isAuthenticated()) {
        const userData = await getCurrentUser();
        if (userData) {
          setUser(userData);
          setAuthenticated(true);
        } else {
          setAuthenticated(false);
        }
      } else {
        setAuthenticated(false);
      }
    } catch (error) {
      console.error('Auth check error:', error);
      setAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const loadUser = async () => {
    setLoading(true);
    try {
      if (isAuthenticated()) {
        const userData = await getCurrentUser();
        if (userData) {
          setUser(userData);
          setAuthenticated(true);
        } else {
          setAuthenticated(false);
          setUser(null);
        }
      } else {
        setAuthenticated(false);
        setUser(null);
      }
    } catch (error) {
      console.error('Load user error:', error);
      setAuthenticated(false);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Check for OAuth callback token in URL first
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    
    if (token) {
      // Handle OAuth callback
      setLoading(true);
      try {
        handleCallback();
        // Remove token from URL
        window.history.replaceState({}, document.title, window.location.pathname);
        // Reload user after storing token
        loadUser();
      } catch (error) {
        console.error('Auth callback error:', error);
        setLoading(false);
        setAuthenticated(false);
      }
    } else {
      // Check if user is already authenticated
      checkAuth();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = {
    user,
    authenticated,
    loading,
    reloadUser: loadUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

