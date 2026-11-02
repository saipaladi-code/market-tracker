import React, { useState, useEffect } from 'react';
import {
  X,
  Compass,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  AlertCircle,
  Copy,
  Check,
  Building2,
  Globe,
  Coins,
  ShieldCheck,
  ExternalLink,
  Info,
  Layers,
  ArrowUpRight
} from 'lucide-react';
import { Article, MarketContextData } from '../types';
import { SentimentBadge } from './SentimentBadge';
import { api } from '../services/api';

interface MarketContextModalProps {
  isOpen: boolean;
  onClose: () => void;
  article: Article | null;
  onOpenTrade?: (article: Article) => void;
}

export const MarketContextModal: React.FC<MarketContextModalProps> = ({
  isOpen,
  onClose,
  article,
  onOpenTrade
}) => {
  const [context, setContext] = useState<MarketContextData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    if (!isOpen || !article) {
      setContext(null);
      setError(null);
      setCopied(false);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);
    setCopied(false);

    api.getMarketContext(article)
      .then((data) => {
        if (!isMounted) return;
        setContext(data);
        setLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error('Failed to load market context:', err);
        setError('Failed to synthesize market context for this headline.');
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, article]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !article) return null;

  const handleCopySummary = () => {
    if (!context) return;
    const summaryText = `[FIN-SENTIMENT Market Context]
Headline: "${context.headline}"
Entity: ${context.entity_name} (${context.entity_type})
Topic: ${context.event_topic}
Sentiment: ${context.sentiment.toUpperCase()} (${(context.confidence * 100).toFixed(1)}%)
Market Relevance: ${context.market_relevance}
Indicators: ${context.market_indicators.map((ind) => `${ind.name} (${ind.change || 'N/A'})`).join(', ')}`;

    navigator.clipboard.writeText(summaryText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'commodity':
        return <Coins className="w-4 h-4 text-amber-400" />;
      case 'company':
        return <Building2 className="w-4 h-4 text-blue-400" />;
      default:
        return <Globe className="w-4 h-4 text-purple-400" />;
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />;
      case 'down':
        return <TrendingDown className="w-3.5 h-3.5 text-rose-400" />;
      default:
        return <Minus className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="market-context-title"
    >
      <div className="bg-navy-900 border border-navy-750 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl space-y-5">
        {/* Header */}
        <div className="px-6 py-4 border-b border-navy-750 flex items-center justify-between sticky top-0 bg-navy-900/95 backdrop-blur-md z-10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-500/15 border border-blue-500/30 text-blue-400 flex items-center justify-center">
              <Compass className="w-4 h-4" />
            </div>
            <div>
              <h3 id="market-context-title" className="font-bold text-white text-sm">
                Market Context & Macro Intelligence
              </h3>
              <p className="text-[10px] text-slate-400 font-mono">
                Systemic Indicators • Sector Benchmarks • Facts vs AI Interpretation
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-navy-800 transition-colors cursor-pointer"
            aria-label="Close Market Context Modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5 pt-0">
          {/* Article & Sentiment Context */}
          <div className="p-4 rounded-xl bg-navy-950/70 border border-navy-800 space-y-2.5">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-2">
                {getEntityIcon(context?.entity_type || 'general_market')}
                <span className="font-semibold text-white text-sm">
                  {context?.entity_name || article.company}
                </span>
                {context?.ticker && (
                  <span className="px-2 py-0.5 rounded bg-blue-500/15 border border-blue-500/30 text-blue-300 text-xs font-mono font-bold">
                    {context.ticker} {context.exchange ? `• ${context.exchange}` : ''}
                  </span>
                )}
                <span className="px-1.5 py-0.5 rounded text-[10px] uppercase font-mono tracking-wider bg-navy-800 text-slate-400 border border-navy-700">
                  {context?.entity_type.replace('_', ' ') || 'Market'}
                </span>
              </div>
              <SentimentBadge sentiment={article.sentiment} confidence={article.confidence} size="xs" />
            </div>
            <p className="text-xs text-slate-300 leading-relaxed italic">
              "{article.title}"
            </p>
            <div className="flex items-center gap-3 text-[11px] text-slate-400 font-mono pt-1 border-t border-navy-800/60">
              <span>Source: <strong className="text-slate-300">{article.source || 'Editorial Feed'}</strong></span>
              {article.published_at && (
                <span>Published: {new Date(article.published_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              )}
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="p-10 text-center space-y-3">
              <RefreshCw className="w-7 h-7 text-blue-400 animate-spin mx-auto" />
              <p className="text-xs text-slate-400 font-mono">
                Synthesizing macroeconomic indicators, sector benchmarks, and fact demarcation...
              </p>
            </div>
          )}

          {/* Error State */}
          {!loading && error && (
            <div className="p-5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Context Engine Error</p>
                <p className="text-[11px] text-rose-400/80 mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Context Details */}
          {!loading && context && (
            <div className="space-y-4">
              {/* Event Topic Card */}
              <div className="p-3 rounded-lg bg-navy-950 border border-navy-800 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-blue-400 shrink-0" />
                  <span className="text-xs text-slate-400">Financial Event Classification:</span>
                  <span className="text-xs font-semibold text-white">{context.event_topic}</span>
                </div>
              </div>

              {/* Market Indicators Grid */}
              {context.market_indicators && context.market_indicators.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                      <TrendingUp className="w-3.5 h-3.5 text-blue-400" />
                      Key Market & Sector Barometers:
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">Live/Session Benchmarks</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                    {context.market_indicators.map((ind, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-navy-950 border border-navy-800 hover:border-navy-700 transition-colors space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-white">{ind.name}</span>
                          <span className="text-[10px] font-mono text-slate-400">{ind.symbol}</span>
                        </div>
                        <div className="flex items-baseline justify-between">
                          <span className="text-sm font-bold font-mono text-slate-200">
                            {ind.value || 'Active'}
                          </span>
                          <div className="flex items-center gap-1">
                            {getTrendIcon(ind.trend)}
                            <span
                              className={`text-xs font-bold font-mono ${
                                ind.trend === 'up'
                                  ? 'text-emerald-400'
                                  : ind.trend === 'down'
                                  ? 'text-rose-400'
                                  : 'text-slate-400'
                              }`}
                            >
                              {ind.change || '0.00%'}
                            </span>
                          </div>
                        </div>
                        <p className="text-[10px] text-slate-400 leading-tight border-t border-navy-900 pt-1">
                          {ind.relevance_note}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Market Relevance Summary */}
              <div className="p-4 rounded-xl bg-gradient-to-br from-navy-950 to-navy-900 border border-blue-500/25 space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-300">
                  <Info className="w-3.5 h-3.5 text-blue-400" />
                  <span>Market Relevance & Transmission Mechanism</span>
                </div>
                <p className="text-xs text-slate-200 leading-relaxed">
                  {context.market_relevance}
                </p>
              </div>

              {/* Facts vs AI Interpretation */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {/* Objective Reported Facts */}
                <div className="p-3.5 rounded-xl bg-navy-950 border border-navy-800 space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Reported Facts (Objective)</span>
                  </div>
                  <ul className="space-y-1.5 text-[11px] text-slate-300 leading-relaxed">
                    {context.facts_vs_interpretation.objective_facts.map((fact, idx) => (
                      <li key={idx} className="flex items-start gap-1.5">
                        <span className="text-emerald-400 shrink-0 mt-0.5">•</span>
                        <span>{fact}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* AI Sentiment Interpretation & Risk Factors */}
                <div className="p-3.5 rounded-xl bg-navy-950 border border-navy-800 space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-purple-400">
                    <Compass className="w-3.5 h-3.5" />
                    <span>AI Sentiment Inference & Catalysts</span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    {context.facts_vs_interpretation.ai_interpretation}
                  </p>
                  {context.facts_vs_interpretation.risk_factors.length > 0 && (
                    <div className="border-t border-navy-900 pt-2 space-y-1">
                      <span className="text-[10px] uppercase font-mono tracking-wider text-slate-500 block">
                        Key Catalysts & Risks:
                      </span>
                      <ul className="space-y-1 text-[10px] text-amber-300/80">
                        {context.facts_vs_interpretation.risk_factors.map((risk, idx) => (
                          <li key={idx} className="flex items-start gap-1">
                            <span className="text-amber-400 shrink-0">•</span>
                            <span>{risk}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
                <button
                  onClick={handleCopySummary}
                  className="w-full sm:flex-1 py-2.5 px-4 rounded-xl bg-navy-800 hover:bg-navy-750 text-slate-200 hover:text-white border border-navy-700 text-xs font-semibold flex items-center justify-center gap-2 transition-colors cursor-pointer"
                >
                  {copied ? (
                    <>
                      <Check className="w-4 h-4 text-emerald-400" />
                      <span>Copied Context Summary!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 text-slate-400" />
                      <span>Copy Context Intelligence</span>
                    </>
                  )}
                </button>

                {onOpenTrade && article.company && article.company !== 'General Market' && (
                  <button
                    onClick={() => {
                      onClose();
                      onOpenTrade(article);
                    }}
                    className="w-full sm:w-auto py-2.5 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-md shadow-emerald-900/30 transition-all cursor-pointer"
                  >
                    <span>Proceed to Trade ({article.company})</span>
                    <ArrowUpRight className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Compliance & Data Freshness Footer */}
          <div className="p-3 rounded-xl bg-navy-950/40 border border-navy-800/60 text-[10px] text-slate-500 flex items-center justify-between">
            <span>FIN-SENTIMENT Market Context Engine • Educational & Informational</span>
            <span>Generated: {context ? new Date(context.generated_at).toLocaleTimeString() : 'Live'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
