import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
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
  GitCompareArrows
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { api } from '../services/api';
import { DashboardStats, Article } from '../types';
import { SentimentBadge } from '../components/SentimentBadge';

const COLORS = {
  positive: '#10b981', // Emerald
  neutral: '#f59e0b',  // Amber
  negative: '#ef4444', // Rose
};

export const DashboardPage: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentNews, setRecentNews] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [statsData, newsData] = await Promise.all([
        api.getDashboardStats(),
        api.getNews({ page: 1, page_size: 6 })
      ]);
      setStats(statsData);
      setRecentNews(newsData.articles || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load dashboard metrics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
        <p className="text-sm text-slate-400">Loading Financial Sentiment Intelligence...</p>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="p-8 text-center bg-navy-900 border border-navy-800 rounded-xl max-w-xl mx-auto my-12">
        <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-white mb-1">Failed to Connect to Analytics Service</h3>
        <p className="text-xs text-slate-400 mb-4">{error || 'Unknown error occurred'}</p>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-xs font-medium"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const pieData = [
    { name: 'Bullish / Positive', value: stats.sentiment_counts.positive, color: COLORS.positive },
    { name: 'Neutral', value: stats.sentiment_counts.neutral, color: COLORS.neutral },
    { name: 'Bearish / Negative', value: stats.sentiment_counts.negative, color: COLORS.negative },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner: Realism & FinBERT Notice */}
      <div className="bg-gradient-to-r from-blue-950/60 to-navy-900 border border-blue-800/30 rounded-xl p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 font-mono text-xs font-semibold">
              LOCAL FinBERT INFERENCE
            </span>
            <span className="text-xs text-slate-400 font-mono">PyTorch CPU Execution</span>
          </div>
          <h2 className="text-base font-bold text-white tracking-tight">
            Financial News Sentiment Analytics
          </h2>
          <p className="text-xs text-slate-300/80 max-w-2xl">
            Tone classification powered by Hugging Face <code className="text-blue-300">ProsusAI/finbert</code>. 
            Statistics are computed from verified distinct headlines.
          </p>
        </div>
        <Link
          to="/analyze"
          className="shrink-0 flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium shadow-md shadow-blue-600/20 transition-all"
        >
          <span>Test Live Headline</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-navy-900 border border-navy-750 p-4 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Articles Analyzed</span>
            <Layers className="w-4 h-4 text-blue-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-white">{stats.total_articles}</span>
            <span className="text-[11px] text-slate-400">distinct</span>
          </div>
          <p className="text-[11px] text-slate-500">
            {stats.total_including_duplicates} total fetched ({stats.total_including_duplicates - stats.total_articles} duplicates filtered)
          </p>
        </div>

        <div className="bg-navy-900 border border-navy-750 p-4 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Bullish Tone</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-emerald-400">
              {stats.sentiment_percentages.positive}%
            </span>
            <span className="text-[11px] text-slate-400 font-mono">({stats.sentiment_counts.positive} articles)</span>
          </div>
          <p className="text-[11px] text-slate-500">Positive financial sentiment tone</p>
        </div>

        <div className="bg-navy-900 border border-navy-750 p-4 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Neutral Tone</span>
            <Minus className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-amber-400">
              {stats.sentiment_percentages.neutral}%
            </span>
            <span className="text-[11px] text-slate-400 font-mono">({stats.sentiment_counts.neutral} articles)</span>
          </div>
          <p className="text-[11px] text-slate-500">Informational / neutral reporting</p>
        </div>

        <div className="bg-navy-900 border border-navy-750 p-4 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Bearish Tone</span>
            <TrendingDown className="w-4 h-4 text-rose-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-rose-400">
              {stats.sentiment_percentages.negative}%
            </span>
            <span className="text-[11px] text-slate-400 font-mono">({stats.sentiment_counts.negative} articles)</span>
          </div>
          <p className="text-[11px] text-slate-500">Negative financial sentiment tone</p>
        </div>
      </div>

      {/* Active Sentiment Conflicts Alert Banner */}
      {stats.active_conflicts && stats.active_conflicts.length > 0 && (
        <div className="p-4 bg-navy-900 border border-amber-500/30 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <GitCompareArrows className="w-4 h-4 text-amber-400" />
              <h3 className="text-xs font-semibold text-white tracking-wide uppercase">
                Active Mixed-Sentiment Conflicts ({stats.active_conflicts.length} Companies)
              </h3>
            </div>
            <Link to="/conflicts" className="text-xs text-blue-400 hover:text-blue-300 font-medium">
              View all conflicts →
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {stats.active_conflicts.map((conf) => (
              <div key={conf.company} className="p-3 bg-navy-950 rounded-lg border border-navy-800 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white">{conf.company}</span>
                  <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 font-mono text-[10px] border border-amber-500/20">
                    Conflict: {(conf.conflict_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex items-center gap-3 text-[11px] text-slate-400">
                  <span className="text-emerald-400 font-mono font-medium">+{conf.positive_count} Positive</span>
                  <span>vs</span>
                  <span className="text-rose-400 font-mono font-medium">-{conf.negative_count} Negative</span>
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2">
                  {conf.explanation}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Analytics Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sentiment Distribution Donut */}
        <div className="bg-navy-900 border border-navy-750 p-5 rounded-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Sentiment Distribution
            </h3>
            <span className="text-[11px] text-slate-500 font-mono">FinBERT Classes</span>
          </div>

          <div className="h-56 relative flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                  itemStyle={{ color: '#e2e8f0' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="p-2 bg-navy-950 rounded border border-navy-800">
              <div className="w-2 h-2 rounded-full bg-emerald-400 mx-auto mb-1"></div>
              <span className="text-slate-400 block text-[10px]">Positive</span>
              <strong className="text-white font-mono">{stats.sentiment_percentages.positive}%</strong>
            </div>
            <div className="p-2 bg-navy-950 rounded border border-navy-800">
              <div className="w-2 h-2 rounded-full bg-amber-400 mx-auto mb-1"></div>
              <span className="text-slate-400 block text-[10px]">Neutral</span>
              <strong className="text-white font-mono">{stats.sentiment_percentages.neutral}%</strong>
            </div>
            <div className="p-2 bg-navy-950 rounded border border-navy-800">
              <div className="w-2 h-2 rounded-full bg-rose-400 mx-auto mb-1"></div>
              <span className="text-slate-400 block text-[10px]">Negative</span>
              <strong className="text-white font-mono">{stats.sentiment_percentages.negative}%</strong>
            </div>
          </div>
        </div>

        {/* Most Discussed Companies */}
        <div className="bg-navy-900 border border-navy-750 p-5 rounded-xl space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Coverage Intensity (Article Count by Company)
            </h3>
            <Link to="/companies" className="text-xs text-blue-400 hover:text-blue-300">
              Deep dive →
            </Link>
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={stats.top_discussed_companies}
                margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="company" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Articles" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent Classified Financial News Feed */}
      <div className="bg-navy-900 border border-navy-750 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Recent Financial Headlines & AI Classifications
            </h3>
            <p className="text-[11px] text-slate-500">Live predictions from local FinBERT</p>
          </div>
          <Link to="/news" className="text-xs text-blue-400 hover:text-blue-300 font-medium">
            Explore All News →
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {recentNews.map((art) => (
            <div
              key={art.id}
              className="bg-navy-950 border border-navy-800 rounded-lg p-3.5 flex flex-col justify-between space-y-3 hover:border-navy-700 transition-colors"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span className="font-semibold text-slate-300">{art.company}</span>
                  <SentimentBadge sentiment={art.sentiment} confidence={art.confidence} />
                </div>
                <h4 className="text-xs font-medium text-white line-clamp-2 leading-snug">
                  {art.title}
                </h4>
              </div>

              <div className="pt-2 border-t border-navy-800/80 flex items-center justify-between text-[10px] text-slate-500">
                <span>{art.source}</span>
                <a
                  href={art.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 text-blue-400 hover:text-blue-300"
                >
                  <span>Source</span>
                  <ExternalLink className="w-2.5 h-2.5" />
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
