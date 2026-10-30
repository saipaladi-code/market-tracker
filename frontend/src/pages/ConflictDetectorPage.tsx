import React, { useState, useEffect } from 'react';
import {
  GitCompareArrows,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Info,
  RefreshCw,
  ShieldAlert,
  ExternalLink,
  SlidersHorizontal,
  CheckCircle2,
  ArrowRight
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { ConflictSignal, Article } from '../types';
import { TradeRoutingModal } from '../components/TradeRoutingModal';

export const ConflictDetectorPage: React.FC = () => {
  const [conflicts, setConflicts] = useState<ConflictSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [threshold, setThreshold] = useState<number>(20); // 20% min divergence
  const [selectedTradeArticle, setSelectedTradeArticle] = useState<Article | null>(null);
  const [tradeModalOpen, setTradeModalOpen] = useState(false);

  const loadConflicts = async () => {
    try {
      setLoading(true);
      const data = await api.getConflicts();
      setConflicts(data);
    } catch (err) {
      console.error('Failed to load conflicts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConflicts();
  }, []);

  const filteredConflicts = conflicts.filter((c) => (c.conflict_score * 100) >= threshold);

  return (
    <div className="space-y-6 pb-12">
      {/* Header & Divergence Mechanics */}
      <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-6 backdrop-blur-md shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
              <GitCompareArrows className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-300 font-mono text-[10px] font-bold border border-amber-500/30">
                  DIVERGENCE ENGINE
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  {conflicts.length} Active Cross-Currents Flagged
                </span>
              </div>
              <h2 className="text-xl font-extrabold text-white tracking-tight">
                Bullish / Bearish Sentiment Conflict Detector
              </h2>
            </div>
          </div>

          <button
            onClick={loadConflicts}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-navy-850 hover:bg-navy-800 text-slate-300 border border-navy-750 rounded-xl text-xs font-semibold self-start md:self-auto cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
            <span>Recompute</span>
          </button>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed max-w-3xl">
          Automated surveillance identifying securities where mainstream financial publishers simultaneously emit
          opposing sentiment signals (positive growth catalysts vs. negative headwinds). Conflict score reflects
          the mathematical narrative divergence between bullish and bearish headline volume.
        </p>

        {/* Sensitivity Filter Toolbar */}
        <div className="pt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-t border-navy-800">
          <div className="flex items-center gap-3 text-xs text-slate-300">
            <SlidersHorizontal className="w-4 h-4 text-slate-400" />
            <span className="font-semibold text-slate-400">Divergence Sensitivity Threshold:</span>
            <input
              type="range"
              min="10"
              max="90"
              step="5"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="accent-blue-500 cursor-pointer w-28 sm:w-36"
            />
            <span className="font-mono text-blue-400 font-bold bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
              {threshold}%+
            </span>
          </div>

          <span className="text-[11px] text-slate-400 font-mono">
            Showing {filteredConflicts.length} of {conflicts.length} flagged securities
          </span>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-12">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
        </div>
      ) : filteredConflicts.length === 0 ? (
        <div className="p-12 text-center bg-navy-900 border border-navy-800 rounded-2xl space-y-3">
          <ShieldAlert className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-slate-200">No Sentiment Divergence Detected</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            All currently analyzed companies exhibit unified directional coverage at a {threshold}% divergence threshold.
          </p>
        </div>
      ) : (
        /* Conflict Cards Stream */
        <div className="space-y-4">
          {filteredConflicts.map((conf) => (
            <div
              key={conf.company}
              className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-6 space-y-5 hover:border-navy-700 transition-all shadow-sm"
            >
              {/* Card Header: Ticker, Conflict Score, Timestamp */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-navy-800">
                <div className="flex items-center gap-3">
                  <span className="px-3 py-1 rounded-xl bg-blue-600/20 text-blue-300 font-mono font-bold text-sm border border-blue-500/30">
                    {conf.ticker}
                  </span>
                  <div>
                    <h3 className="text-base font-bold text-white">{conf.company}</h3>
                    <div className="flex items-center gap-3 text-xs text-slate-400 font-mono mt-0.5">
                      <span className="text-emerald-400 font-semibold">+{conf.positive_count} Bullish</span>
                      <span>vs</span>
                      <span className="text-rose-400 font-semibold">-{conf.negative_count} Bearish</span>
                      <span className="text-slate-600">•</span>
                      <span>{conf.neutral_count} Neutral</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 font-mono uppercase block">Divergence Index</span>
                    <span className="text-base font-bold font-mono text-amber-400">
                      {(conf.conflict_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setSelectedTradeArticle({
                          id: `conflict-${conf.company}`,
                          canonical_id: `conflict-${conf.company}`,
                          title: `${conf.company} (${conf.ticker}) Narrative Divergence Conflict`,
                          company: conf.company,
                          ticker: conf.ticker,
                          url: '',
                          source: 'Sentiment Divergence Engine',
                          published_at: new Date().toISOString(),
                          is_duplicate: false,
                          is_demo: false,
                        });
                        setTradeModalOpen(true);
                      }}
                      className="px-2.5 py-1.5 bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                      title={`Trade ${conf.company} via verified broker`}
                    >
                      <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Trade</span>
                    </button>
                    <Link
                      to={`/companies?company=${encodeURIComponent(conf.company)}`}
                      className="px-3 py-1.5 bg-navy-800 hover:bg-navy-750 text-slate-200 rounded-lg text-xs font-semibold border border-navy-700 transition-colors flex items-center gap-1"
                    >
                      <span>Deep Dive</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              </div>

              {/* Analytical Explanation */}
              <div className="p-3.5 bg-navy-950/80 rounded-xl border border-navy-800 text-xs text-slate-300 leading-relaxed">
                <strong className="text-amber-400 mr-1.5 font-mono">Divergence Rationale:</strong>
                {conf.explanation}
              </div>

              {/* Opposing Signals: Side-by-side columns */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Positive Signals Column */}
                <div className="p-4 bg-emerald-950/20 border border-emerald-900/40 rounded-xl space-y-2.5">
                  <div className="flex items-center gap-2 text-xs font-bold text-emerald-400 uppercase font-mono tracking-wider">
                    <TrendingUp className="w-4 h-4" />
                    <span>Positive Catalysts ({conf.positive_headlines.length})</span>
                  </div>
                  <div className="space-y-2">
                    {conf.positive_headlines.length > 0 ? (
                      conf.positive_headlines.map((hl, i) => (
                        <div
                          key={i}
                          className="p-2.5 bg-navy-950/90 rounded-lg border border-emerald-500/20 text-xs text-slate-200 leading-relaxed font-medium"
                        >
                          "{hl}"
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-slate-500 italic">No specific bullish headline captured.</p>
                    )}
                  </div>
                </div>

                {/* Negative Signals Column */}
                <div className="p-4 bg-rose-950/20 border border-rose-900/40 rounded-xl space-y-2.5">
                  <div className="flex items-center gap-2 text-xs font-bold text-rose-400 uppercase font-mono tracking-wider">
                    <TrendingDown className="w-4 h-4" />
                    <span>Negative Headwinds ({conf.negative_headlines.length})</span>
                  </div>
                  <div className="space-y-2">
                    {conf.negative_headlines.length > 0 ? (
                      conf.negative_headlines.map((hl, i) => (
                        <div
                          key={i}
                          className="p-2.5 bg-navy-950/90 rounded-lg border border-rose-500/20 text-xs text-slate-200 leading-relaxed font-medium"
                        >
                          "{hl}"
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-slate-500 italic">No specific bearish headline captured.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      {/* Broker Trade Routing Modal */}
      <TradeRoutingModal
        isOpen={tradeModalOpen}
        onClose={() => {
          setTradeModalOpen(false);
          setSelectedTradeArticle(null);
        }}
        article={selectedTradeArticle}
      />
    </div>
  );
};
