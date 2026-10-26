import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { TrendingUp, Mail, AlertCircle, CheckCircle2, Loader2, ArrowLeft, Info, KeyRound } from 'lucide-react';
import { ForgotPasswordResponse } from '../types';

export const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ForgotPasswordResponse | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setResult(null);

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email.trim() || !emailRegex.test(email.trim())) {
      setFormError('Please enter a valid work email address.');
      return;
    }

    try {
      setLoading(true);
      const res = await api.forgotPassword(email.trim());
      setResult(res);
    } catch (err: any) {
      setFormError(err?.response?.data?.detail || err?.message || 'Password reset request failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-navy-950 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden select-none">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-gradient-to-b from-blue-600/10 via-cyan-500/5 to-transparent blur-3xl pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
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
            <div className="mb-5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div className="flex-1 leading-relaxed">{formError}</div>
            </div>
          )}

          {result ? (
            <div className="space-y-4">
              {result.smtp_configured ? (
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs leading-relaxed space-y-2">
                  <div className="flex items-center gap-2 font-bold text-emerald-400">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Recovery Instructions Dispatched</span>
                  </div>
                  <p>{result.message}</p>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs leading-relaxed space-y-2.5">
                  <div className="flex items-center gap-2 font-bold text-amber-400">
                    <Info className="w-4 h-4" />
                    <span>SMTP Relay Service Unconfigured</span>
                  </div>
                  <p className="text-slate-300 leading-normal">
                    Email dispatch is currently unconfigured on this backend instance. To enable outbound emails in production, configure <code className="text-cyan-300 font-mono text-[11px] bg-navy-800 px-1 py-0.5 rounded">SMTP_HOST</code>, <code className="text-cyan-300 font-mono text-[11px] bg-navy-800 px-1 py-0.5 rounded">SMTP_PORT</code>, and <code className="text-cyan-300 font-mono text-[11px] bg-navy-800 px-1 py-0.5 rounded">SMTP_PASSWORD</code>.
                  </p>
                  {result.dev_reset_token && (
                    <div className="pt-2 border-t border-amber-500/20">
                      <p className="text-[11px] text-amber-200 mb-2 font-semibold">Local Development Token Generated:</p>
                      <Link
                        to={`/reset-password?token=${encodeURIComponent(result.dev_reset_token)}`}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-colors"
                      >
                        <KeyRound className="w-3.5 h-3.5" />
                        <span>Proceed to Reset Password</span>
                      </Link>
                    </div>
                  )}
                </div>
              )}

              <div className="pt-3">
                <Link
                  to="/login"
                  className="w-full py-2.5 px-4 bg-navy-800 hover:bg-navy-750 border border-navy-700 text-slate-200 font-semibold rounded-xl text-xs flex items-center justify-center gap-2 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Return to Sign In</span>
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="recovery-email" className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Work Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    id="recovery-email"
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

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-3 px-4 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold rounded-xl text-xs sm:text-sm shadow-lg shadow-blue-600/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Verifying Request...</span>
                  </>
                ) : (
                  <span>Send Recovery Instructions</span>
                )}
              </button>

              <div className="pt-3 border-t border-navy-750/60 text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to Sign In</span>
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
