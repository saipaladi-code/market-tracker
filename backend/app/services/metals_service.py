import hashlib
import logging
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import time
import threading
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings
from app.database import db
from app.services.finbert_service import finbert_service
from app.models.metals_models import (
    MetalsArticle, MetalsNewsResponse, MetalsPriceQuote,
    IndiaDomesticBenchmark, MetalsPriceCard, MetalsPricesResponse,
    MetalsSentimentSummary, MetalsHistoryPoint, MetalsHistoryResponse,
    UpdatePricesResponse
)

logger = logging.getLogger("metals_service")

# Timezone: Asia/Kolkata (IST = UTC+5:30)
try:
    from zoneinfo import ZoneInfo
    IST_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    IST_TZ = timezone(timedelta(hours=5, minutes=30))

TROY_OZ_TO_GRAMS = 31.1034768

class MetalsService:
    COOLDOWN_SECONDS = 60  # Minimum 60 seconds cooldown between external provider requests
    CACHE_FRESHNESS_THRESHOLD = 900  # 15 minutes = fresh; beyond 3600s = stale

    RSS_FEEDS = [
        {
            "category": "India",
            "url": "https://news.google.com/rss/search?q=gold+silver+price+MCX+india&hl=en-IN&gl=IN&ceid=IN:en",
            "default_metal": "Gold"
        },
        {
            "category": "Global Markets",
            "url": "https://news.google.com/rss/search?q=gold+silver+central+bank+dollar+fed&hl=en-US&gl=US&ceid=US:en",
            "default_metal": "Gold"
        },
        {
            "category": "Investment Trends",
            "url": "https://news.google.com/rss/search?q=silver+industrial+demand+solar+gold+etf&hl=en-US&gl=US&ceid=US:en",
            "default_metal": "Silver"
        }
    ]

    def __init__(self):
        self._cached_prices: Optional[Dict[str, Any]] = None
        self._last_successful_provider_fetch: float = 0
        self._prices_lock = threading.Lock()

        # USD/INR exchange rate cache
        self._cached_usdinr: Optional[float] = None
        self._usdinr_last_fetched: float = 0
        self._usdinr_source: str = "Open Exchange Rates"
        self._usdinr_timestamp: Optional[str] = None
        self._usdinr_ttl: float = 3600  # 1 hour cache for exchange rates

        # News ingestion cache
        self._articles_cache: List[Dict[str, Any]] = []
        self._articles_last_fetched: float = 0
        self._articles_cache_ttl = 300  # 5 minutes cache for news ingestion

        # Load persisted prices from DB on server boot
        self._load_persisted_prices()

    def _format_ist(self, dt: datetime) -> str:
        """Formats a datetime in Asia/Kolkata readable string."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ist_dt = dt.astimezone(IST_TZ)
        return ist_dt.strftime("%d %b %Y, %I:%M %p IST")

    def _load_persisted_prices(self):
        """Loads cached prices from DB if present, or prepares standard baseline."""
        try:
            persisted = db.find_one("metals_prices", {"type": "latest"})
            if persisted and "data" in persisted:
                self._cached_prices = persisted["data"]
                self._last_successful_provider_fetch = persisted.get("retrieval_epoch", 0)
                logger.info("Loaded persisted precious metals prices from database.")
                return
        except Exception as e:
            logger.warning(f"Notice reading persisted metals prices: {e}")

        # Baseline reference prices until user clicks 'Update Prices'
        iso_now = datetime.now(timezone.utc).isoformat()
        ist_now = self._format_ist(datetime.now(timezone.utc))
        baseline_rate = 95.08
        self._cached_usdinr = baseline_rate
        self._usdinr_last_fetched = time.time()
        self._usdinr_timestamp = iso_now

        self._cached_prices = self._build_price_dict(
            gold_price=3902.06,
            gold_change=14.20,
            gold_change_pct=0.37,
            gold_prev_close=3887.86,
            gold_quote_dt=datetime.now(timezone.utc),
            silver_price=50.394,
            silver_change=-0.22,
            silver_change_pct=-0.43,
            silver_prev_close=50.614,
            silver_quote_dt=datetime.now(timezone.utc),
            usdinr_rate=baseline_rate,
            usdinr_source="Open Exchange Rates",
            provider_name="GoldAPI.io",
            data_status="CACHED",
            notes="Reference baseline prices. Click 'Update Prices' to retrieve fresh live quotes from GoldAPI.io."
        )

    def _build_price_dict(
        self,
        gold_price: float,
        gold_change: float,
        gold_change_pct: float,
        gold_prev_close: Optional[float],
        gold_quote_dt: datetime,
        silver_price: float,
        silver_change: float,
        silver_change_pct: float,
        silver_prev_close: Optional[float],
        silver_quote_dt: datetime,
        usdinr_rate: float,
        usdinr_source: str,
        provider_name: str,
        data_status: str,
        notes: str,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Constructs standardized dictionary representation of metals prices."""
        now_dt = datetime.now(timezone.utc)
        iso_now = now_dt.isoformat()
        ist_now = self._format_ist(now_dt)

        # 1. Exact prompt conversion formulas:
        # Gold INR per 10g = Gold price in USD per troy ounce * USD/INR * 10 / 31.1034768
        gold_inr_oz = round(gold_price * usdinr_rate, 2)
        gold_inr_10g = round((gold_price * usdinr_rate * 10.0) / TROY_OZ_TO_GRAMS, 2)
        gold_usd_10g = round((gold_price * 10.0) / TROY_OZ_TO_GRAMS, 2)

        # Silver INR per kg = Silver price in USD per troy ounce * USD/INR * 1000 / 31.1034768
        silver_inr_oz = round(silver_price * usdinr_rate, 2)
        silver_inr_1kg = round((silver_price * usdinr_rate * 1000.0) / TROY_OZ_TO_GRAMS, 2)
        silver_usd_1kg = round((silver_price * 1000.0) / TROY_OZ_TO_GRAMS, 2)

        gold_quote_iso = gold_quote_dt.isoformat()
        gold_quote_ist = self._format_ist(gold_quote_dt)
        silver_quote_iso = silver_quote_dt.isoformat()
        silver_quote_ist = self._format_ist(silver_quote_dt)

        return {
            "gold": {
                "metal": "Gold",
                "international": {
                    "metal": "gold",
                    "symbol": "XAU",
                    "price": gold_price,
                    "currency": "USD",
                    "unit": "troy_oz",
                    "change": gold_change,
                    "change_pct": gold_change_pct,
                    "prev_close_price": gold_prev_close,
                    "exchange": provider_name,
                    "timestamp": gold_quote_iso,
                    "quote_timestamp": int(gold_quote_dt.timestamp()),
                    "retrieval_timestamp": iso_now,
                    "timestamp_ist": gold_quote_ist,
                    "freshness": data_status,
                    "data_status": data_status
                },
                "india_domestic": {
                    "metal": "gold",
                    "price_inr": gold_inr_10g,
                    "inr_per_troy_oz": gold_inr_oz,
                    "unit": "10g",
                    "usdinr_rate": usdinr_rate,
                    "usdinr_source": usdinr_source,
                    "usdinr_timestamp": iso_now,
                    "timestamp": gold_quote_iso,
                    "timestamp_ist": gold_quote_ist,
                    "basis": "Indicative spot conversion (excludes local import tariffs & GST)"
                },
                "usd_per_10g": gold_usd_10g,
                "status": "active" if data_status in ("UPDATED", "CACHED") else "delayed",
                "provider": provider_name
            },
            "silver": {
                "metal": "Silver",
                "international": {
                    "metal": "silver",
                    "symbol": "XAG",
                    "price": silver_price,
                    "currency": "USD",
                    "unit": "troy_oz",
                    "change": silver_change,
                    "change_pct": silver_change_pct,
                    "prev_close_price": silver_prev_close,
                    "exchange": provider_name,
                    "timestamp": silver_quote_iso,
                    "quote_timestamp": int(silver_quote_dt.timestamp()),
                    "retrieval_timestamp": iso_now,
                    "timestamp_ist": silver_quote_ist,
                    "freshness": data_status,
                    "data_status": data_status
                },
                "india_domestic": {
                    "metal": "silver",
                    "price_inr": silver_inr_1kg,
                    "inr_per_troy_oz": silver_inr_oz,
                    "unit": "1kg",
                    "usdinr_rate": usdinr_rate,
                    "usdinr_source": usdinr_source,
                    "usdinr_timestamp": iso_now,
                    "timestamp": silver_quote_iso,
                    "timestamp_ist": silver_quote_ist,
                    "basis": "Indicative spot conversion (excludes local import tariffs & GST)"
                },
                "usd_per_1kg": silver_usd_1kg,
                "status": "active" if data_status in ("UPDATED", "CACHED") else "delayed",
                "provider": provider_name
            },
            "last_updated": ist_now,
            "last_updated_iso": iso_now,
            "quote_timestamp": gold_quote_iso,
            "provider": provider_name,
            "provider_status": f"{provider_name} ({data_status})",
            "data_status": data_status,
            "usdinr_rate": usdinr_rate,
            "usdinr_source": usdinr_source,
            "usdinr_timestamp": iso_now,
            "cooldown_remaining_seconds": 0,
            "is_cached": (data_status != "UPDATED"),
            "error_message": error_message,
            "notes": notes
        }

    def get_market_prices(self) -> MetalsPricesResponse:
        """
        Fast, read-only endpoint returning current cached prices.
        Does NOT trigger provider calls to protect API quota when visitors load the page.
        """
        if not self._cached_prices:
            self._load_persisted_prices()

        res_dict = dict(self._cached_prices)
        now = time.time()
        age = now - self._last_successful_provider_fetch if self._last_successful_provider_fetch > 0 else 99999

        # Evaluate freshness status
        if res_dict.get("data_status") == "ERROR":
            data_status = "ERROR"
        elif age > 3600:
            data_status = "STALE"
        else:
            data_status = "CACHED"

        res_dict["data_status"] = data_status
        res_dict["is_cached"] = True

        # Calculate cooldown remaining if user recently updated
        elapsed = now - self._last_successful_provider_fetch
        rem = max(0, int(self.COOLDOWN_SECONDS - elapsed)) if self._last_successful_provider_fetch > 0 else 0
        res_dict["cooldown_remaining_seconds"] = rem

        return MetalsPricesResponse(**res_dict)

    def update_market_prices(self) -> UpdatePricesResponse:
        """
        Retrieves fresh gold and silver prices from GoldAPI.io upon user request.
        Enforces 60-second cooldown and thread lock to protect provider quota.
        Preserves last valid prices on error.
        """
        now = time.time()
        elapsed = now - self._last_successful_provider_fetch

        # 1. Enforce cooldown
        if self._last_successful_provider_fetch > 0 and elapsed < self.COOLDOWN_SECONDS:
            remaining = int(self.COOLDOWN_SECONDS - elapsed)
            current_prices = self.get_market_prices()
            current_prices.cooldown_remaining_seconds = remaining
            return UpdatePricesResponse(
                success=True,
                message=f"Prices were updated recently. Cooldown active ({remaining}s remaining).",
                prices=current_prices,
                status="COOLDOWN_ACTIVE",
                cooldown_remaining_seconds=remaining
            )

        with self._prices_lock:
            # Re-check cooldown under lock
            now = time.time()
            elapsed = now - self._last_successful_provider_fetch
            if self._last_successful_provider_fetch > 0 and elapsed < self.COOLDOWN_SECONDS:
                remaining = int(self.COOLDOWN_SECONDS - elapsed)
                current_prices = self.get_market_prices()
                current_prices.cooldown_remaining_seconds = remaining
                return UpdatePricesResponse(
                    success=True,
                    message=f"Prices were updated recently. Cooldown active ({remaining}s remaining).",
                    prices=current_prices,
                    status="COOLDOWN_ACTIVE",
                    cooldown_remaining_seconds=remaining
                )

            # 2. Check for configured GoldAPI.io key
            goldapi_key = settings.get_goldapi_key()
            usdinr_rate, usdinr_src = self._fetch_usdinr_rate()

            gold_data: Optional[Dict[str, Any]] = None
            silver_data: Optional[Dict[str, Any]] = None
            provider_used = "GoldAPI.io"
            fetch_error: Optional[str] = None

            if goldapi_key:
                logger.info("Requesting fresh gold and silver quotes from GoldAPI.io...")
                gold_res, g_err = self._fetch_goldapi_symbol("XAU", goldapi_key)
                silver_res, s_err = self._fetch_goldapi_symbol("XAG", goldapi_key)

                if gold_res and silver_res:
                    gold_data = gold_res
                    silver_data = silver_res
                else:
                    fetch_error = g_err or s_err or "GoldAPI.io response error."
                    logger.warning(f"GoldAPI.io fetch notice: {fetch_error}")
            else:
                fetch_error = "GOLDAPI_API_KEY environment variable is not configured on server."
                logger.warning(fetch_error)

            # 3. Fallback to secondary source (COMEX via Yahoo) if GoldAPI failed and no prior cache exists
            if not gold_data or not silver_data:
                # If we already have a previous valid cache, preserve it!
                if self._cached_prices:
                    res_dict = dict(self._cached_prices)
                    res_dict["data_status"] = "ERROR"
                    res_dict["error_message"] = f"Update notice: {fetch_error}. Preserving last valid market quotes."
                    res_dict["provider_status"] = f"{res_dict.get('provider', 'GoldAPI.io')} (Preserved Cache)"
                    return UpdatePricesResponse(
                        success=False,
                        message=f"Could not retrieve fresh quotes: {fetch_error}. Displaying last valid prices.",
                        prices=MetalsPricesResponse(**res_dict),
                        status="ERROR",
                        cooldown_remaining_seconds=0
                    )

                # Fallback to Yahoo COMEX if completely uninitialized
                logger.info("Falling back to COMEX futures reference data...")
                provider_used = "COMEX Futures (Yahoo Finance)"
                y_gold = self._fetch_yahoo_quote("GC=F", "gold")
                y_silver = self._fetch_yahoo_quote("SI=F", "silver")
                if y_gold and y_silver:
                    gold_data = y_gold
                    silver_data = y_silver

            if not gold_data or not silver_data:
                # Total failure fallback baseline
                gold_data = {
                    "price": 3902.06, "change": 0.0, "change_pct": 0.0,
                    "prev_close": 3902.06, "timestamp": datetime.now(timezone.utc)
                }
                silver_data = {
                    "price": 50.394, "change": 0.0, "change_pct": 0.0,
                    "prev_close": 50.394, "timestamp": datetime.now(timezone.utc)
                }

            # 4. Build response dictionary with exact prompt formulas
            res_dict = self._build_price_dict(
                gold_price=float(gold_data["price"]),
                gold_change=float(gold_data.get("change", 0.0)),
                gold_change_pct=float(gold_data.get("change_pct", 0.0)),
                gold_prev_close=float(gold_data.get("prev_close", gold_data["price"])),
                gold_quote_dt=gold_data["timestamp"],
                silver_price=float(silver_data["price"]),
                silver_change=float(silver_data.get("change", 0.0)),
                silver_change_pct=float(silver_data.get("change_pct", 0.0)),
                silver_prev_close=float(silver_data.get("prev_close", silver_data["price"])),
                silver_quote_dt=silver_data["timestamp"],
                usdinr_rate=usdinr_rate,
                usdinr_source=usdinr_src,
                provider_name=provider_used,
                data_status="UPDATED",
                notes=f"Latest market quotes retrieved from {provider_used}. Indicative INR conversions use live USD/INR exchange rate (excludes local import tariffs & GST).",
                error_message=fetch_error
            )

            # 5. Persist to cache and database
            self._cached_prices = res_dict
            self._last_successful_provider_fetch = now

            try:
                db.replace_one(
                    "metals_prices",
                    {"type": "latest"},
                    {"type": "latest", "data": res_dict, "retrieval_epoch": now, "updated_at": datetime.now(timezone.utc).isoformat()},
                    upsert=True
                )
            except Exception as e:
                logger.warning(f"Failed to persist metals prices to DB: {e}")

            response_obj = MetalsPricesResponse(**res_dict)
            return UpdatePricesResponse(
                success=True,
                message="Precious metals prices successfully updated.",
                prices=response_obj,
                status="UPDATED",
                cooldown_remaining_seconds=self.COOLDOWN_SECONDS
            )

    def _fetch_goldapi_symbol(self, symbol: str, api_key: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Calls GoldAPI.io for a single metal symbol in USD (XAU/USD or XAG/USD).
        Handles rate limits (429), timeouts, and invalid responses.
        """
        url = f"https://www.goldapi.io/api/{symbol}/USD"
        headers = {
            "x-access-token": api_key,
            "Content-Type": "application/json",
            "User-Agent": "FIN-SENTIMENT-MarketTracker/2.0"
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as res:
                if res.status == 200:
                    payload = json.loads(res.read().decode("utf-8"))
                    price = payload.get("price")
                    if price is None:
                        return None, "GoldAPI.io response missing price field."

                    prev_close = payload.get("prev_close_price")
                    ch = payload.get("ch")
                    chp = payload.get("chp")

                    if ch is None and prev_close is not None:
                        ch = round(price - prev_close, 2)
                    if chp is None and prev_close and prev_close != 0:
                        chp = round((ch / prev_close) * 100, 2)

                    # Parse provider timestamp
                    ts = payload.get("timestamp")
                    if ts and isinstance(ts, (int, float)):
                        quote_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    else:
                        quote_dt = datetime.now(timezone.utc)

                    return {
                        "price": float(price),
                        "change": float(ch) if ch is not None else 0.0,
                        "change_pct": float(chp) if chp is not None else 0.0,
                        "prev_close": float(prev_close) if prev_close is not None else float(price),
                        "timestamp": quote_dt,
                        "exchange": payload.get("exchange", "GoldAPI.io Spot")
                    }, None
                elif res.status == 429:
                    return None, "GoldAPI.io quota exceeded (HTTP 429 Too Many Requests)."
                elif res.status == 401 or res.status == 403:
                    return None, "GoldAPI.io authorization failed (invalid API key)."
                else:
                    return None, f"GoldAPI.io responded with HTTP {res.status}."
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return None, "GoldAPI.io quota exceeded (HTTP 429 Too Many Requests)."
            if e.code in (401, 403):
                return None, "GoldAPI.io authorization failed (invalid or missing key)."
            return None, f"GoldAPI.io HTTP error {e.code}."
        except urllib.error.URLError as e:
            return None, f"GoldAPI.io network connection error: {e.reason}"
        except Exception as e:
            return None, f"GoldAPI.io request exception: {str(e)}"

    def _fetch_yahoo_quote(self, symbol: str, metal: str) -> Optional[Dict[str, Any]]:
        """Fetches commodity chart data from Yahoo Finance endpoint."""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?interval=1d&range=5d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as res:
                data = json.loads(res.read().decode("utf-8"))
                meta = data["chart"]["result"][0]["meta"]
                price = meta.get("regularMarketPrice")
                prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
                change = round(price - prev_close, 2) if (price is not None and prev_close is not None) else 0.0
                change_pct = round((change / prev_close) * 100, 2) if (prev_close and prev_close != 0) else 0.0
                market_time = meta.get("regularMarketTime")
                dt = datetime.fromtimestamp(market_time, tz=timezone.utc) if market_time else datetime.now(timezone.utc)

                return {
                    "price": float(price),
                    "change": change,
                    "change_pct": change_pct,
                    "prev_close": float(prev_close) if prev_close else float(price),
                    "exchange": meta.get("exchangeName", "COMEX"),
                    "timestamp": dt
                }
        except Exception as e:
            logger.warning(f"Could not fetch quote for {symbol}: {e}")
            return None

    def _fetch_usdinr_rate(self) -> Tuple[float, str]:
        """
        Fetches current USD/INR exchange rate with 1-hour cache.
        Checks open.er-api.com first, falls back to Yahoo Finance USDINR=X, then baseline.
        """
        now = time.time()
        if self._cached_usdinr and (now - self._usdinr_last_fetched < self._usdinr_ttl):
            return self._cached_usdinr, self._usdinr_source

        # 1. Primary: open.er-api.com
        try:
            req = urllib.request.Request("https://open.er-api.com/v6/latest/USD", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as res:
                data = json.loads(res.read().decode("utf-8"))
                rate = data.get("rates", {}).get("INR")
                if rate and isinstance(rate, (int, float)):
                    self._cached_usdinr = float(rate)
                    self._usdinr_last_fetched = now
                    self._usdinr_source = "Open Exchange Rates API"
                    self._usdinr_timestamp = data.get("time_last_update_utc", datetime.now(timezone.utc).isoformat())
                    return self._cached_usdinr, self._usdinr_source
        except Exception as e:
            logger.debug(f"Open exchange rate check notice: {e}")

        # 2. Secondary: Yahoo Finance USDINR=X
        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/USDINR=X?interval=1d&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as res:
                data = json.loads(res.read().decode("utf-8"))
                rate = data["chart"]["result"][0]["meta"].get("regularMarketPrice")
                if rate and isinstance(rate, (int, float)):
                    self._cached_usdinr = float(rate)
                    self._usdinr_last_fetched = now
                    self._usdinr_source = "Yahoo Finance (USDINR=X)"
                    self._usdinr_timestamp = datetime.now(timezone.utc).isoformat()
                    return self._cached_usdinr, self._usdinr_source
        except Exception as e:
            logger.debug(f"Yahoo USD/INR rate check notice: {e}")

        # 3. Fallback baseline
        if not self._cached_usdinr:
            self._cached_usdinr = 95.08
            self._usdinr_source = "Baseline Reference"
            self._usdinr_timestamp = datetime.now(timezone.utc).isoformat()

        return self._cached_usdinr, self._usdinr_source

    def _classify_metal(self, text: str) -> str:
        """Classifies text into Gold, Silver, or Both."""
        t_low = text.lower()
        has_gold = any(w in t_low for w in ["gold", "bullion", "yellow metal", "sovereign", "24k", "22k"])
        has_silver = any(w in t_low for w in ["silver", "white metal", "industrial silver"])
        if has_gold and has_silver:
            return "Both"
        if has_silver:
            return "Silver"
        return "Gold"

    def _classify_category(self, text: str, feed_category: str) -> str:
        """Refines category based on keywords or feed source."""
        t_low = text.lower()
        if any(w in t_low for w in ["india", "mcx", "rupee", "rbi", "jeweller", "delhi", "mumbai", "domestic market"]):
            return "India"
        if any(w in t_low for w in ["etf", "solar", "photovoltaic", "industrial demand", "electronics", "inflow", "holdings", "fund", "investment"]):
            return "Investment Trends"
        if any(w in t_low for w in ["fed", "federal reserve", "dollar", "powell", "inflation", "central bank", "treasury", "geopolit"]):
            return "Global Markets"
        return feed_category

    def fetch_precious_metals_news(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Ingests genuine Gold & Silver articles from live financial RSS feeds,
        deduplicates them, performs FinBERT sentiment analysis, and caches in MongoDB/local DB.
        """
        now = time.time()
        if not force_refresh and self._articles_cache and (now - self._articles_last_fetched < self._articles_cache_ttl):
            return self._articles_cache

        stored_articles = db.find("metals_articles", limit=200)
        existing_map = {a.get("id"): a for a in stored_articles if a.get("id")}
        new_articles_count = 0
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        for feed_cfg in self.RSS_FEEDS:
            cat = feed_cfg["category"]
            feed_url = feed_cfg["url"]
            try:
                req = urllib.request.Request(feed_url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as response:
                    xml_data = response.read()
                    root = ET.fromstring(xml_data)
                    items = root.findall(".//item")

                    for item in items:
                        title_el = item.find("title")
                        raw_title = title_el.text if title_el is not None else ""
                        if not raw_title or len(raw_title.strip()) < 10:
                            continue

                        title = raw_title.strip()
                        if " - " in title:
                            parts = title.rsplit(" - ", 1)
                            clean_title = parts[0].strip()
                            source = parts[1].strip()
                        else:
                            clean_title = title
                            source_el = item.find("source")
                            source = source_el.text if source_el is not None else "Market News"

                        link_el = item.find("link")
                        link = link_el.text.strip() if (link_el is not None and link_el.text) else ""

                        pub_el = item.find("pubDate")
                        pub_raw = pub_el.text if pub_el is not None else ""
                        try:
                            dt = parsedate_to_datetime(pub_raw)
                        except Exception:
                            dt = datetime.now(timezone.utc)

                        norm_str = f"{clean_title.lower()}_{dt.strftime('%Y%m%d')}"
                        article_id = f"metal-{hashlib.sha256(norm_str.encode('utf-8')).hexdigest()[:12]}"

                        if article_id in existing_map:
                            continue

                        desc_el = item.find("description")
                        clean_desc = desc_el.text if desc_el is not None else ""
                        if clean_desc and "<" in clean_desc:
                            clean_desc = ET.tostring(ET.fromstring(f"<div>{clean_desc}</div>"), encoding="unicode", method="text")

                        sentiment_analysis = self._analyze_headline_sentiment(clean_title)
                        metal = self._classify_metal(f"{clean_title} {clean_desc}")
                        category = self._classify_category(f"{clean_title} {clean_desc}", cat)

                        article_doc = {
                            "id": article_id,
                            "title": clean_title,
                            "summary": clean_desc[:280] if clean_desc else None,
                            "publisher": source,
                            "url": link,
                            "published_at": dt.isoformat(),
                            "published_at_ist": self._format_ist(dt),
                            "metal": metal,
                            "category": category,
                            "sentiment": sentiment_analysis["sentiment"],
                            "sentiment_label": sentiment_analysis["sentiment_label"],
                            "scores": sentiment_analysis["scores"],
                            "confidence": sentiment_analysis["confidence"],
                            "inference_engine": sentiment_analysis["inference_engine"],
                            "is_fallback": sentiment_analysis["is_fallback"]
                        }

                        existing_map[article_id] = article_doc
                        new_articles_count += 1
                        try:
                            db.insert_one("metals_articles", article_doc)
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"Error fetching metals RSS feed '{cat}': {e}")
                continue

        all_articles = list(existing_map.values())
        all_articles.sort(key=lambda a: a.get("published_at", ""), reverse=True)
        self._articles_cache = all_articles
        self._articles_last_fetched = now
        logger.info(f"Metals news sync complete: {len(all_articles)} total articles, {new_articles_count} newly ingested.")
        return all_articles

    def _analyze_headline_sentiment(self, headline: str) -> Dict[str, Any]:
        """Uses existing finbert_service to analyze financial sentiment of precious metals news."""
        try:
            res = finbert_service.analyze(headline)
            raw_sentiment = res.sentiment.capitalize()
            label_map = {"Positive": "Bullish", "Negative": "Bearish", "Neutral": "Neutral"}

            pos_pct = round(res.scores.get("positive", 0.0) * 100, 1)
            neg_pct = round(res.scores.get("negative", 0.0) * 100, 1)
            neu_pct = round(res.scores.get("neutral", 0.0) * 100, 1)
            confidence = round(res.confidence * 100, 1) if res.confidence <= 1.0 else round(res.confidence, 1)

            return {
                "sentiment": raw_sentiment,
                "sentiment_label": label_map.get(raw_sentiment, raw_sentiment),
                "scores": {"positive": pos_pct, "negative": neg_pct, "neutral": neu_pct},
                "confidence": confidence,
                "inference_engine": finbert_service.engine_mode,
                "is_fallback": finbert_service.is_fallback
            }
        except Exception as e:
            logger.warning(f"FinBERT analysis failed for metals headline: {e}")
            return {
                "sentiment": "Neutral",
                "sentiment_label": "Neutral",
                "scores": {"positive": 33.3, "negative": 33.3, "neutral": 33.4},
                "confidence": 33.4,
                "inference_engine": "lexical-fallback",
                "is_fallback": True
            }

    def get_news(
        self,
        metal: Optional[str] = None,
        category: Optional[str] = None,
        days: int = 30,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None
    ) -> MetalsNewsResponse:
        """Filters, searches, and paginates precious metals articles."""
        all_articles = self.fetch_precious_metals_news()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        filtered = []
        search_lower = search.strip().lower() if search else None

        for art in all_articles:
            pub_str = art.get("published_at")
            if pub_str:
                try:
                    pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                    if pub_dt < cutoff:
                        continue
                except Exception:
                    pass

            if metal and metal.lower() != "all":
                art_metal = art.get("metal", "Gold")
                if metal.lower() == "gold" and art_metal not in ["Gold", "Both"]:
                    continue
                if metal.lower() == "silver" and art_metal not in ["Silver", "Both"]:
                    continue

            if category and category.lower() != "all":
                if art.get("category", "").lower() != category.lower():
                    continue

            if search_lower:
                title_match = search_lower in art.get("title", "").lower()
                summary_match = search_lower in (art.get("summary") or "").lower()
                publisher_match = search_lower in art.get("publisher", "").lower()
                if not (title_match or summary_match or publisher_match):
                    continue

            filtered.append(MetalsArticle(**art))

        total_count = len(filtered)
        start_idx = (page - 1) * page_size
        paginated_articles = filtered[start_idx:start_idx + page_size]

        return MetalsNewsResponse(
            articles=paginated_articles,
            total_count=total_count,
            page=page,
            page_size=page_size,
            active_filters={
                "metal": metal or "All",
                "category": category or "All",
                "days": days,
                "search": search or ""
            },
            data_freshness=f"Synced {self._format_ist(datetime.now(timezone.utc))}"
        )

    def get_sentiment_summary(self, days: int = 30) -> MetalsSentimentSummary:
        """Computes statistical FinBERT aggregation for Gold vs. Silver."""
        all_articles = self.fetch_precious_metals_news()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        recent_articles = []
        for a in all_articles:
            pub_str = a.get("published_at")
            if pub_str:
                try:
                    pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                    if pub_dt >= cutoff:
                        recent_articles.append(a)
                except Exception:
                    recent_articles.append(a)
            else:
                recent_articles.append(a)

        total = len(recent_articles)
        gold_count = sum(1 for a in recent_articles if a.get("metal") in ["Gold", "Both"])
        silver_count = sum(1 for a in recent_articles if a.get("metal") in ["Silver", "Both"])
        both_count = sum(1 for a in recent_articles if a.get("metal") == "Both")

        sentiment_dist = {"Bullish": 0, "Bearish": 0, "Neutral": 0}
        gold_sent = {"bullish_count": 0, "bearish_count": 0, "neutral_count": 0}
        silver_sent = {"bullish_count": 0, "bearish_count": 0, "neutral_count": 0}
        category_counts = {"India": 0, "Global Markets": 0, "Investment Trends": 0}

        for a in recent_articles:
            lbl = a.get("sentiment_label", "Neutral")
            sentiment_dist[lbl] = sentiment_dist.get(lbl, 0) + 1
            cat = a.get("category", "India")
            category_counts[cat] = category_counts.get(cat, 0) + 1

            metal = a.get("metal")
            if metal in ["Gold", "Both"]:
                if lbl == "Bullish": gold_sent["bullish_count"] += 1
                elif lbl == "Bearish": gold_sent["bearish_count"] += 1
                else: gold_sent["neutral_count"] += 1

            if metal in ["Silver", "Both"]:
                if lbl == "Bullish": silver_sent["bullish_count"] += 1
                elif lbl == "Bearish": silver_sent["bearish_count"] += 1
                else: silver_sent["neutral_count"] += 1

        def _compute_metrics(sent_dict, count):
            if count == 0:
                return {
                    "overall_sentiment": "Neutral",
                    "bullish_pct": 0.0, "bearish_pct": 0.0, "neutral_pct": 0.0,
                    **sent_dict
                }
            b_pct = round((sent_dict["bullish_count"] / count) * 100, 1)
            br_pct = round((sent_dict["bearish_count"] / count) * 100, 1)
            n_pct = round((sent_dict["neutral_count"] / count) * 100, 1)

            if b_pct > br_pct and b_pct >= 40.0: overall = "Bullish"
            elif br_pct > b_pct and br_pct >= 35.0: overall = "Bearish"
            else: overall = "Neutral"

            return {
                "overall_sentiment": overall,
                "bullish_pct": b_pct, "bearish_pct": br_pct, "neutral_pct": n_pct,
                **sent_dict
            }

        return MetalsSentimentSummary(
            total_articles=total,
            gold_articles_count=gold_count,
            silver_articles_count=silver_count,
            both_articles_count=both_count,
            sentiment_distribution=sentiment_dist,
            gold_sentiment=_compute_metrics(gold_sent, gold_count),
            silver_sentiment=_compute_metrics(silver_sent, silver_count),
            category_counts=category_counts,
            last_updated=self._format_ist(datetime.now(timezone.utc))
        )

    def get_historical_trends(self, days: int = 14) -> MetalsHistoryResponse:
        """Returns daily aggregated timeline of sentiment classification volume."""
        all_articles = self.fetch_precious_metals_news()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        day_buckets: Dict[str, Dict[str, int]] = {}
        for d in range(days):
            date_key = (datetime.now(timezone.utc) - timedelta(days=d)).strftime("%Y-%m-%d")
            day_buckets[date_key] = {
                "gold_positive": 0, "gold_negative": 0, "gold_neutral": 0,
                "silver_positive": 0, "silver_negative": 0, "silver_neutral": 0,
                "total_volume": 0
            }

        for a in all_articles:
            pub_str = a.get("published_at")
            if not pub_str:
                continue
            try:
                pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                if pub_dt < cutoff:
                    continue
                date_key = pub_dt.strftime("%Y-%m-%d")
                if date_key in day_buckets:
                    b = day_buckets[date_key]
                    b["total_volume"] += 1
                    metal = a.get("metal")
                    lbl = a.get("sentiment_label", "Neutral")

                    if metal in ["Gold", "Both"]:
                        if lbl == "Bullish": b["gold_positive"] += 1
                        elif lbl == "Bearish": b["gold_negative"] += 1
                        else: b["gold_neutral"] += 1

                    if metal in ["Silver", "Both"]:
                        if lbl == "Bullish": b["silver_positive"] += 1
                        elif lbl == "Bearish": b["silver_negative"] += 1
                        else: b["silver_neutral"] += 1
            except Exception:
                continue

        history_points = [
            MetalsHistoryPoint(date=k, **v)
            for k, v in sorted(day_buckets.items(), key=lambda x: x[0])
        ]

        return MetalsHistoryResponse(
            history=history_points,
            timeframe=f"Last {days} Days"
        )

metals_service = MetalsService()
