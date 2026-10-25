import React, { useState, useEffect } from 'react';
import {
  GitCompareArrows,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Info,
  RefreshCw,
  ShieldAlert
} from 'lucide-react';
import { api } from '../services/api';
import { ConflictSignal } from '../types';

export const ConflictDetectorPage: React.FC = () => {
  const [conflicts, setConflicts] = useState<ConflictSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [threshold, setThreshold] = useState<number>(20); // 20% min divergence

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
    <div className="space-y-6">
      {/* Header & Concept Explanation */}
      <div className="bg-navy-900 border border-navy-750 p-5 rounded-xl space-y-3">
        <div className="flex items-center gap-2">
          <GitCompareArrows className="w-5 h-5 text-amber-400" />
          <h2 className="text-base font-bold text-white">Bullish/Bearish Sentiment Conflict Detector</h2>
          <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 font-mono text-[10px] border border-amber-500/20">
            Divergence Engine
          </span>
        </div>
        <p className="text-xs text-slate-300/90 leading-relaxed max-w-3xl">
          Identifies securities where published media coverage exhibits simultaneous positive catalysts and negative headwinds.
          This signal highlights narrative polarization—not guaranteed directional price predictions.
        </p>

        {/* Sensitivity Filter */}
        <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-navy-800">
          <div className="flex items-center gap-3 text-xs text-slate-300">
            <span className="font-semibold text-slate-400">Conflict Score Filter:</span>
            <input
              type="range"
              min="10"
              max="90"
              step="5"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="accent-blue-500 cursor-pointer"
            />
            <span className="font-mono text-blue-400 font-bold">{threshold}%+ Divergence</span>
          </div>

          <span className="text-[11px] text-slate-500 font-mono">
            {filteredConflicts.length} flagged companies
          </span>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-12">
          <RefreshCw className="w-6 h-6 text-blue-500 animate-spin" />
        </div>
      ) : filteredConflicts.length === 0 ? (
        <div className="p-12 text-center bg-navy-900 border border-navy-800 rounded-xl space-y-2">
          <ShieldAlert className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <h3 className="text-sm font-semibold text-slate-300">No Sentiment Divergence Detected</h3>
          <p className="text-xs text-slate-500">
            Current articles show unified directional tone across monitored companies at this threshold.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredConflicts.map((conf) => (
            <div
              key={conf.company}
              className="bg-navy-900 border border-navy-750 rounded-xl p-5 space-y-4 hover:border-navy-700 transition-colors"
            >
              {/* Card Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-navy-800">
                <div className="flex items-center gap-3">
                  <span className="px-2.5 py-1 rounded-md bg-blue-600/20 text-blue-300 font-mono font-bold text-xs border border-blue-500/30">
                    {conf.ticker}
                  </span>
                  <div>
                    <h3 className="text-sm font-bold text-white">{conf.company}</h3>
                    <span className="text-[10px] text-slate-400 font-mono">
                      Signal timestamp: {new Date(conf.flagged_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 uppercase font-mono block">Divergence Index</span>
                    <span className="text-base font-bold font-mono text-amber-400">
                      {(conf.conflict_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Conflict Narrative Explanation */}
              <div className="p-3 bg-navy-950 border border-navy-800 rounded-lg text-xs text-slate-300 space-y-1">
                <div className="flex items-center gap-1.5 text-amber-400 font-semibold text-[11px]">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Signal Rationale</span>
                </div>
                <p className="leading-relaxed">{conf.explanation}</p>
              </div>

              {/* Side-by-Side Opposing Headlines */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Positive Bullish Headlines */}
                <div className="bg-navy-950/80 border border-emerald-950 rounded-lg p-3.5 space-y-2">
                  <div className="flex items-center justify-between text-xs text-emerald-400 font-semibold pb-1 border-b border-emerald-900/40">
                    <div className="flex items-center gap-1.5">
                      <TrendingUp className="w-4 h-4" />
                      <span>Bullish / Catalyst Headlines</span>
                    </div>
                    <span className="font-mono text-[11px]">({conf.positive_count})</span>
                  </div>
                  <ul className="space-y-2 text-xs">
                    {conf.positive_headlines.map((h, i) => (
                      <li key={i} className="text-slate-200 pl-3 border-l-2 border-emerald-500/60 leading-snug">
                        "{h}"
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Negative Bearish Headlines */}
                <div className="bg-navy-950/80 border border-rose-950 rounded-lg p-3.5 space-y-2">
                  <div className="flex items-center justify-between text-xs text-rose-400 font-semibold pb-1 border-b border-rose-900/40">
                    <div className="flex items-center gap-1.5">
                      <TrendingDown className="w-4 h-4" />
                      <span>Bearish / Headwind Headlines</span>
                    </div>
                    <span className="font-mono text-[11px]">({conf.negative_count})</span>
                  </div>
                  <ul className="space-y-2 text-xs">
                    {conf.negative_headlines.map((h, i) => (
                      <li key={i} className="text-slate-200 pl-3 border-l-2 border-rose-500/60 leading-snug">
                        "{h}"
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
