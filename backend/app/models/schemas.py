from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

class SentimentScores(BaseModel):
    positive: float = Field(..., ge=0.0, le=1.0)
    negative: float = Field(..., ge=0.0, le=1.0)
    neutral: float = Field(..., ge=0.0, le=1.0)

class AttributionToken(BaseModel):
    token: str
    impact: float
    direction: str
    method: str = "perturbation"  # or 'heuristic'

class SentimentAnalysisResult(BaseModel):
    model_config = {"protected_namespaces": ()}
    text: str
    sentiment: str  # positive, negative, neutral
    confidence: float
    scores: SentimentScores
    model_name: str
    analyzed_at: str
    tokens: List[AttributionToken] = []
    explanation_note: str
    is_fallback: bool = False
    engine_mode: Optional[str] = None
    article_id: Optional[str] = None

class AnalyzeRequest(BaseModel):
    text: str = Field(default="", description="Financial news headline or sentence")

class BatchAnalyzeRequest(BaseModel):
    texts: List[str] = Field(default=[], description="List of headlines to analyze")

class Article(BaseModel):
    model_config = {"protected_namespaces": ()}
    id: str
    canonical_id: str
    title: str
    description: Optional[str] = None
    url: str
    source: str
    published_at: str
    company: str
    sentiment: Optional[str] = None
    confidence: Optional[float] = None
    scores: Optional[SentimentScores] = None
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    is_demo: bool = False
    is_fallback: Optional[bool] = False
    engine_mode: Optional[str] = None
    model_name: Optional[str] = None
    tokens: Optional[List[AttributionToken]] = None
    explanation_note: Optional[str] = None

class NewsSearchRequest(BaseModel):
    query: Optional[str] = None
    company: Optional[str] = None
    sentiment: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    today_only: Optional[bool] = None
    date: Optional[str] = None

class NewsResponse(BaseModel):
    articles: List[Article]
    total_count: int
    page: int
    page_size: int
    is_demo_dataset: bool
    feed_status: Optional[str] = "LIVE FEED"
    last_synced: Optional[str] = None
    filter_date: Optional[str] = None
    news_provider: Optional[str] = None

class CompanySentimentSummary(BaseModel):
    company: str
    ticker: str
    sector: str
    total_articles: int
    positive_count: int
    negative_count: int
    neutral_count: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    average_confidence: float
    has_conflict: bool
    latest_headline: Optional[str] = None

class ConflictSignal(BaseModel):
    company: str
    ticker: str
    conflict_score: float
    positive_count: int
    negative_count: int
    neutral_count: int
    positive_headlines: List[str]
    negative_headlines: List[str]
    explanation: str
    flagged_at: str

class SectorSentiment(BaseModel):
    sector: str
    article_count: int
    bullish_pct: float
    bearish_pct: float
    neutral_pct: float
    net_sentiment_score: float  # -1.0 (bearish) to +1.0 (bullish)
    status: str
    companies: List[str]

class AlertRecord(BaseModel):
    id: str
    company: str
    alert_type: str
    severity: str  # low, medium, high
    message: str
    timestamp: str
    is_read: bool = False
    metrics: Dict[str, Any] = {}

class DataQualityReport(BaseModel):
    model_config = {"protected_namespaces": ()}
    total_articles: int
    missing_headlines: int
    missing_sources: int
    invalid_urls: int
    duplicate_count: int
    duplicate_rate: float
    low_confidence_count: int
    low_confidence_rate: float
    stale_articles_count: int
    model_status: str
    news_api_status: str
    database_status: Dict[str, Any]
    engine_mode: Optional[str] = None

class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    company_focus: Optional[str] = None

class AssistantChatResponse(BaseModel):
    response: str
    relevant_articles: List[Dict[str, Any]] = []
    is_gemini_active: bool
    disclaimer: str
