import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { TrendingUp, Mail, Lock, Eye, EyeOff, AlertCircle, Loader2, ArrowRight, ShieldCheck } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login, demoLogin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Extract redirect query parameter if provided
  const queryParams = new URLSearchParams(location.search);
  const redirectTarget = queryParams.get('redirect') ? decodeURIComponent(queryParams.get('redirect')!) : '/';

  const validateForm = (): boolean => {
    if (!email.trim()) {
      setFormError('Email address is required.');
      return false;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setFormError('Please enter a valid financial email address.');
      return false;
    }
    if (!password) {
      setFormError('Password is required.');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!validateForm()) return;

    try {
      setLoading(true);
      await login(email.trim(), password, rememberMe);
      navigate(redirectTarget, { replace: true });
    } catch (err: any) {
      setFormError(err.message || 'Authentication failed. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-navy-950 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden select-none">
      {/* Background Decorative Radial Glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-gradient-to-b from-blue-600/10 via-cyan-500/5 to-transparent blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-xl shadow-blue-500/20 mb-3 border border-blue-400/20">
            <TrendingUp className="w-6 h-6" />
          </div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-extrabold tracking-wider text-white">FIN-SENTIMENT</h1>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
              PRO
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400 max-w-xs">
            Institutional AI Financial News Intelligence & Market Sentiment Platform
          </p>
        </div>

        {/* Login Card */}
        <div className="mt-8 bg-navy-900/90 border border-navy-750/80 rounded-2xl shadow-2xl p-6 sm:p-8 backdrop-blur-xl">
          <div className="flex items-center justify-between pb-5 mb-5 border-b border-navy-750/60">
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">Analyst Sign In</h2>
              <p className="text-xs text-slate-400 mt-0.5">Access terminal analytics & FinBERT lab</p>
            </div>
            <div className="flex items-center gap-1 px-2 py-1 rounded bg-navy-800/80 border border-navy-700 text-[10px] font-mono text-cyan-400">
              <ShieldCheck className="w-3 h-3" />
              <span>TLS / SHA-256</span>
            </div>
          </div>

          {/* Error Banner */}
          {formError && (
            <div className="mb-5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-xs text-rose-300 animate-in fade-in duration-200">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div className="flex-1 leading-relaxed">{formError}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Field */}
            <div>
              <label htmlFor="login-email" className="block text-xs font-semibold text-slate-300 mb-1.5">
                Work Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  id="login-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@firm.com"
                  autoComplete="email"
                  disabled={loading}
                  className="w-full bg-navy-800/90 border border-navy-750 text-slate-100 placeholder-slate-500 text-xs sm:text-sm rounded-xl pl-10 pr-4 py-2.5 sm:py-3 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors disabled:opacity-50"
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="login-password" className="block text-xs font-semibold text-slate-300">
                  Password
                </label>
                <Link
                  to="/forgot-password"
                  className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors font-medium"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  autoComplete="current-password"
                  disabled={loading}
                  className="w-full bg-navy-800/90 border border-navy-750 text-slate-100 placeholder-slate-500 text-xs sm:text-sm rounded-xl pl-10 pr-10 py-2.5 sm:py-3 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors disabled:opacity-50 font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300 cursor-pointer"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Remember Me Option */}
            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  disabled={loading}
                  className="w-4 h-4 rounded border-navy-750 bg-navy-800 text-blue-600 focus:ring-blue-500 focus:ring-offset-navy-900 cursor-pointer"
                />
                <span className="text-xs text-slate-400">Remember this terminal session (30 days)</span>
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3 px-4 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold rounded-xl text-xs sm:text-sm shadow-lg shadow-blue-600/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Terminal</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            {/* Quick Demo Sign-In Button */}
            <div className="relative flex py-1 items-center">
              <div className="flex-grow border-t border-navy-750"></div>
              <span className="flex-shrink mx-2 text-[10px] uppercase font-mono text-slate-500">or</span>
              <div className="flex-grow border-t border-navy-750"></div>
            </div>

            <button
              type="button"
              disabled={loading}
              onClick={async () => {
                try {
                  setLoading(true);
                  setFormError(null);
                  await demoLogin();
                  navigate(redirectTarget, { replace: true });
                } catch (err: any) {
                  setFormError(err.message || 'Demo analyst login failed.');
                } finally {
                  setLoading(false);
                }
              }}
              className="w-full py-2.5 px-4 bg-navy-800/80 hover:bg-navy-800 text-cyan-400 hover:text-cyan-300 border border-cyan-500/30 rounded-xl text-xs font-semibold transition-all flex items-center justify-center gap-2 cursor-pointer shadow-sm hover:border-cyan-400/50"
            >
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              <span>Instant Demo Analyst Sign-In (1-Click)</span>
            </button>
          </form>

          {/* Footer link to register */}
          <div className="mt-6 pt-5 border-t border-navy-750/60 text-center">
            <p className="text-xs text-slate-400">
              Don't have an analyst account?{' '}
              <Link
                to={redirectTarget !== '/' ? `/signup?redirect=${encodeURIComponent(redirectTarget)}` : '/signup'}
                className="text-cyan-400 hover:text-cyan-300 font-semibold transition-colors"
              >
                Create Account
              </Link>
            </p>
          </div>
        </div>

        {/* Security Notice */}
        <p className="mt-6 text-center text-[11px] text-slate-500">
          Encrypted authentication via bcrypt & signed JWT sessions.
        </p>
      </div>
    </div>
  );
};
