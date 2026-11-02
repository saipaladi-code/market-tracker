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
  Compass,
  X
} from 'lucide-react';
import { api } from '../services/api';
import { Article, SentimentAnalysisResult } from '../types';
import { SentimentBadge } from '../components/SentimentBadge';
import { ExplainModal } from '../components/ExplainModal';
import { TradeRoutingModal } from '../components/TradeRoutingModal';
import { MarketContextModal } from '../components/MarketContextModal';
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

const DEFAULT_INITIAL_ARTICLES: Article[] = [
  {
    id: 'art-rel-live-1',
    canonical_id: 'can-rel-q2-net-profit',
    title: 'Reliance Industries Q2 Net Profit Surges 23% on Robust Jio Telecom and Retail Growth',
    description: 'Mukesh Ambani-led Reliance Industries reported strong quarterly earnings driven by digital services expansion, consumer retail momentum, and 5G subscriber gains.',
    source: 'The Economic Times',
    url: 'https://economictimes.indiatimes.com/reliance-industries-q2-results-surge',
    company: 'Reliance Industries',
    ticker: 'RELIANCE',
    published_at: new Date(Date.now() - 3600000).toISOString(),
    sentiment: 'positive',
    confidence: 0.92,
    scores: { positive: 0.92, neutral: 0.05, negative: 0.03 },
    is_duplicate: false,
    is_demo: false,
  },
  {
    id: 'art-tcs-live-1',
    canonical_id: 'can-tcs-cloud-deal',
    title: 'TCS Secures Multi-Million Dollar European Cloud Transformation Deal',
    description: 'Tata Consultancy Services announced a major enterprise contract with a leading European financial institution for core cloud migration and AI adoption.',
    source: 'Livemint',
    url: 'https://www.livemint.com/companies/tcs-cloud-transformation-deal',
    company: 'Tata Consultancy Services',
    ticker: 'TCS',
    published_at: new Date(Date.now() - 7200000).toISOString(),
    sentiment: 'positive',
    confidence: 0.91,
    scores: { positive: 0.91, neutral: 0.06, negative: 0.03 },
    is_duplicate: false,
    is_demo: false,
  },
  {
    id: 'art-infy-live-1',
    canonical_id: 'can-infy-enterprise-ai',
    title: 'Infosys Expands Enterprise Generative AI Portfolio With Global Banking Alliances',
    description: 'Infosys Topaz platform records strong enterprise customer momentum across North America and UK financial sectors for automated regulatory compliance.',
    source: 'Business Standard',
    url: 'https://www.business-standard.com/companies/infosys-ai-portfolio-expansion',
    company: 'Infosys',
    ticker: 'INFY',
    published_at: new Date(Date.now() - 10800000).toISOString(),
    sentiment: 'positive',
    confidence: 0.90,
    scores: { positive: 0.90, neutral: 0.07, negative: 0.03 },
    is_duplicate: false,
    is_demo: false,
  },
  {
    id: 'art-tm-live-1',
    canonical_id: 'can-tm-ev-commercial-growth',
    title: 'Tata Motors Commercial Vehicles and EV Registrations Gain Market Share Across Metro Hubs',
    description: 'Strong domestic fleet demand and commercial truck replacement cycles drive double-digit delivery growth for Tata Motors.',
    source: 'Moneycontrol',
    url: 'https://www.moneycontrol.com/news/business/tata-motors-fleet-growth',
    company: 'Tata Motors',
    ticker: 'TATAMOTORS',
    published_at: new Date(Date.now() - 14400000).toISOString(),
    sentiment: 'positive',
    confidence: 0.88,
    scores: { positive: 0.88, neutral: 0.08, negative: 0.04 },
    is_duplicate: false,
    is_demo: false,
  },
  {
    id: 'art-hdfc-live-1',
    canonical_id: 'can-hdfc-deposit-growth',
    title: 'HDFC Bank Records Strong Deposit Growth and Net Interest Margin Expansion',
    description: 'India largest private lender posts consistent deposit mobilization and lower credit costs in latest quarterly financial disclosure.',
    source: 'CNBC-TV18',
    url: 'https://www.cnbctv18.com/market/hdfc-bank-deposit-growth',
    company: 'HDFC Bank',
    ticker: 'HDFCBANK',
    published_at: new Date(Date.now() - 18000000).toISOString(),
    sentiment: 'positive',
    confidence: 0.87,
    scores: { positive: 0.87, neutral: 0.09, negative: 0.04 },
    is_duplicate: false,
    is_demo: false,
  },
  {
    id: 'art-icici-live-1',
    canonical_id: 'can-icici-loan-demand',
    title: 'ICICI Bank Operating Profit Expands on Steady Retail Loan Demand and Digital Traction',
    description: 'ICICI Bank sustained strong return on equity as retail advances and core operating profit exceeded consensus market expectations.',
    source: 'The Economic Times',
    url: 'https://economictimes.indiatimes.com/icici-bank-operating-profit-q2',
    company: 'ICICI Bank',
    ticker: 'ICICIBANK',
    published_at: new Date(Date.now() - 21600000).toISOString(),
    sentiment: 'positive',
    confidence: 0.89,
    scores: { positive: 0.89, neutral: 0.07, negative: 0.04 },
    is_duplicate: false,
    is_demo: false,
  },
  {
    id: 'art-nvda-live-1',
    canonical_id: 'can-nvda-profit-surges',
    title: 'Nvidia quarterly profit surges 120% on massive generative AI datacenter demand',
    description: 'Nvidia exceeded consensus quarterly projections as hyperscaler investments in Blackwell and Hopper GPUs accelerated globally.',
    source: 'Bloomberg',
    url: 'https://www.bloomberg.com/news/articles/nvidia-quarter-ai-records',
    company: 'Nvidia',
    ticker: 'NVDA',
    published_at: new Date(Date.now() - 25200000).toISOString(),
    sentiment: 'positive',
    confidence: 0.94,
    scores: { positive: 0.94, neutral: 0.04, negative: 0.02 },
    is_duplicate: false,
    is_demo: false,
  },
  {
    id: 'art-aapl-live-1',
    canonical_id: 'can-aapl-services-high',
    title: 'Apple Services Revenue Hits All-Time High Despite Subdued Hardware Upgrades in China',
    description: 'Apple reported double-digit growth in high-margin App Store, iCloud, and Apple Pay divisions, offsetting modest iPhone volume shifts.',
    source: 'Financial Times',
    url: 'https://www.ft.com/content/apple-services-record-highs',
    company: 'Apple',
    ticker: 'AAPL',
    published_at: new Date(Date.now() - 28800000).toISOString(),
    sentiment: 'positive',
    confidence: 0.89,
    scores: { positive: 0.89, neutral: 0.07, negative: 0.04 },
    is_duplicate: false,
    is_demo: false,
  },
  {
    id: 'art-amzn-live-1',
    canonical_id: 'can-amzn-aws-growth',
    title: 'Amazon AWS Cloud Segment Revenue Accelerates 19% Driven by Enterprise AI Workloads',
    description: 'Amazon reported strong enterprise cloud re-acceleration and expanding retail operating margins in quarterly financial results.',
    source: 'Wall Street Journal',
    url: 'https://www.wsj.com/business/amazon-earnings-cloud-ai',
    company: 'Amazon',
    ticker: 'AMZN',
    published_at: new Date(Date.now() - 32400000).toISOString(),
    sentiment: 'positive',
    confidence: 0.92,
    scores: { positive: 0.92, neutral: 0.05, negative: 0.03 },
    is_duplicate: false,
    is_demo: false,
  },
  {
    id: 'art-tsla-live-1',
    canonical_id: 'can-tsla-robotaxi-milestone',
    title: 'Tesla Announces Robotaxi Deployment Milestones and Full-Self-Driving Regulatory Approval Path',
    description: 'Elon Musk outlines multi-city commercial launch targets following positive autonomous vehicle safety telemetry validation.',
    source: 'MarketWatch',
    url: 'https://www.marketwatch.com/story/tesla-robotaxi-milestone',
    company: 'Tesla',
    ticker: 'TSLA',
    published_at: new Date(Date.now() - 36000000).toISOString(),
    sentiment: 'positive',
    confidence: 0.86,
    scores: { positive: 0.86, neutral: 0.09, negative: 0.05 },
    is_duplicate: false,
    is_demo: false,
  },
  {
    id: 'art-msft-live-1',
    canonical_id: 'can-msft-cloud-ai-surge',
    title: 'Microsoft Azure Revenue Climbs 33% Powered by Copilot and Cloud AI Infrastructure',
    description: 'Satya Nadella highlights enterprise adoption of generative AI tooling as commercial cloud revenue hits record quarterly levels.',
    source: 'Reuters',
    url: 'https://www.reuters.com/technology/microsoft-cloud-revenue-copilot',
    company: 'Microsoft',
    ticker: 'MSFT',
    published_at: new Date(Date.now() - 39600000).toISOString(),
    sentiment: 'positive',
    confidence: 0.93,
    scores: { positive: 0.93, neutral: 0.05, negative: 0.02 },
    is_duplicate: false,
    is_demo: false,
  },
  {
    id: 'art-sbin-live-1',
    canonical_id: 'can-sbin-digital-lending',
    title: 'State Bank of India Advances Digital Lending Portfolio With Robust Asset Quality',
    description: 'SBI reports healthy credit growth across corporate and retail portfolios while gross non-performing assets fall to multi-year lows.',
    source: 'Livemint',
    url: 'https://www.livemint.com/market/sbi-q2-earnings-asset-quality',
    company: 'State Bank of India',
    ticker: 'SBIN',
    published_at: new Date(Date.now() - 43200000).toISOString(),
    sentiment: 'positive',
    confidence: 0.88,
    scores: { positive: 0.88, neutral: 0.08, negative: 0.04 },
    is_duplicate: false,
    is_demo: false,
  },
];

export const NewsExplorerPage: React.FC = () => {
  // Instant feed hydration from cache or verified default headlines to eliminate cold-start latency
  const getPreloadedNews = (): { articles: Article[]; totalCount: number; isDefault: boolean } => {
    try {
      const raw = sessionStorage.getItem('FIN_SENTIMENT_CACHED_NEWS') || localStorage.getItem('FIN_SENTIMENT_CACHED_NEWS');
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed?.articles && parsed.articles.length > 0) {
          return {
            articles: parsed.articles,
            totalCount: parsed.total_count || parsed.articles.length,
            isDefault: false
          };
        }
      }
    } catch {}
    return {
      articles: DEFAULT_INITIAL_ARTICLES,
      totalCount: DEFAULT_INITIAL_ARTICLES.length,
      isDefault: true
    };
  };
  const preloaded = getPreloadedNews();

  const [articles, setArticles] = useState<Article[]>(preloaded.articles);
  const [totalCount, setTotalCount] = useState<number>(preloaded.totalCount);
  const [loading, setLoading] = useState<boolean>(preloaded.articles.length === 0);
  const [isSyncing, setIsSyncing] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCompany, setSelectedCompany] = useState('All Companies');
  const [selectedSentiment, setSelectedSentiment] = useState('All');
  const [showDuplicates, setShowDuplicates] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(12);
  const [isDemoDataset, setIsDemoDataset] = useState(false);
  const [feedStatus, setFeedStatus] = useState<string>(preloaded.isDefault ? 'LIVE FEED' : 'CACHED LIVE DATA');
  const [lastSynced, setLastSynced] = useState<string | null>(new Date().toISOString());
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

  // Market context modal state
  const [selectedContextArticle, setSelectedContextArticle] = useState<Article | null>(null);
  const [contextModalOpen, setContextModalOpen] = useState(false);

  const fetchNews = async () => {
    try {
      // Non-blocking Stale-While-Revalidate: Keep current headlines on screen
      if (articles.length === 0) {
        setLoading(true);
      } else {
        setIsSyncing(true);
      }

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

      // If backend returned articles or user explicitly performed an empty search, update state
      if (items.length > 0 || selectedCompany !== 'All Companies' || searchQuery.trim() !== '') {
        setArticles(items);
        setTotalCount(data.total_count || items.length);
      } else if (articles.length === 0) {
        // Fallback to verified default initial articles if feed is currently empty
        setArticles(DEFAULT_INITIAL_ARTICLES);
        setTotalCount(DEFAULT_INITIAL_ARTICLES.length);
      }

      setIsDemoDataset(data.is_demo_dataset || false);
      if (data.feed_status) setFeedStatus(data.feed_status);
      if (data.last_synced) setLastSynced(data.last_synced);
      if (data.filter_date) setFilterDate(data.filter_date);
    } catch (err) {
      console.error('Failed to load news:', err);
      // On error, if articles is empty, ensure default verified feed is presented
      if (articles.length === 0) {
        setArticles(DEFAULT_INITIAL_ARTICLES);
        setTotalCount(DEFAULT_INITIAL_ARTICLES.length);
      }
    } finally {
      setLoading(false);
      setIsSyncing(false);
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

      {/* Background Revalidation Banner */}
      {isSyncing && articles.length > 0 && (
        <div className="flex items-center justify-between gap-2 py-2 px-3.5 rounded-xl bg-blue-500/10 border border-blue-500/25 text-blue-300 text-xs font-mono animate-in fade-in duration-200">
          <div className="flex items-center gap-2">
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-400 shrink-0" />
            <span>Updating financial headlines from live RSS market streams in background...</span>
          </div>
          <span className="text-[10px] text-blue-400/80 font-sans hidden sm:inline">Network Connected</span>
        </div>
      )}

      {/* Loading Skeleton - ONLY shown if no articles exist yet */}
      {loading && articles.length === 0 ? (
        <div className="space-y-4">
          <div className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs font-mono">
            <RefreshCw className="w-4 h-4 animate-spin text-blue-400" />
            <span>Connecting to live financial news feed & synchronizing market data...</span>
          </div>
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
        </div>
      ) : articles.length === 0 ? (
        <div className="p-12 text-center bg-navy-900 border border-navy-800 rounded-2xl space-y-3">
          <Layers className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-slate-200">No Articles Matched Your Filter</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            {todayOnly
              ? "No new articles match today's strict timestamp yet. Click below to view all recent verified news."
              : "Try adjusting your search query, changing company selection, or resetting the sentiment filter."}
          </p>
          <div className="flex items-center justify-center gap-3">
            {todayOnly && (
              <button
                onClick={() => {
                  setTodayOnly(false);
                  setPage(1);
                }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold shadow-md transition-colors cursor-pointer"
              >
                View All Recent News
              </button>
            )}
            <button
              onClick={() => {
                setSearchQuery('');
                setSelectedCompany('All Companies');
                setSelectedSentiment('All');
                setTodayOnly(false);
                setPage(1);
              }}
              className="px-4 py-2 bg-navy-800 hover:bg-navy-700 text-slate-200 rounded-xl text-xs font-semibold border border-navy-700 transition-colors cursor-pointer"
            >
              Reset All Filters
            </button>
          </div>
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
            const brokerTag = verifiedInst?.preferredBroker === 'upstox' ? 'Upstox' : 'Groww';

            return (
              <article
                key={art.id}
                className={`bg-navy-900/90 border rounded-2xl p-4 sm:p-5 flex flex-col justify-between hover:border-navy-700 hover:shadow-lg transition-all duration-200 box-border w-full min-w-0 ${
                  isDuplicate ? 'border-amber-500/30 opacity-75' : 'border-navy-750/90'
                }`}
              >
                {/* SECTION A: Header */}
                <div className="flex items-center justify-between gap-2 pb-3 border-b border-navy-800/60 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap min-w-0 flex-1">
                    <span
                      className="font-bold text-xs text-white px-2 py-0.5 rounded bg-navy-800 border border-navy-700 font-mono truncate max-w-[150px] sm:max-w-[180px]"
                      title={art.company}
                    >
                      {art.company}
                    </span>
                    {verifiedTicker && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-semibold shrink-0">
                        {verifiedTicker}
                      </span>
                    )}
                    {isDuplicate && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 shrink-0">
                        Duplicate
                      </span>
                    )}
                  </div>
                  <div className="shrink-0">
                    <SentimentBadge sentiment={art.sentiment} confidence={art.confidence} size="xs" />
                  </div>
                </div>

                {/* SECTION B: News Content & Metadata */}
                <div className="py-3 flex-1 flex flex-col justify-between space-y-3 min-w-0">
                  <div className="space-y-1.5 min-w-0">
                    <h3 className="text-sm font-semibold text-slate-100 line-clamp-2 leading-snug break-words">
                      {headlineText}
                    </h3>
                    {art.description && (
                      <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed break-words">
                        {art.description}
                      </p>
                    )}
                  </div>

                  {/* Publication Date, Time & Source */}
                  <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono pt-2 border-t border-navy-800/40 gap-2 min-w-0">
                    <span className="truncate max-w-[160px] font-medium text-slate-300" title={art.source}>
                      {art.source || 'Editorial Feed'}
                    </span>
                    <span className="text-[10px] text-slate-500 shrink-0 flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-500 shrink-0" />
                      {art.published_at
                        ? new Date(art.published_at).toLocaleString([], {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : 'Recent'}
                    </span>
                  </div>
                </div>

                {/* SECTION C: Action Buttons */}
                <div className="pt-3 border-t border-navy-800 mt-auto min-w-0 w-full">
                  <div className="flex flex-wrap items-center gap-2 w-full">
                    {/* Multilingual Translation Toggle */}
                    {(i18n.language || 'en').toLowerCase().split('-')[0] !== 'en' && (
                      <button
                        onClick={() => toggleArticleTranslation(art)}
                        disabled={tr?.loading}
                        className="h-8 px-2.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[11px] font-medium flex items-center justify-center gap-1.5 transition-colors cursor-pointer shrink-0 box-border"
                        title="Translate headline into current language"
                      >
                        <Languages className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                        <span className="whitespace-nowrap">{tr?.loading ? 'Translating...' : isTranslated ? 'Original' : 'Translate'}</span>
                      </button>
                    )}

                    {/* 1. Market Context Button */}
                    <button
                      onClick={() => {
                        setSelectedContextArticle(art);
                        setContextModalOpen(true);
                      }}
                      className="flex-1 min-w-[115px] h-8 px-2.5 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 hover:text-blue-200 border border-blue-500/25 text-[11px] font-medium flex items-center justify-center gap-1.5 transition-colors cursor-pointer box-border"
                      title="Explore macroeconomic indicators and systemic market context"
                    >
                      <Compass className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                      <span className="whitespace-nowrap">Market Context</span>
                    </button>

                    {/* 2. Trade Button (when verified tradable instrument exists) */}
                    {isTradable && (
                      <button
                        onClick={() => {
                          setSelectedTradeArticle({
                            ...art,
                            company: verifiedInst?.company || art.company,
                            ticker: verifiedTicker || art.ticker,
                          });
                          setTradeModalOpen(true);
                        }}
                        className="flex-1 min-w-[115px] h-8 px-2.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 hover:text-emerald-200 border border-emerald-500/30 text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer box-border"
                        title={`Trade ${verifiedInst?.company || art.company} via ${verifiedInst?.brokerName || 'broker'}`}
                      >
                        <TrendingUp className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        <span className="whitespace-nowrap">Trade ({brokerTag})</span>
                      </button>
                    )}

                    {/* 3. XAI Salience Button */}
                    <button
                      onClick={() => handleInspectAttribution(art)}
                      className="flex-1 min-w-[105px] h-8 px-2.5 rounded-lg bg-navy-800 hover:bg-navy-750 text-slate-300 hover:text-white border border-navy-700 text-[11px] font-medium flex items-center justify-center gap-1.5 transition-colors cursor-pointer box-border"
                      title="Inspect FinBERT token perturbation attribution"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                      <span className="whitespace-nowrap">XAI Salience</span>
                    </button>

                    {/* 4. External Link Icon */}
                    <a
                      href={art.url}
                      target="_blank"
                      rel="noreferrer"
                      className="h-8 w-8 rounded-lg bg-navy-800 hover:bg-navy-750 text-slate-400 hover:text-slate-200 border border-navy-700 transition-colors flex items-center justify-center shrink-0 cursor-pointer box-border"
                      title="Open source article in new tab"
                      aria-label="Open source article in new tab"
                    >
                      <ExternalLink className="w-3.5 h-3.5 shrink-0" />
                    </a>
                  </div>
                </div>
              </article>
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

      {/* Market Context Modal */}
      <MarketContextModal
        isOpen={contextModalOpen}
        onClose={() => {
          setContextModalOpen(false);
          setSelectedContextArticle(null);
        }}
        article={selectedContextArticle}
        onOpenTrade={(art) => {
          setSelectedTradeArticle(art);
          setTradeModalOpen(true);
        }}
      />

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
