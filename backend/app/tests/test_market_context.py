import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.market_context_service import market_context_service
from app.models.market_context_models import MarketContextRequest

client = TestClient(app)

def test_indian_company_context():
    req = MarketContextRequest(
        headline="Reliance Industries announces multi-billion dollar renewable and solar gigafactory",
        company="Reliance Industries",
        sentiment="positive",
        confidence=0.88,
        source="Reuters Financial"
    )
    res = market_context_service.generate_context(req)
    assert res.entity_type == "company"
    assert res.entity_name == "Reliance Industries"
    assert res.ticker == "RELIANCE"
    assert res.exchange == "NSE"
    assert res.sentiment == "positive"
    assert len(res.market_indicators) >= 2
    symbols = [ind.symbol for ind in res.market_indicators]
    assert "^NSEI" in symbols
    assert len(res.facts_vs_interpretation.objective_facts) >= 2
    assert "positive" in res.facts_vs_interpretation.ai_interpretation.lower()
    assert len(res.facts_vs_interpretation.risk_factors) >= 1

def test_us_company_context():
    req = MarketContextRequest(
        headline="Apple faces regulatory inquiry regarding App Store payment policies in European Union",
        company="Apple",
        sentiment="negative",
        confidence=0.76,
        source="Bloomberg"
    )
    res = market_context_service.generate_context(req)
    assert res.entity_type == "company"
    assert res.entity_name == "Apple"
    assert res.ticker == "AAPL"
    assert res.exchange == "NASDAQ"
    assert res.sentiment == "negative"
    symbols = [ind.symbol for ind in res.market_indicators]
    assert "^GSPC" in symbols
    assert "^NDX" in symbols
    assert "negative" in res.facts_vs_interpretation.ai_interpretation.lower()

def test_precious_metals_context():
    req = MarketContextRequest(
        headline="COMEX Gold prices surged past record levels on central bank safe-haven reserve buying",
        company="Precious Metals",
        sentiment="positive",
        confidence=0.82
    )
    res = market_context_service.generate_context(req)
    assert res.entity_type == "commodity"
    assert "Gold" in res.entity_name
    symbols = [ind.symbol for ind in res.market_indicators]
    assert "GC=F" in symbols
    assert "USDINR=X" in symbols

def test_general_macro_context():
    req = MarketContextRequest(
        headline="Reserve Bank of India maintains repo rate unchanged citing sticky food inflation",
        company="General Market",
        sentiment="neutral",
        confidence=0.65
    )
    res = market_context_service.generate_context(req)
    assert res.entity_type == "general_market"
    symbols = [ind.symbol for ind in res.market_indicators]
    assert "^NSEI" in symbols
    assert "^INDIAVIX" in symbols

def test_api_post_market_context_endpoint():
    payload = {
        "headline": "Tata Motors reports 24% surge in commercial vehicle and EV deliveries",
        "company": "Tata Motors",
        "sentiment": "positive",
        "confidence": 0.91,
        "source": "Economic Times"
    }
    response = client.post("/api/news/context", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["entity_type"] == "company"
    assert data["ticker"] == "TATAMOTORS"
    assert data["exchange"] == "NSE"
    assert len(data["market_indicators"]) >= 2
    assert "data_source" in data
    assert "facts_vs_interpretation" in data

def test_api_get_article_context_endpoint():
    response = client.get(
        "/api/news/sample-art-001/context",
        params={
            "headline": "Infosys signs $1.5 billion generative AI digital transformation deal",
            "company": "Infosys",
            "sentiment": "positive",
            "confidence": 0.85
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["entity_type"] == "company"
    assert data["ticker"] == "INFY"
    assert len(data["supporting_facts"]) >= 1

def test_context_caching():
    req = MarketContextRequest(
        headline="HDFC Bank expands digital branch network across semi-urban clusters",
        company="HDFC Bank",
        sentiment="positive",
        confidence=0.75
    )
    res1 = market_context_service.generate_context(req)
    res2 = market_context_service.generate_context(req)
    assert res1.generated_at == res2.generated_at
    assert res1.ticker == res2.ticker
