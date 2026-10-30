import logging
from typing import Dict, Any, List, Optional
from app.models.trading_models import (
    BrokerDestination, CompanyTradingRoute,
    SupportedInstrumentsResponse, BrokerCapabilitiesResponse
)

logger = logging.getLogger("broker_routing_service")

# Official Broker Definitions
UPSTOX_BROKER = BrokerDestination(
    broker_id="upstox",
    broker_name="Upstox Pro",
    country="IN",
    market_coverage="Indian Equities, F&O, Currency & Commodity (NSE & BSE)",
    entry_url="https://pro.upstox.com",
    is_direct_link_verified=False,
    requires_user_login=True,
    instructions="Sign in to your Upstox Pro account and search for the ticker on NSE/BSE to place your order.",
    compliance_notice="Orders must be authenticated and submitted directly on Upstox. FIN-SENTIMENT never stores brokerage credentials or automates trading."
)

IBKR_BROKER = BrokerDestination(
    broker_id="ibkr",
    broker_name="Interactive Brokers (IBKR)",
    country="US",
    market_coverage="US & Global Equities, ETFs, Options & Futures (NASDAQ, NYSE, Global)",
    entry_url="https://www.interactivebrokers.com/portal/",
    is_direct_link_verified=False,
    requires_user_login=True,
    instructions="Log in to the IBKR Client Portal and search for the ticker to review real-time market depth and execute your order.",
    compliance_notice="IBKR trading requires individual account authorization and margin/permissions compliance. FIN-SENTIMENT does not place automated trades."
)

# Verified Indian Stock Instruments (NSE / BSE)
VERIFIED_INDIAN_INSTRUMENTS: Dict[str, Dict[str, Any]] = {
    "reliance": {
        "company": "Reliance Industries",
        "ticker": "RELIANCE",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE002A01018",
        "upstox_instrument_key": "NSE_EQ|INE002A01018",
        "aliases": ["reliance", "reliance industries", "ril", "jio"]
    },
    "tata motors": {
        "company": "Tata Motors",
        "ticker": "TATAMOTORS",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE155A01022",
        "upstox_instrument_key": "NSE_EQ|INE155A01022",
        "aliases": ["tata motors", "tatamotors", "tata motors limited"]
    },
    "tcs": {
        "company": "Tata Consultancy Services",
        "ticker": "TCS",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE467B01029",
        "upstox_instrument_key": "NSE_EQ|INE467B01029",
        "aliases": ["tcs", "tata consultancy services", "tata consultancy"]
    },
    "infosys": {
        "company": "Infosys",
        "ticker": "INFY",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE009A01021",
        "upstox_instrument_key": "NSE_EQ|INE009A01021",
        "aliases": ["infosys", "infy", "infosys limited"]
    },
    "hdfc bank": {
        "company": "HDFC Bank",
        "ticker": "HDFCBANK",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE040A01034",
        "upstox_instrument_key": "NSE_EQ|INE040A01034",
        "aliases": ["hdfc bank", "hdfcbank", "hdfc"]
    },
    "icici bank": {
        "company": "ICICI Bank",
        "ticker": "ICICIBANK",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE090A01021",
        "upstox_instrument_key": "NSE_EQ|INE090A01021",
        "aliases": ["icici bank", "icicibank", "icici"]
    },
    "state bank of india": {
        "company": "State Bank of India",
        "ticker": "SBIN",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE062A01020",
        "upstox_instrument_key": "NSE_EQ|INE062A01020",
        "aliases": ["state bank of india", "sbi", "sbin"]
    },
    "bharti airtel": {
        "company": "Bharti Airtel",
        "ticker": "BHARTIARTL",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE397D01024",
        "upstox_instrument_key": "NSE_EQ|INE397D01024",
        "aliases": ["bharti airtel", "airtel", "bhartiartl"]
    },
    "larsen & toubro": {
        "company": "Larsen & Toubro",
        "ticker": "LT",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE018A01030",
        "upstox_instrument_key": "NSE_EQ|INE018A01030",
        "aliases": ["larsen & toubro", "l&t", "lt"]
    },
    "wipro": {
        "company": "Wipro",
        "ticker": "WIPRO",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE075A01022",
        "upstox_instrument_key": "NSE_EQ|INE075A01022",
        "aliases": ["wipro", "wipro limited"]
    }
}

# Verified International Stock Instruments (NASDAQ / NYSE)
VERIFIED_INTERNATIONAL_INSTRUMENTS: Dict[str, Dict[str, Any]] = {
    "apple": {
        "company": "Apple",
        "ticker": "AAPL",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US0378331005",
        "aliases": ["apple", "aapl", "apple inc"]
    },
    "microsoft": {
        "company": "Microsoft",
        "ticker": "MSFT",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US5949181045",
        "aliases": ["microsoft", "msft", "microsoft corp"]
    },
    "nvidia": {
        "company": "Nvidia",
        "ticker": "NVDA",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US67066G1040",
        "aliases": ["nvidia", "nvda", "nvidia corp"]
    },
    "tesla": {
        "company": "Tesla",
        "ticker": "TSLA",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US88160R1014",
        "aliases": ["tesla", "tsla", "tesla inc"]
    },
    "alphabet": {
        "company": "Alphabet",
        "ticker": "GOOGL",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US02079K3059",
        "aliases": ["alphabet", "google", "googl", "goog"]
    },
    "amazon": {
        "company": "Amazon",
        "ticker": "AMZN",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US0231351067",
        "aliases": ["amazon", "amzn", "amazon.com"]
    },
    "jpmorgan chase": {
        "company": "JPMorgan Chase",
        "ticker": "JPM",
        "exchange": "NYSE",
        "country": "US",
        "isin": "US46625H1005",
        "aliases": ["jpmorgan chase", "jpmorgan", "jpm", "chase"]
    },
    "pfizer": {
        "company": "Pfizer",
        "ticker": "PFE",
        "exchange": "NYSE",
        "country": "US",
        "isin": "US7170811035",
        "aliases": ["pfizer", "pfe", "pfizer inc"]
    },
    "exxonmobil": {
        "company": "ExxonMobil",
        "ticker": "XOM",
        "exchange": "NYSE",
        "country": "US",
        "isin": "US30231G1022",
        "aliases": ["exxonmobil", "exxon", "xom", "mobil"]
    },
    "meta": {
        "company": "Meta Platforms",
        "ticker": "META",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US30303M1027",
        "aliases": ["meta", "meta platforms", "facebook"]
    }
}

class BrokerRoutingService:
    def __init__(self):
        self._alias_to_instrument: Dict[str, Dict[str, Any]] = {}
        self._build_lookup_index()

    def _build_lookup_index(self):
        # Index Indian instruments
        for key, data in VERIFIED_INDIAN_INSTRUMENTS.items():
            inst_record = dict(data, is_indian=True)
            self._alias_to_instrument[key] = inst_record
            self._alias_to_instrument[data["ticker"].lower()] = inst_record
            for alias in data.get("aliases", []):
                self._alias_to_instrument[alias.lower()] = inst_record

        # Index International instruments
        for key, data in VERIFIED_INTERNATIONAL_INSTRUMENTS.items():
            inst_record = dict(data, is_indian=False)
            self._alias_to_instrument[key] = inst_record
            self._alias_to_instrument[data["ticker"].lower()] = inst_record
            for alias in data.get("aliases", []):
                self._alias_to_instrument[alias.lower()] = inst_record

    def resolve_instrument(self, identifier: Optional[str]) -> Optional[Dict[str, Any]]:
        if not identifier:
            return None
        cleaned = identifier.strip().lower()
        return self._alias_to_instrument.get(cleaned)

    def get_trading_route(self, identifier: Optional[str]) -> CompanyTradingRoute:
        inst = self.resolve_instrument(identifier)
        if not inst:
            raw_name = (identifier or "Unknown").strip()
            return CompanyTradingRoute(
                is_tradable=False,
                company=raw_name,
                ticker=None,
                exchange=None,
                country=None,
                isin=None,
                upstox_instrument_key=None,
                brokers=[],
                message="Trading for this stock is not currently supported."
            )

        is_indian = inst.get("is_indian", False)
        ticker = inst["ticker"]
        exchange = inst["exchange"]
        company = inst["company"]

        if is_indian:
            # Customise Upstox instructions with verified ticker & exchange
            upstox_copy = UPSTOX_BROKER.model_copy()
            upstox_copy.instructions = f"Sign in to Upstox Pro and search for {ticker} ({exchange}) to execute your order."
            brokers = [upstox_copy]
            msg = f"Verified Indian equity instrument: {ticker} ({exchange}). Route available via Upstox."
        else:
            # Customise IBKR instructions with verified ticker & exchange
            ibkr_copy = IBKR_BROKER.model_copy()
            ibkr_copy.instructions = f"Log in to IBKR Client Portal and search for {ticker} ({exchange}) to place your order."
            brokers = [ibkr_copy]
            msg = f"Verified International equity instrument: {ticker} ({exchange}). Route available via Interactive Brokers (IBKR)."

        return CompanyTradingRoute(
            is_tradable=True,
            company=company,
            ticker=ticker,
            exchange=exchange,
            country=inst.get("country"),
            isin=inst.get("isin"),
            upstox_instrument_key=inst.get("upstox_instrument_key"),
            brokers=brokers,
            message=msg
        )

    def get_all_supported_instruments(self) -> SupportedInstrumentsResponse:
        indian_list = [self.get_trading_route(k) for k in VERIFIED_INDIAN_INSTRUMENTS.keys()]
        intl_list = [self.get_trading_route(k) for k in VERIFIED_INTERNATIONAL_INSTRUMENTS.keys()]
        return SupportedInstrumentsResponse(
            indian_instruments=indian_list,
            international_instruments=intl_list,
            total_verified=len(indian_list) + len(intl_list)
        )

    def get_broker_capabilities(self) -> BrokerCapabilitiesResponse:
        return BrokerCapabilitiesResponse(
            brokers=[UPSTOX_BROKER, IBKR_BROKER],
            compliance_statement="Broker destinations are direct entries to officially documented portals. FIN-SENTIMENT does not execute trades, solicit orders, or store trading credentials."
        )

broker_routing_service = BrokerRoutingService()
