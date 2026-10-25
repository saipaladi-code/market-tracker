import React, { useState, useEffect } from 'react';
import {
  Grid3X3,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Building,
  Info
} from 'lucide-react';
import { api } from '../services/api';
import { SectorSentiment } from '../types';

export const SectorHeatmapPage: React.FC = () => {
  const [sectors, setSectors] = useState<SectorSentiment[]>([]);
  const [selectedSector, setSelectedSector] = useState<SectorSentiment | null>(null);
  const [loading, setLoading] = useState(true);

  const loadSectors = async () => {
    try {
      setLoading(true);
      const data = await api.getSectors();
      setSectors(data);
      if (data.length > 0) {
        setSelectedSector(data[0]);
      }
    } catch (err) {
      console.error('Failed to load sectors:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSectors();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Grid3X3 className="w-5 h-5 text-blue-400" />
          <h2 className="text-base font-bold text-white">Market Sector Sentiment Heatmap</h2>
          <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-mono text-[10px] border border-blue-500/20">
            Sectoral Aggregations
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Aggregated sentiment distribution and net scores (-1.0 Bearish to +1.0 Bullish) across economic sectors.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-12">
          <RefreshCw className="w-6 h-6 text-blue-500 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sectors.map((sec) => {
            const isInsufficient = sec.article_count === 0;
            const isBullish = sec.net_sentiment_score > 0.15;
            const isBearish = sec.net_sentiment_score < -0.15;

            let cardBg = 'bg-navy-900 border-navy-750';
            let scoreColor = 'text-amber-400';

            if (isBullish) {
              cardBg = 'bg-emerald-950/20 border-emerald-800/40 hover:border-emerald-700';
              scoreColor = 'text-emerald-400';
            } else if (isBearish) {
              cardBg = 'bg-rose-950/20 border-rose-800/40 hover:border-rose-700';
              scoreColor = 'text-rose-400';
            } else if (isInsufficient) {
              cardBg = 'bg-navy-950/40 border-navy-800 opacity-60';
              scoreColor = 'text-slate-500';
            }

            return (
              <div
                key={sec.sector}
                onClick={() => setSelectedSector(sec)}
                className={`p-5 rounded-xl border transition-all cursor-pointer space-y-4 ${cardBg} ${
                  selectedSector?.sector === sec.sector ? 'ring-2 ring-blue-500' : ''
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-white">{sec.sector}</h3>
                    <span className="text-[11px] text-slate-400">
                      {isInsufficient ? 'No articles recorded' : `${sec.article_count} verified articles`}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 font-mono block">Net Score</span>
                    <span className={`text-base font-bold font-mono ${scoreColor}`}>
                      {sec.net_sentiment_score > 0 ? `+${sec.net_sentiment_score}` : sec.net_sentiment_score}
                    </span>
                  </div>
                </div>

                {/* Progress bar */}
                {!isInsufficient && (
                  <div className="space-y-1.5">
                    <div className="h-2 w-full bg-navy-950 rounded-full flex overflow-hidden">
                      <div style={{ width: `${sec.bullish_pct}%` }} className="bg-emerald-500 h-full" title={`Bullish ${sec.bullish_pct}%`} />
                      <div style={{ width: `${sec.neutral_pct}%` }} className="bg-amber-500 h-full" title={`Neutral ${sec.neutral_pct}%`} />
                      <div style={{ width: `${sec.bearish_pct}%` }} className="bg-rose-500 h-full" title={`Bearish ${sec.bearish_pct}%`} />
                    </div>

                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-1">
                      <span className="text-emerald-400 font-semibold">{sec.bullish_pct}% Bull</span>
                      <span className="text-amber-400 font-semibold">{sec.neutral_pct}% Neu</span>
                      <span className="text-rose-400 font-semibold">{sec.bearish_pct}% Bear</span>
                    </div>
                  </div>
                )}

                {/* Represented Companies */}
                <div className="pt-2 border-t border-navy-850 flex items-center justify-between text-xs text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <Building className="w-3.5 h-3.5 text-slate-500" />
                    <span>Companies:</span>
                  </div>
                  <span className="font-medium text-slate-300 truncate max-w-[150px]">
                    {sec.companies.length > 0 ? sec.companies.join(', ') : 'None'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Selected Sector Details Box */}
      {selectedSector && selectedSector.article_count > 0 && (
        <div className="p-5 bg-navy-900 border border-navy-750 rounded-xl space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Sector Profile: {selectedSector.sector}
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            The {selectedSector.sector} sector is currently classified as 
            <strong className="text-white"> {selectedSector.status} </strong> with a net sentiment polarity score of 
            <span className="font-mono text-blue-400 font-bold"> {selectedSector.net_sentiment_score}</span>.
            Underlying tracked tickers: {selectedSector.companies.join(', ')}.
          </p>
        </div>
      )}
    </div>
  );
};
