import pytest
from app.services.deduplication_service import deduplication_service, generate_canonical_id, jaccard_similarity
from app.services.conflict_service import conflict_service
from app.services.sector_service import sector_service
from app.services.finbert_service import finbert_service
from app.database import db

def test_canonical_id_generation():
    h1 = "Nvidia reports record quarterly revenue with AI chips"
    h2 = "Nvidia Reports Record Quarterly Revenue With AI Chips"
    id1 = generate_canonical_id(h1, "https://bloomberg.com/news?ref=123")
    id2 = generate_canonical_id(h2, "https://bloomberg.com/news?ref=456")
    # Base URL and normalized text match, so canonical IDs should match
    assert id1 == id2

def test_jaccard_similarity():
    s1 = "Apple reports strong iPhone sales in quarterly earnings"
    s2 = "Apple reports strong iPhone sales in quarterly report"
    sim = jaccard_similarity(s1, s2)
    assert sim >= 0.70

def test_deduplication_processing():
    articles = [
        {"id": "1", "title": "Tesla expands supercharger network globally", "url": "https://tesla.com/1"},
        {"id": "2", "title": "Tesla expands supercharger network globally", "url": "https://tesla.com/1?src=rss"},
        {"id": "3", "title": "Microsoft acquires cloud cybersecurity firm", "url": "https://msft.com/1"}
    ]
    processed, dup_count = deduplication_service.process_articles(articles)
    assert len(processed) == 3
    assert dup_count == 1
    assert processed[1]["is_duplicate"] is True
    assert processed[0]["is_duplicate"] is False
    assert processed[2]["is_duplicate"] is False

def test_conflict_detection():
    articles = [
        {"company": "Tesla", "title": "Tesla beats delivery forecast by 10%", "sentiment": "positive"},
        {"company": "Tesla", "title": "Tesla faces NHTSA safety inquiry into autonomous steering", "sentiment": "negative"},
        {"company": "Apple", "title": "Apple sales climb 5%", "sentiment": "positive"},
        {"company": "Apple", "title": "Apple boosts dividend payout", "sentiment": "positive"}
    ]
    conflicts = conflict_service.detect_conflicts(articles)
    tesla_conflicts = [c for c in conflicts if c["company"] == "Tesla"]
    apple_conflicts = [c for c in conflicts if c["company"] == "Apple"]

    assert len(tesla_conflicts) == 1
    assert tesla_conflicts[0]["conflict_score"] > 0
    assert len(apple_conflicts) == 0  # Apple has only positive, no conflict

def test_sector_service_mapping():
    assert sector_service.get_sector_for_company("Nvidia Corporation") == "Technology"
    assert sector_service.get_sector_for_company("JPMorgan Chase") == "Financials"
    assert sector_service.get_sector_for_company("ExxonMobil") == "Energy"

def test_empty_headline_rejection():
    with pytest.raises(ValueError):
        finbert_service.predict_one("   ")

def test_database_fallback_behavior():
    # Database manager must report connectivity without throwing unhandled exceptions
    status = db.get_status()
    assert "persistence_mode" in status
    assert "connected" in status
    assert status["connected"] is True

def test_finbert_singleton_pattern():
    from app.services.finbert_service import FinBERTService
    instance1 = FinBERTService()
    instance2 = FinBERTService()
    assert instance1 is instance2
    assert instance1 is finbert_service

def test_real_finbert_inference():
    # Test real FinBERT prediction on a clear financial headline
    text = "Nvidia reports record quarterly revenue and net income surges 120% YoY"
    res = finbert_service.predict_one(text, include_explanation=True)
    assert res["sentiment"] == "positive"
    assert res["confidence"] > 0.6
    assert "positive" in res["scores"]
    assert "negative" in res["scores"]
    assert "neutral" in res["scores"]
    total_prob = sum(res["scores"].values())
    assert 0.99 <= total_prob <= 1.01
    assert isinstance(res["tokens"], list)

