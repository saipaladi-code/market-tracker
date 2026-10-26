import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { TrendingUp, Loader2 } from 'lucide-react';

export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-navy-950 flex flex-col items-center justify-center p-4">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-xl shadow-blue-500/25 animate-pulse">
            <TrendingUp className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-sm font-extrabold tracking-wider text-white">FIN-SENTIMENT</h1>
            <p className="text-xs text-slate-400 mt-0.5">Authenticating institutional analyst session...</p>
          </div>
          <Loader2 className="w-5 h-5 text-cyan-400 animate-spin mt-2" />
        </div>
      </div>
    );
  }

  if (!user) {
    const returnUrl = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?redirect=${returnUrl}`} replace />;
  }

  return <>{children}</>;
};

export const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-navy-950 flex flex-col items-center justify-center p-4">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-xl shadow-blue-500/25 animate-pulse">
            <TrendingUp className="w-6 h-6" />
          </div>
          <Loader2 className="w-5 h-5 text-cyan-400 animate-spin mt-2" />
        </div>
      </div>
    );
  }

  if (user) {
    const params = new URLSearchParams(location.search);
    const redirect = params.get('redirect');
    const destination = redirect ? decodeURIComponent(redirect) : '/';
    return <Navigate to={destination} replace />;
  }

  return <>{children}</>;
};
