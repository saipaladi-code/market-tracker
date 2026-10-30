import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User } from '../types';
import { api, getStoredUser, setStoredUser, getStoredAuthToken } from '../services/api';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  demoLogin: () => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const initialUser = getStoredUser();
  const hasToken = !!getStoredAuthToken();
  const [user, setUser] = useState<User | null>(hasToken ? initialUser : null);
  // Only show full-screen loader if there is a token but no cached user profile
  const [isLoading, setIsLoading] = useState<boolean>(hasToken && !initialUser);
  const [error, setError] = useState<string | null>(null);

  const checkSession = async () => {
    const token = getStoredAuthToken();
    if (!token) {
      setUser(null);
      setStoredUser(null);
      setIsLoading(false);
      return;
    }

    try {
      if (!initialUser) {
        setIsLoading(true);
      }
      setError(null);
      const currentUser = await api.getMe();
      setUser(currentUser);
      setStoredUser(currentUser);
    } catch (err: any) {
      // If server explicitly returned 401 Unauthorized, token has expired
      if (err?.response?.status === 401) {
        setUser(null);
        setStoredUser(null);
        api.setAuthToken(null);
      } else {
        // Cold start, network latency, or mobile hotspot lag:
        // KEEP existing stored user so analyst session is preserved without interruption
        console.warn('Session verification deferred (offline / sleeping backend):', err?.message);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkSession();

    // Listen for unauthorized 401 events from the API client (expired session)
    const unsubscribe = api.subscribeUnauthorized(() => {
      setUser(null);
      setStoredUser(null);
      api.setAuthToken(null);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const login = async (email: string, password: string, rememberMe = false) => {
    setError(null);
    try {
      const res = await api.login({ email, password, remember_me: rememberMe });
      setUser(res.user);
      setStoredUser(res.user);
      api.setAuthToken(res.token);
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Authentication failed. Please verify your credentials.';
      setError(msg);
      throw new Error(msg);
    }
  };

  const demoLogin = async () => {
    setError(null);
    try {
      const res = await api.demoLogin();
      setUser(res.user);
      setStoredUser(res.user);
      api.setAuthToken(res.token);
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Demo analyst login failed. Please retry.';
      setError(msg);
      throw new Error(msg);
    }
  };

  const register = async (fullName: string, email: string, password: string) => {
    setError(null);
    try {
      const res = await api.register({ full_name: fullName, email, password });
      setUser(res.user);
      setStoredUser(res.user);
      api.setAuthToken(res.token);
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Registration failed. Please review your input.';
      setError(msg);
      throw new Error(msg);
    }
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (err) {
      console.warn('Server logout error:', err);
    } finally {
      setUser(null);
      setStoredUser(null);
      api.setAuthToken(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        error,
        login,
        demoLogin,
        register,
        logout,
        checkSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
