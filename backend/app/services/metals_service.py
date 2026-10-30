import hashlib
import logging
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import time
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from app.config import settings
from app.database import db
from app.services.finbert_service import finbert_service
from app.models.metals_models import (
    MetalsArticle, MetalsNewsResponse, MetalsPriceQuote,
    IndiaDomesticBenchmark, MetalsPriceCard, MetalsPricesResponse,
    MetalsSentimentSummary, MetalsHistoryPoint, MetalsHistoryResponse
)

logger = logging.getLogger("metals_service")

# Timezone: Asia/Kolkata (IST = UTC+5:30)
try:
    from zoneinfo import ZoneInfo
    IST_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    IST_TZ = timezone(timedelta(hours=5, minutes=30))

class MetalsService:
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
        self._prices_last_fetched: float = 0
        self._price_cache_ttl = 180  # 3 minutes cache for live prices
        self._articles_cache: List[Dict[str, Any]] = []
        self._articles_last_fetched: float = 0
        self._articles_cache_ttl = 300  # 5 minutes cache for news ingestion

    def _format_ist(self, dt: datetime) -> str:
        """Formats a datetime in Asia/Kolkata readable string."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ist_dt = dt.astimezone(IST_TZ)
        return ist_dt.strftime("%d %b %Y, %I:%M %p IST")

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
        # Return memory cache if fresh
        if not force_refresh and self._articles_cache and (now - self._articles_last_fetched < self._articles_cache_ttl):
            return self._articles_cache

        # Try to load existing articles from MongoDB/local DB first
        stored_articles = db.find("metals_articles", limit=200)
        existing_map = {a.get("id"): a for a in stored_articles if a.get("id")}

        new_articles_count = 0
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        for feed_info in self.RSS_FEEDS:
            cat = feed_info["category"]
            feed_url = feed_info["url"]
            try:
                req = urllib.request.Request(feed_url, headers=headers)
                with urllib.request.urlopen(req, timeout=8) as res:
                    xml_data = res.read()
                    root = ET.fromstring(xml_data)
                    items = root.findall(".//item")

                    for item in items:
                        title_el = item.find("title")
                        link_el = item.find("link")
                        pub_date_el = item.find("pubDate")
                        source_el = item.find("source")

                        if title_el is None or not title_el.text:
                            continue

                        raw_title = title_el.text.strip()
                        article_url = link_el.text.strip() if link_el is not None and link_el.text else ""

                        # Extract publisher from title (Google News format: "Title - Publisher")
                        publisher = "Financial Wire"
                        if source_el is not None and source_el.text:
                            publisher = source_el.text.strip()
                        elif " - " in raw_title:
                            parts = raw_title.rsplit(" - ", 1)
                            raw_title = parts[0].strip()
                            publisher = parts[1].strip()

                        # Parse publication date
                        pub_iso = datetime.now(timezone.utc).isoformat()
                        pub_ist = self._format_ist(datetime.now(timezone.utc))
                        if pub_date_el is not None and pub_date_el.text:
                            try:
                                parsed_dt = parsedate_to_datetime(pub_date_el.text.strip())
                                pub_iso = parsed_dt.isoformat()
                                pub_ist = self._format_ist(parsed_dt)
                            except Exception:
                                pass

                        # Deterministic ID based on clean title & publisher
                        art_id = "metal-" + hashlib.sha256(f"{raw_title.lower()}:{publisher.lower()}".encode("utf-8")).hexdigest()[:16]

                        if art_id in existing_map:
                            continue

                        # Classify metal & category
                        metal = self._classify_metal(raw_title)
                        category = self._classify_category(raw_title, cat)

                        # Run FinBERT sentiment analysis on original headline
                        sentiment_data = self._analyze_headline_sentiment(raw_title)

                        article_record = {
                            "id": art_id,
                            "title": raw_title,
                            "summary": f"Precious metals market development covering {metal} in {category}. Source: {publisher}.",
                            "publisher": publisher,
                            "url": article_url,
                            "published_at": pub_iso,
                            "published_at_ist": pub_ist,
                            "metal": metal,
                            "category": category,
                            "sentiment": sentiment_data["sentiment"],
                            "sentiment_label": sentiment_data["sentiment_label"],
                            "scores": sentiment_data["scores"],
                            "confidence": sentiment_data["confidence"],
                            "inference_engine": sentiment_data["inference_engine"],
                            "is_fallback": sentiment_data["is_fallback"],
                            "created_at": datetime.now(timezone.utc).isoformat()
                        }

                        # Save to database
                        db.insert_one("metals_articles", article_record)
                        existing_map[art_id] = article_record
                        new_articles_count += 1

            except Exception as e:
                logger.warning(f"Error fetching metals RSS feed '{cat}': {e}")
                continue

        # Sort all articles by published_at descending
        all_articles = list(existing_map.values())
        all_articles.sort(key=lambda a: a.get("published_at", ""), reverse=True)

        self._articles_cache = all_articles
        self._articles_last_fetched = now
        logger.info(f"Metals news sync complete: {len(all_articles)} total articles, {new_articles_count} newly ingested.")
        return all_articles

    def _analyze_headline_sentiment(self, headline: str) -> Dict[str, Any]:
        """
        Uses existing finbert_service to analyze financial sentiment of precious metals news.
        Distinguishes Positive (Bullish), Negative (Bearish), and Neutral.
        """
        try:
            res = finbert_service.analyze(headline)
            raw_sentiment = res.sentiment.capitalize()  # 'Positive', 'Negative', 'Neutral'
            label_map = {"Positive": "Bullish", "Negative": "Bearish", "Neutral": "Neutral"}

            # Normalise probabilities to percentages
            pos_pct = round(res.scores.get("positive", 0.0) * 100, 1)
            neg_pct = round(res.scores.get("negative", 0.0) * 100, 1)
            neu_pct = round(res.scores.get("neutral", 0.0) * 100, 1)

            confidence = round(res.confidence * 100, 1) if res.confidence <= 1.0 else round(res.confidence, 1)

            return {
                "sentiment": raw_sentiment,
                "sentiment_label": label_map.get(raw_sentiment, raw_sentiment),
                "scores": {
                    "positive": pos_pct,
                    "negative": neg_pct,
                    "neutral": neu_pct
                },
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

    def get_market_prices(self) -> MetalsPricesResponse:
        """
        Retrieves real-time/delayed COMEX Futures prices for Gold and Silver
        and calculates domestic Indian benchmark prices (INR per 10g Gold, INR per 1kg Silver)
        using live USD/INR exchange rates.
        """
        now = time.time()
        if self._cached_prices and (now - self._prices_last_fetched < self._price_cache_ttl):
            return MetalsPricesResponse(**self._cached_prices)

        gold_quote = self._fetch_yahoo_quote("GC=F", "gold")
        silver_quote = self._fetch_yahoo_quote("SI=F", "silver")
        usdinr_rate = self._fetch_usdinr_rate()

        iso_now = datetime.now(timezone.utc).isoformat()
        ist_now = self._format_ist(datetime.now(timezone.utc))

        # 1 troy ounce = 31.1034768 grams
        TROY_OZ_TO_GRAMS = 31.1034768

        # Calculate India Domestic Benchmarks
        # Gold: (USD/oz * USDINR / 31.1035) * 10g * 1.15 (import duty/GST standard parity benchmark)
        gold_price_usd = gold_quote["price"] if gold_quote else 3995.0
        gold_inr_10g = round((gold_price_usd * usdinr_rate / TROY_OZ_TO_GRAMS) * 10.0 * 1.15, -1)

        # Silver: (USD/oz * USDINR / 31.1035) * 1000g (1kg) * 1.15
        silver_price_usd = silver_quote["price"] if silver_quote else 50.8
        silver_inr_1kg = round((silver_price_usd * usdinr_rate / TROY_OZ_TO_GRAMS) * 1000.0 * 1.15, -1)

        gold_intl = MetalsPriceQuote(
            metal="gold",
            symbol="GC=F",
            price=gold_quote["price"] if gold_quote else 3995.0,
            currency="USD",
            unit="troy_oz",
            change=gold_quote.get("change", 0.0) if gold_quote else 0.0,
            change_pct=gold_quote.get("change_pct", 0.0) if gold_quote else 0.0,
            exchange="COMEX",
            timestamp=gold_quote.get("timestamp", iso_now) if gold_quote else iso_now,
            timestamp_ist=gold_quote.get("timestamp_ist", ist_now) if gold_quote else ist_now,
            freshness="delayed" if gold_quote else "unconfigured"
        )

        gold_domestic = IndiaDomesticBenchmark(
            metal="gold",
            price_inr=gold_inr_10g,
            unit="10g",
            usdinr_rate=usdinr_rate,
            timestamp=iso_now,
            timestamp_ist=ist_now,
            basis="COMEX Benchmark + 15% Import/GST Parity"
        )

        silver_intl = MetalsPriceQuote(
            metal="silver",
            symbol="SI=F",
            price=silver_quote["price"] if silver_quote else 50.8,
            currency="USD",
            unit="troy_oz",
            change=silver_quote.get("change", 0.0) if silver_quote else 0.0,
            change_pct=silver_quote.get("change_pct", 0.0) if silver_quote else 0.0,
            exchange="COMEX",
            timestamp=silver_quote.get("timestamp", iso_now) if silver_quote else iso_now,
            timestamp_ist=silver_quote.get("timestamp_ist", ist_now) if silver_quote else ist_now,
            freshness="delayed" if silver_quote else "unconfigured"
        )

        silver_domestic = IndiaDomesticBenchmark(
            metal="silver",
            price_inr=silver_inr_1kg,
            unit="1kg",
            usdinr_rate=usdinr_rate,
            timestamp=iso_now,
            timestamp_ist=ist_now,
            basis="COMEX Benchmark + 15% Import/GST Parity"
        )

        provider_status = "Connected (COMEX Futures / Yahoo Finance Market Feed)"
        if not gold_quote and not silver_quote:
            provider_status = "Provider Unconfigured or Rate Limited — displaying reference benchmark rates"

        result_dict = {
            "gold": {
                "metal": "Gold",
                "international": gold_intl.model_dump(),
                "india_domestic": gold_domestic.model_dump(),
                "status": "active" if gold_quote else "delayed",
                "provider": "COMEX (GC=F) & India MCX Parity Model"
            },
            "silver": {
                "metal": "Silver",
                "international": silver_intl.model_dump(),
                "india_domestic": silver_domestic.model_dump(),
                "status": "active" if silver_quote else "delayed",
                "provider": "COMEX (SI=F) & India MCX Parity Model"
            },
            "last_updated": ist_now,
            "provider_status": provider_status,
            "notes": "International prices quote COMEX Futures in USD per troy ounce. Domestic benchmarks quote INR per 10g (Gold) and 1kg (Silver)."
        }

        self._cached_prices = result_dict
        self._prices_last_fetched = now
        return MetalsPricesResponse(**result_dict)

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
                    "exchange": meta.get("exchangeName", "COMEX"),
                    "timestamp": dt.isoformat(),
                    "timestamp_ist": self._format_ist(dt)
                }
        except Exception as e:
            logger.warning(f"Could not fetch quote for {symbol}: {e}")
            return None

    def _fetch_usdinr_rate(self) -> float:
        """Fetches current USD/INR exchange rate with fallback to standard rate."""
        url = "https://query1.finance.yahoo.com/v8/finance/chart/USDINR=X?interval=1d&range=1d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as res:
                data = json.loads(res.read().decode("utf-8"))
                rate = data["chart"]["result"][0]["meta"].get("regularMarketPrice")
                if rate:
                    return float(rate)
        except Exception:
            pass
        return 95.15  # Fallback current baseline exchange rate

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

        # Filter by cutoff date
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        filtered = []

        search_lower = search.strip().lower() if search else None

        for art in all_articles:
            # Date filter
            pub_str = art.get("published_at")
            if pub_str:
                try:
                    pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                    if pub_dt < cutoff:
                        continue
                except Exception:
                    pass

            # Metal filter: 'Gold', 'Silver', 'Both'
            if metal and metal.lower() != "all":
                art_metal = art.get("metal", "Gold")
                if metal.lower() == "gold" and art_metal not in ["Gold", "Both"]:
                    continue
                if metal.lower() == "silver" and art_metal not in ["Silver", "Both"]:
                    continue

            # Category filter: 'India', 'Global Markets', 'Investment Trends'
            if category and category.lower() != "all":
                if art.get("category", "").lower() != category.lower():
                    continue

            # Search filter
            if search_lower:
                title_match = search_lower in art.get("title", "").lower()
                summary_match = search_lower in (art.get("summary") or "").lower()
                publisher_match = search_lower in art.get("publisher", "").lower()
                if not (title_match or summary_match or publisher_match):
                    continue

            filtered.append(MetalsArticle(**art))

        # Pagination
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
        """Computes comprehensive sentiment metrics and breakdown for Gold & Silver."""
        all_articles = self.fetch_precious_metals_news()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        gold_articles = []
        silver_articles = []
        both_articles = []

        sentiment_dist = {"Bullish": 0, "Bearish": 0, "Neutral": 0}
        category_counts = {"India": 0, "Global Markets": 0, "Investment Trends": 0}

        for a in all_articles:
            pub_str = a.get("published_at")
            if pub_str:
                try:
                    pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                    if pub_dt < cutoff:
                        continue
                except Exception:
                    pass

            metal = a.get("metal", "Gold")
            label = a.get("sentiment_label", "Neutral")
            cat = a.get("category", "Global Markets")

            sentiment_dist[label] = sentiment_dist.get(label, 0) + 1
            category_counts[cat] = category_counts.get(cat, 0) + 1

            if metal == "Gold":
                gold_articles.append(a)
            elif metal == "Silver":
                silver_articles.append(a)
            else:
                both_articles.append(a)
                gold_articles.append(a)
                silver_articles.append(a)

        def compute_breakdown(items: List[Dict[str, Any]]) -> Dict[str, Any]:
            total = len(items)
            if total == 0:
                return {
                    "total": 0,
                    "bullish_count": 0,
                    "bearish_count": 0,
                    "neutral_count": 0,
                    "bullish_pct": 0.0,
                    "bearish_pct": 0.0,
                    "neutral_pct": 0.0,
                    "overall_sentiment": "Neutral"
                }
            bullish = sum(1 for x in items if x.get("sentiment_label") == "Bullish")
            bearish = sum(1 for x in items if x.get("sentiment_label") == "Bearish")
            neutral = total - bullish - bearish

            b_pct = round((bullish / total) * 100, 1)
            bear_pct = round((bearish / total) * 100, 1)
            n_pct = round((neutral / total) * 100, 1)

            if bullish > bearish and bullish > neutral:
                overall = "Bullish"
            elif bearish > bullish and bearish > neutral:
                overall = "Bearish"
            else:
                overall = "Neutral"

            return {
                "total": total,
                "bullish_count": bullish,
                "bearish_count": bearish,
                "neutral_count": neutral,
                "bullish_pct": b_pct,
                "bearish_pct": bear_pct,
                "neutral_pct": n_pct,
                "overall_sentiment": overall
            }

        return MetalsSentimentSummary(
            total_articles=len(all_articles),
            gold_articles_count=len(gold_articles),
            silver_articles_count=len(silver_articles),
            both_articles_count=len(both_articles),
            sentiment_distribution=sentiment_dist,
            gold_sentiment=compute_breakdown(gold_articles),
            silver_sentiment=compute_breakdown(silver_articles),
            category_counts=category_counts,
            last_updated=self._format_ist(datetime.now(timezone.utc))
        )

    def get_historical_trends(self, days: int = 14) -> MetalsHistoryResponse:
        """Aggregates article volume and sentiment distribution per calendar day."""
        all_articles = self.fetch_precious_metals_news()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        daily_buckets: Dict[str, Dict[str, int]] = {}

        # Pre-seed last N days
        for i in range(days, -1, -1):
            d_str = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_buckets[d_str] = {
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
                d_key = pub_dt.strftime("%Y-%m-%d")
            except Exception:
                continue

            if d_key not in daily_buckets:
                daily_buckets[d_key] = {
                    "gold_positive": 0, "gold_negative": 0, "gold_neutral": 0,
                    "silver_positive": 0, "silver_negative": 0, "silver_neutral": 0,
                    "total_volume": 0
                }

            bucket = daily_buckets[d_key]
            bucket["total_volume"] += 1

            metal = a.get("metal", "Gold")
            label = a.get("sentiment_label", "Neutral")

            if metal in ["Gold", "Both"]:
                if label == "Bullish":
                    bucket["gold_positive"] += 1
                elif label == "Bearish":
                    bucket["gold_negative"] += 1
                else:
                    bucket["gold_neutral"] += 1

            if metal in ["Silver", "Both"]:
                if label == "Bullish":
                    bucket["silver_positive"] += 1
                elif label == "Bearish":
                    bucket["silver_negative"] += 1
                else:
                    bucket["silver_neutral"] += 1

        history_points = [
            MetalsHistoryPoint(date=k, **v)
            for k, v in sorted(daily_buckets.items())
        ]

        return MetalsHistoryResponse(
            history=history_points,
            timeframe=f"Last {days} Days"
        )

metals_service = MetalsService()
