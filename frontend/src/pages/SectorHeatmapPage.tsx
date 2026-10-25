import React, { useState, useEffect } from 'react';
import {
  Grid3X3,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Building,
  Info,
  Layers,
  ArrowRight,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import { Link } from 'react-router-dom';
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
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-6 backdrop-blur-md shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-mono font-bold uppercase tracking-wider">
                MACRO SECTOR MATRIX
              </span>
              <span className="text-xs text-slate-400 font-mono">
                {sectors.length} Economic Sectors Tracked
              </span>
            </div>
            <h2 className="text-xl font-extrabold text-white tracking-tight">
              Market Sector Sentiment Heatmap
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Aggregated sentiment tone and net balance scores (-1.0 Bearish to +1.0 Bullish) across major industries.
            </p>
          </div>

          <button
            onClick={loadSectors}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-navy-850 hover:bg-navy-800 text-slate-300 border border-navy-750 rounded-xl text-xs font-semibold self-start md:self-auto cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
            <span>Recalculate Matrix</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-12">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sectors Grid (2 columns on lg) */}
          <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {sectors.map((sec) => {
              const isInsufficient = sec.article_count === 0;
              const isBullish = sec.net_sentiment_score > 0.15;
              const isBearish = sec.net_sentiment_score < -0.15;

              let cardBg = 'bg-navy-900/90 border-navy-750/90';
              let scoreColor = 'text-amber-400';
              let statusBadge = 'Neutral Balance';

              if (isBullish) {
                cardBg = 'bg-emerald-950/20 border-emerald-700/40 hover:border-emerald-500';
                scoreColor = 'text-emerald-400';
                statusBadge = 'Bullish Dominance';
              } else if (isBearish) {
                cardBg = 'bg-rose-950/20 border-rose-700/40 hover:border-rose-500';
                scoreColor = 'text-rose-400';
                statusBadge = 'Bearish Pressure';
              } else if (isInsufficient) {
                cardBg = 'bg-navy-950/40 border-navy-800 opacity-60';
                scoreColor = 'text-slate-500';
                statusBadge = 'No Headlines';
              }

              const isSelected = selectedSector?.sector === sec.sector;

              return (
                <div
                  key={sec.sector}
                  onClick={() => setSelectedSector(sec)}
                  className={`p-5 rounded-2xl border transition-all cursor-pointer space-y-4 shadow-sm hover:shadow-md ${cardBg} ${
                    isSelected ? 'ring-2 ring-blue-500 shadow-blue-500/10' : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-bold text-white">{sec.sector}</h3>
                      <span className="text-[11px] text-slate-400 font-mono">
                        {isInsufficient ? 'No verified articles' : `${sec.article_count} verified articles`}
                      </span>
                    </div>

                    <div className="text-right">
                      <span className="text-[10px] text-slate-400 font-mono uppercase block">Net Score</span>
                      <span className={`text-lg font-extrabold font-mono ${scoreColor}`}>
                        {sec.net_sentiment_score > 0 ? `+${sec.net_sentiment_score}` : sec.net_sentiment_score}
                      </span>
                    </div>
                  </div>

                  {/* Horizontal Segmented Bar */}
                  {!isInsufficient && (
                    <div className="space-y-1.5">
                      <div className="h-2 rounded-full bg-navy-950 flex overflow-hidden border border-navy-800">
                        <div
                          style={{ width: `${sec.bullish_pct}%` }}
                          className="bg-emerald-500 h-full"
                          title={`Bullish: ${sec.bullish_pct}%`}
                        />
                        <div
                          style={{ width: `${sec.neutral_pct}%` }}
                          className="bg-amber-500 h-full"
                          title={`Neutral: ${sec.neutral_pct}%`}
                        />
                        <div
                          style={{ width: `${sec.bearish_pct}%` }}
                          className="bg-rose-500 h-full"
                          title={`Bearish: ${sec.bearish_pct}%`}
                        />
                      </div>

                      <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-0.5">
                        <span className="text-emerald-400">+{sec.bullish_pct}%</span>
                        <span className="text-amber-400">{sec.neutral_pct}%</span>
                        <span className="text-rose-400">-{sec.bearish_pct}%</span>
                      </div>
                    </div>
                  )}

                  {/* Tracked Companies Tags */}
                  <div className="pt-2 border-t border-navy-850 flex flex-wrap gap-1.5">
                    {sec.companies.map((comp) => (
                      <span
                        key={comp}
                        className="px-2 py-0.5 rounded-md bg-navy-950/80 text-[10px] text-slate-300 font-mono border border-navy-800"
                      >
                        {comp}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Drilldown Inspector Card (Right side) */}
          <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-6 space-y-5 h-fit shadow-sm">
            {selectedSector ? (
              <div className="space-y-4">
                <div className="pb-4 border-b border-navy-800">
                  <span className="text-[10px] text-blue-400 font-mono uppercase font-bold tracking-wider">
                    SECTOR DRILLDOWN
                  </span>
                  <h3 className="text-lg font-bold text-white mt-1">{selectedSector.sector}</h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Constituent securities and sentiment distribution.
                  </p>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Total Sector Articles:</span>
                    <strong className="text-white font-mono">{selectedSector.article_count}</strong>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Net Tone Score:</span>
                    <strong className={`font-mono ${
                      selectedSector.net_sentiment_score > 0 ? 'text-emerald-400' : selectedSector.net_sentiment_score < 0 ? 'text-rose-400' : 'text-amber-400'
                    }`}>
                      {selectedSector.net_sentiment_score > 0 ? `+${selectedSector.net_sentiment_score}` : selectedSector.net_sentiment_score}
                    </strong>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Bullish Share:</span>
                    <strong className="text-emerald-400 font-mono">{selectedSector.bullish_pct}%</strong>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Neutral Share:</span>
                    <strong className="text-amber-400 font-mono">{selectedSector.neutral_pct}%</strong>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">Bearish Share:</span>
                    <strong className="text-rose-400 font-mono">{selectedSector.bearish_pct}%</strong>
                  </div>
                </div>

                <div className="pt-3 border-t border-navy-800 space-y-2">
                  <span className="text-xs font-semibold text-slate-300 block">Monitored Constituent Companies:</span>
                  <div className="space-y-2">
                    {selectedSector.companies.map((comp) => (
                      <Link
                        key={comp}
                        to={`/companies?company=${encodeURIComponent(comp)}`}
                        className="flex items-center justify-between p-2.5 bg-navy-950 hover:bg-navy-850 rounded-xl border border-navy-800 text-xs text-slate-200 transition-colors group"
                      >
                        <span className="font-semibold text-white">{comp}</span>
                        <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-blue-400 transition-colors" />
                      </Link>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500 text-center py-8">Select a sector to view detailed constituent analysis.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
