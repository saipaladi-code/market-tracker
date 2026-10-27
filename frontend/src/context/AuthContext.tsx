import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User } from '../types';
import { api } from '../services/api';

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
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const checkSession = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const currentUser = await api.getMe();
      setUser(currentUser);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkSession();

    // Listen for unauthorized 401 events from the API client (expired session)
    const unsubscribe = api.subscribeUnauthorized(() => {
      setUser(null);
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
