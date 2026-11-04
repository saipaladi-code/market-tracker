import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { TrendingUp, Mail, AlertCircle, CheckCircle2, Loader2, ArrowLeft, Info, KeyRound, UserPlus } from 'lucide-react';
import { LanguageSelector } from '../components/LanguageSelector';
import { ForgotPasswordResponse } from '../types';

interface FormErrorState {
  title: string;
  message: string;
  isUnregistered: boolean;
}

export const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ForgotPasswordResponse | null>(null);
  const [formError, setFormError] = useState<FormErrorState | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    setFormError(null);
    setResult(null);

    const trimmedEmail = email.trim();
    // Validate standard email format (user@domain.tld with at least 2 char TLD)
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!trimmedEmail || !emailRegex.test(trimmedEmail)) {
      setFormError({
        title: 'Invalid Email Address',
        message: 'Please enter a valid email address.',
        isUnregistered: false,
      });
      return;
    }

    try {
      setLoading(true);
      const res = await api.forgotPassword(trimmedEmail);
      setResult(res);
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      const rawMsg = typeof detail === 'string'
        ? detail
        : Array.isArray(detail) && detail.length > 0
          ? (typeof detail[0] === 'string' ? detail[0] : detail[0]?.msg || JSON.stringify(detail[0]))
          : err?.message || 'Password reset request failed.';

      const cleanMsg = rawMsg.replace(/^Value error,\s*/i, '');

      if (status === 404 || /not registered/i.test(cleanMsg)) {
        setFormError({
          title: 'Email Not Registered',
          message: cleanMsg || 'This email address is not registered with FIN-SENTIMENT. Please check your email address or create a new account.',
          isUnregistered: true,
        });
      } else if (status === 422 || /valid email/i.test(cleanMsg)) {
        setFormError({
          title: 'Invalid Email Address',
          message: 'Please enter a valid email address.',
          isUnregistered: false,
        });
      } else if (status === 503 || /database/i.test(cleanMsg)) {
        setFormError({
          title: 'Database Service Unavailable',
          message: cleanMsg || 'Database service is currently unavailable. Please try again later.',
          isUnregistered: false,
        });
      } else {
        setFormError({
          title: 'Password Recovery Failed',
          message: cleanMsg || 'Failed to send password recovery email. Please try again later.',
          isUnregistered: false,
        });
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
            Expiring single-use credential recovery
          </p>
        </div>

        <div className="mt-8 bg-navy-900/90 border border-navy-750/80 rounded-2xl shadow-2xl p-6 sm:p-8 backdrop-blur-xl">
          <div className="mb-5 pb-4 border-b border-navy-750/60">
            <h2 className="text-base font-bold text-white tracking-tight">Recover Password</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Enter your email to receive a secure, 15-minute recovery link
            </p>
          </div>

          {formError && (
            <div className="mb-5 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs leading-relaxed space-y-3">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div className="space-y-1 flex-1">
                  <p className="font-bold text-rose-300 text-sm">{formError.title}</p>
                  <p className="text-slate-300 text-xs leading-relaxed">{formError.message}</p>
                </div>
              </div>

              {formError.isUnregistered && (
                <div className="pt-2 border-t border-rose-500/20 flex flex-col sm:flex-row gap-2">
                  <Link
                    to="/register"
                    className="flex-1 py-2 px-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold rounded-lg text-xs flex items-center justify-center gap-1.5 shadow-md shadow-blue-600/20 transition-all cursor-pointer"
                  >
                    <UserPlus className="w-3.5 h-3.5" />
                    <span>Create New Account</span>
                  </Link>
                  <Link
                    to="/login"
                    className="py-2 px-3 bg-navy-800 hover:bg-navy-750 border border-navy-700 text-slate-300 hover:text-white font-medium rounded-lg text-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <span>Return to Login</span>
                  </Link>
                </div>
              )}
            </div>
          )}

          {result ? (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs leading-relaxed space-y-2">
                <div className="flex items-center gap-2 font-bold text-emerald-400 text-sm">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{result.title || 'Recovery Email Sent'}</span>
                </div>
                <p className="text-slate-200 text-xs leading-relaxed">
                  {result.message || 'A password reset link has been sent to your registered email address. Please check your inbox and spam folder.'}
                </p>
              </div>

              {result.dev_reset_token && (
                <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-300 text-xs leading-relaxed space-y-2.5">
                  <div className="flex items-center gap-2 font-bold text-blue-400">
                    <Info className="w-4 h-4" />
                    <span>Password Reset Link (Testing Mode)</span>
                  </div>
                  <p className="text-slate-300 text-[11px] leading-normal">
                    You can proceed directly to reset the password for this account:
                  </p>
                  <div>
                    <Link
                      to={`/reset-password?token=${encodeURIComponent(result.dev_reset_token)}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-colors"
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      <span>Proceed to Reset Password</span>
                    </Link>
                  </div>
                </div>
              )}

              <div className="pt-3">
                <Link
                  to="/login"
                  className="w-full py-2.5 px-4 bg-navy-800 hover:bg-navy-750 border border-navy-700 text-slate-200 font-semibold rounded-xl text-xs flex items-center justify-center gap-2 transition-colors cursor-pointer"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back to Login</span>
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="recovery-email" className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    id="recovery-email"
                    type="text"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="analyst@firm.com"
                    autoComplete="email"
                    disabled={loading}
                    className="w-full bg-navy-800/90 border border-navy-750 text-slate-100 placeholder-slate-500 text-xs sm:text-sm rounded-xl pl-10 pr-4 py-2.5 sm:py-3 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors disabled:opacity-50"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-3 px-4 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold rounded-xl text-xs sm:text-sm shadow-lg shadow-blue-600/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Sending Recovery Link...</span>
                  </>
                ) : (
                  <span>Send Recovery Link</span>
                )}
              </button>

              <div className="pt-3 border-t border-navy-750/60 text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to Login</span>
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
