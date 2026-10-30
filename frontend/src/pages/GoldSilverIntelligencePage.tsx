import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Coins,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Search,
  Calendar,
  ExternalLink,
  Languages,
  Clock,
  ShieldAlert,
  BarChart3,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  Loader2,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  AreaChart,
  Area,
  CartesianGrid
} from 'recharts';
import { api } from '../services/api';
import {
  MetalsPricesResponse,
  MetalsNewsResponse,
  MetalsSentimentSummary,
  MetalsHistoryResponse,
  MetalsArticle
} from '../types';

export const GoldSilverIntelligencePage: React.FC = () => {
  const { t, i18n } = useTranslation();

  // State
  const [prices, setPrices] = useState<MetalsPricesResponse | null>(null);
  const [news, setNews] = useState<MetalsNewsResponse | null>(null);
  const [summary, setSummary] = useState<MetalsSentimentSummary | null>(null);
  const [history, setHistory] = useState<MetalsHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedMetal, setSelectedMetal] = useState<string>('All');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [timeframeDays, setTimeframeDays] = useState<number>(30);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Dynamic Headline Translations Cache: { [articleId]: { translatedText, isShowingTranslated, loading } }
  const [translations, setTranslations] = useState<
    Record<string, { translatedText: string; isShowingTranslated: boolean; loading: boolean }>
  >({});

  const fetchData = async () => {
    try {
      setError(null);
      const [pricesRes, newsRes, summaryRes, historyRes] = await Promise.all([
        api.getMetalsPrices(),
        api.getMetalsNews({
          metal: selectedMetal === 'All' ? undefined : selectedMetal,
          category: selectedCategory === 'All' ? undefined : selectedCategory,
          days: timeframeDays,
          page: currentPage,
          page_size: 12,
          search: searchQuery || undefined
        }),
        api.getMetalsSentiment(timeframeDays),
        api.getMetalsHistory(14)
      ]);

      setPrices(pricesRes);
      setNews(newsRes);
      setSummary(summaryRes);
      setHistory(historyRes);
    } catch (err: any) {
      console.error('Failed to load metals intelligence:', err);
      setError(err?.message || 'Failed to load precious metals intelligence data.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedMetal, selectedCategory, timeframeDays, currentPage]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchData();
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchData();
  };

  const toggleTranslation = async (article: MetalsArticle) => {
    const current = translations[article.id];
    const targetLang = (i18n.language || 'en').toLowerCase().split('-')[0];

    // If target is English, toggle between raw title
    if (targetLang === 'en') {
      return;
    }

    if (current && current.translatedText) {
      setTranslations((prev) => ({
        ...prev,
        [article.id]: {
          ...current,
          isShowingTranslated: !current.isShowingTranslated
        }
      }));
      return;
    }

    // Fetch translation from backend
    setTranslations((prev) => ({
      ...prev,
      [article.id]: {
        translatedText: '',
        isShowingTranslated: false,
        loading: true
      }
    }));

    try {
      const res = await api.translateText(article.title, targetLang, article.id);
      setTranslations((prev) => ({
        ...prev,
        [article.id]: {
          translatedText: res.translated_text || article.title,
          isShowingTranslated: true,
          loading: false
        }
      }));
    } catch (e) {
      console.warn('Translation error for article:', article.id, e);
      setTranslations((prev) => ({
        ...prev,
        [article.id]: {
          translatedText: article.title,
          isShowingTranslated: false,
          loading: false
        }
      }));
    }
  };

  // Recharts comparison data
  const comparisonData = [
    {
      name: t('metals.gold', 'Gold'),
      Bullish: summary?.gold_sentiment.bullish_pct || 0,
      Neutral: summary?.gold_sentiment.neutral_pct || 0,
      Bearish: summary?.gold_sentiment.bearish_pct || 0
    },
    {
      name: t('metals.silver', 'Silver'),
      Bullish: summary?.silver_sentiment.bullish_pct || 0,
      Neutral: summary?.silver_sentiment.neutral_pct || 0,
      Bearish: summary?.silver_sentiment.bearish_pct || 0
    }
  ];

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-navy-750">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-gradient-to-br from-amber-500/20 to-yellow-600/10 border border-amber-500/30 text-amber-400">
              <Coins className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-black tracking-tight text-white flex items-center gap-2">
                <span>{t('metals.title', 'Gold & Silver Market Intelligence')}</span>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30 font-semibold">
                  MCX & COMEX
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                {t(
                  'metals.subtitle',
                  'Real-time bullion market dynamics, COMEX quotes, Indian domestic benchmarks, and FinBERT precious metals sentiment'
                )}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          {prices && (
            <div className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-navy-900 border border-navy-750 text-[11px] text-slate-300 font-mono">
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              <span>{prices.last_updated}</span>
            </div>
          )}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-gradient-to-r from-amber-500 to-yellow-600 hover:from-amber-400 hover:to-yellow-500 text-navy-950 font-bold rounded-lg text-xs shadow-md shadow-amber-500/20 transition-all cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span>{refreshing ? t('common.loading', 'Syncing...') : t('dashboard.refresh', 'Sync Feed')}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Top Section: Live Commodity Prices */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Gold Card */}
        <div className="p-5 rounded-2xl bg-gradient-to-br from-navy-900 to-navy-900/60 border border-amber-500/30 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/5 rounded-full blur-2xl pointer-events-none" />
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-amber-400 shadow-sm shadow-amber-400/50" />
              <h2 className="text-base font-extrabold text-amber-300 tracking-wide">
                {t('metals.goldCard', 'COMEX Gold Futures (GC=F)')}
              </h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
              {prices?.gold.international?.exchange || 'COMEX'} • {prices?.gold.international?.freshness || 'Active'}
            </span>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4">
            {/* International USD/oz */}
            <div className="p-3.5 rounded-xl bg-navy-950/80 border border-navy-750">
              <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">
                International (USD / oz)
              </span>
              <div className="text-2xl font-black font-mono text-white">
                ${prices?.gold.international?.price.toLocaleString() || '3,995.00'}
              </div>
              <div
                className={`flex items-center gap-1 text-xs font-mono font-semibold mt-1 ${
                  (prices?.gold.international?.change || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {(prices?.gold.international?.change || 0) >= 0 ? (
                  <ArrowUpRight className="w-3.5 h-3.5" />
                ) : (
                  <ArrowDownRight className="w-3.5 h-3.5" />
                )}
                <span>
                  {(prices?.gold.international?.change || 0) >= 0 ? '+' : ''}
                  {prices?.gold.international?.change.toFixed(2)} (
                  {prices?.gold.international?.change_pct.toFixed(2)}%)
                </span>
              </div>
            </div>

            {/* India Domestic Benchmark */}
            <div className="p-3.5 rounded-xl bg-navy-950/80 border border-amber-500/20">
              <span className="text-[10px] font-mono uppercase text-amber-400/90 block mb-1">
                {t('metals.indiaDomesticGold', 'India Domestic (10g)')}
              </span>
              <div className="text-2xl font-black font-mono text-amber-300">
                ₹{prices?.gold.india_domestic?.price_inr.toLocaleString('en-IN') || '1,40,590'}
              </div>
              <div className="text-[10px] text-slate-400 font-mono mt-1">
                Basis: COMEX + 15% Tariff/GST Parity
              </div>
            </div>
          </div>
        </div>

        {/* Silver Card */}
        <div className="p-5 rounded-2xl bg-gradient-to-br from-navy-900 to-navy-900/60 border border-slate-400/30 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-slate-300/5 rounded-full blur-2xl pointer-events-none" />
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-slate-300 shadow-sm shadow-slate-300/50" />
              <h2 className="text-base font-extrabold text-slate-200 tracking-wide">
                {t('metals.silverCard', 'COMEX Silver Futures (SI=F)')}
              </h2>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-400/10 text-slate-300 border border-slate-400/20">
              {prices?.silver.international?.exchange || 'COMEX'} • {prices?.silver.international?.freshness || 'Active'}
            </span>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4">
            {/* International USD/oz */}
            <div className="p-3.5 rounded-xl bg-navy-950/80 border border-navy-750">
              <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">
                International (USD / oz)
              </span>
              <div className="text-2xl font-black font-mono text-white">
                ${prices?.silver.international?.price.toFixed(3) || '50.865'}
              </div>
              <div
                className={`flex items-center gap-1 text-xs font-mono font-semibold mt-1 ${
                  (prices?.silver.international?.change || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {(prices?.silver.international?.change || 0) >= 0 ? (
                  <ArrowUpRight className="w-3.5 h-3.5" />
                ) : (
                  <ArrowDownRight className="w-3.5 h-3.5" />
                )}
                <span>
                  {(prices?.silver.international?.change || 0) >= 0 ? '+' : ''}
                  {prices?.silver.international?.change.toFixed(2)} (
                  {prices?.silver.international?.change_pct.toFixed(2)}%)
                </span>
              </div>
            </div>

            {/* India Domestic Benchmark */}
            <div className="p-3.5 rounded-xl bg-navy-950/80 border border-slate-400/20">
              <span className="text-[10px] font-mono uppercase text-slate-300 block mb-1">
                {t('metals.indiaDomesticSilver', 'India Domestic (1kg)')}
              </span>
              <div className="text-2xl font-black font-mono text-slate-100">
                ₹{prices?.silver.india_domestic?.price_inr.toLocaleString('en-IN') || '1,79,150'}
              </div>
              <div className="text-[10px] text-slate-400 font-mono mt-1">
                Basis: COMEX + 15% Tariff/GST Parity
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sentiment Overview KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Gold Sentiment KPI */}
        <div className="p-4 rounded-xl bg-navy-900/90 border border-navy-750">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>{t('metals.gold', 'Gold')} {t('metals.bullishSentiment', 'Sentiment')}</span>
            <span
              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                summary?.gold_sentiment.overall_sentiment === 'Bullish'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : summary?.gold_sentiment.overall_sentiment === 'Bearish'
                  ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                  : 'bg-slate-500/20 text-slate-300 border border-slate-500/30'
              }`}
            >
              {summary?.gold_sentiment.overall_sentiment || 'Neutral'}
            </span>
          </div>
          <div className="text-2xl font-black font-mono text-white">
            {summary?.gold_sentiment.bullish_pct || 0}%
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {summary?.gold_sentiment.bullish_count || 0} Bullish • {summary?.gold_sentiment.bearish_count || 0} Bearish •{' '}
            {summary?.gold_sentiment.neutral_count || 0} Neutral
          </p>
        </div>

        {/* Silver Sentiment KPI */}
        <div className="p-4 rounded-xl bg-navy-900/90 border border-navy-750">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>{t('metals.silver', 'Silver')} {t('metals.bullishSentiment', 'Sentiment')}</span>
            <span
              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                summary?.silver_sentiment.overall_sentiment === 'Bullish'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : summary?.silver_sentiment.overall_sentiment === 'Bearish'
                  ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                  : 'bg-slate-500/20 text-slate-300 border border-slate-500/30'
              }`}
            >
              {summary?.silver_sentiment.overall_sentiment || 'Neutral'}
            </span>
          </div>
          <div className="text-2xl font-black font-mono text-white">
            {summary?.silver_sentiment.bullish_pct || 0}%
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {summary?.silver_sentiment.bullish_count || 0} Bullish • {summary?.silver_sentiment.bearish_count || 0} Bearish •{' '}
            {summary?.silver_sentiment.neutral_count || 0} Neutral
          </p>
        </div>

        {/* Total News Count */}
        <div className="p-4 rounded-xl bg-navy-900/90 border border-navy-750">
          <div className="text-xs text-slate-400 mb-1">Analyzed Articles</div>
          <div className="text-2xl font-black font-mono text-white">
            {summary?.total_articles || 0}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {summary?.gold_articles_count || 0} Gold • {summary?.silver_articles_count || 0} Silver •{' '}
            {summary?.both_articles_count || 0} Both
          </p>
        </div>

        {/* FinBERT Inference Engine Status */}
        <div className="p-4 rounded-xl bg-navy-900/90 border border-navy-750">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Inference Engine</span>
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          </div>
          <div className="text-sm font-bold font-mono text-cyan-300 truncate">
            ProsusAI/finbert
          </div>
          <p className="text-[10px] text-slate-400 mt-1.5 flex items-center gap-1 font-mono">
            <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
            <span>Neural bfloat16 / CPU Ingest</span>
          </p>
        </div>
      </div>

      {/* Visual Analytics: Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Gold vs Silver Sentiment Comparison */}
        <div className="p-5 rounded-2xl bg-navy-900/90 border border-navy-750">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white">
                {t('metals.sentimentComparison', 'Gold vs. Silver Sentiment Comparison')}
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                FinBERT percentage distribution of Bullish, Neutral, and Bearish tone
              </p>
            </div>
            <BarChart3 className="w-4 h-4 text-cyan-400" />
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                  labelStyle={{ color: '#fff', fontWeight: 'bold' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="Bullish" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Neutral" fill="#64748b" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Bearish" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Daily News Volume & Sentiment Trends */}
        <div className="p-5 rounded-2xl bg-navy-900/90 border border-navy-750">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white">
                {t('metals.dailyTrends', 'Daily News Volume & Sentiment Trends')}
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Cumulative precious metals article flow across Indian & global feeds
              </p>
            </div>
            <Layers className="w-4 h-4 text-amber-400" />
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={history?.history || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="volGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="bullGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} tickFormatter={(val) => val.slice(5)} />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Area type="monotone" dataKey="total_volume" name="Article Volume" stroke="#f59e0b" fill="url(#volGrad)" />
                <Area type="monotone" dataKey="gold_positive" name="Bullish Gold" stroke="#10b981" fill="url(#bullGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Precious Metals News Feed Section */}
      <div className="p-5 rounded-2xl bg-navy-900/90 border border-navy-750">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-navy-800">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span>{t('metals.newsFeed', 'Precious Metals News Feed')}</span>
              {news && (
                <span className="text-xs font-mono text-slate-400">
                  ({news.total_count} {t('metals.articlesFound', 'articles found')})
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Genuine financial articles from Indian & global sources analyzed by FinBERT
            </p>
          </div>

          {/* Search bar */}
          <form onSubmit={handleSearchSubmit} className="relative w-full md:w-72">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('metals.searchPlaceholder', 'Search gold, silver, MCX...')}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-navy-950 text-slate-100 placeholder-slate-500 rounded-xl border border-navy-750 focus:outline-none focus:border-amber-500"
            />
          </form>
        </div>

        {/* Filter Badges Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 py-3 border-b border-navy-800/60 text-xs">
          {/* Metal Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 font-medium mr-1">Metal:</span>
            {['All', 'Gold', 'Silver'].map((m) => (
              <button
                key={m}
                onClick={() => {
                  setSelectedMetal(m);
                  setCurrentPage(1);
                }}
                className={`px-2.5 py-1 rounded-lg font-medium transition-colors cursor-pointer text-xs ${
                  selectedMetal === m
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold'
                    : 'bg-navy-950 text-slate-400 hover:text-white border border-navy-750'
                }`}
              >
                {m === 'All' ? t('metals.allMetals', 'All Metals') : t(`metals.${m.toLowerCase()}`, m)}
              </button>
            ))}
          </div>

          {/* Category Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 font-medium mr-1">Market:</span>
            {['All', 'India', 'Global Markets', 'Investment Trends'].map((cat) => (
              <button
                key={cat}
                onClick={() => {
                  setSelectedCategory(cat);
                  setCurrentPage(1);
                }}
                className={`px-2.5 py-1 rounded-lg font-medium transition-colors cursor-pointer text-xs ${
                  selectedCategory === cat
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                    : 'bg-navy-950 text-slate-400 hover:text-white border border-navy-750'
                }`}
              >
                {cat === 'All' ? t('metals.allCategories', 'All') : cat}
              </button>
            ))}
          </div>

          {/* Timeframe Filter */}
          <div className="flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            {[
              { label: t('metals.timeToday', 'Today'), days: 1 },
              { label: t('metals.time7Days', '7 Days'), days: 7 },
              { label: t('metals.time30Days', '30 Days'), days: 30 }
            ].map((tf) => (
              <button
                key={tf.days}
                onClick={() => {
                  setTimeframeDays(tf.days);
                  setCurrentPage(1);
                }}
                className={`px-2.5 py-1 rounded-lg font-mono text-[11px] transition-colors cursor-pointer ${
                  timeframeDays === tf.days
                    ? 'bg-blue-600 text-white font-semibold'
                    : 'bg-navy-950 text-slate-400 hover:text-white border border-navy-750'
                }`}
              >
                {tf.label}
              </button>
            ))}
          </div>
        </div>

        {/* Articles List */}
        {loading ? (
          <div className="py-16 text-center">
            <Loader2 className="w-8 h-8 text-amber-400 animate-spin mx-auto mb-3" />
            <p className="text-xs text-slate-400">{t('common.loading', 'Ingesting precious metals news...')}</p>
          </div>
        ) : news && news.articles.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {news.articles.map((art) => {
              const tr = translations[art.id];
              const isTranslated = tr && tr.isShowingTranslated && tr.translatedText;
              const displayTitle = isTranslated ? tr.translatedText : art.title;

              return (
                <div
                  key={art.id}
                  className="p-4 rounded-xl bg-navy-950/70 border border-navy-750 hover:border-amber-500/30 transition-all flex flex-col justify-between group"
                >
                  <div>
                    {/* Tags row */}
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {/* Metal Tag */}
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                            art.metal === 'Gold'
                              ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                              : art.metal === 'Silver'
                              ? 'bg-slate-300/15 text-slate-200 border border-slate-300/30'
                              : 'bg-yellow-500/15 text-yellow-200 border border-yellow-500/30'
                          }`}
                        >
                          {art.metal}
                        </span>

                        {/* Category Tag */}
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-navy-800 text-slate-300 border border-navy-700">
                          {art.category}
                        </span>
                      </div>

                      {/* FinBERT Sentiment Badge */}
                      <div
                        className={`flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                          art.sentiment_label === 'Bullish'
                            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                            : art.sentiment_label === 'Bearish'
                            ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                            : 'bg-slate-500/15 text-slate-300 border border-slate-500/30'
                        }`}
                      >
                        {art.sentiment_label === 'Bullish' ? (
                          <TrendingUp className="w-3 h-3" />
                        ) : art.sentiment_label === 'Bearish' ? (
                          <TrendingDown className="w-3 h-3" />
                        ) : (
                          <Minus className="w-3 h-3" />
                        )}
                        <span>{art.sentiment_label}</span>
                        <span className="font-mono text-[10px] opacity-80">{art.confidence}%</span>
                      </div>
                    </div>

                    {/* Headline */}
                    <h4 className="text-sm font-semibold text-white group-hover:text-amber-200 transition-colors leading-snug">
                      {displayTitle}
                    </h4>

                    {/* Summary */}
                    {art.summary && (
                      <p className="text-xs text-slate-400 mt-2 line-clamp-2 leading-relaxed">
                        {art.summary}
                      </p>
                    )}
                  </div>

                  {/* Metadata and Controls footer */}
                  <div className="pt-3 mt-3 border-t border-navy-850 flex items-center justify-between text-[11px] text-slate-400">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-300">{art.publisher}</span>
                      <span>•</span>
                      <span className="font-mono text-[10px]">{art.published_at_ist}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Translate Toggle Button */}
                      {(i18n.language || 'en').toLowerCase().split('-')[0] !== 'en' && (
                        <button
                          onClick={() => toggleTranslation(art)}
                          disabled={tr?.loading}
                          className="flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[10px] font-medium transition-colors cursor-pointer"
                          title="Translate headline into current display language"
                        >
                          <Languages className="w-3 h-3" />
                          <span>
                            {tr?.loading
                              ? t('metals.translating', 'Translating...')
                              : isTranslated
                              ? t('metals.originalHeadline', 'Original')
                              : t('metals.translateHeadline', 'Translate')}
                          </span>
                        </button>
                      )}

                      {/* Source Link */}
                      {art.url && (
                        <a
                          href={art.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-slate-400 hover:text-white p-1 rounded hover:bg-navy-800 transition-colors"
                          title="Open original source article"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="py-12 text-center text-slate-400 text-xs">
            No precious metals articles matched the current filters.
          </div>
        )}

        {/* Pagination Bar */}
        {news && news.total_count > 12 && (
          <div className="flex items-center justify-between pt-4 mt-4 border-t border-navy-800 text-xs">
            <span className="text-slate-400 font-mono">
              Page {currentPage} of {Math.ceil(news.total_count / 12)}
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 rounded bg-navy-800 text-slate-200 disabled:opacity-40 hover:bg-navy-700 cursor-pointer"
              >
                Previous
              </button>
              <button
                disabled={currentPage >= Math.ceil(news.total_count / 12)}
                onClick={() => setCurrentPage((p) => p + 1)}
                className="px-3 py-1 rounded bg-navy-800 text-slate-200 disabled:opacity-40 hover:bg-navy-700 cursor-pointer"
              >
                Next
              </button>
            </div>
          </div>
        )}

        {/* Disclaimer footer */}
        <div className="mt-5 p-3 rounded-xl bg-navy-950 border border-navy-800 flex items-start gap-2.5 text-[11px] text-slate-400">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            {t(
              'metals.disclaimer',
              'Sentiment indicates FinBERT NLP textual analysis of financial news reporting and does not constitute a price forecast or investment advice.'
            )}
          </p>
        </div>
      </div>
    </div>
  );
};
