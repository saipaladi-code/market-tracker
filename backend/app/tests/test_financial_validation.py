import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.finbert_service import finbert_service
from app.services.headline_validator import (
    validate_financial_headline,
    assert_valid_financial_headline,
    HeadlineValidationError,
    INVALID_FINANCIAL_HEADLINE_MESSAGE,
    ERROR_INVALID_FINANCIAL_HEADLINE,
    ERROR_HEADLINE_TOO_SHORT,
    ERROR_HEADLINE_TOO_LONG,
    ERROR_HEADLINE_EMPTY,
    MIN_HEADLINE_LENGTH,
    MAX_HEADLINE_LENGTH
)

client = TestClient(app)

REJECTION_CASES = [
    ("hi", ERROR_INVALID_FINANCIAL_HEADLINE),
    ("hello", ERROR_INVALID_FINANCIAL_HEADLINE),
    ("how are you", ERROR_INVALID_FINANCIAL_HEADLINE),
    ("what is your name", ERROR_INVALID_FINANCIAL_HEADLINE),
    ("I love pizza", ERROR_INVALID_FINANCIAL_HEADLINE),
    ("good morning", ERROR_INVALID_FINANCIAL_HEADLINE),
    ("tell me a joke", ERROR_INVALID_FINANCIAL_HEADLINE),
    ("12345", ERROR_INVALID_FINANCIAL_HEADLINE),
    ("", ERROR_HEADLINE_EMPTY),
    ("   ", ERROR_HEADLINE_EMPTY),
    ("!?! ... --- ???", ERROR_INVALID_FINANCIAL_HEADLINE),
    ("asdfghjk qwertyuiop zxcvbnm", ERROR_INVALID_FINANCIAL_HEADLINE),
    ("What is the distance between the earth and the moon in kilometers?", ERROR_INVALID_FINANCIAL_HEADLINE),
    ("Can you please tell me how to bake chocolate chip cookies?", ERROR_INVALID_FINANCIAL_HEADLINE),
    ("The children played happily in the neighborhood park yesterday afternoon.", ERROR_INVALID_FINANCIAL_HEADLINE),
    ("I went to the supermarket to buy some apples and fresh milk for breakfast.", ERROR_INVALID_FINANCIAL_HEADLINE),
]

ACCEPTANCE_CASES = [
    "Apple reports record quarterly revenue, beating analyst expectations.",
    "Tesla shares fall after quarterly profits decline.",
    "Microsoft announces a new earnings forecast.",
    "Reliance Industries reports higher operating revenue.",
    "The central bank keeps interest rates unchanged.",
    "A company announces layoffs amid declining sales.",
    "Amazon faces regulatory scrutiny over its business practices.",
    "A previously unknown company announces a major quarterly loss.",
    "A business reports mixed earnings results and lowers its annual forecast.",
    # Valid financial news about unknown / unfamiliar companies
    "Solaria Energy closes $85 million green bond issuance for regional solar grid expansion.",
    "BioGenix Pharmaceuticals receives FDA priority review designation for oncology candidate.",
    "Quantum Dynamics reports 24% increase in second-quarter commercial software contract bookings.",
    "Kyoto Robotics raises 5 billion yen in Series C venture funding round.",
    # Positive, Negative, Neutral, and Mixed financial headlines
    "Alphabet surges 8% following stellar cloud infrastructure earnings beat.",  # Positive
    "ExxonMobil faces steep earnings loss and dividend cut risk amid persistent oil slump.",  # Negative
    "Tesla releases quarterly vehicle production and delivery summary figures.",  # Neutral
    "Microsoft reports record cloud profit but issues cautious full-year enterprise guidance.",  # Mixed
]


def test_rejection_test_cases_direct_validator():
    """Verify all required invalid samples are rejected by the validator."""
    for text, expected_code in REJECTION_CASES:
        cleaned, code, msg = validate_financial_headline(text)
        assert code is not None, f"Expected {text!r} to be rejected, but passed."
        assert code == expected_code, f"Expected code {expected_code} for {text!r}, got {code}"
        if code == ERROR_INVALID_FINANCIAL_HEADLINE:
            assert msg == INVALID_FINANCIAL_HEADLINE_MESSAGE


def test_rejection_test_cases_via_api():
    """Verify all required invalid samples return HTTP 422 with structured error details via /api/analyze."""
    for text, expected_code in REJECTION_CASES:
        response = client.post("/api/analyze", json={"text": text})
        assert response.status_code == 422, f"Expected 422 for {text!r}, got {response.status_code}"
        data = response.json()
        assert data.get("error_code") == expected_code, f"Expected {expected_code} in response for {text!r}, got {data}"
        if expected_code == ERROR_INVALID_FINANCIAL_HEADLINE:
            assert data.get("message") == INVALID_FINANCIAL_HEADLINE_MESSAGE
            assert data.get("detail") == INVALID_FINANCIAL_HEADLINE_MESSAGE


def test_acceptance_test_cases_direct_validator():
    """Verify all required legitimate financial headlines pass the validator."""
    for text in ACCEPTANCE_CASES:
        cleaned, code, msg = validate_financial_headline(text)
        assert code is None, f"Expected {text!r} to pass validation, but failed with {code}: {msg}"
        assert len(cleaned) >= MIN_HEADLINE_LENGTH


def test_acceptance_test_cases_via_api():
    """Verify all required legitimate financial headlines succeed via /api/analyze."""
    for text in ACCEPTANCE_CASES:
        response = client.post("/api/analyze", json={"text": text})
        assert response.status_code == 200, f"Expected 200 for {text!r}, got {response.status_code}: {response.text}"
        data = response.json()
        assert "sentiment" in data
        assert data["sentiment"] in ("positive", "negative", "neutral")
        assert "scores" in data
        assert "confidence" in data
        assert data["confidence"] > 0.0


def test_boundary_1000_characters_exact():
    """Verify a valid financial statement containing exactly 1,000 characters is accepted."""
    base = (
        "Apple reports record quarterly revenue of $94.9 billion, beating analyst expectations across all product segments. "
        "The technology company experienced surging enterprise cloud demand, resilient handset volume growth, and disciplined "
        "operating expense execution, driving expanded gross margins and optimistic fiscal year guidance. Furthermore, corporate "
        "leadership reiterated committed shareholder capital returns, noting aggressive stock buybacks, dividend distributions, "
        "and sustained cash flow generation despite foreign exchange headwinds. "
    )
    # Construct exact 1000-character financial headline
    padding_word = " market"
    headline_1000 = base
    while len(headline_1000) < 1000:
        remaining = 1000 - len(headline_1000)
        if remaining >= len(padding_word):
            headline_1000 += padding_word
        else:
            headline_1000 += "a" * remaining
    assert len(headline_1000) == 1000

    # Test direct validator
    cleaned, code, msg = validate_financial_headline(headline_1000)
    assert code is None, f"Expected 1000-character financial headline to pass, got {code}: {msg}"

    # Test API
    resp = client.post("/api/analyze", json={"text": headline_1000})
    assert resp.status_code == 200, f"Expected 200 for 1000 chars, got {resp.status_code}: {resp.text}"
    assert resp.json()["sentiment"] in ("positive", "negative", "neutral")


def test_boundary_1001_characters_rejected():
    """Verify that a 1,001-character headline is rejected with HTTP 422 and HEADLINE_TOO_LONG."""
    base = (
        "Apple reports record quarterly revenue of $94.9 billion, beating analyst expectations across all product segments. "
        "The technology company experienced surging enterprise cloud demand, resilient handset volume growth, and disciplined "
        "operating expense execution, driving expanded gross margins and optimistic fiscal year guidance. "
    )
    headline_1001 = (base * 6)[:1000] + "!"
    assert len(headline_1001.strip()) == 1001

    # Direct validator check
    cleaned, code, msg = validate_financial_headline(headline_1001)
    assert code == ERROR_HEADLINE_TOO_LONG
    assert "1000-character limit" in msg
    assert "1001 characters" in msg

    # API check
    resp = client.post("/api/analyze", json={"text": headline_1001})
    assert resp.status_code == 422
    data = resp.json()
    assert data.get("error_code") == ERROR_HEADLINE_TOO_LONG
    assert data.get("character_count") == 1001
    assert data.get("max_length") == 1000


def test_boundary_minimum_length():
    """Verify behavior around the 15-character minimum length boundary."""
    # A short financial statement under 15 characters (e.g. 14 chars)
    short_financial = "Fed rate cut 1"
    assert len(short_financial) == 14
    cleaned, code, msg = validate_financial_headline(short_financial)
    assert code == ERROR_HEADLINE_TOO_SHORT
    assert "Minimum required length is 15" in msg

    # Exactly 15 characters with financial relevance
    exact_15 = "Fed rate cut 10"
    assert len(exact_15) == 15
    cleaned, code, msg = validate_financial_headline(exact_15)
    assert code is None, f"Expected 15 chars to pass, got {code}: {msg}"


def test_invalid_input_never_invokes_inference_engines():
    """
    CRITICAL REQUIREMENT:
    Verify that invalid inputs NEVER invoke local FinBERT, Hugging Face API,
    or the lexical fallback, and never return fabricated scores.
    """
    with patch.object(finbert_service, "_predict_local_pytorch") as mock_local, \
         patch.object(finbert_service, "_predict_huggingface") as mock_hf, \
         patch.object(finbert_service, "_predict_lexical") as mock_lexical, \
         patch.object(finbert_service, "_predict_gemini") as mock_gemini:

        for invalid_text in ["hi", "hello", "I love pizza", "how are you", "12345", "a" * 1001]:
            resp = client.post("/api/analyze", json={"text": invalid_text})
            assert resp.status_code == 422

            # Assert zero calls to any inference engine
            assert mock_local.call_count == 0, f"Local PyTorch was called for {invalid_text!r}!"
            assert mock_hf.call_count == 0, f"Hugging Face API was called for {invalid_text!r}!"
            assert mock_lexical.call_count == 0, f"Lexical fallback was called for {invalid_text!r}!"
            assert mock_gemini.call_count == 0, f"Gemini engine was called for {invalid_text!r}!"


def test_batch_analyze_rejects_invalid_item():
    """Verify /api/analyze/batch rejects when any item in the batch is invalid."""
    batch_payload = {
        "texts": [
            "Apple reports record quarterly revenue, beating analyst expectations.",
            "hi"
        ]
    }
    resp = client.post("/api/analyze/batch", json=batch_payload)
    assert resp.status_code == 422
    assert resp.json().get("error_code") == ERROR_INVALID_FINANCIAL_HEADLINE
