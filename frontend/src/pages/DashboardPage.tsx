import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  Layers,
  ArrowRight,
  ExternalLink,
  Cpu,
  RefreshCw,
  GitCompareArrows,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  Calendar,
  Clock,
  Filter,
  BarChart3,
  LineChart as LineChartIcon,
  Server,
  Zap
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  LineChart,
  Line
} from 'recharts';
import { api } from '../services/api';
import { DashboardStats, Article } from '../types';
import { SentimentBadge } from '../components/SentimentBadge';
import { BackendConfigModal } from '../components/BackendConfigModal';
import { TradeRoutingModal } from '../components/TradeRoutingModal';
import { resolveVerifiedTicker, resolveVerifiedInstrument } from '../utils/tickerLookup';
import { MOCK_DASHBOARD_STATS, MOCK_ARTICLES, MOCK_HISTORY } from '../services/mockData';

const COLORS = {
  positive: '#10b981', // Emerald
  neutral: '#f59e0b',  // Amber
  negative: '#f43f5e', // Rose
};

export const DashboardPage: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats>(MOCK_DASHBOARD_STATS);
  const [recentNews, setRecentNews] = useState<Article[]>(MOCK_ARTICLES.slice(0, 6));
  const [historyData, setHistoryData] = useState<any[]>(MOCK_HISTORY);
  const [loading, setLoading] = useState(true);
  const [timeframe, setTimeframe] = useState<'live' | '24h' | '7d' | 'all'>('live');
  const [showBackendModal, setShowBackendModal] = useState(false);
  const [selectedTradeArticle, setSelectedTradeArticle] = useState<Article | null>(null);
  const [tradeModalOpen, setTradeModalOpen] = useState(false);
  const navigate = useNavigate();

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsData, newsData, historyList] = await Promise.allSettled([
        api.getDashboardStats(),
        api.getNews({ page: 1, page_size: 6 }),
        api.getHistory(),
      ]);

      if (statsData.status === 'fulfilled' && statsData.value) {
        setStats(statsData.value);
      } else {
        setStats(MOCK_DASHBOARD_STATS);
      }

      if (newsData.status === 'fulfilled' && newsData.value) {
        setRecentNews(newsData.value.articles || []);
      } else {
        setRecentNews(MOCK_ARTICLES.slice(0, 6));
      }

      if (historyList.status === 'fulfilled' && Array.isArray(historyList.value) && historyList.value.length > 0) {
        setHistoryData(historyList.value);
      } else {
        setHistoryData(MOCK_HISTORY);
      }
    } catch (err: any) {
      console.warn('Dashboard synchronization fallback:', err);
      setStats(MOCK_DASHBOARD_STATS);
      setRecentNews(MOCK_ARTICLES.slice(0, 6));
      setHistoryData(MOCK_HISTORY);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading && !stats) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="relative">
          <div className="w-12 h-12 rounded-full border-2 border-blue-500/20 border-t-blue-500 animate-spin" />
          <Cpu className="w-5 h-5 text-blue-400 absolute inset-0 m-auto" />
        </div>
        <div className="text-center">
          <p className="text-sm font-semibold text-slate-200">Aggregating Financial Intelligence</p>
          <p className="text-xs text-slate-500 font-mono mt-1">Executing FinBERT inference calculations...</p>
        </div>
      </div>
    );
  }

  const pieData = [
    { name: 'Bullish (Positive)', value: stats.sentiment_counts.positive, color: COLORS.positive },
    { name: 'Neutral', value: stats.sentiment_counts.neutral, color: COLORS.neutral },
    { name: 'Bearish (Negative)', value: stats.sentiment_counts.negative, color: COLORS.negative },
  ];

  const totalDeduplicated = stats.total_including_duplicates - stats.total_articles;
  const dedupEfficiency = stats.total_including_duplicates > 0
    ? Math.round((totalDeduplicated / stats.total_including_duplicates) * 100)
    : 0;

  const isOffline = api.isOffline();

  return (
    <div className="space-y-6 pb-12">
      {/* Offline / Demo Intelligence Banner */}
      {(isOffline || stats.is_demo_dataset) && (
        <div className="flex flex-col sm:flex-row items-center justify-between p-3.5 px-4 bg-navy-900/90 border border-amber-500/30 rounded-2xl gap-3 text-xs shadow-md shadow-amber-500/5">
          <div className="flex items-center gap-2.5 text-amber-300">
            <div className="w-7 h-7 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <span className="font-bold text-white">Standalone Demo Intelligence: </span>
              <span className="text-slate-300">
                {isOffline
                  ? `Backend server at ${api.getBaseUrl()} is offline or unreachable.`
                  : 'Displaying curated institutional FinBERT analysis dataset.'}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => setShowBackendModal(true)}
              className="px-3 py-1.5 bg-navy-800 hover:bg-navy-750 border border-navy-700 text-slate-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5"
            >
              <Server className="w-3.5 h-3.5 text-blue-400" />
              <span>Configure Backend</span>
            </button>
            <button
              onClick={loadData}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry Sync</span>
            </button>
          </div>
        </div>
      )}

      {/* Backend Config Modal */}
      <BackendConfigModal
        isOpen={showBackendModal}
        onClose={() => setShowBackendModal(false)}
        onSave={loadData}
      />
      {/* Top Section / Header Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-navy-900/90 border border-navy-750/80 rounded-2xl p-5 backdrop-blur-md">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-mono font-bold uppercase tracking-wider">
              MARKET SENTIMENT TERMINAL
            </span>
            <span className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              {stats.model_status.toUpperCase()} (ProsusAI/finbert)
            </span>
          </div>
          <h2 className="text-xl font-extrabold text-white tracking-tight">
            Institutional Market Sentiment Overview
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time textual tone classification across verified news with automated narrative divergence detection.
          </p>
        </div>

        {/* Timeframe Controls & Refresh */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="bg-navy-950 p-1 rounded-xl border border-navy-750 flex items-center text-xs">
            {(['live', '24h', '7d', 'all'] as const).map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1 rounded-lg font-medium transition-all ${
                  timeframe === tf
                    ? 'bg-blue-600 text-white font-semibold shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tf === 'live' ? 'Live Session' : tf === '24h' ? '24h Window' : tf === '7d' ? '7D Scope' : 'All History'}
              </button>
            ))}
          </div>

          <button
            onClick={loadData}
            className="flex items-center gap-2 px-4 py-2 bg-navy-850 hover:bg-navy-800 text-slate-200 border border-navy-750 rounded-xl text-xs font-semibold transition-all cursor-pointer"
            title="Refresh current analytics metrics"
          >
            <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
            <span>Refresh</span>
          </button>

          <Link
            to="/analyze"
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-blue-600/20 transition-all"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>FinBERT Lab</span>
          </Link>
        </div>
      </div>

      {/* Top KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Unique Articles Analyzed */}
        <div className="bg-navy-900/90 border border-navy-750/90 p-5 rounded-2xl relative overflow-hidden group hover:border-navy-700 transition-all duration-200 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span className="font-medium">Total Unique Articles</span>
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-3xl font-extrabold font-mono text-white tracking-tight">
              {stats.total_articles}
            </span>
            <span className="text-xs text-slate-400 font-mono">distinct</span>
          </div>
          <div className="pt-2 border-t border-navy-800 flex items-center justify-between text-[11px] text-slate-400">
            <span>Deduplication Filter</span>
            <span className="font-mono text-cyan-400 font-semibold">
              +{totalDeduplicated} duplicates ({dedupEfficiency}%)
            </span>
          </div>
        </div>

        {/* Card 2: Bullish Sentiment */}
        <div className="bg-navy-900/90 border border-navy-750/90 p-5 rounded-2xl relative overflow-hidden group hover:border-emerald-500/30 transition-all duration-200 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span className="font-medium">Bullish Sentiment</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-3xl font-extrabold font-mono text-emerald-400 tracking-tight">
              {stats.sentiment_percentages.positive}%
            </span>
            <span className="text-xs text-slate-400 font-mono">
              ({stats.sentiment_counts.positive} articles)
            </span>
          </div>
          <div className="pt-2 border-t border-navy-800 flex items-center justify-between text-[11px] text-slate-400">
            <span>Market Stance</span>
            <span className="font-medium text-emerald-400">Positive tone dominance</span>
          </div>
        </div>

        {/* Card 3: Neutral Sentiment */}
        <div className="bg-navy-900/90 border border-navy-750/90 p-5 rounded-2xl relative overflow-hidden group hover:border-amber-500/30 transition-all duration-200 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span className="font-medium">Neutral Sentiment</span>
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <Minus className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-3xl font-extrabold font-mono text-amber-400 tracking-tight">
              {stats.sentiment_percentages.neutral}%
            </span>
            <span className="text-xs text-slate-400 font-mono">
              ({stats.sentiment_counts.neutral} articles)
            </span>
          </div>
          <div className="pt-2 border-t border-navy-800 flex items-center justify-between text-[11px] text-slate-400">
            <span>Reporting Tone</span>
            <span className="font-medium text-amber-300">Objective reporting</span>
          </div>
        </div>

        {/* Card 4: Bearish Sentiment */}
        <div className="bg-navy-900/90 border border-navy-750/90 p-5 rounded-2xl relative overflow-hidden group hover:border-rose-500/30 transition-all duration-200 shadow-sm">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span className="font-medium">Bearish Sentiment</span>
            <div className="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
              <TrendingDown className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-3xl font-extrabold font-mono text-rose-400 tracking-tight">
              {stats.sentiment_percentages.negative}%
            </span>
            <span className="text-xs text-slate-400 font-mono">
              ({stats.sentiment_counts.negative} articles)
            </span>
          </div>
          <div className="pt-2 border-t border-navy-800 flex items-center justify-between text-[11px] text-slate-400">
            <span>Risk Index</span>
            <span className="font-medium text-rose-400">Negative headwinds</span>
          </div>
        </div>
      </div>

      {/* Active Sentiment Conflicts Section */}
      {stats.active_conflicts && stats.active_conflicts.length > 0 && (
        <div className="p-5 bg-navy-900/90 border border-amber-500/30 rounded-2xl space-y-4 shadow-lg shadow-amber-500/5">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
                <GitCompareArrows className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white tracking-wide">
                  Active Bullish / Bearish Sentiment Conflicts ({stats.active_conflicts.length} Companies)
                </h3>
                <p className="text-xs text-slate-400">
                  Securities currently exhibiting simultaneous conflicting news signals from major publishers.
                </p>
              </div>
            </div>
            <Link
              to="/conflicts"
              className="text-xs text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1 transition-colors"
            >
              <span>Explore Conflict Engine</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {stats.active_conflicts.map((conf) => (
              <div
                key={conf.company}
                className="p-4 bg-navy-950/80 rounded-xl border border-navy-750 flex flex-col justify-between space-y-3 hover:border-navy-700 transition-colors"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white text-sm">{conf.company}</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-navy-800 text-slate-300 border border-navy-700">
                        {conf.ticker}
                      </span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 font-mono text-[10px] font-bold border border-amber-500/30">
                      {(conf.conflict_score * 100).toFixed(0)}% Divergence
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-emerald-400 font-mono font-semibold flex items-center gap-1">
                      <TrendingUp className="w-3 h-3" />
                      +{conf.positive_count} Bullish
                    </span>
                    <span className="text-slate-600">|</span>
                    <span className="text-rose-400 font-mono font-semibold flex items-center gap-1">
                      <TrendingDown className="w-3 h-3" />
                      -{conf.negative_count} Bearish
                    </span>
                  </div>

                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                    {conf.explanation}
                  </p>
                </div>

                <div className="pt-2 border-t border-navy-800/80 flex items-center justify-between text-[11px]">
                  <Link
                    to={`/companies?company=${encodeURIComponent(conf.company)}`}
                    className="text-blue-400 hover:text-blue-300 font-medium"
                  >
                    View coverage →
                  </Link>
                  <Link
                    to="/conflicts"
                    className="text-slate-400 hover:text-slate-200"
                  >
                    Side-by-side
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Sentiment Distribution Donut */}
        <div className="bg-navy-900/90 border border-navy-750/90 p-5 rounded-2xl space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Sentiment Tone Distribution
              </h3>
              <p className="text-[11px] text-slate-500 font-mono">FinBERT 3-Class Softmax</p>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">
              TOTAL: {stats.total_articles}
            </span>
          </div>

          <div className="h-56 relative flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} stroke="#0b1120" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#070b14',
                    borderColor: '#1c2b4a',
                    borderRadius: '10px',
                    fontSize: '12px',
                    color: '#f8fafc',
                    boxShadow: '0 8px 30px rgba(0,0,0,0.5)'
                  }}
                  itemStyle={{ color: '#e2e8f0' }}
                />
              </PieChart>
            </ResponsiveContainer>
            {/* Center metric label */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-2xl font-extrabold font-mono text-white">{stats.total_articles}</span>
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">Headlines</span>
            </div>
          </div>

          {/* Breakdown pills */}
          <div className="grid grid-cols-3 gap-2 text-center text-xs pt-1">
            <div className="p-2.5 bg-navy-950 rounded-xl border border-navy-800">
              <div className="w-2 h-2 rounded-full bg-emerald-400 mx-auto mb-1" />
              <span className="text-slate-400 block text-[10px]">Bullish</span>
              <strong className="text-emerald-400 font-mono">{stats.sentiment_percentages.positive}%</strong>
            </div>
            <div className="p-2.5 bg-navy-950 rounded-xl border border-navy-800">
              <div className="w-2 h-2 rounded-full bg-amber-400 mx-auto mb-1" />
              <span className="text-slate-400 block text-[10px]">Neutral</span>
              <strong className="text-amber-400 font-mono">{stats.sentiment_percentages.neutral}%</strong>
            </div>
            <div className="p-2.5 bg-navy-950 rounded-xl border border-navy-800">
              <div className="w-2 h-2 rounded-full bg-rose-400 mx-auto mb-1" />
              <span className="text-slate-400 block text-[10px]">Bearish</span>
              <strong className="text-rose-400 font-mono">{stats.sentiment_percentages.negative}%</strong>
            </div>
          </div>
        </div>

        {/* Right: Company Coverage Intensity */}
        <div className="bg-navy-900/90 border border-navy-750/90 p-5 rounded-2xl space-y-4 lg:col-span-2 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Media Coverage Intensity by Company
              </h3>
              <p className="text-[11px] text-slate-500 font-mono">Article volume per monitored ticker</p>
            </div>
            <Link
              to="/companies"
              className="text-xs text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1"
            >
              <span>View all companies</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={stats.top_discussed_companies}
                margin={{ top: 10, right: 10, left: -20, bottom: 25 }}
                onClick={(data: any) => {
                  if (data && data.activePayload && data.activePayload.length > 0) {
                    const comp = data.activePayload[0].payload.company;
                    navigate(`/companies?company=${encodeURIComponent(comp)}`);
                  }
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#1c2b4a" vertical={false} />
                <XAxis
                  dataKey="company"
                  stroke="#64748b"
                  tick={{ fontSize: 11, fill: '#94a3b8' }}
                  interval={0}
                  angle={-15}
                  textAnchor="end"
                />
                <YAxis stroke="#64748b" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#070b14',
                    borderColor: '#1c2b4a',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: '#f8fafc',
                  }}
                  formatter={(value: any) => [`${value} articles`, 'Coverage Volume']}
                />
                <Bar
                  dataKey="count"
                  fill="#3b82f6"
                  radius={[6, 6, 0, 0]}
                  name="Articles"
                  cursor="pointer"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Historical Sentiment Progression (Real Data or Institutional Empty State) */}
      <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-5 space-y-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <LineChartIcon className="w-4 h-4 text-cyan-400" />
              <span>Historical Sentiment Progression</span>
            </h3>
            <p className="text-[11px] text-slate-500 font-mono">
              Aggregated time-series trend of positive vs negative sentiment ratios
            </p>
          </div>
          <Link to="/alerts" className="text-xs text-blue-400 hover:text-blue-300 font-semibold">
            View history audit →
          </Link>
        </div>

        {historyData && historyData.length > 1 ? (
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={historyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1c2b4a" />
                <XAxis dataKey="timestamp" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#070b14', borderColor: '#1c2b4a', borderRadius: '8px', fontSize: '11px' }}
                />
                <Line type="monotone" dataKey="positive_pct" stroke="#10b981" strokeWidth={2} name="Bullish %" dot={false} />
                <Line type="monotone" dataKey="negative_pct" stroke="#f43f5e" strokeWidth={2} name="Bearish %" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="p-8 text-center bg-navy-950/60 rounded-xl border border-navy-800/80 space-y-2">
            <Clock className="w-8 h-8 text-blue-400/60 mx-auto mb-1" />
            <h4 className="text-xs font-semibold text-slate-200">Historical Time-Series Accumulation</h4>
            <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
              Historical trends record sequentially upon each automated news ingestion cycle. Click{' '}
              <strong className="text-blue-400">"Ingest News"</strong> or trigger scheduled refreshes to build multiple timeline points.
            </p>
          </div>
        )}
      </div>

      {/* Recent Classified Financial News Feed */}
      <div className="bg-navy-900/90 border border-navy-750/90 rounded-2xl p-5 space-y-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Live Classified Financial News Headlines
            </h3>
            <p className="text-[11px] text-slate-500 font-mono">
              Classified by local HuggingFace <code className="text-slate-400">ProsusAI/finbert</code>
            </p>
          </div>
          <Link to="/news" className="text-xs text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1">
            <span>Explore All News Feed</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {recentNews.length === 0 ? (
            <div className="col-span-full p-8 text-center bg-navy-950/60 rounded-xl border border-navy-800/80 text-xs text-slate-500">
              No recent classified financial articles recorded. Trigger news refresh to ingest market headlines.
            </div>
          ) : (
            recentNews.map((art) => {
              const verifiedInst = resolveVerifiedInstrument(art.company, art.ticker);
              const verifiedTicker = verifiedInst?.ticker || resolveVerifiedTicker(art.company, art.ticker);
              const isTradable = Boolean(verifiedInst);
              const brokerTag = verifiedInst?.preferredBroker === 'upstox' ? 'Upstox' : 'IBKR';

              return (
                <div
                  key={art.id}
                  className="bg-navy-950/90 border border-navy-800/90 rounded-xl p-4 flex flex-col justify-between space-y-3 hover:border-navy-700 hover:shadow-md transition-all"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs gap-1.5 flex-wrap">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-white px-2 py-0.5 rounded bg-navy-850 border border-navy-750 font-mono text-[11px]">
                          {art.company}
                        </span>
                        {verifiedTicker && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-semibold">
                            {verifiedTicker}
                          </span>
                        )}
                      </div>
                      <SentimentBadge sentiment={art.sentiment} confidence={art.confidence} size="xs" />
                    </div>
                    <h4 className="text-xs font-medium text-slate-100 line-clamp-2 leading-snug">
                      {art.title}
                    </h4>
                  </div>

                  <div className="pt-2 border-t border-navy-800/80 flex items-center justify-between text-[11px] text-slate-400 gap-2">
                    <span className="truncate max-w-[110px]">{art.source}</span>
                    <div className="flex items-center gap-2">
                      {isTradable ? (
                        <button
                          onClick={() => {
                            setSelectedTradeArticle({
                              ...art,
                              company: verifiedInst?.company || art.company,
                              ticker: verifiedTicker || art.ticker,
                            });
                            setTradeModalOpen(true);
                          }}
                          className="px-2 py-0.5 rounded bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30 text-[10px] font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                          title={`Trade ${verifiedInst?.company || art.company} via ${verifiedInst?.brokerName || 'broker'}`}
                        >
                          <TrendingUp className="w-3 h-3 text-emerald-400" />
                          <span>Trade ({brokerTag})</span>
                        </button>
                      ) : (
                        <span className="text-[10px] font-mono text-slate-500 px-1.5 py-0.5 bg-navy-850 rounded border border-navy-750">
                          Market News
                        </span>
                      )}
                      <a
                        href={art.url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        <span>Source</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                </div>
              );
            }))}
        </div>
      </div>
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
