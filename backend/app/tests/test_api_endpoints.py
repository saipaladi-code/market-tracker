import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

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
