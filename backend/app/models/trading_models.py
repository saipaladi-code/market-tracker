from typing import List, Optional
from pydantic import BaseModel, Field

class BrokerDestination(BaseModel):
    broker_id: str = Field(..., description="Unique broker identifier, e.g. 'upstox' or 'groww'")
    broker_name: str = Field(..., description="Official broker display name")
    country: str = Field(..., description="Operating country/region: 'IN' or 'US'")
    market_coverage: str = Field(..., description="Supported exchanges and asset classes")
    entry_url: str = Field(..., description="Official verified broker web trading entry point or portal")
    direct_url: Optional[str] = Field(
        default=None,
        description="Official verified stock-specific instrument/quote page URL if available"
    )
    destination_type: str = Field(
        default="verified_portal_with_ticker_search",
        description="Destination type: 'direct_instrument' | 'verified_portal_with_ticker_search' | 'unsupported'"
    )
    is_direct_link_verified: bool = Field(
        default=False,
        description="True only if a direct stock instrument page URL is officially verified"
    )
    requires_user_login: bool = Field(default=True, description="Indicates that user must log in to broker directly")
    action_label: Optional[str] = Field(
        default=None,
        description="Contextual button label, e.g. 'Open Reliance in Upstox'"
    )
    instructions: str = Field(..., description="Step-by-step guidance for completing the trade with the broker")
    compliance_notice: str = Field(
        default="FIN-SENTIMENT is not a broker-dealer. Trades must be authorized directly by the user on the broker platform."
    )

class CompanyTradingRoute(BaseModel):
    status: str = Field(default="supported", description="Routing status: 'supported' or 'unsupported'")
    is_tradable: bool = Field(..., description="True if verified instrument mapping exists for this company")
    company: str = Field(..., description="Resolved company name")
    ticker: Optional[str] = Field(default=None, description="Verified exchange ticker symbol")
    exchange: Optional[str] = Field(default=None, description="Primary exchange: NSE, BSE, NASDAQ, NYSE")
    country: Optional[str] = Field(default=None, description="Country code: IN or US")
    isin: Optional[str] = Field(default=None, description="International Securities Identification Number if verified")
    upstox_instrument_key: Optional[str] = Field(default=None, description="Upstox instrument token (e.g. NSE_EQ|INE...)")
    destination_type: str = Field(
        default="verified_portal_with_ticker_search",
        description="Routing destination type: 'direct_instrument' | 'verified_portal_with_ticker_search' | 'unsupported'"
    )
    direct_url: Optional[str] = Field(default=None, description="Direct stock-specific destination URL")
    portal_fallback_url: Optional[str] = Field(default=None, description="Safe official portal fallback URL")
    action_label: Optional[str] = Field(default=None, description="Primary action button label")
    share_class_note: Optional[str] = Field(default=None, description="Clarification for multi-class shares like Alphabet")
    brokers: List[BrokerDestination] = Field(default_factory=list, description="Verified available broker destinations")
    recommended_broker: Optional[BrokerDestination] = Field(default=None, description="Preferred broker destination")
    message: str = Field(..., description="Human-readable routing status")
    disclaimer: str = Field(
        default="Sentiment scores reflect news reporting tone and do not guarantee investment performance. Always perform independent diligence."
    )

class SupportedInstrumentsResponse(BaseModel):
    indian_instruments: List[CompanyTradingRoute]
    international_instruments: List[CompanyTradingRoute]
    total_instruments: int = Field(default=0)
    total_verified: int = Field(default=0)

class BrokerCapabilitiesResponse(BaseModel):
    brokers: List[BrokerDestination]
    compliance_statement: str
