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
