import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { TrendingUp, User, Mail, Lock, Eye, EyeOff, AlertCircle, Loader2, ArrowRight, ShieldCheck } from 'lucide-react';

export const SignupPage: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const queryParams = new URLSearchParams(location.search);
  const redirectTarget = queryParams.get('redirect') ? decodeURIComponent(queryParams.get('redirect')!) : '/';

  // Real-time password strength computation
  const hasMinLength = password.length >= 8;
  const hasUpperCase = /[A-Z]/.test(password);
  const hasLowerCase = /[a-z]/.test(password);
  const hasNumber = /\d/.test(password);
  const hasSpecial = /[^A-Za-z0-9]/.test(password);

  const strengthScore = [hasMinLength, hasUpperCase, hasLowerCase, hasNumber, hasSpecial].filter(Boolean).length;
  const isPasswordValid = hasMinLength && hasUpperCase && hasLowerCase && hasNumber;

  const validateForm = (): boolean => {
    if (!fullName.trim() || fullName.trim().length < 2) {
      setFormError('Full name must be at least 2 characters.');
      return false;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setFormError('Please enter a valid financial work email address.');
      return false;
    }
    if (!isPasswordValid) {
      setFormError('Password must be at least 8 characters and include uppercase, lowercase, and numeric characters.');
      return false;
    }
    if (password !== confirmPassword) {
      setFormError('Password confirmation does not match.');
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
      await register(fullName.trim(), email.trim(), password);
      navigate(redirectTarget, { replace: true });
    } catch (err: any) {
      setFormError(err.message || 'Registration failed. Please check your details.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-navy-950 flex flex-col justify-center py-10 px-4 sm:px-6 lg:px-8 relative overflow-hidden select-none">
      {/* Background Decorative Radial Glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-gradient-to-b from-blue-600/10 via-cyan-500/5 to-transparent blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

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
            Create your analyst profile to access real-time sentiment analytics
          </p>
        </div>

        {/* Signup Card */}
        <div className="mt-7 bg-navy-900/90 border border-navy-750/80 rounded-2xl shadow-2xl p-6 sm:p-8 backdrop-blur-xl">
          <div className="flex items-center justify-between pb-4 mb-4 border-b border-navy-750/60">
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">Create Account</h2>
              <p className="text-xs text-slate-400 mt-0.5">Register terminal access credentials</p>
            </div>
            <div className="flex items-center gap-1 px-2 py-1 rounded bg-navy-800/80 border border-navy-700 text-[10px] font-mono text-cyan-400">
              <ShieldCheck className="w-3 h-3" />
              <span>Bcrypt / Argon2</span>
            </div>
          </div>

          {/* Error Banner */}
          {formError && (
            <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-xs text-rose-300 animate-in fade-in duration-200">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div className="flex-1 leading-relaxed">{formError}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3.5">
            {/* Full Name */}
            <div>
              <label htmlFor="signup-name" className="block text-xs font-semibold text-slate-300 mb-1">
                Full Name
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <User className="w-4 h-4" />
                </div>
                <input
                  id="signup-name"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Senior Market Analyst"
                  autoComplete="name"
                  disabled={loading}
                  className="w-full bg-navy-800/90 border border-navy-750 text-slate-100 placeholder-slate-500 text-xs sm:text-sm rounded-xl pl-10 pr-4 py-2.5 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors disabled:opacity-50"
                />
              </div>
            </div>

            {/* Email Address */}
            <div>
              <label htmlFor="signup-email" className="block text-xs font-semibold text-slate-300 mb-1">
                Work Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  id="signup-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyst@firm.com"
                  autoComplete="email"
                  disabled={loading}
                  className="w-full bg-navy-800/90 border border-navy-750 text-slate-100 placeholder-slate-500 text-xs sm:text-sm rounded-xl pl-10 pr-4 py-2.5 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors disabled:opacity-50"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label htmlFor="signup-password" className="block text-xs font-semibold text-slate-300 mb-1">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="signup-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  autoComplete="new-password"
                  disabled={loading}
                  className="w-full bg-navy-800/90 border border-navy-750 text-slate-100 placeholder-slate-500 text-xs sm:text-sm rounded-xl pl-10 pr-10 py-2.5 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors disabled:opacity-50 font-mono"
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

              {/* Password Strength Indicator */}
              {password.length > 0 && (
                <div className="mt-2 space-y-1.5 p-2.5 rounded-lg bg-navy-800/60 border border-navy-750 text-[11px]">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Password Strength:</span>
                    <span
                      className={`font-semibold ${
                        strengthScore <= 2
                          ? 'text-rose-400'
                          : strengthScore <= 3
                          ? 'text-amber-400'
                          : 'text-emerald-400'
                      }`}
                    >
                      {strengthScore <= 2 ? 'Weak' : strengthScore <= 3 ? 'Medium' : 'Strong'}
                    </span>
                  </div>
                  {/* Strength Bar */}
                  <div className="w-full h-1.5 bg-navy-950 rounded-full overflow-hidden flex gap-1">
                    <div
                      className={`h-full flex-1 transition-all rounded-full ${
                        strengthScore >= 1
                          ? strengthScore <= 2
                            ? 'bg-rose-500'
                            : strengthScore <= 3
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                          : 'bg-navy-750'
                      }`}
                    />
                    <div
                      className={`h-full flex-1 transition-all rounded-full ${
                        strengthScore >= 3
                          ? strengthScore === 3
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                          : 'bg-navy-750'
                      }`}
                    />
                    <div
                      className={`h-full flex-1 transition-all rounded-full ${
                        strengthScore >= 4 ? 'bg-emerald-500' : 'bg-navy-750'
                      }`}
                    />
                  </div>
                  {/* Requirements Checklist */}
                  <div className="grid grid-cols-2 gap-1 text-[10px] pt-1 text-slate-400">
                    <div className="flex items-center gap-1">
                      <span className={hasMinLength ? 'text-emerald-400' : 'text-slate-500'}>●</span> 8+ Characters
                    </div>
                    <div className="flex items-center gap-1">
                      <span className={hasUpperCase ? 'text-emerald-400' : 'text-slate-500'}>●</span> 1+ Uppercase (A-Z)
                    </div>
                    <div className="flex items-center gap-1">
                      <span className={hasLowerCase ? 'text-emerald-400' : 'text-slate-500'}>●</span> 1+ Lowercase (a-z)
                    </div>
                    <div className="flex items-center gap-1">
                      <span className={hasNumber ? 'text-emerald-400' : 'text-slate-500'}>●</span> 1+ Number (0-9)
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <label htmlFor="signup-confirm-password" className="block text-xs font-semibold text-slate-300 mb-1">
                Confirm Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="signup-confirm-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat password"
                  autoComplete="new-password"
                  disabled={loading}
                  className="w-full bg-navy-800/90 border border-navy-750 text-slate-100 placeholder-slate-500 text-xs sm:text-sm rounded-xl pl-10 pr-10 py-2.5 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors disabled:opacity-50 font-mono"
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
              {confirmPassword.length > 0 && password !== confirmPassword && (
                <p className="text-[11px] text-rose-400 mt-1">Passwords do not match.</p>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full mt-3 py-3 px-4 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold rounded-xl text-xs sm:text-sm shadow-lg shadow-blue-600/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Registering Account...</span>
                </>
              ) : (
                <>
                  <span>Create Analyst Account</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Footer link to login */}
          <div className="mt-5 pt-4 border-t border-navy-750/60 text-center">
            <p className="text-xs text-slate-400">
              Already have an account?{' '}
              <Link
                to={redirectTarget !== '/' ? `/login?redirect=${encodeURIComponent(redirectTarget)}` : '/login'}
                className="text-cyan-400 hover:text-cyan-300 font-semibold transition-colors"
              >
                Sign In
              </Link>
            </p>
          </div>
        </div>

        {/* Security Notice */}
        <p className="mt-5 text-center text-[11px] text-slate-500">
          Passwords are automatically salted and hashed via bcrypt before persistence.
        </p>
      </div>
    </div>
  );
};
