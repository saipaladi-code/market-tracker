import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import db

client = TestClient(app)

def test_explain_article_preserves_canonical_prediction():
    """
    Tests that /api/news/{article_id}/explain returns the article's canonical
    sentiment class, confidence score, and probability scores, and that
    token attribution does not alter or overwrite the saved prediction.
    """
    # 1. Seed or retrieve a test article
    articles_res = client.get("/api/news?page=1&page_size=5")
    assert articles_res.status_code == 200
    articles_data = articles_res.json()
    assert len(articles_data["articles"]) > 0

    target_article = articles_data["articles"][0]
    art_id = target_article["id"]
    canonical_sentiment = target_article["sentiment"]
    canonical_confidence = target_article["confidence"]
    canonical_scores = target_article["scores"]

    # 2. Call /api/news/{article_id}/explain
    explain_res = client.get(f"/api/news/{art_id}/explain")
    assert explain_res.status_code == 200
    explain_data = explain_res.json()

    # 3. Verify identical sentiment and confidence
    assert explain_data["article_id"] == art_id
    assert explain_data["sentiment"] == canonical_sentiment
    assert abs(explain_data["confidence"] - canonical_confidence) < 1e-4

    # 4. Verify identical class probability for predicted class
    if canonical_scores:
        if canonical_sentiment == "positive":
            assert abs(explain_data["scores"]["positive"] - canonical_confidence) < 1e-4
        elif canonical_sentiment == "negative":
            assert abs(explain_data["scores"]["negative"] - canonical_confidence) < 1e-4
        elif canonical_sentiment == "neutral":
            assert abs(explain_data["scores"]["neutral"] - canonical_confidence) < 1e-4

    # 5. Verify token attribution exists without modifying sentiment
    assert isinstance(explain_data["tokens"], list)

    # 6. Re-query the article from /api/news to confirm the stored prediction was NOT overwritten
    verify_res = client.get(f"/api/news?page=1&page_size=5")
    verify_data = verify_res.json()
    verified_article = next(a for a in verify_data["articles"] if a["id"] == art_id)

    assert verified_article["sentiment"] == canonical_sentiment
    assert abs(verified_article["confidence"] - canonical_confidence) < 1e-4

def test_explain_article_not_found():
    """Verifies that an unknown article ID returns HTTP 404."""
    res = client.get("/api/news/non-existent-article-99999/explain")
    assert res.status_code == 404
