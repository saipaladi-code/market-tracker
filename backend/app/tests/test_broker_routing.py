import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.broker_routing_service import broker_routing_service

client = TestClient(app)

def test_indian_stock_routing_upstox():
    """Verifies that Indian stocks route to Upstox with verified NSE/BSE ticker."""
    # Test by company name
    res = client.get("/api/trading/route?company=Reliance")
    assert res.status_code == 200
    data = res.json()
    assert data["is_tradable"] is True
    assert data["ticker"] == "RELIANCE"
    assert data["exchange"] == "NSE"
    assert data["country"] == "IN"
    assert len(data["brokers"]) == 1
    broker = data["brokers"][0]
    assert broker["broker_id"] == "upstox"
    assert broker["entry_url"] == "https://pro.upstox.com"
    assert broker["is_direct_link_verified"] is False
    assert "RELIANCE" in broker["instructions"]

    # Test Tata Motors by alias
    res_tata = client.get("/api/trading/route?ticker=TATAMOTORS")
    assert res_tata.status_code == 200
    assert res_tata.json()["is_tradable"] is True
    assert res_tata.json()["ticker"] == "TATAMOTORS"

def test_international_stock_routing_ibkr():
    """Verifies that International stocks route to Interactive Brokers with verified US ticker."""
    res = client.get("/api/trading/route?company=Apple")
    assert res.status_code == 200
    data = res.json()
    assert data["is_tradable"] is True
    assert data["ticker"] == "AAPL"
    assert data["exchange"] == "NASDAQ"
    assert data["country"] == "US"
    assert len(data["brokers"]) == 1
    broker = data["brokers"][0]
    assert broker["broker_id"] == "ibkr"
    assert broker["entry_url"] == "https://www.interactivebrokers.com/portal/"
    assert broker["is_direct_link_verified"] is False
    assert "AAPL" in broker["instructions"]

    # Test Nvidia
    res_nvda = client.get("/api/trading/route?company=Nvidia")
    assert res_nvda.status_code == 200
    assert res_nvda.json()["ticker"] == "NVDA"
    assert res_nvda.json()["brokers"][0]["broker_id"] == "ibkr"

def test_ambiguous_and_unsupported_instruments():
    """Verifies that ambiguous names and unsupported companies cleanly return not supported."""
    unsupported = ["General Market", "Unknown Corp", "CryptoCoinXYZ", "asdfghjk", ""]
    for item in unsupported:
        res = client.get(f"/api/trading/route?company={item}")
        assert res.status_code == 200
        data = res.json()
        assert data["is_tradable"] is False
        assert data["ticker"] is None
        assert data["brokers"] == []
        assert "not currently supported" in data["message"].lower()

def test_supported_instruments_endpoint():
    """Verifies listing of all verified Indian and International instruments."""
    res = client.get("/api/trading/supported-instruments")
    assert res.status_code == 200
    data = res.json()
    assert len(data["indian_instruments"]) >= 10
    assert len(data["international_instruments"]) >= 10
    assert data["total_verified"] >= 20

def test_broker_capabilities_endpoint():
    """Verifies broker capabilities and compliance declarations."""
    res = client.get("/api/trading/brokers")
    assert res.status_code == 200
    data = res.json()
    broker_ids = [b["broker_id"] for b in data["brokers"]]
    assert "upstox" in broker_ids
    assert "ibkr" in broker_ids
    assert "compliance_statement" in data
