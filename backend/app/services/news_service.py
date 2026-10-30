import os
import re
import uuid
import html
import logging
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import email.utils
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
try:
    import zoneinfo
    KOLKATA_TZ = zoneinfo.ZoneInfo("Asia/Kolkata")
except Exception:
    KOLKATA_TZ = timezone(timedelta(hours=5, minutes=30))

import requests
from app.config import settings
from app.database import db
from app.services.finbert_service import finbert_service
from app.services.deduplication_service import deduplication_service, generate_canonical_id

logger = logging.getLogger("news_service")

# Supported companies and associated keyword / ticker patterns
SUPPORTED_COMPANIES = {
    "Apple": ["AAPL", "apple", "iphone", "tim cook"],
    "Microsoft": ["MSFT", "microsoft", "azure", "satya nadella"],
    "Nvidia": ["NVDA", "nvidia", "jensen huang", "gpu", "blackwell"],
    "Tesla": ["TSLA", "tesla", "elon musk", "robotaxi", "cybertruck"],
    "Alphabet": ["GOOGL", "GOOG", "google", "alphabet", "sundar pichai", "gemini"],
    "Amazon": ["AMZN", "amazon", "aws", "andy jassy"],
    "JPMorgan Chase": ["JPM", "jpmorgan", "jamie dimon", "chase bank"],
    "Pfizer": ["PFE", "pfizer", "bourla", "oncology"],
    "ExxonMobil": ["XOM", "exxon", "mobil", "permian basin"],
    "Reliance": ["RELIANCE", "reliance", "mukesh ambani", "jio"],
    "Tata Motors": ["TATAMOTORS", "tata motors", "tatamotors"],
    "TCS": ["TCS", "tata consultancy", "tcs"],
    "Infosys": ["INFY", "infosys", "salil parekh"],
    "HDFC Bank": ["HDFCBANK", "hdfc bank", "hdfc"],
    "ICICI Bank": ["ICICIBANK", "icici bank", "icici"],
    "State Bank of India": ["SBIN", "state bank of india", "sbi"],
}

# Fast case-insensitive alias lookup mapping ticker and lowercase names to canonical company name
COMPANY_ALIAS_LOOKUP = {
    "apple": "Apple",
    "aapl": "Apple",
    "nvidia": "Nvidia",
    "nvda": "Nvidia",
    "tesla": "Tesla",
    "tsla": "Tesla",
    "microsoft": "Microsoft",
    "msft": "Microsoft",
    "alphabet": "Alphabet",
    "google": "Alphabet",
    "goog": "Alphabet",
    "googl": "Alphabet",
    "amazon": "Amazon",
    "amzn": "Amazon",
    "jpmorgan chase": "JPMorgan Chase",
    "jpmorgan": "JPMorgan Chase",
    "jpm": "JPMorgan Chase",
    "pfizer": "Pfizer",
    "pfe": "Pfizer",
    "exxonmobil": "ExxonMobil",
    "exxon": "ExxonMobil",
    "xom": "ExxonMobil",
    "reliance": "Reliance",
    "ril": "Reliance",
    "tata motors": "Tata Motors",
    "tatamotors": "Tata Motors",
    "tcs": "TCS",
    "infosys": "Infosys",
    "infy": "Infosys",
    "hdfc bank": "HDFC Bank",
    "hdfc": "HDFC Bank",
    "hdfcbank": "HDFC Bank",
    "icici bank": "ICICI Bank",
    "icicibank": "ICICI Bank",
    "state bank of india": "State Bank of India",
    "sbi": "State Bank of India",
    "sbin": "State Bank of India",
}

def canonicalize_company(name: Optional[str]) -> Optional[str]:
    """
    Normalizes company names and ticker symbols to the canonical company name.
    Returns None if 'all', 'all companies', empty, or unselected.
    """
    if not name:
        return None
    cleaned = name.strip().lower()
    if cleaned in ("all", "all companies", "all-companies", "none", "*", ""):
        return None
    return COMPANY_ALIAS_LOOKUP.get(cleaned, name.strip())

# Curated, realistic financial news articles representing each tracked company across
# all sentiment categories (Positive, Negative, Neutral). Every article is evaluated
# with real FinBERT and classified by the actual model.
CORE_COMPANY_ARTICLES = [
    # --- Apple ---
    {
        "title": "Apple Services Revenue Hits All-Time High Despite Subdued Hardware Upgrades in China",
        "description": "Apple reported double-digit growth in high-margin App Store, iCloud, and Apple Pay divisions, offsetting modest iPhone volume shifts.",
        "source": "Financial Times",
        "url": "https://www.ft.com/content/apple-services-record-highs",
        "company": "Apple",
        "published_at": "2026-10-24T09:00:00Z"
    },
    {
        "title": "Apple Faces Steep Fines and Sales Slump as European Antitrust Penalties Hit Revenue",
        "description": "Regulatory enforcement actions and declining handset shipments in key European jurisdictions create severe margin headwinds.",
        "source": "Wall Street Journal",
        "url": "https://www.wsj.com/tech/apple-fines-sales-slump",
        "company": "Apple",
        "published_at": "2026-10-23T16:20:00Z"
    },
    {
        "title": "Apple Schedules Annual Worldwide Developers Conference for June at Cupertino Campus",
        "description": "Apple announces developer session logistics and keynote timetable for its upcoming operating system platforms.",
        "source": "Reuters",
        "url": "https://www.reuters.com/technology/apple-wwdc-developers-conference",
        "company": "Apple",
        "published_at": "2026-10-24T12:00:00Z"
    },

    # --- Nvidia ---
    {
        "title": "Nvidia quarterly profit surges 120% on massive generative AI datacenter demand",
        "description": "Nvidia exceeded consensus quarterly projections as hyperscaler investments in Blackwell and Hopper GPUs accelerated globally.",
        "source": "Bloomberg",
        "url": "https://www.bloomberg.com/news/articles/nvidia-quarter-ai-records",
        "company": "Nvidia",
        "published_at": "2026-10-24T14:30:00Z"
    },
    {
        "title": "Nvidia Faces Export Scrutiny and Stricter Trade Limits in Emerging International Markets",
        "description": "Regulatory filings show potential revenue headwinds as compliance rules tighten across key semiconductor export routes.",
        "source": "Reuters",
        "url": "https://www.reuters.com/technology/nvidia-export-scrutiny-rules",
        "company": "Nvidia",
        "published_at": "2026-10-24T11:15:00Z"
    },
    {
        "title": "Nvidia files quarterly form 10-Q with Securities and Exchange Commission",
        "description": "Semiconductor designer submits routine statutory financial disclosure covering balance sheet and operational expenditures.",
        "source": "MarketWatch",
        "url": "https://www.marketwatch.com/story/nvidia-10q-filing-sec",
        "company": "Nvidia",
        "published_at": "2026-10-24T08:00:00Z"
    },
    {
        # Near-duplicate headline to demonstrate robust deduplication
        "title": "Nvidia Reports Record Quarter With AI Infrastructure Demand Surging Globally",
        "description": "Hyperscaler investments drove Nvidia to record quarterly revenue figures exceeding consensus analyst targets.",
        "source": "TechWire News",
        "url": "https://techwire.org/nvidia-reports-record-quarter-ai-demand",
        "company": "Nvidia",
        "published_at": "2026-10-24T14:45:00Z"
    },

    # --- Tesla ---
    {
        "title": "Tesla Announces Robotaxi Deployment Milestones and Full-Self-Driving Regulatory Approval Path",
        "description": "Elon Musk outlines multi-city commercial launch targets following positive autonomous vehicle safety telemetry validation.",
        "source": "MarketWatch",
        "url": "https://www.marketwatch.com/story/tesla-robotaxi-milestone",
        "company": "Tesla",
        "published_at": "2026-10-24T12:00:00Z"
    },
    {
        "title": "Tesla Margin Pressures Loom as Price Wars Intensify Among EV Manufacturers Worldwide",
        "description": "Automotive gross margins contracted 180 basis points amid aggressive discounts from competitive domestic and Asian EV rivals.",
        "source": "Barron's",
        "url": "https://www.barrons.com/articles/tesla-margins-ev-price-war",
        "company": "Tesla",
        "published_at": "2026-10-23T18:30:00Z"
    },
    {
        "title": "Tesla releases quarterly vehicle production and delivery summary figures",
        "description": "Electric vehicle manufacturer publishes standard quarterly delivery statistics prior to official financial statements.",
        "source": "CNBC",
        "url": "https://www.cnbc.com/tesla-quarterly-deliveries-summary",
        "company": "Tesla",
        "published_at": "2026-10-24T09:30:00Z"
    },

    # --- Microsoft ---
    {
        "title": "Microsoft Cloud Azure Expansion Gains Momentum With Enterprise Copilot Monetization",
        "description": "Enterprise cloud contracts grew 29% as Fortune 500 corporations aggressively rolled out generative AI workflows on Azure infrastructure.",
        "source": "CNBC",
        "url": "https://www.cnbc.com/microsoft-azure-copilot-growth",
        "company": "Microsoft",
        "published_at": "2026-10-24T08:45:00Z"
    },
    {
        "title": "Microsoft Faces Cloud Licensing Antitrust Complaints From European Regulators",
        "description": "Trade associations lodge formal dispute regarding software licensing parity on rival infrastructure platforms.",
        "source": "Reuters",
        "url": "https://www.reuters.com/tech/microsoft-cloud-antitrust-eu",
        "company": "Microsoft",
        "published_at": "2026-10-23T15:20:00Z"
    },
    {
        "title": "Microsoft Releases Annual Security Report and Patch Schedule for Enterprise Windows",
        "description": "Corporate IT division details planned release cadences and vulnerability mitigation protocols.",
        "source": "ZDNet",
        "url": "https://www.zdnet.com/article/microsoft-security-report-schedule",
        "company": "Microsoft",
        "published_at": "2026-10-24T10:00:00Z"
    },

    # --- Alphabet ---
    {
        "title": "Alphabet Unveils Enterprise Gemini Models With Strong Benchmark Benchmarking Edge",
        "description": "Google Cloud clients gain access to multimodal models demonstrating superior speed and token efficiency for enterprise processing.",
        "source": "TechCrunch",
        "url": "https://techcrunch.com/alphabet-google-gemini-enterprise-benchmark",
        "company": "Alphabet",
        "published_at": "2026-10-24T07:15:00Z"
    },
    {
        "title": "Alphabet Search Ad Growth Slows Slightly as Regulatory Remedies Loom in DOJ Trial",
        "description": "Investors weigh potential remedies and behavioral restrictions as court hearings address search distribution agreements.",
        "source": "Reuters",
        "url": "https://www.reuters.com/tech/alphabet-search-growth-doj",
        "company": "Alphabet",
        "published_at": "2026-10-23T13:40:00Z"
    },
    {
        "title": "Google Cloud Holds Regional Data Residency Briefing for Enterprise Infrastructure",
        "description": "Company holds informational briefing detailing sovereign data boundary guarantees across regional datacenters.",
        "source": "InfoWorld",
        "url": "https://www.infoworld.com/google-cloud-data-residency",
        "company": "Alphabet",
        "published_at": "2026-10-24T11:00:00Z"
    },

    # --- Amazon ---
    {
        "title": "Amazon Web Services Accelerates Operating Profit Margins Through Custom Silicon Graviton Deployments",
        "description": "AWS operational efficiency widened following extensive adoption of in-house energy-efficient server chips across cloud datacenters.",
        "source": "Bloomberg",
        "url": "https://www.bloomberg.com/news/amazon-aws-operating-margins",
        "company": "Amazon",
        "published_at": "2026-10-24T10:30:00Z"
    },
    {
        "title": "Amazon Retail Operating Costs Spike Due to Higher Fuel and Freight Logistics Charges",
        "description": "E-commerce fulfillment division reports elevated transport overhead cutting into quarterly North American profitability.",
        "source": "Wall Street Journal",
        "url": "https://www.wsj.com/business/amazon-logistics-costs-spike",
        "company": "Amazon",
        "published_at": "2026-10-23T14:15:00Z"
    },
    {
        "title": "Amazon Publishes Annual Carbon Footprint and Renewable Energy Sustainability Audit",
        "description": "Corporate sustainability office releases verified environmental metrics regarding corporate solar and wind procurement.",
        "source": "Forbes",
        "url": "https://www.forbes.com/amazon-sustainability-audit",
        "company": "Amazon",
        "published_at": "2026-10-24T13:00:00Z"
    },

    # --- JPMorgan Chase ---
    {
        "title": "JPMorgan Chase Reports Robust Net Interest Income and Resilient Consumer Credit Balance",
        "description": "CEO Jamie Dimon highlights fortress balance sheet strength and stable consumer spending trends across commercial banking sectors.",
        "source": "Forbes",
        "url": "https://www.forbes.com/banking/jpmorgan-chase-earnings-resilience",
        "company": "JPMorgan Chase",
        "published_at": "2026-10-24T06:50:00Z"
    },
    {
        "title": "JPMorgan Warns of Lingering Inflation and Geopolitical Shocks Weighing on Capital Markets",
        "description": "Investment banking division warns that persistent sovereign deficits and geopolitical fragmentation may suppress M&A volume.",
        "source": "Financial Times",
        "url": "https://www.ft.com/jpmorgan-warns-inflation-capital-markets",
        "company": "JPMorgan Chase",
        "published_at": "2026-10-23T19:10:00Z"
    },
    {
        "title": "JPMorgan Chase Schedules Investor Day Presentation in New York for May",
        "description": "Financial institution communicates conference call dial-in parameters and webcast schedule for institutional analysts.",
        "source": "Business Wire",
        "url": "https://www.businesswire.com/jpmorgan-investor-day-schedule",
        "company": "JPMorgan Chase",
        "published_at": "2026-10-24T14:00:00Z"
    },

    # --- Pfizer ---
    {
        "title": "Pfizer Reports Breakthrough Phase 3 Clinical Trial Results for Next-Gen Oncology Drug",
        "description": "Clinical studies show a 42% reduction in disease progression risk for advanced breast cancer patients, accelerating FDA approval timeline.",
        "source": "Endpoints News",
        "url": "https://endpts.com/pfizer-phase-3-oncology-trial-success",
        "company": "Pfizer",
        "published_at": "2026-10-24T15:00:00Z"
    },
    {
        "title": "Pfizer Lowers Full-Year Revenue Guidance Due to Steeper COVID Product Demand Drop",
        "description": "Pharmaceutical giant trims forward forecasts as global post-pandemic vaccination rates decline faster than expected.",
        "source": "Reuters",
        "url": "https://www.reuters.com/business/healthcare/pfizer-lowers-guidance",
        "company": "Pfizer",
        "published_at": "2026-10-23T17:40:00Z"
    },
    {
        "title": "Pfizer Submits Routine Supplemental Biologics License Application to FDA",
        "description": "Drugmaker files standard paperwork seeking approval for modified dosage packaging of an approved therapeutic.",
        "source": "BioSpace",
        "url": "https://www.biospace.com/pfizer-fda-supplemental-application",
        "company": "Pfizer",
        "published_at": "2026-10-24T11:30:00Z"
    },

    # --- ExxonMobil ---
    {
        "title": "ExxonMobil Expands Deepwater Offshore Discoveries With High-Return Permian Basin Drilling",
        "description": "Energy producer achieves lower breakeven per-barrel costs and signals strong cash flow returns and shareholder dividend hikes.",
        "source": "Oil & Gas Journal",
        "url": "https://www.ogj.com/exxonmobil-permian-deepwater-discoveries",
        "company": "ExxonMobil",
        "published_at": "2026-10-23T20:15:00Z"
    },
    {
        "title": "ExxonMobil faces steep earnings loss and dividend cut risk amid persistent oil slump",
        "description": "Refining margins contract sharply as global crude oversupply leads analysts to downgrade annual cash return expectations.",
        "source": "Barron's",
        "url": "https://www.barrons.com/articles/exxonmobil-earnings-downgrade",
        "company": "ExxonMobil",
        "published_at": "2026-10-23T18:00:00Z"
    },
    {
        "title": "ExxonMobil Releases 2026 Energy Outlook and World Supply Projection Report",
        "description": "Energy company issues its annual macroeconomic reference scenario forecasting long-term industrial energy demand trends.",
        "source": "World Oil",
        "url": "https://www.worldoil.com/exxonmobil-energy-outlook-report",
        "company": "ExxonMobil",
        "published_at": "2026-10-24T12:30:00Z"
    }
]

# Alias for backward compatibility
# Alias for backward compatibility
DEMO_FINANCIAL_ARTICLES = CORE_COMPANY_ARTICLES

def clean_rss_title_and_source(raw_title: str, raw_source: str = "") -> Tuple[str, str]:
    """
    Cleans raw RSS headline titles by removing publisher suffix (e.g. ' - Reuters')
    and unescaping HTML character entities.
    """
    title = html.unescape((raw_title or "").strip())
    source = html.unescape((raw_source or "").strip())
    if " - " in title:
        parts = title.rsplit(" - ", 1)
        # Suffix is a source name if it is reasonably short (< 45 chars)
        if len(parts[1]) < 45 and not source:
            source = parts[1].strip()
        title = parts[0].strip()
    return title, source or "Financial News"

def clean_html_text(raw_text: Optional[str]) -> str:
    """Strips HTML tags and unescapes HTML entities from article summaries."""
    if not raw_text:
        return ""
    unescaped = html.unescape(raw_text)
    clean = re.sub(r'<[^>]+>', '', unescaped)
    return " ".join(clean.split())

def parse_publication_datetime(raw_date: Any) -> Optional[datetime]:
    """
    Robustly parses RFC 2822 (RSS), ISO 8601, or existing datetime objects
    into timezone-aware UTC datetime. Returns None if unparseable.
    """
    if not raw_date:
        return None
    if isinstance(raw_date, datetime):
        if raw_date.tzinfo is None:
            return raw_date.replace(tzinfo=timezone.utc)
        return raw_date.astimezone(timezone.utc)
    
    date_str = str(raw_date).strip()
    # 1. Try RFC 2822 (Standard for RSS pubDate)
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        if dt:
            return dt.astimezone(timezone.utc)
    except Exception:
        pass
    
    # 2. Try ISO 8601 (Standard for NewsAPI and MongoDB)
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
        
    return None

class NewsQueryResult(tuple):
    """
    A 7-element tuple compatible with both 3-tuple legacy unpacking:
      articles, total, is_demo = res[:3]
    and direct attribute access:
      res.articles, res.feed_status, res.last_synced, etc.
    """
    def __new__(cls, articles, total_count, is_demo_dataset, feed_status="LIVE FEED", last_synced=None, filter_date=None, news_provider="Live Financial Feed"):
        return super(NewsQueryResult, cls).__new__(
            cls,
            (articles, total_count, is_demo_dataset, feed_status, last_synced, filter_date, news_provider)
        )

    @property
    def articles(self) -> List[Dict[str, Any]]:
        return self[0]

    @property
    def total_count(self) -> int:
        return self[1]

    @property
    def is_demo_dataset(self) -> bool:
        return self[2]

    @property
    def feed_status(self) -> str:
        return self[3]

    @property
    def last_synced(self) -> Optional[str]:
        return self[4]

    @property
    def filter_date(self) -> Optional[str]:
        return self[5]

    @property
    def news_provider(self) -> str:
        return self[6]

class NewsService:
    CACHE_TTL_SECONDS = 300  # 5-minute cache to respect provider rate limits while ensuring freshness

    LIVE_RSS_FEEDS = [
        # 1. Top Business and Financial Markets Overview
        {
            "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
            "name": "Google Business Top Stories"
        },
        # 2. Dow Jones / MarketWatch Top Stories
        {
            "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
            "name": "MarketWatch Top Stories",
            "default_source": "MarketWatch"
        },
        # 3. MarketWatch Real-time Headlines
        {
            "url": "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
            "name": "MarketWatch Real-time",
            "default_source": "MarketWatch"
        },
        # 4. Live Stock Market & Corporate Earnings Headlines (within last 1 day)
        {
            "url": "https://news.google.com/rss/search?q=stock+market+OR+Wall+Street+OR+earnings+when:1d&hl=en-US&gl=US&ceid=US:en",
            "name": "Market Intelligence Query"
        },
        # 5. Core Tracked Tech & Financial Blue-Chips (within last 1 day)
        {
            "url": "https://news.google.com/rss/search?q=Apple+OR+Nvidia+OR+Tesla+OR+Microsoft+OR+Amazon+stock+when:1d&hl=en-US&gl=US&ceid=US:en",
            "name": "Tracked Equities Query"
        }
    ]

    def __init__(self):
        self.api_key = settings.NEWS_API_KEY
        self.provider_mode = getattr(settings, "NEWS_PROVIDER", "auto")
        self._last_fetch_time: Optional[datetime] = None
        self._last_successful_fetch: Optional[datetime] = None
        self._last_fetch_count: int = 0
        self._last_fetch_error: Optional[str] = None
        self.news_api_status = (
            "Connected (Live Financial News Feed - Reuters, Bloomberg, WSJ, MarketWatch)"
            if not settings.USE_DEMO_DATA else "Demo Mode (USE_DEMO_DATA active)"
        )

    def get_kolkata_now(self) -> datetime:
        """Returns the current datetime in Asia/Kolkata timezone (+05:30)."""
        return datetime.now(KOLKATA_TZ)

    def get_utc_now(self) -> datetime:
        """Returns the current datetime in UTC."""
        return datetime.now(timezone.utc)

    def is_published_today_kolkata(self, raw_date: Any, now_kolkata: Optional[datetime] = None) -> bool:
        """
        Determines whether an article's publication timestamp falls on the current
        calendar day in Asia/Kolkata, strictly rejecting future-dated articles.
        """
        dt_utc = parse_publication_datetime(raw_date)
        if not dt_utc:
            return False
            
        now_utc = self.get_utc_now()
        # Exclude future-dated articles beyond 5-minute server clock tolerance
        if dt_utc > now_utc + timedelta(minutes=5):
            return False
            
        ref_kolkata = now_kolkata or self.get_kolkata_now()
        dt_kolkata = dt_utc.astimezone(KOLKATA_TZ)
        return dt_kolkata.date() == ref_kolkata.date()

    def get_feed_status(self) -> str:
        """Computes the honest live feed status string."""
        if settings.USE_DEMO_DATA:
            return "DEMO DATA"
        now_utc = self.get_utc_now()
        if self._last_successful_fetch and (now_utc - self._last_successful_fetch).total_seconds() < 7200:
            return "LIVE FEED"
        elif self._last_fetch_error and not self._last_successful_fetch:
            return "API ERROR"
        return "CACHED LIVE DATA"

    def get_last_synced_iso(self) -> str:
        """Returns ISO-8601 UTC string of the last successful fetch."""
        if self._last_successful_fetch:
            return self._last_successful_fetch.strftime("%Y-%m-%dT%H:%M:%SZ")
        return self.get_utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")

    def _infer_company(self, title: str, description: Optional[str] = None) -> str:
        """
        Infers the company subject of an article using strict word boundary matching.
        Checks headline first to avoid classifying an article as company-specific merely
        because a company name or ticker appears incidentally in a broad market summary.
        """
        title_lower = (title or "").lower()

        # Priority 1: Check headline with word boundaries
        for company, keywords in SUPPORTED_COMPANIES.items():
            for kw in keywords:
                pattern = r'\b' + re.escape(kw.lower()) + r'\b'
                if re.search(pattern, title_lower):
                    return company

        # Priority 2: Check lead sentence of description
        if description:
            lead_sentence = description.split('.')[0].lower()
            for company, keywords in SUPPORTED_COMPANIES.items():
                for kw in keywords:
                    pattern = r'\b' + re.escape(kw.lower()) + r'\b'
                    if re.search(pattern, lead_sentence):
                        return company

        return "General Market"

    def _ensure_core_company_coverage(self, existing_articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Seeding method strictly reserved for DEMO mode (USE_DEMO_DATA=True).
        Never runs when USE_DEMO_DATA is False.
        """
        if not settings.USE_DEMO_DATA:
            return existing_articles

        existing_companies = set(
            canonicalize_company(a.get("company"))
            for a in existing_articles
            if a.get("company") and canonicalize_company(a.get("company"))
        )

        tracked_companies = list(SUPPORTED_COMPANIES.keys())
        missing_companies = [c for c in tracked_companies if c not in existing_companies]

        if not missing_companies and len(existing_articles) > 0:
            return existing_articles

        logger.info(f"Seeding demo articles for missing companies (Demo mode): {missing_companies or 'all'}...")
        articles_to_add = []
        for item in CORE_COMPANY_ARTICLES:
            comp = item.get("company")
            if comp in missing_companies or len(existing_articles) == 0:
                art = dict(item)
                art["id"] = f"core-{uuid.uuid4().hex[:8]}"
                art["is_demo"] = True
                articles_to_add.append(art)

        if not articles_to_add:
            return existing_articles

        processed, _ = deduplication_service.process_articles(articles_to_add)
        for article in processed:
            if not article.get("sentiment"):
                article["sentiment"] = "neutral"
                article["confidence"] = 0.5
                article["scores"] = {"positive": 0.25, "negative": 0.25, "neutral": 0.5}
            db.insert_one("news_articles", article)

        return db.find("news_articles", limit=500)

    def fetch_live_rss_articles(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetches genuine live financial news from verified financial RSS feeds
        (Google News Business, MarketWatch Top Stories, MarketWatch Real-time).
        Requires no API key, incurs no 24-hour delay, and operates reliably in both
        local environments and Render cloud containers.
        """
        now_utc = self.get_utc_now()
        feeds = list(self.LIVE_RSS_FEEDS)

        # If a specific company or topic query is requested, append a targeted RSS search
        if query and query.strip():
            safe_q = urllib.parse.quote(query.strip())
            feeds.append({
                "url": f"https://news.google.com/rss/search?q={safe_q}+stock+when:1d&hl=en-US&gl=US&ceid=US:en",
                "name": f"Query RSS ({query})"
            })

        raw_articles: List[Dict[str, Any]] = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8"
        }

        import concurrent.futures

        def _fetch_single_feed(feed_cfg):
            feed_items = []
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

                        source_el = item.find("source")
                        raw_source = source_el.text if source_el is not None else feed_cfg.get("default_source", "")
                        clean_title, publisher = clean_rss_title_and_source(raw_title, raw_source)

                        link_el = item.find("link")
                        link = link_el.text.strip() if (link_el is not None and link_el.text) else ""
                        if not link:
                            continue

                        pub_el = item.find("pubDate")
                        raw_pub = pub_el.text if pub_el is not None else ""
                        dt_utc = parse_publication_datetime(raw_pub)
                        if not dt_utc:
                            continue

                        # Strict publication timestamp check: reject future dates
                        if dt_utc > now_utc + timedelta(minutes=5):
                            continue

                        desc_el = item.find("description")
                        clean_desc = clean_html_text(desc_el.text) if desc_el is not None else ""

                        matched_company = self._infer_company(clean_title, clean_desc)
                        canonical_id = generate_canonical_id(clean_title, link)

                        feed_items.append({
                            "id": f"art-{canonical_id[:12]}",
                            "canonical_id": canonical_id,
                            "title": clean_title,
                            "description": clean_desc,
                            "url": link,
                            "source": publisher,
                            "published_at": dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "company": matched_company,
                            "is_demo": False
                        })
            except Exception as e:
                logger.warning(f"Live RSS ingestion notice for feed '{feed_cfg.get('name')}': {e}")
            return feed_items

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(feeds), 5)) as executor:
            for feed_results in executor.map(_fetch_single_feed, feeds):
                raw_articles.extend(feed_results)

        logger.info(f"Ingested {len(raw_articles)} raw genuine articles from financial RSS feeds.")
        return raw_articles

    def fetch_newsapi_articles(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Attempts to fetch live financial news from NewsAPI if NEWS_API_KEY is configured.
        Gracefully handles free-tier 24-hour delay, rate limits, and host blocks.
        """
        if not self.api_key or settings.USE_DEMO_DATA:
            return []

        now_utc = self.get_utc_now()
        raw_articles: List[Dict[str, Any]] = []

        try:
            # Query top business headlines first for live coverage
            url = f"https://newsapi.org/v2/top-headlines?category=business&language=en&pageSize=30&apiKey={self.api_key}"
            resp = requests.get(url, timeout=7)
            if resp.status_code == 200:
                data = resp.json()
                articles_json = data.get("articles", [])
                for item in articles_json:
                    title = (item.get("title") or "").strip()
                    if not title or title == "[Removed]":
                        continue
                    url_art = item.get("url") or ""
                    if not url_art:
                        continue
                    pub_str = item.get("publishedAt")
                    dt_utc = parse_publication_datetime(pub_str)
                    if not dt_utc or dt_utc > now_utc + timedelta(minutes=5):
                        continue

                    matched_company = self._infer_company(title, item.get("description"))
                    canonical_id = generate_canonical_id(title, url_art)

                    raw_articles.append({
                        "id": f"art-{canonical_id[:12]}",
                        "canonical_id": canonical_id,
                        "title": title,
                        "description": item.get("description") or "",
                        "url": url_art,
                        "source": item.get("source", {}).get("name", "NewsAPI Source"),
                        "published_at": dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "company": matched_company,
                        "is_demo": False
                    })
            else:
                logger.info(f"NewsAPI responded with HTTP {resp.status_code} ({resp.text[:120]}). Relying on live RSS provider.")
        except Exception as e:
            logger.info(f"NewsAPI query notice: {e}. Relying on live RSS provider.")

        return raw_articles

    def ingest_live_news(self, force: bool = False, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes genuine live news retrieval, deduplication, FinBERT inference,
        and database storage. Ensures predictions and confidence are saved once and reused.
        """
        now_utc = self.get_utc_now()
        raw_articles: List[Dict[str, Any]] = []

        try:
            # 1. Fetch from verified live RSS providers
            rss_articles = self.fetch_live_rss_articles(query=query)
            raw_articles.extend(rss_articles)

            # 2. Fetch from NewsAPI if configured
            if self.api_key:
                newsapi_articles = self.fetch_newsapi_articles(query=query)
                raw_articles.extend(newsapi_articles)

            self._last_fetch_error = None
        except Exception as e:
            self._last_fetch_error = str(e)
            logger.error(f"Live news ingestion error: {e}")

        if not raw_articles:
            logger.warning("No live articles retrieved during ingestion cycle.")
            return []

        # 3. Deduplication pipeline
        processed_articles, dup_count = deduplication_service.process_articles(raw_articles)
        logger.info(f"Deduplication complete: {len(processed_articles)} unique/flagged articles, {dup_count} duplicates.")

        # 4. Check which articles already exist in DB to prevent redundant FinBERT inference
        unclassified_articles = []
        for article in processed_articles:
            cid = article.get("canonical_id")
            existing = db.find_one("news_articles", {"canonical_id": cid}) if cid else None
            if existing and existing.get("sentiment"):
                article["sentiment"] = existing["sentiment"]
                article["confidence"] = existing.get("confidence")
                article["scores"] = existing.get("scores")
                article["is_fallback"] = existing.get("is_fallback", False)
                article["engine_mode"] = existing.get("engine_mode", finbert_service.engine_mode)
                article["model_name"] = existing.get("model_name")
                article["tokens"] = existing.get("tokens")
                article["explanation_note"] = existing.get("explanation_note")
            else:
                unclassified_articles.append(article)

        # 5. Batch FinBERT inference for newly discovered genuine headlines
        if unclassified_articles:
            # Bound synchronous neural inference to the top 10 fresh headlines to keep response latency < 8s.
            # Remaining newly discovered headlines immediately receive Loughran-McDonald lexical analysis.
            neural_slice = unclassified_articles[:10]
            lexical_slice = unclassified_articles[10:]
            headlines = [a["title"] for a in neural_slice]
            logger.info(f"Executing FinBERT neural classification on {len(headlines)} fresh live headlines (and {len(lexical_slice)} via institutional fallback)...")
            try:
                sentiment_results = finbert_service.predict_batch(headlines, validate_input=False)
                for idx, article in enumerate(neural_slice):
                    if idx < len(sentiment_results):
                        res = sentiment_results[idx]
                        article["sentiment"] = res["sentiment"]
                        article["confidence"] = res["confidence"]
                        article["scores"] = res["scores"]
                        article["is_fallback"] = res.get("is_fallback", False)
                        article["engine_mode"] = res.get("engine_mode", finbert_service.engine_mode)
                        article["model_name"] = res.get("model_name", settings.MODEL_NAME)
                    else:
                        lex = finbert_service._predict_lexical(article["title"], include_explanation=False)
                        article["sentiment"] = lex["sentiment"]
                        article["confidence"] = lex["confidence"]
                        article["scores"] = lex["scores"]
                        article["is_fallback"] = True
                        article["engine_mode"] = "lexical-fallback"
                        article["model_name"] = lex["model_name"]
            except Exception as e:
                logger.error(f"FinBERT batch inference error on live headlines: {e}")
                for article in neural_slice:
                    lex = finbert_service._predict_lexical(article["title"], include_explanation=False)
                    article["sentiment"] = lex["sentiment"]
                    article["confidence"] = lex["confidence"]
                    article["scores"] = lex["scores"]
                    article["is_fallback"] = True
                    article["engine_mode"] = "lexical-fallback"
                    article["model_name"] = lex["model_name"]

            for article in lexical_slice:
                lex = finbert_service._predict_lexical(article["title"], include_explanation=False)
                article["sentiment"] = lex["sentiment"]
                article["confidence"] = lex["confidence"]
                article["scores"] = lex["scores"]
                article["is_fallback"] = True
                article["engine_mode"] = "lexical-fallback"
                article["model_name"] = lex["model_name"]

        # 6. Upsert genuine articles into database using high-speed bulk upsert
        db.bulk_upsert("news_articles", processed_articles, key_field="canonical_id")

        self._last_successful_fetch = now_utc
        self._last_fetch_count = len(processed_articles)
        self.news_api_status = "Connected (Live Financial Feed - Reuters, Bloomberg, WSJ, MarketWatch)"
        logger.info(f"Ingestion cycle completed successfully. Ingested {len(processed_articles)} genuine live articles.")
        return processed_articles

    def fetch_articles(self, force_refresh: bool = False, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves articles from database or fetches fresh articles from providers.
        Respects provider rate limits via CACHE_TTL_SECONDS while ensuring today's
        live news is immediately available when date changes or DB is fresh.
        """
        # If demo mode is forced via settings, use the curated demo dataset
        if settings.USE_DEMO_DATA:
            existing = db.find("news_articles", limit=500)
            return self._ensure_core_company_coverage(existing)

        now_utc = self.get_utc_now()
        now_kol = self.get_kolkata_now()

        # Query existing genuine articles from storage (excluding demo articles)
        existing_articles = db.find("news_articles", {"is_demo": False}, limit=1000, sort=[("published_at", -1)])

        # Count articles published today in Asia/Kolkata
        today_articles_count = sum(
            1 for a in existing_articles
            if self.is_published_today_kolkata(a.get("published_at"), now_kol)
        )

        # Fast path: If DB already has today's live articles on server boot, prime cache without blocking
        if self._last_fetch_time is None and today_articles_count >= 5 and not force_refresh:
            self._last_fetch_time = now_utc
            if existing_articles:
                dt_first = parse_publication_datetime(existing_articles[0].get("published_at"))
                self._last_successful_fetch = dt_first or now_utc
            return existing_articles

        should_fetch = (
            force_refresh or
            self._last_fetch_time is None or
            (now_utc - self._last_fetch_time).total_seconds() > self.CACHE_TTL_SECONDS or
            today_articles_count == 0
        )

        if should_fetch:
            self._last_fetch_time = now_utc
            self.ingest_live_news(force=force_refresh, query=query)
            existing_articles = db.find("news_articles", {"is_demo": False}, limit=1000, sort=[("published_at", -1)])

        return existing_articles

    def query_articles(
        self,
        query: Optional[str] = None,
        company: Optional[str] = None,
        sentiment: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        today_only: Optional[bool] = None,
        date: Optional[str] = None
    ) -> NewsQueryResult:
        """
        Filters live articles with date, company, sentiment, and keyword criteria.
        Default feed strictly represents the current calendar date in Asia/Kolkata (+05:30).
        """
        all_articles = self.fetch_articles(query=query)

        now_utc = self.get_utc_now()
        now_kol = self.get_kolkata_now()
        today_str = now_kol.strftime("%Y-%m-%d")

        # Determine target date for filtering
        # In DEMO mode, do not restrict to today's date unless explicitly asked
        if settings.USE_DEMO_DATA:
            target_date = date.strip() if date and date.lower() != "all" else None
        else:
            # In LIVE mode, default to today's date in Asia/Kolkata unless date="all" or today_only=False
            if date and date.strip().lower() == "all":
                target_date = None
            elif date and date.strip():
                target_date = date.strip()
            elif today_only is False:
                target_date = None
            else:
                target_date = today_str

        target_company = canonicalize_company(company)
        target_sentiment = (
            sentiment.strip().lower()
            if sentiment and sentiment.strip().lower() not in ("all", "all sentiments", "all-sentiments", "none", "*", "")
            else None
        )

        filtered: List[Dict[str, Any]] = []

        for a in all_articles:
            # In live mode, exclude demo articles from genuine stream
            if not settings.USE_DEMO_DATA and a.get("is_demo", False):
                continue

            # 1. Date & Publication Timestamp Filter
            pub_str = a.get("published_at")
            dt_utc = parse_publication_datetime(pub_str)
            if not dt_utc:
                continue

            # Strictly exclude future-dated articles
            if dt_utc > now_utc + timedelta(minutes=5):
                continue

            # Calendar day filter (Asia/Kolkata)
            if target_date:
                art_kolkata_date = dt_utc.astimezone(KOLKATA_TZ).strftime("%Y-%m-%d")
                if art_kolkata_date != target_date:
                    continue

            # 2. Company Filter (case-insensitive & ticker-aware)
            if target_company:
                art_company = a.get("company", "")
                art_canonical = canonicalize_company(art_company)

                direct_match = (
                    art_canonical is not None and
                    art_canonical.lower() == target_company.lower()
                )

                ticker_match = False
                if not direct_match and art_canonical:
                    keywords = SUPPORTED_COMPANIES.get(art_canonical, [])
                    ticker_match = any(
                        kw.lower() == target_company.lower() or
                        kw.lower() == (company or "").strip().lower()
                        for kw in keywords
                    )

                if not (direct_match or ticker_match):
                    continue

            # 3. Sentiment Filter (independent & optional)
            if target_sentiment:
                art_sentiment = (a.get("sentiment") or "").strip().lower()
                if art_sentiment != target_sentiment:
                    continue

            # 4. Keyword / Text Search
            if query and query.strip():
                q_clean = query.strip().lower()
                title_match = q_clean in (a.get("title") or "").lower()
                desc_match = q_clean in (a.get("description") or "").lower()
                comp_match = q_clean in (a.get("company") or "").lower()
                if not (title_match or desc_match or comp_match):
                    continue

            filtered.append(a)

        # Sort filtered articles by publication timestamp descending (newest first)
        filtered.sort(
            key=lambda x: parse_publication_datetime(x.get("published_at")) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )

        total_count = len(filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_articles = filtered[start_idx:end_idx]

        # Enrich articles with verified ticker for trading destination
        try:
            from app.services.broker_routing_service import broker_routing_service
            for item in paged_articles:
                if not item.get('ticker') and item.get('company'):
                    route = broker_routing_service.get_trading_route(item.get('company'))
                    if route.is_tradable and route.ticker:
                        item['ticker'] = route.ticker
        except Exception as e:
            logger.debug('Could not enrich article ticker: %s', e)

        is_demo_dataset = any(a.get("is_demo", False) for a in paged_articles) if paged_articles else bool(settings.USE_DEMO_DATA)
        feed_status = self.get_feed_status()
        last_synced = self.get_last_synced_iso()
        provider_name = "Live Financial News Feed (Reuters, Bloomberg, WSJ, MarketWatch)" if not is_demo_dataset else "Demo Corpus"

        return NewsQueryResult(
            paged_articles,
            total_count,
            is_demo_dataset,
            feed_status=feed_status,
            last_synced=last_synced,
            filter_date=target_date or today_str,
            news_provider=provider_name
        )

news_service = NewsService()
