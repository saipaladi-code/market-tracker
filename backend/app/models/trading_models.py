from typing import List, Optional
from pydantic import BaseModel, Field

class BrokerDestination(BaseModel):
    broker_id: str = Field(..., description="Unique broker identifier, e.g. 'upstox' or 'ibkr'")
    broker_name: str = Field(..., description="Official broker display name")
    country: str = Field(..., description="Operating country/region: 'IN' or 'US'")
    market_coverage: str = Field(..., description="Supported exchanges and asset classes")
    entry_url: str = Field(..., description="Official verified broker web trading entry point")
    is_direct_link_verified: bool = Field(
        default=False,
        description="True only if a direct unauthenticated pre-filled order URL is officially documented"
    )
    requires_user_login: bool = Field(default=True, description="Indicates that user must log in to broker directly")
    instructions: str = Field(..., description="Step-by-step guidance for completing the trade with the broker")
    compliance_notice: str = Field(
        default="FIN-SENTIMENT is not a broker-dealer. Trades must be authorized directly by the user on the broker platform."
    )

class CompanyTradingRoute(BaseModel):
    is_tradable: bool = Field(..., description="True if verified instrument mapping exists for this company")
    company: str = Field(..., description="Resolved company name")
    ticker: Optional[str] = Field(default=None, description="Verified exchange ticker symbol")
    exchange: Optional[str] = Field(default=None, description="Primary exchange: NSE, BSE, NASDAQ, NYSE")
    country: Optional[str] = Field(default=None, description="Country code: IN or US")
    isin: Optional[str] = Field(default=None, description="International Securities Identification Number if verified")
    upstox_instrument_key: Optional[str] = Field(default=None, description="Upstox instrument token (e.g. NSE_EQ|INE...)")
    brokers: List[BrokerDestination] = Field(default_factory=list, description="Verified available broker destinations")
    message: str = Field(..., description="Human-readable routing status")
    disclaimer: str = Field(
        default="Sentiment scores reflect news reporting tone and do not guarantee investment performance. Always perform independent diligence."
    )

class SupportedInstrumentsResponse(BaseModel):
    indian_instruments: List[CompanyTradingRoute]
    international_instruments: List[CompanyTradingRoute]
    total_verified: int

class BrokerCapabilitiesResponse(BaseModel):
    brokers: List[BrokerDestination]
    compliance_statement: str
