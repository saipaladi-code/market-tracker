import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Building2,
  TrendingUp,
  TrendingDown,
  Minus,
  GitCompareArrows,
  ExternalLink,
  Layers,
  Calendar,
  AlertTriangle,
  RefreshCw,
  Search,
  Sparkles,
  BarChart3,
  Clock,
  CheckCircle2
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar
} from 'recharts';
import { api } from '../services/api';
import { CompanySummary, Article } from '../types';
import { SentimentBadge } from '../components/SentimentBadge';
import { TradeRoutingModal } from '../components/TradeRoutingModal';
import { resolveVerifiedTicker, resolveVerifiedInstrument } from '../utils/tickerLookup';

export const CompanyAnalysisPage: React.FC = () => {
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<string>('Nvidia');
  const [companyDetail, setCompanyDetail] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const location = useLocation();
  const [selectedTradeArticle, setSelectedTradeArticle] = useState<Article | null>(null);
  const [tradeModalOpen, setTradeModalOpen] = useState(false);

  // Read URL query parameter if user navigated from search bar or dashboard
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const compParam = params.get('company');
    if (compParam) {
      setSelectedCompany(compParam);
    }
  }, [location.search]);

  useEffect(() => {
    const loadCompanyList = async () => {
      try {
        setLoading(true);
        const list = await api.getCompanies();
        setCompanies(list);
        if (list.length > 0 && !selectedCompany) {
          setSelectedCompany(list[0].company);
        }
      } catch (err) {
        console.error('Failed to load companies:', err);
      } finally {
        setLoading(false);
      }
    };
    loadCompanyList();
  }, []);

  useEffect(() => {
    if (!selectedCompany) return;
    const loadDetail = async () => {
      try {
        setDetailLoading(true);
        const data = await api.getCompanyDetail(selectedCompany);
        setCompanyDetail(data);
      } catch (err) {
        console.error('Failed to load company detail:', err);
      } finally {
        setDetailLoading(false);
      }
    };
    loadDetail();
  }, [selectedCompany]);

  const activeSummary = companies.find(
    (c) => c.company.toLowerCase() === selectedCompany.toLowerCase()
  ) || companies[0];

  const filteredCompanyList = companies.filter(
    (c) =>
      c.company.toLowerCase().includes(searchFilter.toLowerCase()) ||
      (c.ticker || '').toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-6 backdrop-blur-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-mono font-bold uppercase tracking-wider">
                SECURITIES SURVEILLANCE
              </span>
              <span className="text-xs text-slate-400 font-mono">
                {companies.length} Tracked Institutional Equities
              </span>
            </div>
            <h2 className="text-xl font-extrabold text-white tracking-tight">
              Company Sentiment Deep Dive
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              In-depth tonal distribution, narrative conflict detection, and individual headline coverage.
            </p>
          </div>

          {/* Quick search input */}
          <div className="relative max-w-xs w-full">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Filter company list..."
              className="w-full bg-navy-950 border border-navy-700/80 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Horizontal Company Pill Selector */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
        {filteredCompanyList.map((c) => {
          const isSelected = selectedCompany.toLowerCase() === c.company.toLowerCase();
          return (
            <button
              key={c.company}
              onClick={() => setSelectedCompany(c.company)}
              className={`px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all border flex items-center gap-2 cursor-pointer ${
                isSelected
                  ? 'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-600/20'
                  : 'bg-navy-900/90 border-navy-750 text-slate-300 hover:bg-navy-850 hover:text-white'
              }`}
            >
              <span className="font-mono">{c.ticker}</span>
              <span className={isSelected ? 'text-white' : 'text-slate-400'}>{c.company}</span>
              {c.has_conflict && (
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" title="Active mixed-sentiment conflict" />
              )}
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-12">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
        </div>
      ) : activeSummary ? (
        <div className="space-y-6">
          {/* Active Company Hero Metric Banner */}
          <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-6 shadow-sm">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-5 border-b border-navy-800">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center text-white font-mono font-extrabold text-xl shadow-lg shadow-blue-500/20">
                  {activeSummary.ticker}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-xl font-bold text-white">{activeSummary.company}</h3>
                    <span className="px-2 py-0.5 rounded-md bg-navy-800 text-slate-300 border border-navy-700 text-xs font-mono">
                      {activeSummary.sector}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Total Ingested Articles: <strong className="text-white font-mono">{activeSummary.total_articles} distinct</strong>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 flex-wrap">
                {activeSummary.has_conflict && (
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-medium">
                    <GitCompareArrows className="w-4 h-4 text-amber-400" />
                    <span>Mixed-Sentiment Polarization Detected</span>
                  </div>
                )}
                {(() => {
                  const heroInst = resolveVerifiedInstrument(activeSummary.company, activeSummary.ticker);
                  const heroBroker = heroInst?.preferredBroker === 'upstox' ? 'Upstox' : 'IBKR';
                  return (
                    <button
                      onClick={() => {
                        setSelectedTradeArticle({
                          id: `hero-${activeSummary.company}`,
                          canonical_id: `hero-${activeSummary.company}`,
                          title: `${heroInst?.company || activeSummary.company} (${heroInst?.ticker || activeSummary.ticker}) Surveillance & Market Depth`,
                          company: heroInst?.company || activeSummary.company,
                          ticker: heroInst?.ticker || activeSummary.ticker,
                          url: '',
                          source: 'Securities Surveillance',
                          published_at: new Date().toISOString(),
                          is_duplicate: false,
                          is_demo: false,
                        });
                        setTradeModalOpen(true);
                      }}
                      className="px-3.5 py-2 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 text-xs font-semibold flex items-center gap-2 transition-colors cursor-pointer shadow-sm"
                      title={`Trade ${heroInst?.company || activeSummary.company} via ${heroInst?.brokerName || 'broker'}`}
                    >
                      <TrendingUp className="w-4 h-4 text-emerald-400" />
                      <span>Trade {heroInst?.ticker || activeSummary.ticker} ({heroBroker})</span>
                    </button>
                  );
                })()}
              </div>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-5">
              <div className="p-4 bg-navy-950/80 rounded-xl border border-navy-800">
                <span className="text-xs text-slate-400 block mb-1">Bullish Tone</span>
                <span className="text-2xl font-extrabold font-mono text-emerald-400">
                  {activeSummary.positive_pct}%
                </span>
                <span className="text-[11px] text-slate-500 block font-mono">
                  {activeSummary.positive_count} articles
                </span>
              </div>

              <div className="p-4 bg-navy-950/80 rounded-xl border border-navy-800">
                <span className="text-xs text-slate-400 block mb-1">Neutral Tone</span>
                <span className="text-2xl font-extrabold font-mono text-amber-400">
                  {activeSummary.neutral_pct}%
                </span>
                <span className="text-[11px] text-slate-500 block font-mono">
                  {activeSummary.neutral_count} articles
                </span>
              </div>

              <div className="p-4 bg-navy-950/80 rounded-xl border border-navy-800">
                <span className="text-xs text-slate-400 block mb-1">Bearish Tone</span>
                <span className="text-2xl font-extrabold font-mono text-rose-400">
                  {activeSummary.negative_pct}%
                </span>
                <span className="text-[11px] text-slate-500 block font-mono">
                  {activeSummary.negative_count} articles
                </span>
              </div>

              <div className="p-4 bg-navy-950/80 rounded-xl border border-navy-800">
                <span className="text-xs text-slate-400 block mb-1">Mean AI Confidence</span>
                <span className="text-2xl font-extrabold font-mono text-white">
                  {(activeSummary.average_confidence * 100).toFixed(1)}%
                </span>
                <span className="text-[11px] text-slate-500 block font-mono">FinBERT Softmax</span>
              </div>
            </div>
          </div>

          {/* Active Conflict Spotlight if present */}
          {companyDetail?.conflict && (
            <div className="bg-navy-900/90 border border-amber-500/30 rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <GitCompareArrows className="w-5 h-5 text-amber-400" />
                  <h4 className="text-sm font-bold text-white">
                    Narrative Divergence Analysis ({activeSummary.company})
                  </h4>
                </div>
                <span className="px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-mono text-xs font-bold border border-amber-500/30">
                  Conflict Score: {(companyDetail.conflict.conflict_score * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {companyDetail.conflict.explanation}
              </p>
            </div>
          )}

          {/* Company Historical Trend if available */}
          {companyDetail?.history && companyDetail.history.length > 1 && (
            <div className="bg-navy-900/90 border border-navy-750 rounded-2xl p-5 space-y-4 shadow-sm">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span>Historical Sentiment Progression ({activeSummary.company})</span>
              </h4>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={companyDetail.history} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1c2b4a" />
                    <XAxis dataKey="timestamp" stroke="#64748b" tick={{ fontSize: 10 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#070b14', borderColor: '#1c2b4a', borderRadius: '8px', fontSize: '11px' }}
                    />
                    <Line type="monotone" dataKey="positive_pct" stroke="#10b981" strokeWidth={2} name="Bullish %" />
                    <Line type="monotone" dataKey="negative_pct" stroke="#f43f5e" strokeWidth={2} name="Bearish %" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Company Related Articles Feed */}
          <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Published Headlines for {activeSummary.company}
                </h4>
                <p className="text-[11px] text-slate-500 font-mono">
                  {companyDetail?.articles?.length || 0} distinct articles indexed
                </p>
              </div>
            </div>

            {detailLoading ? (
              <div className="p-8 text-center">
                <RefreshCw className="w-6 h-6 text-blue-500 animate-spin mx-auto" />
              </div>
            ) : companyDetail?.articles && companyDetail.articles.length > 0 ? (
              <div className="space-y-3">
                {companyDetail.articles.map((art: Article) => (
                  <div
                    key={art.id}
                    className="p-4 bg-navy-950/80 border border-navy-800 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-3 hover:border-navy-700 transition-colors"
                  >
                    <div className="space-y-1.5 flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <SentimentBadge sentiment={art.sentiment} confidence={art.confidence} size="xs" />
                        <span className="text-[11px] text-slate-500 font-mono">{art.source}</span>
                      </div>
                      <h5 className="text-xs font-semibold text-slate-100 leading-snug">
                        {art.title}
                      </h5>
                    </div>

                    <div className="flex items-center gap-2 self-start md:self-auto shrink-0">
                      {(() => {
                        const hlInst = resolveVerifiedInstrument(art.company, art.ticker) || resolveVerifiedInstrument(activeSummary.company, activeSummary.ticker);
                        const hlBroker = hlInst?.preferredBroker === 'upstox' ? 'Upstox' : 'IBKR';
                        return (
                          <button
                            onClick={() => {
                              setSelectedTradeArticle({
                                ...art,
                                company: hlInst?.company || art.company || activeSummary.company,
                                ticker: hlInst?.ticker || art.ticker || activeSummary.ticker,
                              });
                              setTradeModalOpen(true);
                            }}
                            className="px-2.5 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                            title={`Trade ${hlInst?.company || art.company} via ${hlInst?.brokerName || 'broker'}`}
                          >
                            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                            <span>Trade ({hlBroker})</span>
                          </button>
                        );
                      })()}
                      <a
                        href={art.url}
                        target="_blank"
                        rel="noreferrer"
                        className="px-3 py-1.5 bg-navy-800 hover:bg-navy-750 text-slate-300 hover:text-white border border-navy-700 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors"
                      >
                        <span>Read Original</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic p-6 text-center bg-navy-950 rounded-xl border border-navy-800">
                No articles found for {activeSummary.company}.
              </p>
            )}
          </div>
        </div>
      ) : null}
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
