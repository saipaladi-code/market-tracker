import React, { useState, useEffect } from 'react';
import {
  X,
  Server,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ExternalLink,
  Zap,
  Globe,
  Sliders,
  HelpCircle,
  Copy,
  Check
} from 'lucide-react';
import { api } from '../services/api';

interface BackendConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave?: () => void;
}

export const BackendConfigModal: React.FC<BackendConfigModalProps> = ({
  isOpen,
  onClose,
  onSave,
}) => {
  const [apiUrl, setApiUrl] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    latency?: number;
    message?: string;
  } | null>(null);
  const [copied, setCopied] = useState(false);
  const [showDeploymentGuide, setShowDeploymentGuide] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setApiUrl(api.getBaseUrl());
      setTestResult(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    const res = await api.testConnection(apiUrl);
    setTestResult(res);
    setTesting(false);
  };

  const handleSave = () => {
    api.setBaseUrl(apiUrl);
    if (onSave) onSave();
    onClose();
  };

  const handleReset = () => {
    api.resetBaseUrl();
    setApiUrl(api.getBaseUrl());
    setTestResult(null);
    if (onSave) onSave();
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isOffline = api.isOffline();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-navy-900 border border-navy-750 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-navy-750 flex items-center justify-between bg-navy-950/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">Backend Connection Settings</h3>
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                  isOffline
                    ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                    : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                }`}>
                  {isOffline ? '⚡ Standalone Demo' : '● Live API Connected'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Configure your FastAPI / FinBERT server endpoint URL
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-navy-800 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 overflow-y-auto">
          {/* Status banner */}
          <div className={`p-3.5 rounded-xl border flex items-start gap-3 text-xs ${
            isOffline
              ? 'bg-amber-500/10 border-amber-500/20 text-amber-200'
              : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-200'
          }`}>
            {isOffline ? (
              <Zap className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            )}
            <div className="leading-relaxed">
              <strong>{isOffline ? 'Operating in Standalone Demo Mode' : 'Connected to Live Server'}</strong>
              <p className="text-[11px] opacity-90 mt-0.5">
                {isOffline
                  ? 'The backend server was not detected or is still spinning up. The frontend is displaying realistic pre-analyzed FinBERT intelligence with full interactive functionality.'
                  : `Active connection established with ${apiUrl}. Live headlines and FinBERT inference enabled.`}
              </p>
            </div>
          </div>

          {/* URL Input Form */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-200">
              API Server Base URL
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="e.g. https://your-backend.onrender.com or http://localhost:8000"
                className="flex-1 px-3.5 py-2.5 bg-navy-950 border border-navy-750 focus:border-blue-500 focus:outline-none rounded-xl text-xs font-mono text-white placeholder-slate-500"
              />
              <button
                type="button"
                onClick={handleTest}
                disabled={testing}
                className="px-4 py-2.5 bg-navy-800 hover:bg-navy-750 border border-navy-700 text-slate-200 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer"
              >
                {testing ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-400" />
                ) : (
                  <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
                )}
                <span>Test Ping</span>
              </button>
            </div>
            <p className="text-[11px] text-slate-500">
              Saved automatically in your browser's local storage for this session.
            </p>
          </div>

          {/* Test Result Message */}
          {testResult && (
            <div className={`p-3 rounded-xl border flex items-center justify-between text-xs animate-in fade-in ${
              testResult.success
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
            }`}>
              <div className="flex items-center gap-2">
                {testResult.success ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                )}
                <span>{testResult.message}</span>
              </div>
              {testResult.latency !== undefined && (
                <span className="font-mono text-[11px] opacity-80">{testResult.latency} ms</span>
              )}
            </div>
          )}

          {/* Deployment Instructions Accordion */}
          <div className="pt-2 border-t border-navy-800">
            <button
              onClick={() => setShowDeploymentGuide(!showDeploymentGuide)}
              className="w-full flex items-center justify-between text-xs text-blue-400 hover:text-blue-300 font-semibold py-1 transition-colors"
            >
              <div className="flex items-center gap-1.5">
                <HelpCircle className="w-3.5 h-3.5" />
                <span>Need to deploy or link your backend on Render / Vercel?</span>
              </div>
              <span className="text-[11px] font-mono">{showDeploymentGuide ? '▲ Hide' : '▼ Show Instructions'}</span>
            </button>

            {showDeploymentGuide && (
              <div className="mt-3 p-3.5 bg-navy-950 rounded-xl border border-navy-800 text-xs text-slate-300 space-y-3 font-sans">
                <div>
                  <h4 className="font-bold text-white mb-1">Option 1: Deploy Backend to Render (Free)</h4>
                  <p className="text-slate-400 text-[11px] leading-relaxed">
                    1. On <a href="https://render.com" target="_blank" rel="noreferrer" className="text-blue-400 underline">Render.com</a>, create a <strong>Web Service</strong> connected to your GitHub repository.
                  </p>
                  <p className="text-slate-400 text-[11px] leading-relaxed mt-1">
                    2. Set <strong>Root Directory</strong> to <code>backend</code>.
                  </p>
                  <p className="text-slate-400 text-[11px] leading-relaxed mt-1">
                    3. Set <strong>Build Command</strong> to:
                    <code className="block bg-navy-900 p-1.5 mt-1 rounded font-mono text-[10px] text-emerald-300">
                      pip install -r requirements.txt
                    </code>
                  </p>
                  <p className="text-slate-400 text-[11px] leading-relaxed mt-1">
                    4. Set <strong>Start Command</strong> to:
                    <code className="block bg-navy-900 p-1.5 mt-1 rounded font-mono text-[10px] text-emerald-300">
                      uvicorn app.main:app --host 0.0.0.0 --port $PORT
                    </code>
                  </p>
                </div>

                <div className="pt-2 border-t border-navy-800">
                  <h4 className="font-bold text-white mb-1">Option 2: Configure Vercel Frontend Environment</h4>
                  <p className="text-slate-400 text-[11px] leading-relaxed">
                    In your Vercel Project Settings &gt; <strong>Environment Variables</strong>:
                  </p>
                  <div className="flex items-center justify-between bg-navy-900 p-2 mt-1 rounded font-mono text-[11px]">
                    <span className="text-cyan-300">VITE_API_URL = https://your-backend.onrender.com</span>
                    <button
                      onClick={() => handleCopy('VITE_API_URL')}
                      className="text-slate-400 hover:text-white transition-colors"
                      title="Copy variable name"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-navy-750 bg-navy-950/70 flex items-center justify-between">
          <button
            onClick={handleReset}
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
          >
            Reset to Default
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-navy-850 hover:bg-navy-800 text-slate-300 rounded-xl text-xs font-semibold transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-blue-600/20 transition-all cursor-pointer"
            >
              Save & Apply
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
