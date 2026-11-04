import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { TrendingUp, Lock, Eye, EyeOff, AlertCircle, CheckCircle2, Loader2, ArrowRight } from 'lucide-react';
import { LanguageSelector } from '../components/LanguageSelector';

export const ResetPasswordPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  // 1. Automatically extract token from URL query parameters (e.g. ?token=ABC123)
  const queryParams = new URLSearchParams(location.search);
  const initialToken = queryParams.get('token') || '';

  // 2. Temporary frontend state (never stored in localStorage, never logged, never rendered as visible text)
  const [token, setToken] = useState(initialToken);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [isTokenInvalid, setIsTokenInvalid] = useState(!initialToken.trim());
  const [success, setSuccess] = useState(false);
  const [countdown, setCountdown] = useState(3);

  // Clear temporary token state when component unmounts
  useEffect(() => {
    return () => {
      setToken('');
    };
  }, []);

  // Countdown redirect to login upon successful password reset
  useEffect(() => {
    if (success) {
      const interval = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(interval);
            navigate('/login');
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [success, navigate]);

  // Password strength validation: >=8 chars, uppercase, lowercase, number
  const hasMinLength = newPassword.length >= 8;
  const hasUpperCase = /[A-Z]/.test(newPassword);
  const hasLowerCase = /[a-z]/.test(newPassword);
  const hasNumber = /\d/.test(newPassword);
  const isPasswordValid = hasMinLength && hasUpperCase && hasLowerCase && hasNumber;

  const validateForm = (): boolean => {
    if (!token.trim()) {
      setIsTokenInvalid(true);
      setFormError('Your password reset link is invalid or has expired. Please request a new password reset link.');
      return false;
    }
    if (!isPasswordValid) {
      setFormError('New password must contain at least 8 characters, an uppercase letter, a lowercase letter, and a number.');
      return false;
    }
    if (newPassword !== confirmPassword) {
      setFormError('Password confirmation does not match.');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return; // Prevent multiple submissions
    setFormError(null);

    if (!validateForm()) return;

    try {
      setLoading(true);
      await api.resetPassword(token.trim(), newPassword);
      api.setAuthToken(null);
      // Immediately clear sensitive token and credentials from memory
      setToken('');
      setNewPassword('');
      setConfirmPassword('');
      setSuccess(true);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || '';
      const isTokenIssue =
        err?.response?.status === 400 ||
        err?.response?.status === 404 ||
        /token|expired|invalid|used/i.test(detail);

      if (isTokenIssue) {
        setIsTokenInvalid(true);
        setFormError('Your password reset link is invalid or has expired. Please request a new password reset link.');
      } else {
        setFormError(detail || 'Password update failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-navy-950 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden select-none">
      {/* Universal Multilingual Language Selector */}
      <div className="absolute top-4 right-4 z-20 notranslate" translate="no">
        <LanguageSelector />
      </div>
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-gradient-to-b from-blue-600/10 via-cyan-500/5 to-transparent blur-3xl pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="flex flex-col items-center text-center">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-xl shadow-blue-500/20 mb-3 border border-blue-400/20">
            <TrendingUp className="w-6 h-6" />
          </div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-extrabold tracking-wider text-white notranslate" translate="no">FIN-SENTIMENT</h1>
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30 notranslate" translate="no">PRO</span>
          </div>
          <p className="mt-1 text-xs text-slate-400 max-w-xs">
            Set your new credentials to restore terminal access
          </p>
        </div>

        <div className="mt-8 bg-navy-900/90 border border-navy-750/80 rounded-2xl shadow-2xl p-6 sm:p-8 backdrop-blur-xl">
          <div className="mb-5 pb-4 border-b border-navy-750/60">
            <h2 className="text-base font-bold text-white tracking-tight">Set New Password</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Establish a strong password for your analyst session
            </p>
          </div>

          {/* Success State */}
          {success ? (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs leading-relaxed space-y-2">
                <div className="flex items-center gap-2 font-bold text-emerald-400">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>Password updated successfully</span>
                </div>
                <p>
                  Your password has been updated successfully. Please log in with your new password.
                </p>
                <p className="text-emerald-400/80 text-[11px]">
                  Redirecting to the login page in {countdown}s...
                </p>
              </div>

              <div className="pt-2">
                <Link
                  to="/login"
                  className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold rounded-xl text-xs sm:text-sm flex items-center justify-center gap-2 shadow-lg shadow-blue-600/25 transition-all cursor-pointer"
                >
                  <span>Log in with New Password</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          ) : isTokenInvalid ? (
            /* Missing, Invalid, or Expired Token State */
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-xs text-rose-300 leading-relaxed">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-rose-300 mb-1">Invalid or Expired Link</p>
                  <p className="text-slate-300">
                    Your password reset link is invalid or has expired. Please request a new password reset link.
                  </p>
                </div>
              </div>

              <div className="pt-2 space-y-3">
                <Link
                  to="/forgot-password"
                  className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold rounded-xl text-xs sm:text-sm flex items-center justify-center gap-2 shadow-lg shadow-blue-600/25 transition-all cursor-pointer"
                >
                  <span>Request New Password Reset Link</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <div className="text-center pt-2">
                  <Link
                    to="/login"
                    className="text-xs text-slate-400 hover:text-white transition-colors"
                  >
                    Cancel & Return to Login
                  </Link>
                </div>
              </div>
            </div>
          ) : (
            /* Valid Token: Form with ONLY New Password and Confirm New Password */
            <form onSubmit={handleSubmit} className="space-y-4">
              {formError && (
                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-xs text-rose-300">
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  <div className="flex-1 leading-relaxed">{formError}</div>
                </div>
              )}

              {/* New Password Field */}
              <div>
                <label htmlFor="new-password" className="block text-xs font-semibold text-slate-300 mb-1.5">
                  New Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    id="new-password"
                    type={showPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    autoComplete="new-password"
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

              {/* Confirm Password Field */}
              <div>
                <label htmlFor="confirm-new-password" className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Confirm New Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    id="confirm-new-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repeat new password"
                    autoComplete="new-password"
                    disabled={loading}
                    className="w-full bg-navy-800/90 border border-navy-750 text-slate-100 placeholder-slate-500 text-xs sm:text-sm rounded-xl pl-10 pr-10 py-2.5 sm:py-3 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors disabled:opacity-50 font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300 cursor-pointer"
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {confirmPassword.length > 0 && newPassword !== confirmPassword && (
                  <p className="text-[11px] text-rose-400 mt-1">Passwords do not match.</p>
                )}
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
                    <span>Updating Password...</span>
                  </>
                ) : (
                  <span>Update Password</span>
                )}
              </button>

              {/* Cancel Link */}
              <div className="pt-3 border-t border-navy-750/60 text-center">
                <Link
                  to="/login"
                  className="text-xs text-slate-400 hover:text-white transition-colors"
                >
                  Cancel & Return to Login
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
