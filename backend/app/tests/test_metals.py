import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_metals_prices():
    response = client.get("/api/metals/prices")
    assert response.status_code == 200
    data = response.json()
    assert "gold" in data
    assert "silver" in data
    assert "india_domestic" in data["gold"]
    assert "international" in data["gold"]
    assert data["gold"]["india_domestic"]["unit"] == "10g"
    assert data["silver"]["india_domestic"]["unit"] == "1kg"
    assert data["gold"]["international"]["currency"] == "USD"

def test_get_metals_news_endpoint():
    response = client.get("/api/metals/news?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert "articles" in data
    assert "total_count" in data
    assert "data_freshness" in data
    assert len(data["articles"]) <= 5
    if data["articles"]:
        a = data["articles"][0]
        assert "title" in a
        assert "metal" in a
        assert a["metal"] in ["Gold", "Silver", "Both"]
        assert "sentiment" in a
        assert "scores" in a
        assert "published_at_ist" in a

def test_metals_sentiment_summary():
    response = client.get("/api/metals/sentiment?days=30")
    assert response.status_code == 200
    data = response.json()
    assert "gold_sentiment" in data
    assert "silver_sentiment" in data
    assert "sentiment_distribution" in data

def test_metals_history():
    response = client.get("/api/metals/history?days=7")
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert len(data["history"]) >= 7
