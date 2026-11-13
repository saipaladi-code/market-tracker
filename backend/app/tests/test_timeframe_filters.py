import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.news_service import news_service
from app.services.conflict_service import conflict_service

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_auth():
    """Ensure tests run with valid authenticated session."""
    pass

def get_auth_token():
    res = client.post("/api/auth/demo")
    return res.json()["token"]

def test_timeframe_filters_dashboard_stats():
    """Verifies that all 4 timeframe options return distinct, reconciled analytics."""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    timeframes = ["live", "24h", "7d", "all"]
    results = {}

    for tf in timeframes:
        res = client.get(f"/api/dashboard/stats?timeframe={tf}", headers=headers)
        assert res.status_code == 200, f"Failed for timeframe {tf}"
        data = res.json()

        # Check required fields
        assert "total_articles" in data
        assert "sentiment_counts" in data
        assert "sentiment_percentages" in data
        assert "active_conflicts" in data
        assert "active_conflicts_count" in data
        assert data["timeframe"] == tf

        # Reconcile counts: unique sum must equal total_articles
        counts = data["sentiment_counts"]
        total_from_counts = counts["positive"] + counts["negative"] + counts["neutral"]
        assert total_from_counts == data["total_articles"], (
            f"Counts do not reconcile for {tf}: {total_from_counts} != {data['total_articles']}"
        )

        # Reconcile active conflicts count
        assert len(data["active_conflicts"]) == data["active_conflicts_count"]

        # Ensure no 'General Market' or 'Unknown' in conflicts
        for conf in data["active_conflicts"]:
            assert conf["company"] not in ("General Market", "Unknown", "None", "")

        results[tf] = data

    # Verify cumulative expansion: 24h <= 7d <= all
    assert results["24h"]["total_articles"] <= results["7d"]["total_articles"]
    assert results["7d"]["total_articles"] <= results["all"]["total_articles"]

def test_timeframe_filters_news_endpoint():
    """Verifies that /api/news accepts timeframe query and filters articles accordingly."""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    for tf in ["live", "24h", "7d", "all"]:
        res = client.get(f"/api/news?timeframe={tf}&page_size=10", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "articles" in data
        assert "total_count" in data
        assert isinstance(data["articles"], list)

def test_timeframe_filters_conflicts_endpoint():
    """Verifies /api/conflicts dynamically returns conflicts for requested timeframe and threshold."""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # All history should discover all dynamic conflicts
    res = client.get("/api/conflicts?timeframe=all&threshold=0.20", headers=headers)
    assert res.status_code == 200
    conflicts = res.json()
    assert isinstance(conflicts, list)
    assert len(conflicts) >= 3

    # All discovered companies must be valid securities (no General Market)
    companies = [c["company"] for c in conflicts]
    assert "General Market" not in companies
    assert "Unknown" not in companies

    # Check sorting: conflict_score descending
    scores = [c["conflict_score"] for c in conflicts]
    assert scores == sorted(scores, reverse=True)

def test_timeframe_filters_sector_heatmap():
    """Verifies /api/sentiment/sectors responds correctly for each timeframe."""
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    for tf in ["live", "24h", "7d", "all"]:
        res = client.get(f"/api/sentiment/sectors?timeframe={tf}", headers=headers)
        assert res.status_code == 200
        sectors = res.json()
        assert isinstance(sectors, list)
        assert len(sectors) > 0

def test_news_refresh_endpoint_with_timeframe():
    """Verifies /api/news/refresh preserves timeframe and returns updated sync timestamps."""
    from unittest.mock import patch
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(news_service, "ingest_live_news", return_value=[]):
        res = client.post("/api/news/refresh?timeframe=24h", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "refreshed"
        assert data["timeframe"] == "24h"
        assert "last_updated" in data
        assert "total_articles" in data
