import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from app.config import settings
from app.services.news_service import (
    news_service,
    clean_rss_title_and_source,
    clean_html_text,
    parse_publication_datetime,
    KOLKATA_TZ
)
from app.services.deduplication_service import deduplication_service, generate_canonical_id
from app.database import db

SAMPLE_RSS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Financial News Test</title>
    <item>
      <title>Nvidia surges on massive AI datacenter chip demand - Bloomberg</title>
      <link>https://bloomberg.com/news/articles/nvidia-ai-demand-test</link>
      <description>&lt;p&gt;Hyperscaler investments drive semiconductor gains.&lt;/p&gt;</description>
      <pubDate>Mon, 26 Oct 2026 12:00:00 GMT</pubDate>
      <source url="https://bloomberg.com">Bloomberg</source>
    </item>
    <item>
      <title>Tesla announces autonomous robotaxi regulatory milestone - Reuters</title>
      <link>https://reuters.com/business/tesla-robotaxi-milestone-test</link>
      <description>Electric automaker outlines safety telemetry metrics.</description>
      <pubDate>Mon, 26 Oct 2026 10:30:00 GMT</pubDate>
      <source url="https://reuters.com">Reuters</source>
    </item>
  </channel>
</rss>"""

def test_clean_rss_title_and_source():
    # Strips trailing publisher suffix and unescapes HTML entities
    title, source = clean_rss_title_and_source("Tech &amp; Media Stocks Gain - Reuters")
    assert title == "Tech & Media Stocks Gain"
    assert source == "Reuters"

    # Preserves titles without suffix
    title2, source2 = clean_rss_title_and_source("Apple Reports Q4 Revenue Record", "Bloomberg")
    assert title2 == "Apple Reports Q4 Revenue Record"
    assert source2 == "Bloomberg"

def test_clean_html_text():
    html_desc = "<p>Alphabet &amp; Microsoft report <b>record</b> cloud revenue.</p>"
    clean = clean_html_text(html_desc)
    assert clean == "Alphabet & Microsoft report record cloud revenue."

def test_parse_publication_datetime_rfc2822():
    raw_rfc = "Mon, 26 Oct 2026 12:30:00 GMT"
    dt = parse_publication_datetime(raw_rfc)
    assert dt is not None
    assert dt.tzinfo == timezone.utc
    assert dt.year == 2026
    assert dt.month == 10
    assert dt.day == 26
    assert dt.hour == 12
    assert dt.minute == 30

def test_parse_publication_datetime_iso():
    raw_iso = "2026-10-26T14:45:00Z"
    dt = parse_publication_datetime(raw_iso)
    assert dt is not None
    assert dt.year == 2026
    assert dt.hour == 14
    assert dt.minute == 45

def test_current_day_filtering_asia_kolkata():
    # Fixed reference time: 2026-10-26 14:00:00 UTC (19:30:00 IST)
    ref_utc = datetime(2026, 10, 26, 14, 0, 0, tzinfo=timezone.utc)
    ref_kolkata = ref_utc.astimezone(KOLKATA_TZ)

    # 1. Article published today in Kolkata (12:00 UTC = 17:30 IST on Oct 26)
    art_today = "2026-10-26T12:00:00Z"
    assert news_service.is_published_today_kolkata(art_today, ref_kolkata) is True

    # 2. Article published on midnight boundary (Oct 25 19:00 UTC = Oct 26 00:30 IST) -> TODAY in Kolkata!
    art_midnight_boundary = "2026-10-25T19:00:00Z"
    assert news_service.is_published_today_kolkata(art_midnight_boundary, ref_kolkata) is True

    # 3. Article published yesterday in Kolkata (Oct 25 15:00 UTC = Oct 25 20:30 IST) -> YESTERDAY!
    art_yesterday = "2026-10-25T15:00:00Z"
    assert news_service.is_published_today_kolkata(art_yesterday, ref_kolkata) is False

    # 4. Future-dated article (> ref_utc + 5 min, e.g. 15:00 UTC when ref is 14:00 UTC) -> EXCLUDED!
    with patch.object(news_service, 'get_utc_now', return_value=ref_utc):
        art_future = "2026-10-26T16:00:00Z"
        assert news_service.is_published_today_kolkata(art_future, ref_kolkata) is False

def test_deduplication_across_refreshes():
    articles = [
        {
            "title": "Nvidia quarterly profit surges 120% on AI GPU demand",
            "url": "https://bloomberg.com/news/nvidia-records?utm=twitter",
            "source": "Bloomberg",
            "published_at": "2026-10-26T12:00:00Z"
        },
        # Exact same article with different tracking parameters
        {
            "title": "Nvidia quarterly profit surges 120% on AI GPU demand",
            "url": "https://bloomberg.com/news/nvidia-records?utm=linkedin",
            "source": "Bloomberg",
            "published_at": "2026-10-26T12:00:00Z"
        },
        # Near duplicate syndicate
        {
            "title": "Nvidia Quarterly Profit Surges 120% On Massive AI GPU Demand",
            "url": "https://techwire.com/nvidia-quarter-records",
            "source": "TechWire",
            "published_at": "2026-10-26T12:05:00Z"
        }
    ]
    processed, dup_count = deduplication_service.process_articles(articles)
    assert len(processed) == 3
    assert dup_count == 2
    assert processed[0]["is_duplicate"] is False
    assert processed[1]["is_duplicate"] is True
    assert processed[2]["is_duplicate"] is True

def test_live_rss_mock_ingestion(monkeypatch):
    monkeypatch.setattr(settings, "USE_DEMO_DATA", False)

    class MockResponse:
        def __init__(self, data):
            self.data = data
        def read(self):
            return self.data
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_urlopen(req, timeout=6):
        return MockResponse(SAMPLE_RSS_XML)

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        raw_articles = news_service.fetch_live_rss_articles()
        assert len(raw_articles) >= 2
        nvda_art = next((a for a in raw_articles if "Nvidia" in a["title"]), None)
        assert nvda_art is not None
        assert nvda_art["company"] == "Nvidia"
        assert nvda_art["is_demo"] is False
        assert nvda_art["source"] == "Bloomberg"
        assert "2026-10-26" in nvda_art["published_at"]

def test_query_articles_live_feed_status(monkeypatch):
    monkeypatch.setattr(settings, "USE_DEMO_DATA", False)
    res = news_service.query_articles(page=1, page_size=10, today_only=True)
    assert res.feed_status in ("LIVE FEED", "CACHED LIVE DATA")
    assert res.is_demo_dataset is False
    assert res.filter_date is not None
    assert len(res.articles) <= 10

def test_query_articles_explicit_date():
    # Query with specific date
    res = news_service.query_articles(date="2026-10-26", page=1, page_size=5)
    assert res.filter_date == "2026-10-26"
    assert all("2026-10-26" in (a.get("published_at") or "") for a in res.articles)

def test_finbert_prediction_persistence():
    headline = "Amazon Web Services announces record cloud infrastructure revenue"
    art = {
        "id": "test-persist-1",
        "canonical_id": generate_canonical_id(headline, "https://aws.amazon.com"),
        "title": headline,
        "company": "Amazon",
        "source": "AWS News",
        "published_at": "2026-10-26T10:00:00Z",
        "is_demo": False,
        "sentiment": "positive",
        "confidence": 0.9412,
        "scores": {"positive": 0.9412, "negative": 0.0300, "neutral": 0.0288}
    }
    db.insert_one("news_articles", art)

    retrieved = db.find_one("news_articles", {"id": "test-persist-1"})
    assert retrieved is not None
    assert retrieved["sentiment"] == "positive"
    assert retrieved["confidence"] == 0.9412
    assert retrieved["scores"]["positive"] == 0.9412
