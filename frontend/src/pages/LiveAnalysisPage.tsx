import React, { useState, useRef } from 'react';
import {
  Sparkles,
  Send,
  HelpCircle,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  X,
  Zap,
  Cpu,
  Layers,
  Info,
  Clock,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  Minus
} from 'lucide-react';
import { api } from '../services/api';
import { SentimentAnalysisResult } from '../types';
import { SentimentBadge } from '../components/SentimentBadge';
import {
  validateFinancialHeadline,
  MAX_HEADLINE_LENGTH,
  MIN_HEADLINE_LENGTH,
  INVALID_FINANCIAL_HEADLINE_MESSAGE
} from '../services/headlineValidator';

const SAMPLE_HEADLINES = [
  {
    category: 'Bullish Earnings Beat',
    title: 'NVDA Record Revenue',
    text: 'Nvidia reports record quarterly data center revenue of $26 billion as global hyperscalers aggressively expand AI compute clusters.',
  },
  {
    category: 'Bearish Margin Squeeze',
    title: 'TSLA Margin Pressure',
    text: 'Tesla operating margin falls to 6.3% as aggressive international EV price cuts and rising production costs severely erode automotive profits.',
  },
  {
    category: 'Neutral Central Bank Policy',
    title: 'Fed Rate Decision',
    text: 'Federal Open Market Committee holds benchmark interest rate unchanged at 5.25%-5.50% awaiting sustained progress on core PCE inflation metrics.',
  },
  {
    category: 'Regulatory Headwinds',
    title: 'Antitrust Scrutiny',
    text: 'Department of Justice files comprehensive civil antitrust lawsuit against tech conglomerate alleging monopolization of digital ad exchange infrastructure.',
  },
  {
    category: 'Mixed Signals / Divergence',
    title: 'Cloud vs Hardware Divergence',
    text: 'Microsoft cloud enterprise revenue beats consensus expectations by 18% despite softening personal computing hardware demand and exchange rate volatility.',
  },
];

export const LiveAnalysisPage: React.FC = () => {
  const [headline, setHeadline] = useState('');
  const [result, setResult] = useState<SentimentAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pasteNotification, setPasteNotification] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [flashCard, setFlashCard] = useState(false);
  const resultRef = useRef<HTMLDivElement>(null);

  const trimmedHeadline = headline.trim();
  const validation = validateFinancialHeadline(trimmedHeadline);
  const isButtonDisabled = loading || !trimmedHeadline || !validation.isValid;

  const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const pasteData = e.clipboardData.getData('text');
    if (!pasteData) return;

    const textarea = e.currentTarget;
    const start = textarea.selectionStart ?? 0;
    const end = textarea.selectionEnd ?? 0;
    const currentVal = textarea.value;

    const prospective = currentVal.slice(0, start) + pasteData + currentVal.slice(end);

    if (prospective.length > MAX_HEADLINE_LENGTH) {
      e.preventDefault();
      const truncated = prospective.slice(0, MAX_HEADLINE_LENGTH);
      setHeadline(truncated);
      setPasteNotification('Pasted text was truncated to the 1,000-character limit.');
      setTimeout(() => setPasteNotification(null), 6000);
      if (error) setError(null);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    let val = e.target.value;
    if (val.length > MAX_HEADLINE_LENGTH) {
      val = val.slice(0, MAX_HEADLINE_LENGTH);
    }
    setHeadline(val);
    if (error) setError(null);
  };

  const handleAnalyze = async (textToAnalyze?: string) => {
    if (loading) return; // Prevent repeated submissions while processing

    const rawText = textToAnalyze !== undefined ? textToAnalyze : headline;
    const text = rawText.trim();

    // Client-side pre-validation
    const check = validateFinancialHeadline(text);
    if (!check.isValid) {
      setResult(null); // Clear stale results when new input is invalid
      setError(check.message || INVALID_FINANCIAL_HEADLINE_MESSAGE);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setHeadline(rawText.length > MAX_HEADLINE_LENGTH ? rawText.slice(0, MAX_HEADLINE_LENGTH) : rawText);

      const startTime = performance.now();
      const data = await api.analyzeHeadline(text);
      const elapsed = Math.round(performance.now() - startTime);

      setResult(data);
      setLatencyMs(elapsed);
      setFlashCard(true);

      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 50);

      setTimeout(() => {
        setFlashCard(false);
      }, 1200);
    } catch (err: any) {
      setResult(null); // Clear stale sentiment results on rejection
      const apiError = err?.response?.data;
      const msg = apiError?.detail || apiError?.message || err?.message || 'Sentiment analysis failed on backend.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setHeadline('');
    setResult(null);
    setError(null);
    setPasteNotification(null);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Page Header */}
      <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-6 backdrop-blur-md">
        <div className="flex items-center gap-2.5 mb-2">
          <div className="w-8 h-8 rounded-xl bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-lg font-extrabold text-white tracking-tight">FinBERT Interactive Sentiment Lab</h2>
            <p className="text-xs text-slate-400 font-mono">
              Live PyTorch CPU forward pass via <code className="text-blue-300">ProsusAI/finbert</code>
            </p>
          </div>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed mt-2 max-w-2xl">
          Enter any financial headline, earnings report excerpt, or analyst statement. The model executes on-device CPU inference,
          returning softmax probability distributions and perturbation-based token attribution deltas.
        </p>
      </div>

      {/* Input Workbench Card */}
      <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-6 space-y-4 shadow-sm">
        <div>
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="financial-headline-input" className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <span>Financial Headline / Statement Input</span>
              <span
                id="char-counter"
                className={`text-[10px] font-mono font-medium transition-colors ${
                  headline.length >= MAX_HEADLINE_LENGTH
                    ? 'text-amber-400 font-bold'
                    : headline.length > 900
                    ? 'text-blue-400'
                    : 'text-slate-500'
                }`}
              >
                ({headline.length} / {MAX_HEADLINE_LENGTH} characters)
              </span>
            </label>
            {headline && (
              <button
                type="button"
                onClick={handleClear}
                className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
              >
                <X className="w-3 h-3" />
                <span>Clear</span>
              </button>
            )}
          </div>

          <div className="relative">
            <textarea
              id="financial-headline-input"
              rows={3}
              value={headline}
              maxLength={MAX_HEADLINE_LENGTH}
              onChange={handleChange}
              onPaste={handlePaste}
              placeholder="e.g. Alphabet surges 7% after cloud revenue accelerates past Wall Street targets..."
              className="w-full bg-navy-950 border border-navy-700/80 rounded-xl p-4 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all font-sans leading-relaxed"
            />
          </div>
        </div>

        {/* Truncation Notification */}
        {pasteNotification && (
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-300 flex items-center gap-2.5">
            <Info className="w-4 h-4 shrink-0 text-amber-400" />
            <span>{pasteNotification}</span>
          </div>
        )}

        {/* Validation / Error Message */}
        {error && (
          <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-300 flex items-center gap-2.5">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
            <span className="flex-1 leading-relaxed">{error}</span>
          </div>
        )}

        {/* Inline Guidance When Input Is Active But Invalid */}
        {trimmedHeadline.length > 0 && !error && !validation.isValid && (
          <div className="p-2.5 bg-navy-950/90 border border-slate-700/60 rounded-xl text-[11px] text-slate-400 flex items-center gap-2">
            <Info className="w-3.5 h-3.5 shrink-0 text-blue-400" />
            <span className="leading-snug">{validation.message}</span>
          </div>
        )}

        {/* Presets and Submit */}
        <div className="space-y-3 pt-1">
          <div>
            <span className="text-[11px] text-slate-400 font-medium block mb-2">Select Curated Financial Example:</span>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_HEADLINES.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleAnalyze(sample.text)}
                  className={`px-3 py-1.5 rounded-lg text-xs border transition-all text-left flex items-center gap-1.5 cursor-pointer ${
                    headline === sample.text
                      ? 'bg-blue-600/25 border-blue-500 text-blue-300 font-semibold'
                      : 'bg-navy-950 hover:bg-navy-800 text-slate-300 border-navy-800'
                  }`}
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                  <span>{sample.category}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-navy-800/80">
            <div className="flex items-center gap-2 text-[11px] text-slate-500 font-mono">
              <Cpu className="w-3.5 h-3.5 text-blue-400" />
              <span>Inference Engine: Local CPU (No Cloud Token Required)</span>
            </div>

            <button
              id="run-finbert-inference-btn"
              type="button"
              onClick={() => handleAnalyze()}
              disabled={isButtonDisabled}
              className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl text-xs font-bold shadow-lg shadow-blue-600/30 transition-all cursor-pointer"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Computing Softmax...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>Run FinBERT Inference</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Analysis Result Card */}
      {result && (
        <div
          ref={resultRef}
          className={`bg-navy-900/90 border rounded-2xl p-6 space-y-6 transition-all duration-300 shadow-xl ${
            flashCard ? 'border-blue-500 ring-2 ring-blue-500/40' : 'border-navy-750/90'
          }`}
        >
          {/* Result Card Header */}
          <div className="flex items-center justify-between pb-4 border-b border-navy-750/80 flex-wrap gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider font-semibold">
                  FinBERT Classification Verdict
                </span>
                {latencyMs !== null && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 text-[10px] font-mono border border-emerald-500/20">
                    <Zap className="w-2.5 h-2.5" />
                    <span>{latencyMs}ms Latency</span>
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <SentimentBadge sentiment={result.sentiment} confidence={result.confidence} size="md" />
                <span className="text-xs text-slate-300 font-mono">
                  Confidence Score: <strong className="text-white">{(result.confidence * 100).toFixed(1)}%</strong>
                </span>
              </div>
            </div>

            <div className="text-right text-[11px] text-slate-400 font-mono">
              <span className="text-slate-300 font-semibold">{result.model_name}</span>
              <span className="block text-[10px] text-slate-500">{new Date(result.analyzed_at).toLocaleTimeString()} UTC</span>
            </div>
          </div>

          {/* Three Probability Distribution Meters */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Softmax Probability Distribution
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Bullish */}
              <div className="bg-navy-950/80 p-4 rounded-xl border border-navy-800">
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Bullish (Positive)</span>
                  </span>
                  <span className="text-emerald-400 font-mono font-bold">
                    {(result.scores.positive * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-navy-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${result.scores.positive * 100}%` }}
                  />
                </div>
              </div>

              {/* Neutral */}
              <div className="bg-navy-950/80 p-4 rounded-xl border border-navy-800">
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <Minus className="w-3.5 h-3.5 text-amber-400" />
                    <span>Neutral Tone</span>
                  </span>
                  <span className="text-amber-400 font-mono font-bold">
                    {(result.scores.neutral * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-navy-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-amber-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${result.scores.neutral * 100}%` }}
                  />
                </div>
              </div>

              {/* Bearish */}
              <div className="bg-navy-950/80 p-4 rounded-xl border border-navy-800">
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <TrendingDown className="w-3.5 h-3.5 text-rose-400" />
                    <span>Bearish (Negative)</span>
                  </span>
                  <span className="text-rose-400 font-mono font-bold">
                    {(result.scores.negative * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-navy-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-rose-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${result.scores.negative * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Explainable AI: Token Perturbation Breakdown */}
          <div className="space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <span>Explainable AI: Perturbation Word Salience</span>
                <span title="Measures drop in model confidence when each token is masked individually.">
                  <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
                </span>
              </h4>
              <span className="text-[10px] text-blue-400 font-mono bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                Method: Token Masking Delta ΔP
              </span>
            </div>

            {result.tokens && result.tokens.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {result.tokens.map((token, i) => {
                  const isPositiveDelta = token.impact > 0;
                  return (
                    <div
                      key={i}
                      className="flex items-center justify-between p-3 bg-navy-950/80 border border-navy-800 rounded-xl text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-blue-300 font-bold bg-blue-900/30 px-2 py-0.5 rounded-md border border-blue-800/40">
                          {token.token}
                        </span>
                        <span className="text-[11px] text-slate-400 capitalize">
                          {token.direction} influence
                        </span>
                      </div>
                      <span className={`font-mono font-bold ${isPositiveDelta ? 'text-emerald-400' : 'text-slate-400'}`}>
                        {isPositiveDelta ? `+${(token.impact * 100).toFixed(1)}%` : `${(token.impact * 100).toFixed(1)}%`}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic p-3 bg-navy-950 rounded-xl border border-navy-800">
                Single-token text or uniform attention distribution.
              </p>
            )}
          </div>

          {/* Transparent Scientific Disclaimer */}
          <div className="p-4 bg-navy-950/90 border border-navy-800 rounded-xl text-xs space-y-1.5 text-slate-400">
            <div className="flex items-center gap-2 font-bold text-slate-300">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>Scientific Note & Platform Transparency</span>
            </div>
            <p className="text-[11px] leading-relaxed text-slate-400">
              {result.explanation_note} Word impact scores represent local confidence shifts when individual words are masked.
              FinBERT is an NLP sentiment classifier analyzing semantic tone; it does not evaluate corporate fundamentals or forecast stock price movements.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
