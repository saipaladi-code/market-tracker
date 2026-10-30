import re
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
# Upstox is the preferred and verified broker for all Indian equities.
VERIFIED_INDIAN_INSTRUMENTS: Dict[str, Dict[str, Any]] = {
    "reliance": {
        "company": "Reliance Industries",
        "ticker": "RELIANCE",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE002A01018",
        "upstox_instrument_key": "NSE_EQ|INE002A01018",
        "preferred_broker": "upstox",
        "aliases": [
            "reliance", "reliance industries", "reliance industries limited", "reliance industries ltd",
            "ril", "jio", "reliance (reliance)", "reliance industries (ril)"
        ]
    },
    "tata motors": {
        "company": "Tata Motors",
        "ticker": "TATAMOTORS",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE155A01022",
        "upstox_instrument_key": "NSE_EQ|INE155A01022",
        "preferred_broker": "upstox",
        "aliases": [
            "tata motors", "tatamotors", "tata motors limited", "tata motors ltd", "tata motors (tatamotors)"
        ]
    },
    "tcs": {
        "company": "Tata Consultancy Services",
        "ticker": "TCS",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE467B01029",
        "upstox_instrument_key": "NSE_EQ|INE467B01029",
        "preferred_broker": "upstox",
        "aliases": [
            "tcs", "tata consultancy services", "tata consultancy services (tcs)", "tata consultancy",
            "tcs ltd", "tata consultancy services limited"
        ]
    },
    "infosys": {
        "company": "Infosys",
        "ticker": "INFY",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE009A01021",
        "upstox_instrument_key": "NSE_EQ|INE009A01021",
        "preferred_broker": "upstox",
        "aliases": [
            "infosys", "infy", "infosys limited", "infosys ltd", "infosys (infy)"
        ]
    },
    "hdfc bank": {
        "company": "HDFC Bank",
        "ticker": "HDFCBANK",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE040A01034",
        "upstox_instrument_key": "NSE_EQ|INE040A01034",
        "preferred_broker": "upstox",
        "aliases": [
            "hdfc bank", "hdfcbank", "hdfc", "hdfc bank limited", "hdfc bank ltd", "hdfc bank (hdfcbank)"
        ]
    },
    "icici bank": {
        "company": "ICICI Bank",
        "ticker": "ICICIBANK",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE090A01021",
        "upstox_instrument_key": "NSE_EQ|INE090A01021",
        "preferred_broker": "upstox",
        "aliases": [
            "icici bank", "icicibank", "icici", "icici bank limited", "icici bank ltd", "icici bank (icicibank)"
        ]
    },
    "state bank of india": {
        "company": "State Bank of India",
        "ticker": "SBIN",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE062A01020",
        "upstox_instrument_key": "NSE_EQ|INE062A01020",
        "preferred_broker": "upstox",
        "aliases": [
            "state bank of india", "sbi", "sbin", "state bank of india (sbin)", "state bank"
        ]
    },
    "bharti airtel": {
        "company": "Bharti Airtel",
        "ticker": "BHARTIARTL",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE397D01024",
        "upstox_instrument_key": "NSE_EQ|INE397D01024",
        "preferred_broker": "upstox",
        "aliases": [
            "bharti airtel", "airtel", "bhartiartl", "bharti airtel (bhartiartl)", "bharti airtel limited"
        ]
    },
    "larsen & toubro": {
        "company": "Larsen & Toubro",
        "ticker": "LT",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE018A01030",
        "upstox_instrument_key": "NSE_EQ|INE018A01030",
        "preferred_broker": "upstox",
        "aliases": [
            "larsen & toubro", "l&t", "lt", "larsen and toubro", "larsen & toubro (lt)", "larsen & toubro limited"
        ]
    },
    "wipro": {
        "company": "Wipro",
        "ticker": "WIPRO",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE075A01022",
        "upstox_instrument_key": "NSE_EQ|INE075A01022",
        "preferred_broker": "upstox",
        "aliases": [
            "wipro", "wipro limited", "wipro ltd", "wipro (wipro)"
        ]
    }
}

# Verified US Stock Instruments (NASDAQ / NYSE)
# Interactive Brokers (IBKR) is only used when the relevant instrument and destination are verified as supported.
VERIFIED_US_INSTRUMENTS: Dict[str, Dict[str, Any]] = {
    "apple": {
        "company": "Apple",
        "ticker": "AAPL",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US0378331005",
        "preferred_broker": "ibkr",
        "aliases": ["apple", "aapl", "apple inc", "apple inc.", "apple (aapl)"]
    },
    "microsoft": {
        "company": "Microsoft",
        "ticker": "MSFT",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US5949181045",
        "preferred_broker": "ibkr",
        "aliases": ["microsoft", "msft", "microsoft corp", "microsoft corporation", "microsoft (msft)"]
    },
    "nvidia": {
        "company": "Nvidia",
        "ticker": "NVDA",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US67066G1040",
        "preferred_broker": "ibkr",
        "aliases": ["nvidia", "nvda", "nvidia corp", "nvidia corporation", "nvidia (nvda)"]
    },
    "tesla": {
        "company": "Tesla",
        "ticker": "TSLA",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US88160R1014",
        "preferred_broker": "ibkr",
        "aliases": ["tesla", "tsla", "tesla inc", "tesla inc.", "tesla motors", "tesla (tsla)"]
    },
    "alphabet": {
        "company": "Alphabet",
        "ticker": "GOOGL",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US02079K3059",
        "preferred_broker": "ibkr",
        "aliases": ["alphabet", "google", "googl", "goog", "alphabet inc", "alphabet (googl)"]
    },
    "amazon": {
        "company": "Amazon",
        "ticker": "AMZN",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US0231351067",
        "preferred_broker": "ibkr",
        "aliases": ["amazon", "amzn", "amazon.com", "amazon.com inc", "amazon (amzn)"]
    },
    "jpmorgan chase": {
        "company": "JPMorgan Chase",
        "ticker": "JPM",
        "exchange": "NYSE",
        "country": "US",
        "isin": "US46625H1005",
        "preferred_broker": "ibkr",
        "aliases": ["jpmorgan chase", "jpmorgan", "jpm", "chase", "jpmorgan chase & co", "jpmorgan chase (jpm)"]
    },
    "pfizer": {
        "company": "Pfizer",
        "ticker": "PFE",
        "exchange": "NYSE",
        "country": "US",
        "isin": "US7170811035",
        "preferred_broker": "ibkr",
        "aliases": ["pfizer", "pfe", "pfizer inc", "pfizer (pfe)"]
    },
    "exxonmobil": {
        "company": "ExxonMobil",
        "ticker": "XOM",
        "exchange": "NYSE",
        "country": "US",
        "isin": "US30231G1022",
        "preferred_broker": "ibkr",
        "aliases": ["exxonmobil", "exxon", "xom", "mobil", "exxon mobil corp", "exxonmobil (xom)"]
    },
    "meta": {
        "company": "Meta Platforms",
        "ticker": "META",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US30303M1027",
        "preferred_broker": "ibkr",
        "aliases": ["meta", "meta platforms", "facebook", "meta platforms inc", "meta (meta)"]
    }
}

class BrokerRoutingService:
    def __init__(self):
        self._alias_to_instrument: Dict[str, Dict[str, Any]] = {}
        self._build_lookup_index()

    def _build_lookup_index(self):
        # 1. Index Indian instruments (Upstox) - Priority 1 for Indian equities
        for key, data in VERIFIED_INDIAN_INSTRUMENTS.items():
            inst_record = dict(data, is_indian=True, is_verified_us=False)
            self._alias_to_instrument[key.lower()] = inst_record
            self._alias_to_instrument[data["ticker"].lower()] = inst_record
            self._alias_to_instrument[data["company"].lower()] = inst_record
            for alias in data.get("aliases", []):
                self._alias_to_instrument[alias.lower()] = inst_record

        # 2. Index US instruments (IBKR) - Only for verified US equities
        for key, data in VERIFIED_US_INSTRUMENTS.items():
            inst_record = dict(data, is_indian=False, is_verified_us=True)
            self._alias_to_instrument[key.lower()] = inst_record
            self._alias_to_instrument[data["ticker"].lower()] = inst_record
            self._alias_to_instrument[data["company"].lower()] = inst_record
            for alias in data.get("aliases", []):
                self._alias_to_instrument[alias.lower()] = inst_record

    def _normalize_string(self, text: Optional[str]) -> str:
        if not text:
            return ""
        # Remove extra whitespace and convert to lowercase
        cleaned = text.strip().lower()
        # Remove common corporate punctuation and noise
        cleaned = re.sub(r'[\'\"\,]', '', cleaned)
        return cleaned

    def _extract_candidates(self, identifier: Optional[str]) -> List[str]:
        """Extracts candidate lookup strings handling parenthetical tickers like 'Apple (AAPL)'."""
        if not identifier:
            return []
        raw = identifier.strip()
        candidates: List[str] = [raw]

        # 1. Check parenthetical format: e.g. "Apple (AAPL)" or "Tata Consultancy Services (TCS)"
        paren_match = re.search(r'^(.*?)\s*\(([A-Za-z0-9\.\-\:\&]+)\)\s*$', raw)
        if paren_match:
            name_part = paren_match.group(1).strip()
            ticker_part = paren_match.group(2).strip()
            # Prioritize ticker candidate then name candidate
            if ticker_part:
                candidates.append(ticker_part)
            if name_part:
                candidates.append(name_part)

        # 2. Common corporate suffix stripping: "Apple Inc." -> "Apple", "Reliance Industries Limited" -> "Reliance Industries"
        for c in list(candidates):
            stripped = re.sub(
                r'\b(inc\.|inc|corp\.|corp|corporation|ltd\.|ltd|limited|co\.|co|plc|holdings|platforms)\b',
                '',
                c,
                flags=re.IGNORECASE
            ).strip()
            if stripped and stripped != c:
                candidates.append(stripped)

        return candidates

    def resolve_instrument(self, identifier: Optional[str]) -> Optional[Dict[str, Any]]:
        if not identifier:
            return None

        candidates = self._extract_candidates(identifier)
        for cand in candidates:
            norm = self._normalize_string(cand)
            if norm in self._alias_to_instrument:
                return self._alias_to_instrument[norm]

        # Fallback check against ticker keys directly (case-insensitive)
        for cand in candidates:
            c_clean = cand.strip().upper()
            for inst in VERIFIED_INDIAN_INSTRUMENTS.values():
                if inst["ticker"] == c_clean or inst["company"].upper() == c_clean:
                    return dict(inst, is_indian=True, is_verified_us=False)
            for inst in VERIFIED_US_INSTRUMENTS.values():
                if inst["ticker"] == c_clean or inst["company"].upper() == c_clean:
                    return dict(inst, is_indian=False, is_verified_us=True)

        return None

    def get_trading_route(self, identifier: Optional[str]) -> CompanyTradingRoute:
        inst = self.resolve_instrument(identifier)
        if not inst:
            raw_name = (identifier or "Unknown").strip()
            return CompanyTradingRoute(
                status="unsupported",
                is_tradable=False,
                company=raw_name,
                ticker=None,
                exchange=None,
                country=None,
                isin=None,
                upstox_instrument_key=None,
                brokers=[],
                recommended_broker=None,
                message="Trading destination not verified or currently unavailable. FIN-SENTIMENT only routes to verified broker instruments.",
                disclaimer="Trading routes require verified broker instrument catalog mappings. Unverified or general market securities cannot be traded directly."
            )

        country = inst.get("country", "")
        exchange = inst.get("exchange", "")
        ticker = inst["ticker"]
        company = inst["company"]

        # RULE 1: Indian stocks MUST use Upstox as preferred broker
        if country == "IN" or exchange in ("NSE", "BSE") or inst.get("is_indian", False):
            upstox_copy = UPSTOX_BROKER.model_copy()
            upstox_copy.instructions = (
                f"Sign in to your Upstox Pro account and search for {ticker} ({exchange}) to execute your order."
            )
            brokers = [upstox_copy]
            msg = f"Verified Indian equity instrument: {ticker} ({exchange}). Preferred route: Upstox Pro."
            recommended = upstox_copy

        # RULE 2: US stocks use Interactive Brokers ONLY when verified as supported
        elif (country == "US" or exchange in ("NASDAQ", "NYSE")) and inst.get("is_verified_us", False):
            ibkr_copy = IBKR_BROKER.model_copy()
            ibkr_copy.instructions = (
                f"Log in to the IBKR Client Portal and search for {ticker} ({exchange}) to review real-time quote depth and execute your order."
            )
            brokers = [ibkr_copy]
            msg = f"Verified US equity instrument: {ticker} ({exchange}). Preferred route: Interactive Brokers (IBKR)."
            recommended = ibkr_copy

        # RULE 3: Other international stocks MUST NOT silently route to IBKR
        else:
            return CompanyTradingRoute(
                status="unsupported",
                is_tradable=False,
                company=company,
                ticker=ticker,
                exchange=exchange,
                country=country,
                isin=inst.get("isin"),
                upstox_instrument_key=None,
                brokers=[],
                recommended_broker=None,
                message="Trading destination not verified or currently unavailable. International equity without verified broker coverage.",
                disclaimer="FIN-SENTIMENT never silently routes unsupported international stocks to a broker."
            )

        return CompanyTradingRoute(
            status="supported",
            is_tradable=True,
            company=company,
            ticker=ticker,
            exchange=exchange,
            country=country,
            isin=inst.get("isin"),
            upstox_instrument_key=inst.get("upstox_instrument_key"),
            brokers=brokers,
            recommended_broker=recommended,
            message=msg,
            disclaimer="Sentiment scores reflect news reporting tone and do not guarantee investment performance. Always perform independent diligence."
        )

    def get_trading_route_by_identifiers(
        self,
        company: Optional[str] = None,
        ticker: Optional[str] = None
    ) -> CompanyTradingRoute:
        """
        Attempts resolution using ticker first if available, then company name, then composite string.
        Guarantees that Indian stocks resolve to Upstox and US stocks resolve to Interactive Brokers.
        """
        # Try ticker first
        if ticker and ticker.strip():
            route = self.get_trading_route(ticker.strip())
            if route.is_tradable:
                return route

        # Try company name
        if company and company.strip():
            route = self.get_trading_route(company.strip())
            if route.is_tradable:
                return route

        # Try composite string if both exist (e.g. "Apple (AAPL)")
        if company and ticker:
            composite = f"{company.strip()} ({ticker.strip()})"
            route = self.get_trading_route(composite)
            if route.is_tradable:
                return route

        # Fallback to unsupported result
        raw = (company or ticker or "Unknown").strip()
        return self.get_trading_route(raw)

    def get_all_supported_instruments(self) -> SupportedInstrumentsResponse:
        indian_routes = [self.get_trading_route(k) for k in VERIFIED_INDIAN_INSTRUMENTS.keys()]
        intl_routes = [self.get_trading_route(k) for k in VERIFIED_US_INSTRUMENTS.keys()]
        total_count = len(indian_routes) + len(intl_routes)
        return SupportedInstrumentsResponse(
            indian_instruments=indian_routes,
            international_instruments=intl_routes,
            total_instruments=total_count,
            total_verified=total_count
        )

    def get_broker_capabilities(self) -> BrokerCapabilitiesResponse:
        return BrokerCapabilitiesResponse(
            brokers=[UPSTOX_BROKER, IBKR_BROKER],
            compliance_statement="Broker destinations are direct entries to officially documented portals. FIN-SENTIMENT does not execute trades, solicit orders, or store trading credentials."
        )

broker_routing_service = BrokerRoutingService()
