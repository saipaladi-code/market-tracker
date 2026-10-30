import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.broker_routing_service import broker_routing_service

client = TestClient(app)

def test_indian_stock_routing_upstox():
    """Verifies that all specified Indian stocks route to Upstox Pro."""
    indian_samples = [
        ("Reliance Industries", "RELIANCE"),
        ("Tata Consultancy Services (TCS)", "TCS"),
        ("TCS", "TCS"),
        ("Tata Motors", "TATAMOTORS"),
        ("Infosys", "INFY"),
        ("HDFC Bank", "HDFCBANK"),
        ("ICICI Bank", "ICICIBANK"),
        ("State Bank of India", "SBIN"),
        ("Bharti Airtel", "BHARTIARTL"),
        ("Larsen & Toubro", "LT"),
        ("Wipro", "WIPRO")
    ]

    for comp_query, expected_ticker in indian_samples:
        res = client.get("/api/trading/route", params={"company": comp_query})
        assert res.status_code == 200, f"Failed for {comp_query}"
        data = res.json()
        assert data["is_tradable"] is True, f"Expected {comp_query} to be tradable"
        assert data["ticker"] == expected_ticker, f"Expected ticker {expected_ticker} for {comp_query}, got {data['ticker']}"
        assert data["exchange"] == "NSE"
        assert data["country"] == "IN"
        assert len(data["brokers"]) == 1
        broker = data["brokers"][0]
        assert broker["broker_id"] == "upstox", f"Expected Upstox for {comp_query}, got {broker['broker_id']}"
        assert broker["entry_url"] == "https://pro.upstox.com"
        assert expected_ticker in broker["instructions"]

def test_international_us_stock_routing_ibkr():
    """Verifies that verified US stocks route to Interactive Brokers (IBKR)."""
    us_samples = [
        ("Apple (AAPL)", "AAPL"),
        ("Apple", "AAPL"),
        ("Microsoft (MSFT)", "MSFT"),
        ("Microsoft", "MSFT"),
        ("Tesla (TSLA)", "TSLA"),
        ("Tesla", "TSLA"),
        ("Amazon (AMZN)", "AMZN"),
        ("NVIDIA (NVDA)", "NVDA"),
        ("Nvidia", "NVDA"),
        ("Alphabet (GOOGL)", "GOOGL"),
        ("Meta", "META"),
        ("JPMorgan Chase", "JPM")
    ]

    for comp_query, expected_ticker in us_samples:
        res = client.get("/api/trading/route", params={"company": comp_query})
        assert res.status_code == 200, f"Failed for {comp_query}"
        data = res.json()
        assert data["is_tradable"] is True, f"Expected {comp_query} to be tradable"
        assert data["ticker"] == expected_ticker
        assert data["country"] == "US"
        assert len(data["brokers"]) == 1
        broker = data["brokers"][0]
        assert broker["broker_id"] == "ibkr", f"Expected IBKR for {comp_query}, got {broker['broker_id']}"
        assert broker["entry_url"] == "https://www.interactivebrokers.com/portal/"
        assert expected_ticker in broker["instructions"]

def test_other_international_stocks_not_routed_to_ibkr():
    """Verifies other international and unsupported stocks are NOT silently routed to IBKR."""
    unsupported_samples = [
        "Bavarian Nordic",
        "Novo Nordisk",
        "ASML",
        "Toyota Motor",
        "Tencent",
        "Unknown International Corp",
        "General Market",
        "Macro Economy",
        ""
    ]

    for item in unsupported_samples:
        res = client.get("/api/trading/route", params={"company": item})
        assert res.status_code == 200
        data = res.json()
        assert data["is_tradable"] is False, f"Expected {item} to NOT be tradable"
        assert data["brokers"] == [], f"Expected 0 brokers for {item}, but got {data['brokers']}"
        assert data.get("recommended_broker") is None
        assert "not verified" in data["message"].lower() or "not currently supported" in data["message"].lower()

def test_composite_ticker_and_company_parameters():
    """Verifies resolution when both company and ticker are passed separately."""
    res = client.get("/api/trading/route", params={"company": "Tata Consultancy Services", "ticker": "TCS"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_tradable"] is True
    assert data["ticker"] == "TCS"
    assert data["brokers"][0]["broker_id"] == "upstox"

    res_us = client.get("/api/trading/route", params={"company": "Apple Inc", "ticker": "AAPL"})
    assert res_us.status_code == 200
    data_us = res_us.json()
    assert data_us["is_tradable"] is True
    assert data_us["ticker"] == "AAPL"
    assert data_us["brokers"][0]["broker_id"] == "ibkr"

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
