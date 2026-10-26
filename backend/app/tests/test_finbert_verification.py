import pytest
from unittest.mock import patch, MagicMock
from app.services.finbert_service import finbert_service, FinBERTService
from app.config import settings

def test_positive_financial_text():
    """Tests sentiment analysis on clear positive financial text."""
    text = "Apple reported record-shattering revenue and massive operating margin expansion."
    result = finbert_service.predict_one(text, include_explanation=True)
    assert result["sentiment"] == "positive"
    assert result["scores"]["positive"] > result["scores"]["negative"]
    total = sum(result["scores"].values())
    assert 0.99 <= total <= 1.01
    assert result["confidence"] == result["scores"]["positive"]
    assert isinstance(result["tokens"], list)

def test_negative_financial_text():
    """Tests sentiment analysis on clear negative financial text."""
    text = "Company announces steep quarterly net loss and severe revenue decline."
    result = finbert_service.predict_one(text, include_explanation=True)
    assert result["sentiment"] == "negative"
    assert result["scores"]["negative"] > result["scores"]["positive"]
    total = sum(result["scores"].values())
    assert 0.99 <= total <= 1.01
    assert result["confidence"] == result["scores"]["negative"]

def test_neutral_corporate_announcement():
    """Tests sentiment analysis on neutral corporate scheduling news."""
    text = "The Federal Reserve scheduled its upcoming Federal Open Market Committee meeting for next Tuesday."
    result = finbert_service.predict_one(text, include_explanation=True)
    assert result["sentiment"] == "neutral"
    assert result["scores"]["neutral"] >= 0.50
    total = sum(result["scores"].values())
    assert 0.99 <= total <= 1.01

def test_mixed_financial_headline():
    """Tests response structure and probability validity on conflicting headline."""
    text = "Nvidia reported stellar revenue growth exceeding forecasts, but warned of severe supply disruptions."
    result = finbert_service.predict_one(text, include_explanation=True)
    assert result["sentiment"] in ("positive", "negative", "neutral")
    total = sum(result["scores"].values())
    assert 0.99 <= total <= 1.01
    assert 0.0 <= result["confidence"] <= 1.0

def test_hosted_huggingface_genuine_response_mapping():
    """Verifies that genuine Hugging Face Serverless API responses are mapped accurately."""
    mock_hf_response = [
        [
            {"label": "positive", "score": 0.8845},
            {"label": "negative", "score": 0.0655},
            {"label": "neutral", "score": 0.0500}
        ]
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_hf_response

    svc = FinBERTService()
    svc.cache.clear()
    svc.engine_mode = "hosted-huggingface"

    with patch("requests.post", return_value=mock_resp), \
         patch.object(settings, "HUGGINGFACE_API_KEY", "hf_mock_token_123"):
        result = svc._predict_huggingface("Apple reports record quarterly profits", include_explanation=False)
        assert result["sentiment"] == "positive"
        assert result["confidence"] == 0.8845
        assert result["scores"]["positive"] == 0.8845
        assert result["scores"]["negative"] == 0.0655
        assert result["scores"]["neutral"] == 0.0500
        assert result["is_fallback"] is False
        assert "Hosted Hugging Face" in result["model_name"]
        total = sum(result["scores"].values())
        assert 0.99 <= total <= 1.01

def test_hosted_huggingface_perturbation_salience():
    """Verifies genuine perturbation testing against the hosted model."""
    def fake_post(url, json=None, headers=None, timeout=None):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        inp = json.get("inputs", "") if json else ""
        if "record" in inp:
            # Full text with 'record'
            mock_resp.json.return_value = [[
                {"label": "positive", "score": 0.9200},
                {"label": "negative", "score": 0.0400},
                {"label": "neutral", "score": 0.0400}
            ]]
        else:
            # Perturbed text without 'record' has lower positive confidence
            mock_resp.json.return_value = [[
                {"label": "positive", "score": 0.7100},
                {"label": "negative", "score": 0.1500},
                {"label": "neutral", "score": 0.1400}
            ]]
        return mock_resp

    svc = FinBERTService()
    svc.cache.clear()
    svc.engine_mode = "hosted-huggingface"

    with patch("requests.post", side_effect=fake_post), \
         patch.object(settings, "HUGGINGFACE_API_KEY", "hf_mock_token_123"):
        result = svc._predict_huggingface("Apple reports record profits", include_explanation=True)
        assert result["sentiment"] == "positive"
        assert result["is_fallback"] is False
        tokens = result["tokens"]
        assert len(tokens) > 0
        # Check that the token impact was calculated via perturbation
        assert tokens[0]["method"] == "perturbation-delta"
        assert tokens[0]["impact"] == 0.2100  # 0.9200 - 0.7100

def test_provider_quota_exhaustion_routes_to_identified_fallback():
    """Verifies that HTTP 429 quota exhaustion from hosted provider routes to explicit fallback."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Rate limit exceeded"

    svc = FinBERTService()
    svc.cache.clear()
    svc.engine_mode = "hosted-huggingface"

    with patch("requests.post", return_value=mock_resp), \
         patch.object(settings, "HUGGINGFACE_API_KEY", "hf_mock_token_123"):
        result = svc._predict_huggingface("Apple reports surging cloud revenues", include_explanation=True)
        assert result["is_fallback"] is True
        assert result["engine_mode"] == "lexical-fallback"
        assert "Fallback" in result["model_name"]
        assert "rate limit" in result["explanation_note"].lower() or "429" in result["explanation_note"]
        # Verify tokens are not falsely labeled as perturbation
        for tok in result["tokens"]:
            assert tok["method"] == "lexicon-match"

def test_invalid_provider_response_handling():
    """Verifies that malformed provider responses are handled without unhandled 500 exceptions."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"unexpected_key": "bad_data"}  # Not a list of labels

    svc = FinBERTService()
    svc.cache.clear()
    svc.engine_mode = "hosted-huggingface"

    with patch("requests.post", return_value=mock_resp), \
         patch.object(settings, "HUGGINGFACE_API_KEY", "hf_mock_token_123"):
        result = svc._predict_huggingface("Tesla deliveries miss Wall Street forecasts", include_explanation=False)
        assert result["is_fallback"] is True
        assert result["engine_mode"] == "lexical-fallback"
        total = sum(result["scores"].values())
        assert 0.99 <= total <= 1.01

def test_missing_api_credentials_transparency():
    """Verifies that missing HUGGINGFACE_API_KEY cleanly flags fallback mode without claiming FinBERT."""
    svc = FinBERTService()
    svc.cache.clear()
    svc.engine_mode = "uninitialized"
    svc.status = "uninitialized"

    with patch.object(settings, "HUGGINGFACE_API_KEY", None), \
         patch.object(settings, "HUGGINGFACE_API_KEY_1", None), \
         patch.object(settings, "HUGGINGFACE_API_KEY_2", None), \
         patch.object(settings, "HUGGINGFACE_API_KEY_3", None), \
         patch.object(settings, "HUGGINGFACE_API_KEY_4", None), \
         patch.object(settings, "GEMINI_API_KEY", None), \
         patch.object(settings, "USE_LOCAL_FINBERT", False), \
         patch.object(settings, "FINBERT_INFERENCE_URL", None):
        svc.load_model()
        assert svc.engine_mode == "lexical-fallback"
        diag = svc.get_memory_diagnostics()
        assert diag["is_fallback"] is True
        assert diag["has_hf_token"] is False


def test_target_headline_indian_shares_fall():
    """
    Tests exact headline:
    'Indian Shares Fall as Rising Crude Oil Prices and Middle East Tensions Weigh on Investor Sentiment.'
    Verifies that the fallback naturally identifies the negative context (fall, tensions, weigh),
    calculates consistent heuristic weights summing to 1.0000, and provides non-zero keyword attribution.
    """
    text = "Indian Shares Fall as Rising Crude Oil Prices and Middle East Tensions Weigh on Investor Sentiment."
    svc = FinBERTService()
    svc.cache.clear()

    result = svc._predict_lexical(text, include_explanation=True)

    # 1. Correct sentiment identification
    assert result["sentiment"] == "negative"
    assert result["scores"]["negative"] > result["scores"]["positive"]
    assert result["scores"]["negative"] > result["scores"]["neutral"]

    # 2. Mathematical consistency: distribution sums to exactly 1.0000
    total_scores = sum(result["scores"].values())
    assert round(total_scores, 4) == 1.0
    assert result["confidence"] == result["scores"]["negative"]

    # 3. Honest fallback metadata
    assert result["is_fallback"] is True
    assert result["engine_mode"] == "lexical-fallback"
    assert "Loughran-McDonald Institutional Lexicon (Rule-Based Fallback)" == result["model_name"]
    assert "heuristic polarity weights" in result["explanation_note"]
    assert "not calibrated neural probabilities" in result["explanation_note"]

    # 4. Explainability: matched negative keywords with non-zero directional contribution
    tokens = result["tokens"]
    assert len(tokens) >= 3
    matched_words = [t["token"].lower() for t in tokens]
    assert "fall" in matched_words
    assert "tensions" in matched_words
    assert "weigh" in matched_words

    for t in tokens:
        assert t["impact"] != 0.0
        assert t["impact"] < 0  # Negative directional contribution
        assert t["direction"] == "negative"
        assert t["method"] == "lexicon-match"


def test_lexical_fallback_across_sentiments():
    """Verifies that rule-based fallback correctly handles positive, negative, neutral, and mixed headlines."""
    svc = FinBERTService()

    # Positive headline
    pos_res = svc._predict_lexical("Company announces record profits, surging revenue growth, and dividend boost.", include_explanation=True)
    assert pos_res["sentiment"] == "positive"
    assert pos_res["scores"]["positive"] > pos_res["scores"]["negative"]
    assert round(sum(pos_res["scores"].values()), 4) == 1.0
    assert len(pos_res["tokens"]) > 0
    assert pos_res["tokens"][0]["impact"] > 0
    assert pos_res["tokens"][0]["direction"] == "positive"

    # Negative headline
    neg_res = svc._predict_lexical("Bank faces severe liquidity crisis, credit downgrade, and mounting loan defaults.", include_explanation=True)
    assert neg_res["sentiment"] == "negative"
    assert neg_res["scores"]["negative"] > neg_res["scores"]["positive"]
    assert round(sum(neg_res["scores"].values()), 4) == 1.0
    assert len(neg_res["tokens"]) > 0
    assert neg_res["tokens"][0]["impact"] < 0
    assert neg_res["tokens"][0]["direction"] == "negative"

    # Neutral headline (informational financial announcement without polar keywords)
    neu_res = svc._predict_lexical("Federal Reserve publishes calendar for scheduled monetary policy meetings.", include_explanation=True)
    assert neu_res["sentiment"] == "neutral"
    assert neu_res["scores"]["neutral"] >= 0.50
    assert round(sum(neu_res["scores"].values()), 4) == 1.0

    # Mixed headline (contains both positive and negative signals)
    mixed_res = svc._predict_lexical("Tech firm reports record revenue growth but warns of margin slump and profit decline.", include_explanation=True)
    assert round(sum(mixed_res["scores"].values()), 4) == 1.0
    assert mixed_res["scores"]["positive"] > 0.05
    assert mixed_res["scores"]["negative"] > 0.05
    # Both directions present in tokens
    token_directions = {t["direction"] for t in mixed_res["tokens"]}
    assert "positive" in token_directions
    assert "negative" in token_directions


# -------------------------------------------------------------------------------------------------
# MULTI-KEY HUGGING FACE INFERENCE & ERROR HANDLING TESTS (SIMULATED VIA MOCKS)
# Note: These tests use mocked HTTP responses to verify error handling and failover algorithms.
# They validate logic and do not claim that live Hugging Face inference is operational.
# -------------------------------------------------------------------------------------------------

def test_settings_get_huggingface_api_keys_deduplication():
    """Verifies that Settings correctly collects, trims, and deduplicates up to 4 keys in priority order."""
    with patch.object(settings, "HUGGINGFACE_API_KEY_1", "  hf_key_primary  "), \
         patch.object(settings, "HUGGINGFACE_API_KEY_2", "hf_key_secondary"), \
         patch.object(settings, "HUGGINGFACE_API_KEY_3", "hf_key_primary"), \
         patch.object(settings, "HUGGINGFACE_API_KEY_4", "  "), \
         patch.object(settings, "HUGGINGFACE_API_KEY", "hf_legacy_fallback"):
        keys = settings.get_huggingface_api_keys()
        assert keys == ["hf_key_primary", "hf_key_secondary", "hf_legacy_fallback"]
        assert len(keys) == 3


def test_multi_key_successful_inference_on_primary_key():
    """
    Tests that when the primary configured key succeeds with HTTP 200,
    it returns genuine ProsusAI/finbert output without trying secondary keys.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [[
        {"label": "positive", "score": 0.9421},
        {"label": "negative", "score": 0.0210},
        {"label": "neutral", "score": 0.0369}
    ]]

    svc = FinBERTService()
    svc.cache.clear()
    svc.engine_mode = "hosted-huggingface"

    with patch("requests.post", return_value=mock_resp) as mock_post, \
         patch.object(settings, "HUGGINGFACE_API_KEY_1", "hf_key_1"), \
         patch.object(settings, "HUGGINGFACE_API_KEY_2", "hf_key_2"), \
         patch.object(settings, "HUGGINGFACE_API_KEY_3", None), \
         patch.object(settings, "HUGGINGFACE_API_KEY_4", None), \
         patch.object(settings, "HUGGINGFACE_API_KEY", None):
        result = svc._predict_huggingface("Apple reports record quarterly sales", include_explanation=False)

        assert result["is_fallback"] is False
        assert result["sentiment"] == "positive"
        assert result["confidence"] == 0.9421
        assert result["engine_mode"] == "hosted-huggingface"
        # Primary key succeeded, so only 1 HTTP request should have been made
        assert mock_post.call_count == 1
        # Verify the Authorization header used key 1
        call_headers = mock_post.call_args[1]["headers"]
        assert call_headers["Authorization"] == "Bearer hf_key_1"


def test_key_failover_on_authentication_error_401():
    """
    Tests key failover: Key 1 returns 401 Unauthorized, Key 2 succeeds with 200 OK.
    Verifies that the backend cleanly fails over to Key 2 for genuine FinBERT inference.
    """
    resp_401 = MagicMock()
    resp_401.status_code = 401
    resp_401.text = "Invalid token"

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = [[
        {"label": "positive", "score": 0.9150},
        {"label": "negative", "score": 0.0420},
        {"label": "neutral", "score": 0.0430}
    ]]

    svc = FinBERTService()
    svc.cache.clear()
    svc.engine_mode = "hosted-huggingface"

    with patch("requests.post", side_effect=[resp_401, resp_200]) as mock_post, \
         patch.object(settings, "HUGGINGFACE_API_KEY_1", "hf_expired_key"), \
         patch.object(settings, "HUGGINGFACE_API_KEY_2", "hf_valid_key"), \
         patch.object(settings, "HUGGINGFACE_API_KEY_3", None), \
         patch.object(settings, "HUGGINGFACE_API_KEY_4", None), \
         patch.object(settings, "HUGGINGFACE_API_KEY", None):
        result = svc._predict_huggingface("Microsoft reports stronger cloud profits", include_explanation=False)

        assert result["is_fallback"] is False
        assert result["sentiment"] == "positive"
        assert result["confidence"] == 0.9150
        # Exactly 2 requests: first failed with 401, second succeeded
        assert mock_post.call_count == 2
        first_call_headers = mock_post.call_args_list[0][1]["headers"]
        second_call_headers = mock_post.call_args_list[1][1]["headers"]
        assert first_call_headers["Authorization"] == "Bearer hf_expired_key"
        assert second_call_headers["Authorization"] == "Bearer hf_valid_key"


def test_key_failover_on_rate_limit_429():
    """
    Tests key failover: Key 1 returns 429 Too Many Requests, Key 2 succeeds.
    Verifies that an independent credential with available capacity is tried and used.
    """
    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.text = "Rate limit reached"

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = [[
        {"label": "negative", "score": 0.8750},
        {"label": "positive", "score": 0.0550},
        {"label": "neutral", "score": 0.0700}
    ]]

    svc = FinBERTService()
    svc.cache.clear()
    svc.engine_mode = "hosted-huggingface"

    with patch("requests.post", side_effect=[resp_429, resp_200]) as mock_post, \
         patch.object(settings, "HUGGINGFACE_API_KEY_1", "hf_rate_limited_key"), \
         patch.object(settings, "HUGGINGFACE_API_KEY_2", "hf_fresh_key"), \
         patch.object(settings, "HUGGINGFACE_API_KEY_3", None), \
         patch.object(settings, "HUGGINGFACE_API_KEY_4", None), \
         patch.object(settings, "HUGGINGFACE_API_KEY", None):
        result = svc._predict_huggingface("Tesla deliveries miss Wall Street consensus", include_explanation=False)

        assert result["is_fallback"] is False
        assert result["sentiment"] == "negative"
        assert result["confidence"] == 0.8750
        assert mock_post.call_count == 2


def test_payment_error_402_halts_failover_and_falls_back():
    """
    Requirements 5 & 8:
    Do not assume HTTP 402 can be fixed by switching keys.
    Do not rotate keys to bypass provider billing limits.
    Verifies that when HTTP 402 is returned, failover halts immediately and routes to Loughran-McDonald fallback.
    """
    resp_402 = MagicMock()
    resp_402.status_code = 402
    resp_402.text = '{"error":"You have no remaining credits for serverless Inference Providers."}'

    svc = FinBERTService()
    svc.cache.clear()
    svc.engine_mode = "hosted-huggingface"

    with patch("requests.post", return_value=resp_402) as mock_post, \
         patch.object(settings, "HUGGINGFACE_API_KEY_1", "hf_key_1"), \
         patch.object(settings, "HUGGINGFACE_API_KEY_2", "hf_key_2"), \
         patch.object(settings, "HUGGINGFACE_API_KEY_3", "hf_key_3"), \
         patch.object(settings, "HUGGINGFACE_API_KEY_4", "hf_key_4"), \
         patch.object(settings, "HUGGINGFACE_API_KEY", None):
        result = svc._predict_huggingface("Alphabet announces quarterly revenue surge", include_explanation=False)

        # Must fall back gracefully
        assert result["is_fallback"] is True
        assert result["engine_mode"] == "lexical-fallback"
        assert "Loughran-McDonald" in result["model_name"]
        assert "402" in result["explanation_note"]
        # CRITICAL: requests.post must NOT rotate through key_2, key_3, key_4
        assert mock_post.call_count == 1


def test_server_error_5xx_halts_failover():
    """
    Requirement 4: Switching keys will not resolve provider infrastructure outages (500/503).
    Verifies that 5xx errors halt failover and fall back without trying other keys unnecessarily.
    """
    resp_503 = MagicMock()
    resp_503.status_code = 503
    resp_503.text = "Service Unavailable"

    svc = FinBERTService()
    svc.cache.clear()
    svc.engine_mode = "hosted-huggingface"

    with patch("requests.post", return_value=resp_503) as mock_post, \
         patch.object(settings, "HUGGINGFACE_API_KEY_1", "hf_key_1"), \
         patch.object(settings, "HUGGINGFACE_API_KEY_2", "hf_key_2"):
        result = svc._predict_huggingface("Market closes higher as inflation moderates", include_explanation=False)

        assert result["is_fallback"] is True
        assert result["engine_mode"] == "lexical-fallback"
        assert "503" in result["explanation_note"]
        assert mock_post.call_count == 1


def test_all_keys_authentication_failure():
    """Tests that when all configured keys fail with 401, the system cleanly falls back to Loughran-McDonald."""
    resp_401 = MagicMock()
    resp_401.status_code = 401
    resp_401.text = "Unauthorized"

    svc = FinBERTService()
    svc.cache.clear()
    svc.engine_mode = "hosted-huggingface"

    with patch("requests.post", return_value=resp_401) as mock_post, \
         patch.object(settings, "HUGGINGFACE_API_KEY_1", "hf_bad_1"), \
         patch.object(settings, "HUGGINGFACE_API_KEY_2", "hf_bad_2"):
        result = svc._predict_huggingface("Nvidia graphics processor demand surges", include_explanation=False)

        assert result["is_fallback"] is True
        assert result["engine_mode"] == "lexical-fallback"
        # Both keys were attempted before falling back
        assert mock_post.call_count == 2


def test_network_timeout_routes_to_fallback():
    """Verifies that network timeout exceptions are caught cleanly without unhandled server 500s."""
    import requests

    svc = FinBERTService()
    svc.cache.clear()
    svc.engine_mode = "hosted-huggingface"

    with patch("requests.post", side_effect=requests.exceptions.Timeout("Connection timed out")), \
         patch.object(settings, "HUGGINGFACE_API_KEY_1", "hf_key_1"):
        result = svc._predict_huggingface("Amazon beats earnings estimates for Q3", include_explanation=False)

        assert result["is_fallback"] is True
        assert result["engine_mode"] == "lexical-fallback"
        assert "timed out" in result["explanation_note"].lower()


def test_api_keys_never_exposed_in_responses():
    """Verifies that API key secrets are never exposed in prediction results or memory diagnostics."""
    secret_key = "hf_SUPER_SECRET_TOKEN_DO_NOT_LEAK_999"

    resp_401 = MagicMock()
    resp_401.status_code = 401
    resp_401.text = "Unauthorized"

    svc = FinBERTService()
    svc.cache.clear()
    svc.engine_mode = "hosted-huggingface"

    with patch("requests.post", return_value=resp_401), \
         patch.object(settings, "HUGGINGFACE_API_KEY_1", secret_key):
        result = svc._predict_huggingface("Federal Reserve announces rate policy", include_explanation=False)
        diagnostics = svc.get_memory_diagnostics()

        # Check all string representations
        res_str = str(result)
        diag_str = str(diagnostics)
        assert secret_key not in res_str
        assert secret_key not in diag_str
        assert diagnostics["has_hf_token"] is True
        assert diagnostics["configured_hf_keys_count"] == 1


# -------------------------------------------------------------------------------------------------
# LOCAL FINBERT PYTORCH VERIFICATION TESTS
# -------------------------------------------------------------------------------------------------

def test_local_finbert_weights_and_tokenizer_complete():
    """Verifies that backend/data/finbert_bfloat16 contains all 6 required Hugging Face files."""
    import os

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    local_bfloat16_dir = os.path.join(base_dir, "data", "finbert_bfloat16")

    required_files = [
        "config.json",
        "model.safetensors",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.txt"
    ]
    assert os.path.exists(local_bfloat16_dir), f"Model directory {local_bfloat16_dir} missing"
    for fname in required_files:
        fpath = os.path.join(local_bfloat16_dir, fname)
        assert os.path.exists(fpath), f"Missing required file: {fname}"
        assert os.path.getsize(fpath) > 0, f"File {fname} is empty"


def test_local_finbert_real_inference_target_headline():
    """
    Runs genuine local FinBERT neural inference on the target headline:
    'Indian Shares Fall as Rising Crude Oil Prices and Middle East Tensions Weigh on Investor Sentiment.'
    Verifies that real neural inference succeeds, is_fallback is False, and returns calibrated probabilities.
    """
    text = "Indian Shares Fall as Rising Crude Oil Prices and Middle East Tensions Weigh on Investor Sentiment."
    svc = FinBERTService()
    svc.cache.clear()

    # Load local model
    assert svc._load_local_pytorch() is True

    result = svc.predict_one(text, include_explanation=True)

    # 1. Verification of genuine neural inference
    assert result["is_fallback"] is False
    assert result["engine_mode"] == "local-bfloat16"
    assert "local-bfloat16" in result["model_name"]

    # 2. Probability verification
    assert result["sentiment"] == "negative"
    assert result["scores"]["negative"] > 0.90
    assert result["scores"]["positive"] < 0.05
    assert result["scores"]["neutral"] < 0.10
    total = sum(result["scores"].values())
    assert 0.99 <= total <= 1.01

    # 3. Genuine perturbation explainability
    assert isinstance(result["tokens"], list)
    assert len(result["tokens"]) > 0
    token_methods = {t["method"] for t in result["tokens"]}
    assert "perturbation-delta" in token_methods



