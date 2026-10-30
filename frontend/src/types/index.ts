export interface SentimentScores {
  positive: number;
  negative: number;
  neutral: number;
}

export interface AttributionToken {
  token: string;
  impact: number;
  direction: string;
  method: string;
}

export interface SentimentAnalysisResult {
  text: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  confidence: number;
  scores: SentimentScores;
  model_name: string;
  analyzed_at: string;
  tokens: AttributionToken[];
  explanation_note: string;
  is_fallback?: boolean;
  engine_mode?: string;
  article_id?: string;
}

export interface Article {
  id: string;
  canonical_id: string;
  title: string;
  description?: string;
  url: string;
  source: string;
  published_at: string;
  company: string;
  ticker?: string;
  sentiment?: 'positive' | 'negative' | 'neutral';
  confidence?: number;
  scores?: SentimentScores;
  is_duplicate: boolean;
  duplicate_of?: string;
  is_demo: boolean;
  is_fallback?: boolean;
  engine_mode?: string;
  model_name?: string;
  tokens?: AttributionToken[];
  explanation_note?: string;
}

export type FeedStatus = 'LIVE FEED' | 'CACHED LIVE DATA' | 'DEMO DATA' | 'API ERROR';

export interface NewsResponse {
  articles: Article[];
  total_count: number;
  page: number;
  page_size: number;
  is_demo_dataset: boolean;
  feed_status?: FeedStatus;
  last_synced?: string;
  filter_date?: string;
  news_provider?: string;
  error_message?: string;
}

export interface DashboardStats {
  total_articles: number;
  total_including_duplicates: number;
  sentiment_counts: {
    positive: number;
    negative: number;
    neutral: number;
  };
  sentiment_percentages: {
    positive: number;
    negative: number;
    neutral: number;
  };
  top_discussed_companies: Array<{ company: string; count: number }>;
  news_sources: Array<{ source: string; count: number }>;
  active_conflicts_count: number;
  active_conflicts: ConflictSignal[];
  is_demo_dataset: boolean;
  feed_status?: FeedStatus;
  filter_date?: string;
  last_synced?: string;
  last_updated: string;
  model_status: string;
}

export interface CompanySummary {
  company: string;
  ticker: string;
  sector: string;
  total_articles: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  positive_pct: number;
  negative_pct: number;
  neutral_pct: number;
  average_confidence: number;
  has_conflict: boolean;
  latest_headline?: string;
}

export interface ConflictSignal {
  company: string;
  ticker: string;
  conflict_score: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  positive_headlines: string[];
  negative_headlines: string[];
  explanation: string;
  flagged_at: string;
}

export interface SectorSentiment {
  sector: string;
  article_count: number;
  bullish_pct: number;
  bearish_pct: number;
  neutral_pct: number;
  net_sentiment_score: number;
  status: string;
  companies: string[];
}

export interface AlertRecord {
  id: string;
  company: string;
  alert_type: string;
  severity: 'low' | 'medium' | 'high';
  message: string;
  timestamp: string;
  is_read: boolean;
  metrics: Record<string, any>;
}

export interface DataQualityReport {
  total_articles: number;
  missing_headlines: number;
  missing_sources: number;
  invalid_urls: number;
  duplicate_count: number;
  duplicate_rate: number;
  low_confidence_count: number;
  low_confidence_rate: number;
  stale_articles_count: number;
  model_status: string;
  news_api_status: string;
  engine_mode?: string;
  database_status: {
    persistence_mode: string;
    connected: boolean;
    message: string;
    database_name: string;
  };
}

export interface AssistantChatResponse {
  response: string;
  relevant_articles: Array<{
    title: string;
    source: string;
    url: string;
    sentiment: string;
    confidence: number;
    company: string;
  }>;
  is_gemini_active: boolean;
  disclaimer: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  created_at?: string;
}

export interface AuthResponse {
  user: User;
  token: string;
  expires_in: number;
  message: string;
}

export interface ForgotPasswordResponse {
  message: string;
  status: string;
  smtp_configured: boolean;
  dev_reset_token?: string;
}

export interface MessageResponse {
  message: string;
  status: string;
}


// Precious Metals Intelligence Types
export interface MetalsPriceQuote {
  metal: 'gold' | 'silver';
  symbol: string;
  price: number;
  currency: string;
  unit: string;
  change: number;
  change_pct: number;
  exchange: string;
  timestamp: string;
  timestamp_ist: string;
  freshness: string;
}

export interface IndiaDomesticBenchmark {
  metal: 'gold' | 'silver';
  price_inr: number;
  unit: string;
  usdinr_rate: number;
  timestamp: string;
  timestamp_ist: string;
  basis: string;
}

export interface MetalsPriceCard {
  metal: string;
  international?: MetalsPriceQuote;
  india_domestic?: IndiaDomesticBenchmark;
  status: 'active' | 'delayed' | 'unconfigured';
  provider: string;
}

export interface MetalsPricesResponse {
  gold: MetalsPriceCard;
  silver: MetalsPriceCard;
  last_updated: string;
  provider_status: string;
  notes: string;
}

export interface MetalsArticle {
  id: string;
  title: string;
  summary?: string;
  publisher: string;
  url: string;
  published_at: string;
  published_at_ist: string;
  metal: 'Gold' | 'Silver' | 'Both';
  category: 'India' | 'Global Markets' | 'Investment Trends';
  sentiment: 'Positive' | 'Negative' | 'Neutral';
  sentiment_label: 'Bullish' | 'Bearish' | 'Neutral';
  scores: {
    positive: number;
    negative: number;
    neutral: number;
  };
  confidence: number;
  inference_engine: string;
  is_fallback: boolean;
}

export interface MetalsNewsResponse {
  articles: MetalsArticle[];
  total_count: number;
  page: number;
  page_size: number;
  active_filters: {
    metal: string;
    category: string;
    days: number;
    search: string;
  };
  data_freshness: string;
  disclaimer: string;
}

export interface MetalsSentimentSummary {
  total_articles: number;
  gold_articles_count: number;
  silver_articles_count: number;
  both_articles_count: number;
  sentiment_distribution: {
    Bullish: number;
    Bearish: number;
    Neutral: number;
  };
  gold_sentiment: {
    total: number;
    bullish_count: number;
    bearish_count: number;
    neutral_count: number;
    bullish_pct: number;
    bearish_pct: number;
    neutral_pct: number;
    overall_sentiment: string;
  };
  silver_sentiment: {
    total: number;
    bullish_count: number;
    bearish_count: number;
    neutral_count: number;
    bullish_pct: number;
    bearish_pct: number;
    neutral_pct: number;
    overall_sentiment: string;
  };
  category_counts: {
    India: number;
    'Global Markets': number;
    'Investment Trends': number;
  };
  last_updated: string;
  disclaimer: string;
}

export interface MetalsHistoryPoint {
  date: string;
  gold_positive: number;
  gold_negative: number;
  gold_neutral: number;
  silver_positive: number;
  silver_negative: number;
  silver_neutral: number;
  total_volume: number;
}

export interface MetalsHistoryResponse {
  history: MetalsHistoryPoint[];
  timeframe: string;
}

export interface TranslateResponse {
  original_text: string;
  translated_text: string;
  source_lang: string;
  target_lang: string;
  cached: boolean;
  provider: string;
  status: string;
}

export interface LanguageInfo {
  code: string;
  name: string;
  native: string;
  dir: 'ltr' | 'rtl';
}

export interface BrokerDestination {
  broker_id: string;
  broker_name: string;
  country: string;
  market_coverage: string;
  entry_url: string;
  is_direct_link_verified: boolean;
  requires_user_login: boolean;
  instructions: string;
  compliance_notice: string;
}

export interface CompanyTradingRoute {
  status: 'supported' | 'unsupported';
  is_tradable: boolean;
  company: string;
  ticker: string | null;
  exchange: string | null;
  country: string | null;
  isin?: string | null;
  upstox_instrument_key?: string | null;
  brokers: BrokerDestination[];
  recommended_broker: BrokerDestination | null;
  message: string;
  disclaimer: string;
}

export interface SupportedInstrumentsResponse {
  total_instruments: number;
  indian_instruments: Array<{
    company: string;
    ticker: string;
    exchange: string;
    country: string;
    isin?: string;
    upstox_instrument_key?: string;
  }>;
  international_instruments: Array<{
    company: string;
    ticker: string;
    exchange: string;
    country: string;
  }>;
}
