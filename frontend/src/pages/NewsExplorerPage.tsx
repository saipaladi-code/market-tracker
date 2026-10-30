import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  ExternalLink,
  Sparkles,
  RefreshCw,
  AlertCircle,
  Clock,
  Layers,
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  CheckCircle2,
  SlidersHorizontal,
  Building2,
  Languages,
  TrendingUp,
  X
} from 'lucide-react';
import { api } from '../services/api';
import { Article, SentimentAnalysisResult } from '../types';
import { SentimentBadge } from '../components/SentimentBadge';
import { ExplainModal } from '../components/ExplainModal';
import { TradeRoutingModal } from '../components/TradeRoutingModal';
import { resolveVerifiedTicker, resolveVerifiedInstrument } from '../utils/tickerLookup';
import { getCanonicalSentimentResult } from '../utils/canonicalSentiment';
import { useTranslation } from 'react-i18next';

const COMPANIES = [
  { label: 'All Companies', value: 'All Companies' },
  { label: 'Reliance Industries (RELIANCE)', value: 'Reliance Industries' },
  { label: 'Tata Consultancy Services (TCS)', value: 'Tata Consultancy Services' },
  { label: 'Tata Motors (TATAMOTORS)', value: 'Tata Motors' },
  { label: 'Infosys (INFY)', value: 'Infosys' },
  { label: 'HDFC Bank (HDFCBANK)', value: 'HDFC Bank' },
  { label: 'ICICI Bank (ICICIBANK)', value: 'ICICI Bank' },
  { label: 'State Bank of India (SBIN)', value: 'State Bank of India' },
  { label: 'Bharti Airtel (BHARTIARTL)', value: 'Bharti Airtel' },
  { label: 'L&T (LT)', value: 'Larsen & Toubro' },
  { label: 'Wipro (WIPRO)', value: 'Wipro' },
  { label: 'Apple (AAPL)', value: 'Apple' },
  { label: 'Microsoft (MSFT)', value: 'Microsoft' },
  { label: 'Amazon (AMZN)', value: 'Amazon' },
  { label: 'Tesla (TSLA)', value: 'Tesla' },
  { label: 'Nvidia (NVDA)', value: 'Nvidia' },
  { label: 'Alphabet (GOOGL)', value: 'Alphabet' },
  { label: 'Meta Platforms (META)', value: 'Meta Platforms' },
  { label: 'JPMorgan Chase (JPM)', value: 'JPMorgan Chase' },
  { label: 'Pfizer (PFE)', value: 'Pfizer' },
  { label: 'ExxonMobil (XOM)', value: 'ExxonMobil' },
];

const SENTIMENTS = [
  { label: 'All Sentiments', value: 'All' },
  { label: 'Positive Tone Only', value: 'Positive' },
  { label: 'Neutral Tone Only', value: 'Neutral' },
  { label: 'Negative Tone Only', value: 'Negative' },
];

export const NewsExplorerPage: React.FC = () => {
  const [articles, setArticles] = useState<Article[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCompany, setSelectedCompany] = useState('All Companies');
  const [selectedSentiment, setSelectedSentiment] = useState('All');
  const [showDuplicates, setShowDuplicates] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(12);
  const [isDemoDataset, setIsDemoDataset] = useState(false);
  const [feedStatus, setFeedStatus] = useState<string>('LIVE FEED');
  const [lastSynced, setLastSynced] = useState<string | null>(null);
  const [filterDate, setFilterDate] = useState<string | null>(null);
  const [todayOnly, setTodayOnly] = useState<boolean>(true);
  const { i18n, t } = useTranslation();
  const [translations, setTranslations] = useState<Record<string, { text: string; isTranslated: boolean; loading: boolean }>>({});

  const toggleArticleTranslation = async (article: Article) => {
    const currentLang = (i18n.language || 'en').toLowerCase().split('-')[0];
    if (currentLang === 'en') return;

    const current = translations[article.id];
    if (current && current.text) {
      setTranslations((prev) => ({
        ...prev,
        [article.id]: { ...current, isTranslated: !current.isTranslated },
      }));
      return;
    }

    setTranslations((prev) => ({
      ...prev,
      [article.id]: { text: '', isTranslated: false, loading: true },
    }));

    try {
      const res = await api.translateText(article.title, currentLang, article.id);
      setTranslations((prev) => ({
        ...prev,
        [article.id]: { text: res.translated_text || article.title, isTranslated: true, loading: false },
      }));
    } catch {
      setTranslations((prev) => ({
        ...prev,
        [article.id]: { text: article.title, isTranslated: false, loading: false },
      }));
    }
  };

  // Explain modal state
  const [selectedExplainResult, setSelectedExplainResult] = useState<SentimentAnalysisResult | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const [explainError, setExplainError] = useState<string | null>(null);

  // Trade routing modal state
  const [selectedTradeArticle, setSelectedTradeArticle] = useState<Article | null>(null);
  const [tradeModalOpen, setTradeModalOpen] = useState(false);

  const fetchNews = async () => {
    try {
      setLoading(true);
      const data = await api.getNews({
        page,
        page_size: pageSize,
        company: selectedCompany === 'All Companies' ? undefined : selectedCompany,
        sentiment: selectedSentiment === 'All' ? undefined : selectedSentiment.toLowerCase(),
        query: searchQuery.trim() || undefined,
        today_only: todayOnly,
      });

      let items = data.articles || [];
      if (!showDuplicates) {
        items = items.filter((a: Article) => !a.is_duplicate);
      }

      setArticles(items);
      setTotalCount(data.total_count || 0);
      setIsDemoDataset(data.is_demo_dataset || false);
      if (data.feed_status) setFeedStatus(data.feed_status);
      if (data.last_synced) setLastSynced(data.last_synced);
      if (data.filter_date) setFilterDate(data.filter_date);
    } catch (err) {
      console.error('Failed to load news:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNews();
  }, [page, selectedCompany, selectedSentiment, showDuplicates, todayOnly]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchNews();
  };

  const handleInspectAttribution = async (article: Article) => {
    // 1. Immediately establish and display canonical inference result from article
    const canonical = getCanonicalSentimentResult(article);
    setSelectedExplainResult(canonical);
    setExplainError(null);

    // 2. If article already has attribution tokens cached, no network fetch needed
    if (canonical.tokens && canonical.tokens.length > 0) {
      return;
    }

    // 3. Asynchronously fetch explanation tokens without overwriting canonical sentiment or confidence
    try {
      setExplainLoading(true);
      const explained = await api.explainArticle(article);
      setSelectedExplainResult((current) => {
        // Prevent race condition if user closed or switched to another article
        if (!current || current.article_id !== article.id) return current;
        return {
          ...current,
          tokens: explained.tokens && explained.tokens.length > 0 ? explained.tokens : current.tokens,
          explanation_note: explained.explanation_note || current.explanation_note,
          is_fallback: explained.is_fallback !== undefined ? explained.is_fallback : current.is_fallback,
        };
      });

      // Cache tokens in article state so reopening modal is instantaneous
      setArticles((prev) =>
        prev.map((a) => (a.id === article.id ? { ...a, tokens: explained.tokens } : a))
      );
    } catch (err: any) {
      console.warn('Attribution lookup failed:', err);
      setExplainError(err?.message || 'Attribution lookup failed.');
    } finally {
      setExplainLoading(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  const hasActiveFilters =
    selectedCompany !== 'All Companies' ||
    selectedSentiment !== 'All' ||
    searchQuery.trim() !== '';

  const handleClearAllFilters = () => {
    setSearchQuery('');
    setSelectedCompany('All Companies');
    setSelectedSentiment('All');
    setPage(1);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Controls Banner */}
      <div className="bg-navy-900/90 border border-navy-750/90 p-5 rounded-2xl space-y-4 backdrop-blur-md shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-mono font-bold uppercase tracking-wider">
                EDITORIAL INTELLIGENCE FEED
              </span>
              <span className="text-xs text-slate-400 font-mono">
                {totalCount} Verified Headlines Ingested
              </span>
            </div>
            <h2 className="text-xl font-extrabold text-white tracking-tight">
              Classified Financial News Stream
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              News headlines classified by FinBERT with deduplication analysis and explainable AI attribution.
            </p>
          </div>

          {/* Dataset Status Badge - Honest Multi-State Indicator */}
          {feedStatus === 'LIVE FEED' && !isDemoDataset && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs self-start md:self-auto font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>LIVE FEED</span>
              {filterDate && (
                <span className="text-[10px] text-emerald-300/80 border-l border-emerald-500/30 pl-2">
                  Asia/Kolkata: {filterDate}
                </span>
              )}
            </div>
          )}
          {feedStatus === 'CACHED LIVE DATA' && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs self-start md:self-auto font-mono">
              <Clock className="w-3.5 h-3.5 text-blue-400" />
              <span>CACHED LIVE DATA</span>
              {lastSynced && (
                <span className="text-[10px] text-blue-300/80 border-l border-blue-500/30 pl-2">
                  Synced: {new Date(lastSynced).toLocaleTimeString()}
                </span>
              )}
            </div>
          )}
          {(feedStatus === 'DEMO DATA' || (isDemoDataset && feedStatus !== 'API ERROR')) && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs self-start md:self-auto font-mono">
              <AlertCircle className="w-4 h-4 text-amber-400" />
              <span>DEMO DATASET ACTIVE</span>
            </div>
          )}
          {feedStatus === 'API ERROR' && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs self-start md:self-auto font-mono">
              <AlertCircle className="w-4 h-4 text-rose-400" />
              <span>API ERROR</span>
            </div>
          )}
        </div>

        {/* Search Bar & Multi-filter Controls */}
        <form onSubmit={handleSearchSubmit} className="space-y-3 pt-2 border-t border-navy-800">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
            {/* Search Input */}
            <div className="md:col-span-6 relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search headlines by keyword (e.g. quarterly earnings, margin, cloud)..."
                className="w-full bg-navy-950 border border-navy-700/80 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            {/* Company Dropdown */}
            <div className="md:col-span-3">
              <select
                value={selectedCompany}
                onChange={(e) => {
                  setSelectedCompany(e.target.value);
                  setPage(1);
                }}
                className="w-full bg-navy-950 border border-navy-700/80 rounded-xl px-3 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500 cursor-pointer"
              >
                {COMPANIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Sentiment Filter Tabs */}
            <div className="md:col-span-3">
              <select
                value={selectedSentiment}
                onChange={(e) => {
                  setSelectedSentiment(e.target.value);
                  setPage(1);
                }}
                className="w-full bg-navy-950 border border-navy-700/80 rounded-xl px-3 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500 cursor-pointer"
              >
                {SENTIMENTS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Bottom Filter Toggles & Actions */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div className="flex flex-wrap items-center gap-4 text-xs">
              <label className="flex items-center gap-2 cursor-pointer text-slate-300">
                <input
                  type="checkbox"
                  checked={todayOnly}
                  onChange={(e) => {
                    setTodayOnly(e.target.checked);
                    setPage(1);
                  }}
                  className="accent-blue-500 rounded cursor-pointer"
                />
                <span className="font-medium text-slate-200">Today's News Only (Asia/Kolkata)</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-slate-300">
                <input
                  type="checkbox"
                  checked={showDuplicates}
                  onChange={(e) => setShowDuplicates(e.target.checked)}
                  className="accent-blue-500 rounded cursor-pointer"
                />
                <span>Include filtered near-duplicates ({totalCount} total)</span>
              </label>
            </div>

            <button
              type="submit"
              className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-blue-600/20 transition-all cursor-pointer"
            >
              Apply Filter Query
            </button>
          </div>

          {/* Active Filter Chips / Clear Controls */}
          {hasActiveFilters && (
            <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-navy-800 animate-fadeIn">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Active Filters:</span>
              {selectedCompany !== 'All Companies' && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-500/10 border border-blue-500/30 text-blue-300 text-xs font-medium">
                  <span>Company: {selectedCompany}</span>
                  <button
                    type="button"
                    onClick={() => { setSelectedCompany('All Companies'); setPage(1); }}
                    className="hover:text-white transition-colors cursor-pointer"
                    title="Remove company filter"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </span>
              )}
              {selectedSentiment !== 'All' && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-medium">
                  <span>Tone: {selectedSentiment}</span>
                  <button
                    type="button"
                    onClick={() => { setSelectedSentiment('All'); setPage(1); }}
                    className="hover:text-white transition-colors cursor-pointer"
                    title="Remove sentiment filter"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </span>
              )}
              {searchQuery.trim() && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-700/50 border border-slate-600 text-slate-200 text-xs font-medium">
                  <span>Search: "{searchQuery.trim()}"</span>
                  <button
                    type="button"
                    onClick={() => { setSearchQuery(''); setPage(1); }}
                    className="hover:text-white transition-colors cursor-pointer"
                    title="Remove search filter"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </span>
              )}
              <button
                type="button"
                onClick={handleClearAllFilters}
                className="text-xs text-rose-400 hover:text-rose-300 underline font-medium ml-1 transition-colors cursor-pointer"
              >
                Clear All Filters
              </button>
            </div>
          )}
        </form>
      </div>

      {/* Loading Skeleton */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-navy-900 border border-navy-800 rounded-2xl p-5 space-y-3 animate-pulse">
              <div className="h-4 bg-navy-800 rounded w-1/3" />
              <div className="h-5 bg-navy-800 rounded w-full" />
              <div className="h-12 bg-navy-800 rounded w-full" />
              <div className="h-4 bg-navy-800 rounded w-1/2 pt-2" />
            </div>
          ))}
        </div>
      ) : articles.length === 0 ? (
        <div className="p-12 text-center bg-navy-900 border border-navy-800 rounded-2xl space-y-3">
          <Layers className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-slate-200">No Articles Matched Your Filter</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Try adjusting your search query, changing company selection, or resetting the sentiment filter.
          </p>
          <button
            onClick={() => {
              setSearchQuery('');
              setSelectedCompany('All Companies');
              setSelectedSentiment('All');
              setPage(1);
            }}
            className="px-4 py-2 bg-navy-800 hover:bg-navy-700 text-slate-200 rounded-xl text-xs font-semibold border border-navy-700 transition-colors"
          >
            Reset All Filters
          </button>
        </div>
      ) : (
        /* Articles Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {articles.map((art) => {
            const isDuplicate = Boolean(art.is_duplicate);
            const tr = translations[art.id];
            const isTranslated = tr && tr.isTranslated && tr.text;
            const headlineText = isTranslated ? tr.text : art.title;
            const verifiedInst = resolveVerifiedInstrument(art.company, art.ticker);
            const verifiedTicker = verifiedInst?.ticker || resolveVerifiedTicker(art.company, art.ticker);
            const isTradable = Boolean(verifiedInst);
            const brokerTag = verifiedInst?.preferredBroker === 'upstox' ? 'Upstox' : 'IBKR';

            return (
              <div
                key={art.id}
                className={`bg-navy-900/90 border rounded-2xl p-5 flex flex-col justify-between space-y-4 hover:border-navy-700 hover:shadow-lg transition-all duration-200 ${
                  isDuplicate ? 'border-amber-500/30 opacity-75' : 'border-navy-750/90'
                }`}
              >
                <div className="space-y-3">
                  {/* Card Header: Ticker, Duplicate tag, Sentiment Badge */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-xs text-white px-2 py-0.5 rounded bg-navy-800 border border-navy-700 font-mono">
                        {art.company}
                      </span>
                      {verifiedTicker && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-semibold">
                          {verifiedTicker}
                        </span>
                      )}
                      {isDuplicate && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                          Duplicate
                        </span>
                      )}
                    </div>
                    <SentimentBadge sentiment={art.sentiment} confidence={art.confidence} size="xs" />
                  </div>

                  {/* Headline */}
                  <h3 className="text-sm font-semibold text-slate-100 line-clamp-2 leading-snug">
                    {headlineText}
                  </h3>

                  {/* Description snippet if available */}
                  {art.description && (
                    <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                      {art.description}
                    </p>
                  )}
                </div>

                {/* Card Footer: Metadata and XAI Explain button */}
                <div className="pt-3 border-t border-navy-800 flex items-center justify-between text-xs text-slate-400 gap-2">
                  <div className="min-w-0">
                    <span className="truncate block font-medium text-slate-300">{art.source}</span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {art.published_at
                        ? new Date(art.published_at).toLocaleString([], {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : 'Recent'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {/* Multilingual Translation Toggle */}
                    {(i18n.language || 'en').toLowerCase().split('-')[0] !== 'en' && (
                      <button
                        onClick={() => toggleArticleTranslation(art)}
                        disabled={tr?.loading}
                        className="px-2 py-1 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[10px] font-medium flex items-center gap-1 transition-colors cursor-pointer"
                        title="Translate headline into current language"
                      >
                        <Languages className="w-3 h-3 text-cyan-400" />
                        <span>{tr?.loading ? 'Translating...' : isTranslated ? 'Original' : 'Translate'}</span>
                      </button>
                    )}

                    {/* Trade Button (only shown for verified tradable instruments) */}
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
                        className="px-2.5 py-1 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 hover:text-emerald-200 border border-emerald-500/30 text-[11px] font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                        title={`Trade ${verifiedInst?.company || art.company} via ${verifiedInst?.brokerName || 'broker'}`}
                      >
                        <TrendingUp className="w-3 h-3 text-emerald-400" />
                        <span>Trade ({brokerTag})</span>
                      </button>
                    ) : (
                      <span
                        className="px-2 py-0.5 rounded text-[10px] font-mono text-slate-500 bg-navy-800/60 border border-navy-750"
                        title="Macroeconomic / general market news"
                      >
                        Market Context
                      </span>
                    )}

                    {/* Explain Button */}
                    <button
                      onClick={() => handleInspectAttribution(art)}
                      className="px-2.5 py-1 rounded-lg bg-navy-800 hover:bg-navy-750 text-slate-300 hover:text-white border border-navy-700 text-[11px] font-medium flex items-center gap-1 transition-colors cursor-pointer"
                      title="Inspect FinBERT token perturbation attribution"
                    >
                      <Sparkles className="w-3 h-3 text-blue-400" />
                      <span>XAI Salience</span>
                    </button>

                    {/* External Link */}
                    <a
                      href={art.url}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1.5 rounded-lg bg-navy-800 hover:bg-navy-750 text-slate-400 hover:text-slate-200 border border-navy-700 transition-colors"
                      title="Open source article in new tab"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-navy-800 text-xs text-slate-400">
          <div>
            Showing Page <strong className="text-white font-mono">{page}</strong> of{' '}
            <strong className="text-white font-mono">{totalPages}</strong> ({totalCount} verified headlines)
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-2 rounded-xl bg-navy-900 border border-navy-750 hover:bg-navy-800 disabled:opacity-40 text-slate-300 transition-colors cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-3 py-1 font-mono font-semibold text-white bg-navy-950 border border-navy-750 rounded-xl">
              {page}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-2 rounded-xl bg-navy-900 border border-navy-750 hover:bg-navy-800 disabled:opacity-40 text-slate-300 transition-colors cursor-pointer"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
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

      {/* XAI Attribution Explain Modal */}
      <ExplainModal
        isOpen={Boolean(selectedExplainResult)}
        onClose={() => {
          setSelectedExplainResult(null);
          setExplainLoading(false);
        }}
        result={selectedExplainResult}
        loadingTokens={explainLoading}
      />
    </div>
  );
};
