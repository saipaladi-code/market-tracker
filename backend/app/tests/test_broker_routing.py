import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.broker_routing_service import broker_routing_service

client = TestClient(app)

def test_indian_stock_routing_groww_direct_navigation():
    """
    Verifies that all specified Indian stocks route to Groww with verified direct
    stock instrument pages (https://groww.in/stocks/{slug}) rather than generic homepages.
    """
    indian_samples = [
        ("Reliance Industries", "RELIANCE", "https://groww.in/stocks/reliance-industries-ltd"),
        ("Tata Consultancy Services (TCS)", "TCS", "https://groww.in/stocks/tata-consultancy-services-ltd"),
        ("TCS", "TCS", "https://groww.in/stocks/tata-consultancy-services-ltd"),
        ("Tata Motors", "TATAMOTORS", "https://groww.in/stocks/tata-motors-ltd"),
        ("Infosys", "INFY", "https://groww.in/stocks/infosys-ltd"),
        ("HDFC Bank", "HDFCBANK", "https://groww.in/stocks/hdfc-bank-ltd"),
        ("ICICI Bank", "ICICIBANK", "https://groww.in/stocks/icici-bank-ltd"),
        ("State Bank of India", "SBIN", "https://groww.in/stocks/state-bank-of-india"),
        ("Bharti Airtel", "BHARTIARTL", "https://groww.in/stocks/bharti-airtel-ltd"),
        ("Larsen & Toubro", "LT", "https://groww.in/stocks/larsen-toubro-ltd"),
        ("Wipro", "WIPRO", "https://groww.in/stocks/wipro-ltd")
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
        assert data["portal_fallback_url"] == "https://groww.in/stocks"
        assert "Open " in data["action_label"]
        assert "on Groww" in data["action_label"]

        assert len(data["brokers"]) >= 1
        broker = data["recommended_broker"]
        assert broker["broker_id"] == "groww", f"Expected Groww for {comp_query}, got {broker['broker_id']}"
        assert broker["entry_url"] == expected_url
        assert broker["is_direct_link_verified"] is True
        assert expected_ticker in broker["instructions"]

def test_international_us_stock_groww_unsupported():
    """
    Verifies that US stocks (Apple, Amazon, Nvidia, Tesla, etc.) are correctly identified
    with ticker and exchange metadata, but clearly classified as unsupported on Groww
    since Groww discontinued retail US stock trading under LRS guidelines.
    """
    us_samples = [
        ("Apple (AAPL)", "AAPL", "Apple"),
        ("Apple", "AAPL", "Apple"),
        ("Microsoft (MSFT)", "MSFT", "Microsoft"),
        ("Tesla (TSLA)", "TSLA", "Tesla"),
        ("Amazon (AMZN)", "AMZN", "Amazon"),
        ("NVIDIA (NVDA)", "NVDA", "Nvidia")
    ]

    for comp_query, expected_ticker, short_name in us_samples:
        res = client.get("/api/trading/route", params={"company": comp_query})
        assert res.status_code == 200, f"Failed for {comp_query}"
        data = res.json()
        assert data["is_tradable"] is False, f"Expected {comp_query} to be untradable on Groww"
        assert data["ticker"] == expected_ticker
        assert data["country"] == "US"
        assert data["destination_type"] == "unsupported"
        assert data["direct_url"] is None
        assert data["portal_fallback_url"] == "https://groww.in/us-stocks/popular-us-stocks-and-etfs"
        assert "unsupported" in data["message"].lower() or "unavailable" in data["message"].lower()

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
    """Verifies Tata Motors commercial and main listed symbol TATAMOTORS on NSE routed to Groww."""
    res = client.get("/api/trading/route", params={"company": "Tata Motors"})
    assert res.status_code == 200
    data = res.json()
    assert data["ticker"] == "TATAMOTORS"
    assert data["exchange"] == "NSE"
    assert data["isin"] == "INE155A01022"
    assert data["destination_type"] == "direct_instrument"
    assert data["direct_url"] == "https://groww.in/stocks/tata-motors-ltd"

def test_other_international_stocks_not_routed_to_groww():
    """Verifies other international and unsupported stocks are NOT silently routed to arbitrary stocks."""
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
        assert data["destination_type"] == "unsupported"
        assert data["direct_url"] is None
        assert "not verified" in data["message"].lower() or "unavailable" in data["message"].lower()

def test_indian_stocks_groww_direct_routing():
    """Verifies Indian stocks route to Groww with official stock-specific URLs."""
    indian_tickers = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "TATAMOTORS"]
    for t in indian_tickers:
        res = client.get("/api/trading/route", params={"ticker": t})
        assert res.status_code == 200
        data = res.json()
        assert data["country"] == "IN"
        assert data["recommended_broker"]["broker_id"] == "groww"
        assert "groww.in/stocks/" in data["direct_url"]

def test_composite_ticker_and_company_parameters():
    """Verifies resolution when both company and ticker are passed separately."""
    res = client.get("/api/trading/route", params={"company": "Tata Consultancy Services", "ticker": "TCS"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_tradable"] is True
    assert data["ticker"] == "TCS"
    assert data["recommended_broker"]["broker_id"] == "groww"
    assert data["direct_url"] == "https://groww.in/stocks/tata-consultancy-services-ltd"

    res_us = client.get("/api/trading/route", params={"company": "Apple Inc", "ticker": "AAPL"})
    assert res_us.status_code == 200
    data_us = res_us.json()
    assert data_us["is_tradable"] is False
    assert data_us["ticker"] == "AAPL"
    assert data_us["destination_type"] == "unsupported"

def test_supported_instruments_endpoint():
    """Verifies listing of all verified Indian and International instruments."""
    res = client.get("/api/trading/supported-instruments")
    assert res.status_code == 200
    data = res.json()
    assert len(data["indian_instruments"]) >= 10
    assert len(data["international_instruments"]) >= 10
    assert data["total_verified"] >= 20
    # Every Indian instrument must have direct_url on Groww
    for inst in data["indian_instruments"]:
        assert inst["destination_type"] == "direct_instrument"
        assert inst["direct_url"] is not None
        assert "groww.in/stocks/" in inst["direct_url"]

def test_broker_capabilities_endpoint():
    """Verifies broker capabilities and compliance declarations."""
    res = client.get("/api/trading/brokers")
    assert res.status_code == 200
    data = res.json()
    broker_ids = [b["broker_id"] for b in data["brokers"]]
    assert "groww" in broker_ids
    assert "compliance_statement" in data
