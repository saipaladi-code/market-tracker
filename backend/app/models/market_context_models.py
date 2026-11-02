from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class MarketIndicator(BaseModel):
    name: str = Field(..., description="Indicator or benchmark index name (e.g. NIFTY 50, S&P 500, COMEX Gold)")
    symbol: str = Field(..., description="Ticker or benchmark symbol (e.g. ^NSEI, ^GSPC, GC=F)")
    value: Optional[str] = Field(None, description="Current indicative value or price level")
    change: Optional[str] = Field(None, description="Session percentage change, e.g. '+0.85%' or '-0.42%'")
    trend: Literal['up', 'down', 'neutral'] = Field('neutral', description="Directional trend")
    relevance_note: str = Field(..., description="Context on why this indicator relates to the headline")

class FactsVsInterpretation(BaseModel):
    objective_facts: List[str] = Field(default_factory=list, description="Verifiable reported facts mentioned in news")
    ai_interpretation: str = Field(..., description="AI sentiment analysis and market implication assessment")
    risk_factors: List[str] = Field(default_factory=list, description="Key counterweights, volatility risks, or catalysts to monitor")

class MarketContextResponse(BaseModel):
    headline: str
    entity_type: Literal['company', 'general_market', 'commodity']
    entity_name: str
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    event_topic: str
    sentiment: str
    confidence: float
    market_relevance: str
    supporting_facts: List[str]
    market_indicators: List[MarketIndicator]
    facts_vs_interpretation: FactsVsInterpretation
    generated_at: str
    data_source: str

class MarketContextRequest(BaseModel):
    headline: str
    company: Optional[str] = None
    ticker: Optional[str] = None
    sentiment: Optional[str] = 'neutral'
    confidence: Optional[float] = 0.5
    source: Optional[str] = 'Editorial Feed'
    article_id: Optional[str] = None
