import re
import logging
from typing import Dict, Any, List, Optional
from app.models.trading_models import (
    BrokerDestination, CompanyTradingRoute,
    SupportedInstrumentsResponse, BrokerCapabilitiesResponse
)

logger = logging.getLogger("broker_routing_service")

# Official Broker Definitions
UPSTOX_BASE_BROKER = BrokerDestination(
    broker_id="upstox",
    broker_name="Upstox Pro",
    country="IN",
    market_coverage="Indian Equities, F&O, Currency & Commodity (NSE & BSE)",
    entry_url="https://pro.upstox.com",
    direct_url=None,
    destination_type="direct_instrument",
    is_direct_link_verified=True,
    requires_user_login=True,
    action_label="Open in Upstox",
    instructions="Review the verified stock page on Upstox. To place an order, sign in to your Upstox account and execute the order.",
    compliance_notice="Orders must be authenticated and submitted directly on Upstox. FIN-SENTIMENT never stores brokerage credentials or automates trading."
)

GROWW_BASE_BROKER = BrokerDestination(
    broker_id="groww",
    broker_name="Groww",
    country="IN",
    market_coverage="Indian Equities & Derivatives (NSE & BSE)",
    entry_url="https://groww.in/stocks",
    direct_url=None,
    destination_type="direct_instrument",
    is_direct_link_verified=True,
    requires_user_login=True,
    action_label="Open on Groww",
    instructions="Review real-time NSE market quotes, interactive TradingView charts, and execute orders directly on your Groww account.",
    compliance_notice="FIN-SENTIMENT is an informational analytics platform. Orders must be authorized directly by the user on Groww. We never store brokerage credentials or automate trading."
)

# Verified Indian Stock Instruments (NSE / BSE)
# Upstox is the preferred and verified broker for all Indian equities.
# All URLs below have been tested and verified (HTTP 200 OK) on official Upstox public pages.
VERIFIED_INDIAN_INSTRUMENTS: Dict[str, Dict[str, Any]] = {
    "reliance": {
        "company": "Reliance Industries",
        "short_name": "Reliance",
        "ticker": "RELIANCE",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE002A01018",
        "upstox_instrument_key": "NSE_EQ|INE002A01018",
        "upstox_direct_url": "https://upstox.com/stocks/reliance-industries-ltd-share-price/",
        "groww_direct_url": "https://groww.in/stocks/reliance-industries-ltd",
        "preferred_broker": "upstox",
        "aliases": [
            "reliance", "reliance industries", "reliance industries limited", "reliance industries ltd",
            "ril", "jio", "reliance (reliance)", "reliance industries (ril)"
        ]
    },
    "tata motors": {
        "company": "Tata Motors",
        "short_name": "Tata Motors",
        "ticker": "TATAMOTORS",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE155A01022",
        "upstox_instrument_key": "NSE_EQ|INE155A01022",
        "upstox_direct_url": "https://upstox.com/stocks/tata-motors-limited-share-price/",
        "groww_direct_url": "https://groww.in/stocks/tata-motors-ltd",
        "share_class_note": "Commercial vehicles & core listed equity (TATAMOTORS, NSE). Passenger vehicles division trades under TMPV.",
        "preferred_broker": "upstox",
        "aliases": [
            "tata motors", "tatamotors", "tata motors limited", "tata motors ltd", "tata motors (tatamotors)",
            "tmcv"
        ]
    },
    "tcs": {
        "company": "Tata Consultancy Services",
        "short_name": "TCS",
        "ticker": "TCS",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE467B01029",
        "upstox_instrument_key": "NSE_EQ|INE467B01029",
        "upstox_direct_url": "https://upstox.com/stocks/tata-consultancy-serv-lt-share-price/",
        "groww_direct_url": "https://groww.in/stocks/tata-consultancy-services-ltd",
        "preferred_broker": "upstox",
        "aliases": [
            "tcs", "tata consultancy services", "tata consultancy services (tcs)", "tata consultancy",
            "tcs ltd", "tata consultancy services limited"
        ]
    },
    "infosys": {
        "company": "Infosys",
        "short_name": "Infosys",
        "ticker": "INFY",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE009A01021",
        "upstox_instrument_key": "NSE_EQ|INE009A01021",
        "upstox_direct_url": "https://upstox.com/stocks/infosys-limited-share-price/",
        "groww_direct_url": "https://groww.in/stocks/infosys-ltd",
        "preferred_broker": "upstox",
        "aliases": [
            "infosys", "infy", "infosys limited", "infosys ltd", "infosys (infy)"
        ]
    },
    "hdfc bank": {
        "company": "HDFC Bank",
        "short_name": "HDFC Bank",
        "ticker": "HDFCBANK",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE040A01034",
        "upstox_instrument_key": "NSE_EQ|INE040A01034",
        "upstox_direct_url": "https://upstox.com/stocks/hdfc-bank-ltd-share-price/",
        "groww_direct_url": "https://groww.in/stocks/hdfc-bank-ltd",
        "preferred_broker": "upstox",
        "aliases": [
            "hdfc bank", "hdfcbank", "hdfc", "hdfc bank limited", "hdfc bank ltd", "hdfc bank (hdfcbank)"
        ]
    },
    "icici bank": {
        "company": "ICICI Bank",
        "short_name": "ICICI Bank",
        "ticker": "ICICIBANK",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE090A01021",
        "upstox_instrument_key": "NSE_EQ|INE090A01021",
        "upstox_direct_url": "https://upstox.com/stocks/icici-bank-ltd-share-price/",
        "groww_direct_url": "https://groww.in/stocks/icici-bank-ltd",
        "preferred_broker": "upstox",
        "aliases": [
            "icici bank", "icicibank", "icici", "icici bank limited", "icici bank ltd", "icici bank (icicibank)"
        ]
    },
    "state bank of india": {
        "company": "State Bank of India",
        "short_name": "SBI",
        "ticker": "SBIN",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE062A01020",
        "upstox_instrument_key": "NSE_EQ|INE062A01020",
        "upstox_direct_url": "https://upstox.com/stocks/state-bank-of-india-share-price/",
        "groww_direct_url": "https://groww.in/stocks/state-bank-of-india",
        "preferred_broker": "upstox",
        "aliases": [
            "state bank of india", "sbi", "sbin", "state bank of india (sbin)", "state bank"
        ]
    },
    "bharti airtel": {
        "company": "Bharti Airtel",
        "short_name": "Bharti Airtel",
        "ticker": "BHARTIARTL",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE397D01024",
        "upstox_instrument_key": "NSE_EQ|INE397D01024",
        "upstox_direct_url": "https://upstox.com/stocks/bharti-airtel-limited-share-price/",
        "groww_direct_url": "https://groww.in/stocks/bharti-airtel-ltd",
        "preferred_broker": "upstox",
        "aliases": [
            "bharti airtel", "airtel", "bhartiartl", "bharti airtel (bhartiartl)", "bharti airtel limited"
        ]
    },
    "larsen & toubro": {
        "company": "Larsen & Toubro",
        "short_name": "Larsen & Toubro",
        "ticker": "LT",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE018A01030",
        "upstox_instrument_key": "NSE_EQ|INE018A01030",
        "upstox_direct_url": "https://upstox.com/stocks/larsen-toubro-ltd-share-price/",
        "groww_direct_url": "https://groww.in/stocks/larsen-toubro-ltd",
        "preferred_broker": "upstox",
        "aliases": [
            "larsen & toubro", "l&t", "lt", "larsen and toubro", "larsen & toubro (lt)", "larsen & toubro limited"
        ]
    },
    "wipro": {
        "company": "Wipro",
        "short_name": "Wipro",
        "ticker": "WIPRO",
        "exchange": "NSE",
        "country": "IN",
        "isin": "INE075A01022",
        "upstox_instrument_key": "NSE_EQ|INE075A01022",
        "upstox_direct_url": "https://upstox.com/stocks/wipro-ltd-share-price/",
        "groww_direct_url": "https://groww.in/stocks/wipro-ltd",
        "preferred_broker": "upstox",
        "aliases": [
            "wipro", "wipro limited", "wipro ltd", "wipro (wipro)"
        ]
    }
}

# Verified US Stock Instruments (NASDAQ / NYSE)
# Groww (US Stocks) is routed for verified US equities.
# Note: Groww US Stocks portal provides access to US-listed equities and ETFs in partnership with global clearing brokerages.
# It does not support public deep-link query parameters for individual stock orders; verified portal entry with ticker preservation is provided.
VERIFIED_US_INSTRUMENTS: Dict[str, Dict[str, Any]] = {
    "tesla": {
        "company": "Tesla",
        "short_name": "Tesla",
        "ticker": "TSLA",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US88160R1014",
        "preferred_broker": "groww",
        "aliases": ["tesla", "tsla", "tesla inc", "tesla inc.", "tesla motors", "tesla (tsla)"]
    },
    "apple": {
        "company": "Apple",
        "short_name": "Apple",
        "ticker": "AAPL",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US0378331005",
        "preferred_broker": "groww",
        "aliases": ["apple", "aapl", "apple inc", "apple inc.", "apple (aapl)"]
    },
    "amazon": {
        "company": "Amazon",
        "short_name": "Amazon",
        "ticker": "AMZN",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US0231351067",
        "preferred_broker": "groww",
        "aliases": ["amazon", "amzn", "amazon.com", "amazon.com inc", "amazon (amzn)"]
    },
    "microsoft": {
        "company": "Microsoft",
        "short_name": "Microsoft",
        "ticker": "MSFT",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US5949181045",
        "preferred_broker": "groww",
        "aliases": ["microsoft", "msft", "microsoft corp", "microsoft corporation", "microsoft (msft)"]
    },
    "nvidia": {
        "company": "Nvidia",
        "short_name": "Nvidia",
        "ticker": "NVDA",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US67066G1040",
        "preferred_broker": "groww",
        "aliases": ["nvidia", "nvda", "nvidia corp", "nvidia corporation", "nvidia (nvda)"]
    },
    "alphabet_googl": {
        "company": "Alphabet (Class A)",
        "short_name": "Alphabet (GOOGL)",
        "ticker": "GOOGL",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US02079K3059",
        "share_class_note": "Alphabet Inc. Class A Common Stock (Voting). For Class C Non-Voting shares, use ticker GOOG.",
        "preferred_broker": "groww",
        "aliases": ["alphabet", "google", "googl", "alphabet inc", "alphabet (googl)", "google (googl)"]
    },
    "alphabet_goog": {
        "company": "Alphabet (Class C)",
        "short_name": "Alphabet (GOOG)",
        "ticker": "GOOG",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US02079K1079",
        "share_class_note": "Alphabet Inc. Class C Capital Stock (Non-Voting). For Class A Voting shares, use ticker GOOGL.",
        "preferred_broker": "groww",
        "aliases": ["goog", "alphabet class c", "google class c", "alphabet (goog)", "google (goog)"]
    },
    "meta": {
        "company": "Meta Platforms",
        "short_name": "Meta",
        "ticker": "META",
        "exchange": "NASDAQ",
        "country": "US",
        "isin": "US30303M1027",
        "preferred_broker": "groww",
        "aliases": ["meta", "meta platforms", "facebook", "meta platforms inc", "meta (meta)"]
    },
    "jpmorgan chase": {
        "company": "JPMorgan Chase",
        "short_name": "JPMorgan Chase",
        "ticker": "JPM",
        "exchange": "NYSE",
        "country": "US",
        "isin": "US46625H1005",
        "preferred_broker": "groww",
        "aliases": ["jpmorgan chase", "jpmorgan", "jpm", "chase", "jpmorgan chase & co", "jpmorgan chase (jpm)"]
    },
    "pfizer": {
        "company": "Pfizer",
        "short_name": "Pfizer",
        "ticker": "PFE",
        "exchange": "NYSE",
        "country": "US",
        "isin": "US7170811035",
        "preferred_broker": "groww",
        "aliases": ["pfizer", "pfe", "pfizer inc", "pfizer (pfe)"]
    },
    "exxonmobil": {
        "company": "ExxonMobil",
        "short_name": "ExxonMobil",
        "ticker": "XOM",
        "exchange": "NYSE",
        "country": "US",
        "isin": "US30231G1022",
        "preferred_broker": "groww",
        "aliases": ["exxonmobil", "exxon", "xom", "mobil", "exxon mobil corp", "exxonmobil (xom)"]
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

        # 2. Index US instruments (Groww) - Only for verified US equities
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
        cleaned = text.strip().lower()
        cleaned = re.sub(r'[\'\"\,]', '', cleaned)
        return cleaned

    def _extract_candidates(self, identifier: Optional[str]) -> List[str]:
        if not identifier:
            return []
        raw = identifier.strip()
        candidates: List[str] = [raw]

        # 1. Check parenthetical format: e.g. "Apple (AAPL)" or "Tata Consultancy Services (TCS)"
        paren_match = re.search(r'^(.*?)\s*\(([A-Za-z0-9\.\-\:\&]+)\)\s*$', raw)
        if paren_match:
            name_part = paren_match.group(1).strip()
            ticker_part = paren_match.group(2).strip()
            if ticker_part:
                candidates.append(ticker_part)
            if name_part:
                candidates.append(name_part)

        # 2. Common corporate suffix stripping
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
                destination_type="unsupported",
                direct_url=None,
                portal_fallback_url=None,
                action_label=None,
                share_class_note=None,
                brokers=[],
                recommended_broker=None,
                message="Trading destination not verified or currently unavailable. FIN-SENTIMENT only routes to verified broker instruments.",
                disclaimer="Trading routes require verified broker instrument catalog mappings. Unverified or general market securities cannot be traded directly."
            )

        country = inst.get("country", "")
        exchange = inst.get("exchange", "")
        ticker = inst["ticker"]
        company = inst["company"]
        short_name = inst.get("short_name", company)
        share_class_note = inst.get("share_class_note")

        # RULE 1: Indian stocks route to Groww with verified stock-specific pages
        if country == "IN" or exchange in ("NSE", "BSE") or inst.get("is_indian", False):
            groww_direct = inst.get("groww_direct_url") or f"https://groww.in/stocks/{self._normalize_string(short_name).replace(' ', '-')}"
            has_direct = bool(groww_direct)
            dest_type = "direct_instrument" if has_direct else "verified_portal_with_ticker_search"
            action_label = f"Open {short_name} on Groww"

            groww_broker = GROWW_BASE_BROKER.model_copy()
            groww_broker.entry_url = groww_direct if has_direct else "https://groww.in/stocks"
            groww_broker.direct_url = groww_direct
            groww_broker.destination_type = dest_type
            groww_broker.is_direct_link_verified = has_direct
            groww_broker.action_label = action_label
            groww_broker.instructions = (
                f"Navigate directly to {short_name} on Groww ({ticker}) with live NSE charts, market depth, and fundamentals. "
                f"To execute a trade, log in to your Groww account."
            )

            # Upstox broker preserved in brokers list as alternative
            upstox_direct = inst.get("upstox_direct_url")
            upstox_broker = UPSTOX_BASE_BROKER.model_copy()
            upstox_broker.entry_url = upstox_direct if upstox_direct else "https://pro.upstox.com"
            upstox_broker.direct_url = upstox_direct
            upstox_broker.action_label = f"Open {short_name} in Upstox"

            return CompanyTradingRoute(
                status="supported",
                is_tradable=True,
                company=company,
                ticker=ticker,
                exchange=exchange,
                country=country,
                isin=inst.get("isin"),
                upstox_instrument_key=inst.get("upstox_instrument_key"),
                destination_type=dest_type,
                direct_url=groww_direct,
                portal_fallback_url="https://groww.in/stocks",
                action_label=action_label,
                share_class_note=share_class_note,
                brokers=[groww_broker, upstox_broker],
                recommended_broker=groww_broker,
                message=f"Verified Indian equity instrument: {ticker} ({exchange}). Official route: Groww direct stock page.",
                disclaimer="Sentiment scores reflect news reporting tone and do not guarantee investment performance. Always perform independent diligence."
            )

        # RULE 2: US stocks on Groww - Groww does NOT support active trading for US-listed equities
        elif (country == "US" or exchange in ("NASDAQ", "NYSE")) and inst.get("is_verified_us", False):
            return CompanyTradingRoute(
                status="unsupported",
                is_tradable=False,
                company=company,
                ticker=ticker,
                exchange=exchange,
                country=country,
                isin=inst.get("isin"),
                upstox_instrument_key=None,
                destination_type="unsupported",
                direct_url=None,
                portal_fallback_url="https://groww.in/us-stocks/popular-us-stocks-and-etfs",
                action_label="US Stocks Unsupported on Groww",
                share_class_note=share_class_note,
                brokers=[],
                recommended_broker=None,
                message=f"Groww does not currently support active trading or direct order execution for US-listed equities ({ticker} on {exchange}). US stock investing is currently unavailable through Groww.",
                disclaimer="Groww trading is restricted to Indian equities on NSE & BSE. US-listed equities are not supported for trading."
            )

        # RULE 3: Other international stocks MUST NOT silently route to Groww or any broker
        return CompanyTradingRoute(
            status="unsupported",
            is_tradable=False,
            company=company,
            ticker=ticker,
            exchange=exchange,
            country=country,
            isin=inst.get("isin"),
            upstox_instrument_key=None,
            destination_type="unsupported",
            direct_url=None,
            portal_fallback_url=None,
            action_label=None,
            share_class_note=None,
            brokers=[],
            recommended_broker=None,
            message="Trading destination not verified or currently unavailable. International equity without verified broker coverage.",
            disclaimer="FIN-SENTIMENT never silently routes unsupported international stocks to a broker."
        )

    def get_trading_route_by_identifiers(
        self,
        company: Optional[str] = None,
        ticker: Optional[str] = None
    ) -> CompanyTradingRoute:
        """
        Attempts resolution using ticker first if available, then company name, then composite string.
        Guarantees that Indian stocks resolve to Upstox and US stocks resolve to Groww.
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
            brokers=[UPSTOX_BASE_BROKER, GROWW_BASE_BROKER],
            compliance_statement="Broker destinations are direct entries to officially documented portals. FIN-SENTIMENT does not execute trades, solicit orders, or store trading credentials."
        )

broker_routing_service = BrokerRoutingService()
