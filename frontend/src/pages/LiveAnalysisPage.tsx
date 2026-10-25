import React, { useState, useRef } from 'react';
import { Sparkles, Send, HelpCircle, AlertTriangle, CheckCircle, RefreshCw, X, Zap } from 'lucide-react';
import { api } from '../services/api';
import { SentimentAnalysisResult } from '../types';
import { SentimentBadge } from '../components/SentimentBadge';

const SAMPLE_HEADLINES = [
  {
    title: 'Bullish Earnings',
    text: 'Nvidia reports record quarterly data center revenue of $26 billion as hyperscalers expand AI computing clusters.',
  },
  {
    title: 'Bearish Margin Squeeze',
    text: 'Tesla operating profit sinks 40% year-over-year as aggressive EV price wars severely erode automotive gross margins.',
  },
  {
    title: 'Neutral Policy',
    text: 'Federal Open Market Committee holds benchmark interest rate steady between 5.25% and 5.50% awaiting inflation data.',
  },
  {
    title: 'Mixed Signals',
    text: 'Apple beats consensus revenue estimates driven by services growth despite European Union regulatory compliance fines.',
  },
];

export const LiveAnalysisPage: React.FC = () => {
  const [headline, setHeadline] = useState('');
  const [result, setResult] = useState<SentimentAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [flashCard, setFlashCard] = useState(false);
  const resultRef = useRef<HTMLDivElement>(null);

  const handleAnalyze = async (textToAnalyze?: string) => {
    const text = (textToAnalyze !== undefined ? textToAnalyze : headline).trim();
    if (!text) {
      setError('Please provide a financial headline or sentence to analyze.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setHeadline(text);
      
      const startTime = performance.now();
      const data = await api.analyzeHeadline(text);
      const elapsed = Math.round(performance.now() - startTime);

      setResult(data);
      setLatencyMs(elapsed);
      setFlashCard(true);

      // Smooth scroll down to result card so the user immediately sees it
      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 50);

      setTimeout(() => {
        setFlashCard(false);
      }, 1200);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Sentiment analysis failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setHeadline('');
    setResult(null);
    setError(null);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Sparkles className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-bold text-white">FinBERT Interactive Sentiment Lab</h2>
          <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[10px] font-mono border border-blue-500/20">
            Hugging Face ProsusAI/finbert
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Direct real-time inference on the PyTorch FinBERT model running locally on your laptop CPU.
        </p>
      </div>

      {/* Input Box */}
      <div className="bg-navy-900 border border-navy-750 rounded-xl p-5 space-y-4">
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Enter Financial Headline / Financial Statement
            </label>
            {headline && (
              <button
                type="button"
                onClick={handleClear}
                className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200"
              >
                <X className="w-3 h-3" />
                <span>Clear text</span>
              </button>
            )}
          </div>
          <div className="relative">
            <textarea
              rows={3}
              value={headline}
              onChange={(e) => setHeadline(e.target.value)}
              placeholder="e.g., Alphabet surges 8% after cloud profit exceeds Wall Street forecasts..."
              className="w-full bg-navy-950 border border-navy-700 rounded-lg p-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>
        </div>

        {error && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-400 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
          {/* Quick presets */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] text-slate-400">Try sample:</span>
            {SAMPLE_HEADLINES.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleAnalyze(sample.text)}
                className={`px-2.5 py-1 rounded text-[11px] border transition-colors ${
                  headline === sample.text
                    ? 'bg-blue-600/30 border-blue-500 text-blue-300 font-semibold'
                    : 'bg-navy-800 hover:bg-navy-700 text-slate-300 border-navy-700'
                }`}
              >
                {sample.title}
              </button>
            ))}
          </div>

          <button
            onClick={() => handleAnalyze()}
            disabled={loading || !headline.trim()}
            className="flex items-center justify-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-lg shadow-blue-600/30 transition-all cursor-pointer"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-white" />
                <span>Analyzing on CPU...</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>Classify Sentiment</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Analysis Result Card */}
      {result && (
        <div
          ref={resultRef}
          className={`bg-navy-900 border rounded-xl p-6 space-y-6 transition-all duration-300 ${
            flashCard ? 'border-blue-500 ring-2 ring-blue-500/50 shadow-xl shadow-blue-500/10' : 'border-navy-750'
          }`}
        >
          {/* Result Card Header */}
          <div className="flex items-center justify-between pb-4 border-b border-navy-700/60 flex-wrap gap-2">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider block">
                  Model Classification Outcome
                </span>
                {latencyMs !== null && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-mono border border-emerald-500/20">
                    <Zap className="w-2.5 h-2.5" />
                    <span>{latencyMs}ms inference</span>
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <SentimentBadge sentiment={result.sentiment} confidence={result.confidence} />
                <span className="text-xs text-slate-400 font-mono">
                  Confidence: <strong className="text-white">{(result.confidence * 100).toFixed(1)}%</strong>
                </span>
              </div>
            </div>
            <div className="text-right text-[11px] text-slate-500 font-mono">
              <span className="text-slate-400 font-medium">{result.model_name}</span>
              <span className="block text-[10px]">{new Date(result.analyzed_at).toLocaleTimeString()}</span>
            </div>
          </div>

          {/* Probability Bars */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              FinBERT Class Distribution
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="bg-navy-950 p-3 rounded-lg border border-navy-800">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">Bullish / Positive</span>
                  <span className="text-emerald-400 font-mono font-bold">
                    {(result.scores.positive * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-navy-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-emerald-500 h-1.5 rounded-full"
                    style={{ width: `${result.scores.positive * 100}%` }}
                  />
                </div>
              </div>

              <div className="bg-navy-950 p-3 rounded-lg border border-navy-800">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">Neutral</span>
                  <span className="text-amber-400 font-mono font-bold">
                    {(result.scores.neutral * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-navy-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-amber-500 h-1.5 rounded-full"
                    style={{ width: `${result.scores.neutral * 100}%` }}
                  />
                </div>
              </div>

              <div className="bg-navy-950 p-3 rounded-lg border border-navy-800">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">Bearish / Negative</span>
                  <span className="text-rose-400 font-mono font-bold">
                    {(result.scores.negative * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-navy-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-rose-500 h-1.5 rounded-full"
                    style={{ width: `${result.scores.negative * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Explainable AI: Token Perturbation Breakdown */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <span>Explainable AI: Perturbation Word Salience</span>
                <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
              </h4>
              <span className="text-[10px] text-blue-400 font-mono">
                Method: Single-token masking Δ
              </span>
            </div>

            {result.tokens && result.tokens.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {result.tokens.map((token, i) => {
                  const isPositiveDelta = token.impact > 0;
                  return (
                    <div
                      key={i}
                      className="flex items-center justify-between p-2.5 bg-navy-950 border border-navy-800 rounded-md text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-blue-300 font-semibold bg-blue-900/30 px-2 py-0.5 rounded border border-blue-800/40">
                          {token.token}
                        </span>
                        <span className="text-[11px] text-slate-400 capitalize">
                          {token.direction}
                        </span>
                      </div>
                      <span className={`font-mono font-medium ${isPositiveDelta ? 'text-emerald-400' : 'text-slate-400'}`}>
                        {isPositiveDelta ? `+${(token.impact * 100).toFixed(1)}%` : `${(token.impact * 100).toFixed(1)}%`}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">Uniform impact or single-word token.</p>
            )}
          </div>

          {/* Limitations Disclaimer */}
          <div className="p-3.5 bg-navy-950 border border-navy-800 rounded-lg text-xs space-y-1 text-slate-400">
            <div className="flex items-center gap-2 font-semibold text-slate-300">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>Scientific Note & Limitations</span>
            </div>
            <p className="text-[11px] leading-relaxed">
              {result.explanation_note} Word impact scores represent local confidence shifts when individual words are masked.
              FinBERT is an NLP sentiment classifier and must not be used as an automated trading algorithm.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
