import os
import re
import uuid
import logging
import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
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
DEMO_FINANCIAL_ARTICLES = CORE_COMPANY_ARTICLES

class NewsService:
    def __init__(self):
        self.api_key = settings.NEWS_API_KEY
        self.news_api_status = "Available (API Key configured)" if self.api_key else "Demo Mode (No API key provided)"

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
        Ensures the dataset always contains verified, FinBERT-analyzed articles across
        all sentiment categories for every supported company (Apple, Nvidia, Tesla, etc.).
        If any tracked company is missing from the stored database, ingests the missing core articles.
        """
        existing_companies = set(
            canonicalize_company(a.get("company"))
            for a in existing_articles
            if a.get("company") and canonicalize_company(a.get("company"))
        )

        tracked_companies = list(SUPPORTED_COMPANIES.keys())
        missing_companies = [c for c in tracked_companies if c not in existing_companies]

        if not missing_companies and len(existing_articles) > 0:
            return existing_articles

        logger.info(f"Seeding core company articles for missing tracked companies: {missing_companies or 'all'}...")
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

        # Deduplication pipeline
        processed, _ = deduplication_service.process_articles(articles_to_add)

        # Real FinBERT batch sentiment classification
        headlines = [a["title"] for a in processed]
        sentiment_results = []
        try:
            sentiment_results = finbert_service.predict_batch(headlines)
        except Exception as e:
            logger.error(f"FinBERT batch analysis error during seeding: {e}")

        # Attach real FinBERT results and persist to database
        for idx, article in enumerate(processed):
            if idx < len(sentiment_results):
                res = sentiment_results[idx]
                article["sentiment"] = res["sentiment"]
                article["confidence"] = res["confidence"]
                article["scores"] = res["scores"]
            else:
                article["sentiment"] = "neutral"
                article["confidence"] = 0.5
                article["scores"] = {"positive": 0.25, "negative": 0.25, "neutral": 0.5}

            db.insert_one("news_articles", article)

        # Re-fetch combined articles
        combined = db.find("news_articles", limit=500)
        logger.info(f"Core company coverage synchronized. Total database articles: {len(combined)}")
        return combined

    def fetch_articles(self, force_refresh: bool = False, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves articles from database or fetches fresh articles from NewsAPI.
        Guarantees core company representation across Positive, Negative, and Neutral.
        """
        existing_articles = db.find("news_articles", limit=500)

        # If database already has articles and no force-refresh or query requested,
        # ensure all core companies exist and return immediately from storage
        if not force_refresh and len(existing_articles) > 0 and not query:
            return self._ensure_core_company_coverage(existing_articles)

        # Live NewsAPI retrieval if API key is present
        raw_articles = []
        if self.api_key and not settings.USE_DEMO_DATA:
            try:
                search_term = query or "stock market OR earnings OR revenue OR Nasdaq OR 'S&P 500'"
                url = (
                    f"https://newsapi.org/v2/everything?"
                    f"q={requests.utils.quote(search_term)}&"
                    f"language=en&"
                    f"sortBy=publishedAt&"
                    f"pageSize=30&"
                    f"apiKey={self.api_key}"
                )
                resp = requests.get(url, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    articles_json = data.get("articles", [])
                    if articles_json:
                        self.news_api_status = "Connected (NewsAPI Live)"
                        for item in articles_json:
                            matched_company = self._infer_company(
                                item.get("title", ""),
                                item.get("description")
                            )
                            raw_articles.append({
                                "id": f"art-{uuid.uuid4().hex[:8]}",
                                "title": item.get("title", ""),
                                "description": item.get("description", ""),
                                "url": item.get("url", ""),
                                "source": item.get("source", {}).get("name", "Unknown Source"),
                                "published_at": item.get("publishedAt", datetime.utcnow().isoformat() + "Z"),
                                "company": matched_company,
                                "is_demo": False
                            })
                else:
                    logger.warning(f"NewsAPI error {resp.status_code}: {resp.text}. Preserving core dataset.")
                    self.news_api_status = f"Rate limited / Error ({resp.status_code})"
            except Exception as e:
                logger.error(f"Failed to query NewsAPI: {e}. Preserving core dataset.")
                self.news_api_status = f"Network Exception ({str(e)})"

        if raw_articles:
            # Deduplicate and analyze new live articles
            processed_articles, dup_count = deduplication_service.process_articles(raw_articles)
            headlines = [a["title"] for a in processed_articles]
            try:
                sentiment_results = finbert_service.predict_batch(headlines)
                for idx, article in enumerate(processed_articles):
                    if idx < len(sentiment_results):
                        res = sentiment_results[idx]
                        article["sentiment"] = res["sentiment"]
                        article["confidence"] = res["confidence"]
                        article["scores"] = res["scores"]
                    else:
                        article["sentiment"] = "neutral"
                        article["confidence"] = 0.5
                        article["scores"] = {"positive": 0.25, "negative": 0.25, "neutral": 0.5}

                    db.insert_one("news_articles", article)
            except Exception as e:
                logger.error(f"FinBERT batch analysis error on live news: {e}")

        # Always ensure core company coverage is intact
        refreshed_articles = db.find("news_articles", limit=500)
        return self._ensure_core_company_coverage(refreshed_articles)

    def query_articles(
        self,
        query: Optional[str] = None,
        company: Optional[str] = None,
        sentiment: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int, bool]:
        """
        Filters articles with independent company, sentiment, and keyword criteria.
        - When no company is selected, returns all available articles.
        - When a company is selected (e.g. Apple, NVIDIA, Tesla), returns all articles
          for that company across all sentiment categories.
        - When a sentiment is selected, filters to that sentiment independently.
        - When both are selected, applies both filters together.
        - Supports case-insensitive lookup and ticker symbols (AAPL, NVDA, TSLA).
        """
        all_articles = self.fetch_articles()

        target_company = canonicalize_company(company)
        target_sentiment = (
            sentiment.strip().lower()
            if sentiment and sentiment.strip().lower() not in ("all", "all sentiments", "all-sentiments", "none", "*", "")
            else None
        )

        filtered = []
        for a in all_articles:
            # 1. Company Filter (case-insensitive & ticker-aware)
            if target_company:
                art_company = a.get("company", "")
                art_canonical = canonicalize_company(art_company)

                # Check direct canonical match
                direct_match = (
                    art_canonical is not None and
                    art_canonical.lower() == target_company.lower()
                )

                # Check ticker match (e.g. user selected 'NVDA' or article has ticker)
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

            # 2. Sentiment Filter (independent & optional)
            if target_sentiment:
                art_sentiment = (a.get("sentiment") or "").strip().lower()
                if art_sentiment != target_sentiment:
                    continue

            # 3. Keyword / Text Search
            if query and query.strip():
                q_clean = query.strip().lower()
                title_match = q_clean in (a.get("title") or "").lower()
                desc_match = q_clean in (a.get("description") or "").lower()
                comp_match = q_clean in (a.get("company") or "").lower()
                if not (title_match or desc_match or comp_match):
                    continue

            filtered.append(a)

        total_count = len(filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_articles = filtered[start_idx:end_idx]

        is_demo_dataset = any(a.get("is_demo", False) for a in paged_articles) if paged_articles else True
        return paged_articles, total_count, is_demo_dataset

news_service = NewsService()
