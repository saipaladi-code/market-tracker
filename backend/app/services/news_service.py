import os
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

# Realistic curated demo articles for college presentation & testing without live keys
DEMO_FINANCIAL_ARTICLES = [
    {
        "title": "Nvidia Reports Record Quarter as AI Infrastructure Demand Accelerates Globally",
        "description": "Nvidia exceeded Wall Street quarterly revenue estimates driven by soaring hyperscaler spending on next-generation Blackwell and Hopper AI GPUs.",
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
        "title": "Apple Services Revenue Hits All-Time High Despite Subdued Hardware Upgrades in China",
        "description": "Apple reported double-digit growth in its high-margin App Store, iCloud, and Apple Pay divisions, offsetting modest iPhone volume shifts.",
        "source": "Financial Times",
        "url": "https://www.ft.com/content/apple-services-record-highs",
        "company": "Apple",
        "published_at": "2026-10-24T09:00:00Z"
    },
    {
        "title": "European Regulators Launch Deep Antitrust Review of Apple App Ecosystem Policies",
        "description": "European Commission opens another non-compliance inquiry into developer payment rules, creating litigation overhang.",
        "source": "Wall Street Journal",
        "url": "https://www.wsj.com/tech/apple-eu-antitrust-inquiry",
        "company": "Apple",
        "published_at": "2026-10-23T16:20:00Z"
    },
    {
        "title": "Microsoft Cloud Azure Expansion Gains Momentum With Enterprise Copilot Monetization",
        "description": "Enterprise cloud contracts grew 29% as Fortune 500 corporations aggressively rolled out generative AI workflows on Azure infrastructure.",
        "source": "CNBC",
        "url": "https://www.cnbc.com/microsoft-azure-copilot-growth",
        "company": "Microsoft",
        "published_at": "2026-10-24T08:45:00Z"
    },
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
        "title": "Amazon Web Services Accelerates Operating Profit Margins Through Custom Silicon Graviton Deployments",
        "description": "AWS operational efficiency widened following extensive adoption of in-house energy-efficient server chips across cloud datacenters.",
        "source": "Bloomberg",
        "url": "https://www.bloomberg.com/news/amazon-aws-operating-margins",
        "company": "Amazon",
        "published_at": "2026-10-24T10:30:00Z"
    },
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
        "title": "Pfizer Reports Breakthrough Phase 3 Clinical Trial Results for Next-Gen Oncology Drug",
        "description": "Clinical studies show a 42% reduction in disease progression risk for advanced breast cancer patients, accelerating FDA approval timeline.",
        "source": "Endpoints News",
        "url": "https://endpts.com/pfizer-phase-3-oncology-trial-success",
        "company": "Pfizer",
        "published_at": "2026-10-24T15:00:00Z"
    },
    {
        "title": "ExxonMobil Expands Deepwater Offshore Discoveries With High-Return Permian Basin Drilling",
        "description": "Energy producer achieves lower breakeven per-barrel costs and signals strong cash flow returns and shareholder dividend hikes.",
        "source": "Oil & Gas Journal",
        "url": "https://www.ogj.com/exxonmobil-permian-deepwater-discoveries",
        "company": "ExxonMobil",
        "published_at": "2026-10-23T20:15:00Z"
    },
    # Near-duplicate headline to demonstrate robust deduplication
    {
        "title": "Nvidia Reports Record Quarter With AI Infrastructure Demand Surging Globally",
        "description": "Hyperscaler investments drove Nvidia to record quarterly revenue figures exceeding consensus analyst targets.",
        "source": "TechWire News",
        "url": "https://techwire.org/nvidia-reports-record-quarter-ai-demand",
        "company": "Nvidia",
        "published_at": "2026-10-24T14:45:00Z"
    }
]

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

class NewsService:
    def __init__(self):
        self.api_key = settings.NEWS_API_KEY
        self.news_api_status = "Available (API Key configured)" if self.api_key else "Demo Mode (No API key provided)"

    def fetch_articles(self, force_refresh: bool = False, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves articles from database or fetches fresh articles from NewsAPI / Demo dataset.
        Analyzes sentiment via FinBERT if unanalyzed.
        """
        existing_articles = db.find("news_articles", limit=200)

        if not force_refresh and len(existing_articles) > 0 and not query:
            return existing_articles

        # Attempt live NewsAPI retrieval if key is present
        raw_articles = []
        is_demo = True

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
                        is_demo = False
                        self.news_api_status = "Connected (NewsAPI Live)"
                        for item in articles_json:
                            # Map company from title/description
                            matched_company = self._infer_company(item.get("title", "") + " " + (item.get("description") or ""))
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
                    logger.warning(f"NewsAPI error {resp.status_code}: {resp.text}. Falling back to demo data.")
                    self.news_api_status = f"Rate limited / Error ({resp.status_code}) - Fallback to Demo Data"
            except Exception as e:
                logger.error(f"Failed to query NewsAPI: {e}. Falling back to demo dataset.")
                self.news_api_status = f"Network Exception - Fallback to Demo Data ({str(e)})"

        # If live retrieval yielded nothing or no key configured, use DEMO_FINANCIAL_ARTICLES
        if not raw_articles:
            is_demo = True
            for demo_item in DEMO_FINANCIAL_ARTICLES:
                art = dict(demo_item)
                art["id"] = f"demo-{uuid.uuid4().hex[:8]}"
                art["is_demo"] = True
                raw_articles.append(art)

        # Apply Deduplication Pipeline
        processed_articles, dup_count = deduplication_service.process_articles(raw_articles)
        logger.info(f"Processed {len(processed_articles)} articles ({dup_count} duplicates flagged)")

        # Run Real FinBERT Sentiment Inference for all articles
        headlines = [a["title"] for a in processed_articles]
        sentiment_results = []
        try:
            sentiment_results = finbert_service.predict_batch(headlines)
        except Exception as e:
            logger.error(f"FinBERT batch analysis error: {e}")

        # Attach sentiment result to each article and persist
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

            # Store into database
            db.insert_one("news_articles", article)

        return processed_articles

    def _infer_company(self, text: str) -> str:
        text_lower = text.lower()
        for company, keywords in SUPPORTED_COMPANIES.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    return company
        return "General Market"

    def query_articles(
        self,
        query: Optional[str] = None,
        company: Optional[str] = None,
        sentiment: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int, bool]:
        """Filters articles with pagination."""
        all_articles = self.fetch_articles()

        filtered = []
        for a in all_articles:
            if company and company.lower() != "all" and a.get("company", "").lower() != company.lower():
                continue
            if sentiment and sentiment.lower() != "all" and (a.get("sentiment") or "").lower() != sentiment.lower():
                continue
            if query:
                q_clean = query.lower()
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
