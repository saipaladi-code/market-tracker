from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class MetalsPriceQuote(BaseModel):
    metal: str = Field(..., description="Precious metal: 'gold' or 'silver'")
    symbol: str = Field(..., description="Exchange ticker symbol, e.g. 'XAU', 'XAG', 'GC=F', 'SI=F'")
    price: float = Field(..., description="Current price in quotation currency (per troy ounce)")
    currency: str = Field(default="USD", description="Quotation currency, e.g. USD")
    unit: str = Field(default="troy_oz", description="Quotation unit, e.g. troy_oz")
    change: float = Field(default=0.0, description="Absolute daily price change")
    change_pct: float = Field(default=0.0, description="Percentage daily price change")
    prev_close_price: Optional[float] = Field(default=None, description="Previous close price")
    open_price: Optional[float] = Field(default=None, description="Open price")
    high_price: Optional[float] = Field(default=None, description="Day high price")
    low_price: Optional[float] = Field(default=None, description="Day low price")
    exchange: str = Field(default="GoldAPI.io", description="Primary commodity exchange or provider")
    timestamp: str = Field(..., description="Price timestamp in ISO format")
    quote_timestamp: Optional[int] = Field(default=None, description="Quote epoch timestamp (seconds) from provider")
    retrieval_timestamp: Optional[str] = Field(default=None, description="Timestamp when data was retrieved by backend")
    timestamp_ist: str = Field(..., description="Price timestamp formatted in Asia/Kolkata")
    freshness: str = Field(default="UPDATED", description="Data freshness indicator: 'UPDATED' | 'CACHED' | 'STALE' | 'ERROR'")
    data_status: str = Field(default="UPDATED", description="Status label")

class IndiaDomesticBenchmark(BaseModel):
    metal: str = Field(..., description="Precious metal: 'gold' or 'silver'")
    price_inr: float = Field(..., description="Indicative spot price in Indian Rupees (10g Gold / 1kg Silver)")
    inr_per_troy_oz: float = Field(default=0.0, description="International spot price converted to INR per troy ounce")
    unit: str = Field(..., description="Standard Indian unit: '10g' for gold, '1kg' for silver")
    usdinr_rate: float = Field(..., description="Applied USD/INR conversion rate")
    usdinr_source: str = Field(default="Open Exchange Rates", description="Exchange rate provider source")
    usdinr_timestamp: Optional[str] = Field(default=None, description="Exchange rate quote timestamp")
    timestamp: str = Field(..., description="Benchmark timestamp")
    timestamp_ist: str = Field(..., description="Benchmark timestamp in Asia/Kolkata")
    basis: str = Field(default="Indicative spot conversion (excludes local import duties & GST)", description="Price calculation basis")

class MetalsPriceCard(BaseModel):
    metal: str = Field(..., description="Precious metal name ('Gold' or 'Silver')")
    international: Optional[MetalsPriceQuote] = None
    india_domestic: Optional[IndiaDomesticBenchmark] = None
    usd_per_10g: Optional[float] = Field(default=None, description="Indicative converted USD price per 10 grams")
    usd_per_1kg: Optional[float] = Field(default=None, description="Indicative converted USD price per 1 kilogram")
    status: str = Field(default="active", description="'active' | 'delayed' | 'unconfigured'")
    provider: str = Field(default="GoldAPI.io", description="Price provider attribution")

class MetalsPricesResponse(BaseModel):
    gold: MetalsPriceCard
    silver: MetalsPriceCard
    last_updated: str
    last_updated_iso: Optional[str] = None
    quote_timestamp: Optional[str] = None
    provider: str = "GoldAPI.io"
    provider_status: str
    data_status: str = "CACHED"  # "UPDATED" | "CACHED" | "STALE" | "ERROR"
    usdinr_rate: float = 84.0
    usdinr_source: str = "Open Exchange Rates"
    usdinr_timestamp: Optional[str] = None
    cooldown_remaining_seconds: int = 0
    is_cached: bool = True
    error_message: Optional[str] = None
    notes: str

class UpdatePricesResponse(BaseModel):
    success: bool
    message: str
    prices: MetalsPricesResponse
    status: str = "UPDATED"
    cooldown_remaining_seconds: int = 0

class CurrencyContextResponse(BaseModel):
    country: str
    currency: str
    detected: bool
    supported_currencies: List[str] = ["INR", "USD"]

class MetalsArticle(BaseModel):
    id: str = Field(..., description="Unique deterministic article ID")
    title: str = Field(..., description="Original news headline")
    summary: Optional[str] = Field(default=None, description="Article summary or lead snippet")
    publisher: str = Field(..., description="News publisher or publication source")
    url: str = Field(..., description="Original canonical article URL")
    published_at: str = Field(..., description="Publication timestamp (ISO 8601)")
    published_at_ist: str = Field(..., description="Publication timestamp formatted in Asia/Kolkata (IST)")
    metal: str = Field(..., description="Classified metal: 'Gold' | 'Silver' | 'Both'")
    category: str = Field(..., description="Market category: 'India' | 'Global Markets' | 'Investment Trends'")
    sentiment: str = Field(..., description="FinBERT sentiment: 'Positive' | 'Negative' | 'Neutral'")
    sentiment_label: str = Field(..., description="Market sentiment label: 'Bullish' | 'Bearish' | 'Neutral'")
    scores: Dict[str, float] = Field(..., description="FinBERT probability distribution: positive, negative, neutral")
    confidence: float = Field(..., description="Top confidence percentage (0.0 to 100.0)")
    inference_engine: str = Field(..., description="Inference engine used, e.g. 'local-bfloat16' or 'lexical-fallback'")
    is_fallback: bool = Field(default=False, description="True if lexical fallback was used instead of neural FinBERT")

class MetalsNewsResponse(BaseModel):
    articles: List[MetalsArticle]
    total_count: int
    page: int
    page_size: int
    active_filters: Dict[str, Any]
    data_freshness: str
    disclaimer: str = Field(
        default="Sentiment reflects FinBERT NLP analysis of news reporting and does not constitute a price forecast or investment advice."
    )

class MetalsSentimentSummary(BaseModel):
    total_articles: int
    gold_articles_count: int
    silver_articles_count: int
    both_articles_count: int
    sentiment_distribution: Dict[str, int]
    gold_sentiment: Dict[str, Any]
    silver_sentiment: Dict[str, Any]
    category_counts: Dict[str, int]
    last_updated: str
    disclaimer: str = Field(
        default="FinBERT scores evaluate text tone in news reporting and do not predict future market returns."
    )

class MetalsHistoryPoint(BaseModel):
    date: str
    gold_positive: int = 0
    gold_negative: int = 0
    gold_neutral: int = 0
    silver_positive: int = 0
    silver_negative: int = 0
    silver_neutral: int = 0
    total_volume: int = 0

class MetalsHistoryResponse(BaseModel):
    history: List[MetalsHistoryPoint]
    timeframe: str

class TranslateRequest(BaseModel):
    text: str = Field(..., description="Text to translate", min_length=1)
    target_lang: str = Field(..., description="ISO 639 target language code, e.g. 'te', 'hi', 'ta', 'es'")
    article_id: Optional[str] = Field(default=None, description="Optional article ID for deterministic cache keying")

class TranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    target_lang: str
    is_cached: bool = False
    provider: str = "Google Translate"
