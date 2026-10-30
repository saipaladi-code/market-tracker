import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "endpoints" in data

def test_lightweight_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model_ready" in data

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model" in data
    assert "database" in data
    assert "news_api" in data

def test_dashboard_stats():
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_articles" in data
    assert "sentiment_counts" in data
    assert "sentiment_percentages" in data
    assert "top_discussed_companies" in data
    assert "active_conflicts" in data

def test_news_retrieval_and_filtering():
    response = client.get("/api/news?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert "articles" in data
    assert len(data["articles"]) <= 5
    assert "total_count" in data

def test_analyze_empty_headline_error():
    response = client.post("/api/analyze", json={"text": ""})
    assert response.status_code == 422 or response.status_code == 400

def test_companies_endpoint():
    response = client.get("/api/companies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "ticker" in data[0]

def test_sector_sentiments():
    response = client.get("/api/sentiment/sectors")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(s["sector"] == "Technology" for s in data)

def test_data_quality_endpoint():
    response = client.get("/api/data-quality")
    assert response.status_code == 200
    data = response.json()
    assert "duplicate_rate" in data
    assert "database_status" in data

def test_assistant_chat_fallback():
    response = client.post("/api/assistant/chat", json={"message": "What is the sentiment on Nvidia?"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "disclaimer" in data

def test_company_and_sentiment_filtering_scenarios(monkeypatch):
    monkeypatch.setattr("app.config.settings.USE_DEMO_DATA", True)
    # 1. All articles with no filters
    r_all = client.get("/api/news?page_size=100")
    assert r_all.status_code == 200
    total_unfiltered = r_all.json()["total_count"]
    assert total_unfiltered > 0

    # 2. Apple with all sentiment categories
    r_apple = client.get("/api/news?company=Apple&page_size=50")
    assert r_apple.status_code == 200
    apple_data = r_apple.json()
    assert apple_data["total_count"] > 0
    assert all(a["company"] == "Apple" for a in apple_data["articles"])
    apple_sentiments = set(a["sentiment"] for a in apple_data["articles"])
    assert "positive" in apple_sentiments
    assert "negative" in apple_sentiments
    assert "neutral" in apple_sentiments

    # 3. NVIDIA with all sentiment categories (also testing ticker NVDA and case-insensitivity)
    r_nvda = client.get("/api/news?company=NVDA&page_size=50")
    assert r_nvda.status_code == 200
    nvda_data = r_nvda.json()
    assert nvda_data["total_count"] > 0
    assert all(a["company"] == "Nvidia" for a in nvda_data["articles"])
    nvda_sentiments = set(a["sentiment"] for a in nvda_data["articles"])
    assert "positive" in nvda_sentiments
    assert "negative" in nvda_sentiments
    assert "neutral" in nvda_sentiments

    # 4. Tesla with all sentiment categories (also testing ticker TSLA)
    r_tsla = client.get("/api/news?company=TSLA&page_size=50")
    assert r_tsla.status_code == 200
    tsla_data = r_tsla.json()
    assert tsla_data["total_count"] > 0
    assert all(a["company"] == "Tesla" for a in tsla_data["articles"])
    tsla_sentiments = set(a["sentiment"] for a in tsla_data["articles"])
    assert "positive" in tsla_sentiments
    assert "negative" in tsla_sentiments
    assert "neutral" in tsla_sentiments

    # 5. Apple + Positive
    r_app_pos = client.get("/api/news?company=Apple&sentiment=positive")
    assert r_app_pos.status_code == 200
    app_pos_data = r_app_pos.json()
    assert app_pos_data["total_count"] > 0
    assert all(a["company"] == "Apple" and a["sentiment"] == "positive" for a in app_pos_data["articles"])

    # 6. Apple + Negative
    r_app_neg = client.get("/api/news?company=Apple&sentiment=negative")
    assert r_app_neg.status_code == 200
    app_neg_data = r_app_neg.json()
    assert app_neg_data["total_count"] > 0
    assert all(a["company"] == "Apple" and a["sentiment"] == "negative" for a in app_neg_data["articles"])

    # 7. Apple + Neutral
    r_app_neu = client.get("/api/news?company=Apple&sentiment=neutral")
    assert r_app_neu.status_code == 200
    app_neu_data = r_app_neu.json()
    assert app_neu_data["total_count"] > 0
    assert all(a["company"] == "Apple" and a["sentiment"] == "neutral" for a in app_neu_data["articles"])

    # 8. Clearing all filters
    r_reset = client.get("/api/news?page_size=100")
    assert r_reset.status_code == 200
    assert r_reset.json()["total_count"] == total_unfiltered

def test_demo_analyst_login_and_authenticated_news_access():
    """Verifies instant demo analyst sign-in and Bearer-authenticated news retrieval."""
    res = client.post("/api/auth/demo")
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["user"]["email"] == "demo.analyst@finsentiment.ai"
    assert len(data["token"]) > 20

    token = data["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify access to protected news endpoint
    news_res = client.get("/api/news", headers=headers)
    assert news_res.status_code == 200
    news_data = news_res.json()
    assert "articles" in news_data
    assert "feed_status" in news_data
    assert news_data["feed_status"] in ("LIVE FEED", "CACHED LIVE DATA")

    # Verify access to dashboard stats
    stats_res = client.get("/api/dashboard/stats", headers=headers)
    assert stats_res.status_code == 200
    assert "total_articles" in stats_res.json()

def test_news_refresh_endpoints_support_get_and_post():
    """Ensures /api/news/refresh responds on both POST and GET without 405 Method Not Allowed."""
    from unittest.mock import patch
    from app.services.news_service import news_service

    auth_res = client.post("/api/auth/demo")
    token = auth_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(news_service, "fetch_articles", return_value=[{"title": "Test news", "is_demo": False}]), \
         patch.object(news_service, "ingest_live_news", return_value=[]):
        # Test POST /api/news/refresh
        res_post = client.post("/api/news/refresh", headers=headers)
        assert res_post.status_code == 200
        assert "message" in res_post.json()
        assert "feed_status" in res_post.json()

        # Test GET /api/news/refresh
        res_get = client.get("/api/news/refresh", headers=headers)
        assert res_get.status_code == 200
        assert "message" in res_get.json()
        assert "feed_status" in res_get.json()


