import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.broker_routing_service import broker_routing_service

client = TestClient(app)

def test_indian_stock_routing_upstox_direct_navigation():
    """
    Verifies that all specified Indian stocks route to Upstox with verified direct
    stock instrument pages rather than generic broker homepages.
    """
    indian_samples = [
        ("Reliance Industries", "RELIANCE", "https://upstox.com/stocks/reliance-industries-ltd-share-price/"),
        ("Tata Consultancy Services (TCS)", "TCS", "https://upstox.com/stocks/tata-consultancy-serv-lt-share-price/"),
        ("TCS", "TCS", "https://upstox.com/stocks/tata-consultancy-serv-lt-share-price/"),
        ("Tata Motors", "TATAMOTORS", "https://upstox.com/stocks/tata-motors-limited-share-price/"),
        ("Infosys", "INFY", "https://upstox.com/stocks/infosys-limited-share-price/"),
        ("HDFC Bank", "HDFCBANK", "https://upstox.com/stocks/hdfc-bank-ltd-share-price/"),
        ("ICICI Bank", "ICICIBANK", "https://upstox.com/stocks/icici-bank-ltd-share-price/"),
        ("State Bank of India", "SBIN", "https://upstox.com/stocks/state-bank-of-india-share-price/"),
        ("Bharti Airtel", "BHARTIARTL", "https://upstox.com/stocks/bharti-airtel-limited-share-price/"),
        ("Larsen & Toubro", "LT", "https://upstox.com/stocks/larsen-toubro-ltd-share-price/"),
        ("Wipro", "WIPRO", "https://upstox.com/stocks/wipro-ltd-share-price/")
    ]

    for comp_query, expected_ticker, expected_url in indian_samples:
        res = client.get("/api/trading/route", params={"company": comp_query})
        assert res.status_code == 200, f"Failed for {comp_query}"
        data = res.json()
        assert data["is_tradable"] is True, f"Expected {comp_query} to be tradable"
        assert data["ticker"] == expected_ticker, f"Expected ticker {expected_ticker} for {comp_query}, got {data['ticker']}"
        assert data["exchange"] == "NSE"
        assert data["country"] == "IN"
        assert data["destination_type"] == "direct_instrument"
        assert data["direct_url"] == expected_url, f"Expected {expected_url}, got {data['direct_url']}"
        assert data["portal_fallback_url"] == "https://pro.upstox.com"
        assert f"Open " in data["action_label"]
        assert "in Upstox" in data["action_label"]

        assert len(data["brokers"]) == 1
        broker = data["brokers"][0]
        assert broker["broker_id"] == "upstox", f"Expected Upstox for {comp_query}, got {broker['broker_id']}"
        assert broker["entry_url"] == expected_url
        assert broker["is_direct_link_verified"] is True
        assert expected_ticker in broker["instructions"]

def test_international_us_stock_routing_ibkr_with_ticker_preservation():
    """
    Verifies that verified US stocks route to Interactive Brokers (IBKR) with
    verified_portal_with_ticker_search type, preserving ticker and exchange.
    """
    us_samples = [
        ("Apple (AAPL)", "AAPL", "Apple"),
        ("Apple", "AAPL", "Apple"),
        ("Microsoft (MSFT)", "MSFT", "Microsoft"),
        ("Microsoft", "MSFT", "Microsoft"),
        ("Tesla (TSLA)", "TSLA", "Tesla"),
        ("Tesla", "TSLA", "Tesla"),
        ("Amazon (AMZN)", "AMZN", "Amazon"),
        ("NVIDIA (NVDA)", "NVDA", "Nvidia"),
        ("Nvidia", "NVDA", "Nvidia"),
        ("Alphabet (GOOGL)", "GOOGL", "Alphabet (GOOGL)"),
        ("Meta", "META", "Meta"),
        ("JPMorgan Chase", "JPM", "JPMorgan Chase")
    ]

    for comp_query, expected_ticker, short_name in us_samples:
        res = client.get("/api/trading/route", params={"company": comp_query})
        assert res.status_code == 200, f"Failed for {comp_query}"
        data = res.json()
        assert data["is_tradable"] is True, f"Expected {comp_query} to be tradable"
        assert data["ticker"] == expected_ticker
        assert data["country"] == "US"
        assert data["destination_type"] == "verified_portal_with_ticker_search"
        assert data["portal_fallback_url"] == "https://www.interactivebrokers.com/portal/"
        assert f"Open " in data["action_label"]
        assert "in Interactive Brokers" in data["action_label"]

        assert len(data["brokers"]) == 1
        broker = data["brokers"][0]
        assert broker["broker_id"] == "ibkr", f"Expected IBKR for {comp_query}, got {broker['broker_id']}"
        assert broker["entry_url"] == "https://www.interactivebrokers.com/portal/"
        assert broker["is_direct_link_verified"] is False
        assert expected_ticker in broker["instructions"]

def test_alphabet_share_classes_differentiation():
    """Verifies that Alphabet share classes (GOOGL vs GOOG) are differentiated accurately."""
    res_googl = client.get("/api/trading/route", params={"company": "Alphabet (GOOGL)"})
    assert res_googl.status_code == 200
    data_googl = res_googl.json()
    assert data_googl["ticker"] == "GOOGL"
    assert "Class A" in (data_googl.get("share_class_note") or "")

    res_goog = client.get("/api/trading/route", params={"ticker": "GOOG"})
    assert res_goog.status_code == 200
    data_goog = res_goog.json()
    assert data_goog["ticker"] == "GOOG"
    assert "Class C" in (data_goog.get("share_class_note") or "")

def test_tata_motors_instrument_verification():
    """Verifies Tata Motors commercial and main listed symbol TATAMOTORS on NSE."""
    res = client.get("/api/trading/route", params={"company": "Tata Motors"})
    assert res.status_code == 200
    data = res.json()
    assert data["ticker"] == "TATAMOTORS"
    assert data["exchange"] == "NSE"
    assert data["isin"] == "INE155A01022"
    assert data["destination_type"] == "direct_instrument"
    assert data["direct_url"] == "https://upstox.com/stocks/tata-motors-limited-share-price/"

def test_other_international_stocks_not_routed_to_ibkr():
    """Verifies other international and unsupported stocks are NOT silently routed to IBKR or Upstox."""
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
        assert data["destination_type"] == "unsupported"
        assert data["direct_url"] is None
        assert "not verified" in data["message"].lower() or "not currently supported" in data["message"].lower()

def test_indian_stocks_never_route_to_ibkr():
    """Verifies Indian stocks never accidentally select IBKR."""
    indian_tickers = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "TATAMOTORS"]
    for t in indian_tickers:
        res = client.get("/api/trading/route", params={"ticker": t})
        assert res.status_code == 200
        data = res.json()
        assert data["country"] == "IN"
        assert data["brokers"][0]["broker_id"] == "upstox"

def test_us_stocks_never_route_to_upstox():
    """Verifies US stocks never accidentally select Upstox."""
    us_tickers = ["TSLA", "AAPL", "AMZN", "MSFT", "NVDA", "GOOGL"]
    for t in us_tickers:
        res = client.get("/api/trading/route", params={"ticker": t})
        assert res.status_code == 200
        data = res.json()
        assert data["country"] == "US"
        assert data["brokers"][0]["broker_id"] == "ibkr"

def test_composite_ticker_and_company_parameters():
    """Verifies resolution when both company and ticker are passed separately."""
    res = client.get("/api/trading/route", params={"company": "Tata Consultancy Services", "ticker": "TCS"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_tradable"] is True
    assert data["ticker"] == "TCS"
    assert data["brokers"][0]["broker_id"] == "upstox"
    assert data["direct_url"] == "https://upstox.com/stocks/tata-consultancy-serv-lt-share-price/"

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
    # Every Indian instrument must have direct_url
    for inst in data["indian_instruments"]:
        assert inst["destination_type"] == "direct_instrument"
        assert inst["direct_url"] is not None
        assert "upstox.com/stocks/" in inst["direct_url"]

def test_broker_capabilities_endpoint():
    """Verifies broker capabilities and compliance declarations."""
    res = client.get("/api/trading/brokers")
    assert res.status_code == 200
    data = res.json()
    broker_ids = [b["broker_id"] for b in data["brokers"]]
    assert "upstox" in broker_ids
    assert "ibkr" in broker_ids
    assert "compliance_statement" in data
