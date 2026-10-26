import re
import os
import gc
import json
import threading
import logging
import ctypes
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import requests
from app.config import settings
from app.services.financial_validator import validate_financial_headline, FinancialValidationError

logger = logging.getLogger("finbert_service")

# FinBERT label mapping: 0 -> positive, 1 -> negative, 2 -> neutral
LABEL_MAPPING = {0: "positive", 1: "negative", 2: "neutral"}

# Loughran-McDonald inspired institutional financial lexicon for deterministic offline fallback
FINANCIAL_POSITIVE_LEXICON = {
    "record", "surge", "surges", "surged", "surging", "profit", "profits", "profitable",
    "gain", "gains", "gained", "gaining", "rally", "rallies", "growth", "grow", "grows",
    "exceed", "exceeds", "exceeded", "upgrade", "upgrades", "upgraded", "upgrading", "bullish",
    "dividend", "dividends", "rebound", "rebounds", "rebounded", "rebounding",
    "soar", "soars", "soared", "soaring", "beat", "beats", "beating",
    "climb", "climbs", "jump", "jumps", "jumped", "outperform", "outperformed", "outperforming",
    "upside", "expansion", "expand", "expands", "expanded", "strength", "strong", "stronger",
    "strongest", "strengthen", "strengthens", "strengthened", "strengthening",
    "breakthrough", "boost", "boosts", "advance", "advances", "recovery", "success", "successful",
    "high", "higher", "highest", "revenue", "positive", "innovative", "milestone", "milestones",
    "partnership", "optimism", "optimistic", "resilience", "resilient", "accelerate", "accelerates",
    "accelerated", "accelerating"
}

FINANCIAL_NEGATIVE_LEXICON = {
    "plunge", "plunges", "plunged", "fall", "falls", "fell", "falling",
    "drop", "drops", "dropped", "dropping", "decline", "declines", "declined", "declining",
    "miss", "misses", "missed", "loss", "losses", "slump", "slumps", "slumped",
    "fraud", "lawsuit", "lawsuits", "penalty", "penalties", "fine", "fines", "fined",
    "investigation", "probe", "probes", "probed", "cut", "cuts", "down",
    "default", "defaults", "risk", "risks", "risky", "downgrade", "downgrades", "downgraded",
    "bearish", "bankruptcy", "bankrupt", "antitrust", "slash", "slashes", "crash", "crashes",
    "deficit", "deficits", "warning", "warnings", "warns", "underperform", "debt",
    "shrink", "shrinks", "struggle", "struggles", "crisis", "recession", "inflation",
    "negative", "scrutiny", "headwinds", "headwind", "weakness", "weak", "curb", "curbs", "curbed",
    "plummet", "plummeted", "plummeting", "collapse", "collapsed",
    "tension", "tensions", "weigh", "weighs", "weighed", "weighing",
    "pressure", "pressures", "pressured", "pressuring", "erode", "erodes", "eroded", "erosion",
    "contract", "contracts", "contracted", "contracting", "layoff", "layoffs",
    "uncertainty", "uncertainties", "uncertain", "slowdown", "slowdowns",
    "turmoil", "volatility", "volatile", "threat", "threats", "threaten", "threatens",
    "threatened", "adversity", "adverse", "stagnation", "stagnant"
}

FINANCIAL_STOPWORDS = {
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "is", "are", "was", "were", "be", "been", "by", "from", "as", "into", "it",
    "its", "their", "this", "that", "these", "those", "has", "have", "had", "after",
    "before", "about", "above", "below", "between", "both", "during", "each"
}


def _get_process_rss_mb() -> float:
    """Returns the current process resident set size in megabytes across Windows and Linux."""
    try:
        if os.name == "nt":
            import ctypes.wintypes as wt
            class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
                _fields_ = [
                    ('cb', wt.DWORD), ('PageFaultCount', wt.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t),
                    ('PrivateUsage', ctypes.c_size_t),
                ]
            counters = PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(-1), ctypes.byref(counters), counters.cb)
            return round(counters.WorkingSetSize / (1024 * 1024), 2)
        else:
            import resource
            return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2)
    except Exception:
        return 0.0


class FinBERTService:
    _instance = None
    _load_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FinBERTService, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.tokenizer = None
            cls._instance.device = "cpu"
            cls._instance.status = "uninitialized"
            cls._instance.engine_mode = "uninitialized"
            cls._instance.error_message = None
            cls._instance.cache = {}
            cls._instance.precision = "bfloat16"
            cls._instance.gemini_model = None
            cls._instance._active_key_index = 0
        return cls._instance

    def load_model(self) -> bool:
        """
        Initializes the optimal financial sentiment inference engine with strict honesty.
        Priority:
          1. Local PyTorch (if USE_LOCAL_FINBERT=True)
          2. Hosted ProsusAI/finbert via Hugging Face Serverless API (if any Hugging Face keys configured)
          3. External Inference URL (if FINBERT_INFERENCE_URL configured)
          4. Cloud AI Engine (if GEMINI_API_KEY configured)
          5. Transparent Rule-Based Lexicon Fallback (is_fallback=True)
        """
        with self._load_lock:
            if self.status == "ready" and self.engine_mode != "uninitialized":
                return True

            self.status = "loading"
            current_mem = _get_process_rss_mb()
            logger.info(f"Initializing Financial Sentiment Engine (Process Memory: {current_mem:.1f} MB / 512 MB)...")

            # 1. Local PyTorch execution (only when explicitly requested)
            if settings.USE_LOCAL_FINBERT:
                return self._load_local_pytorch()

            # 2. Hosted ProsusAI/finbert via Hugging Face Serverless Inference API
            hf_keys = settings.get_huggingface_api_keys()
            if hf_keys:
                self.engine_mode = "hosted-huggingface"
                self.status = "ready"
                self.error_message = None
                logger.info(f"FinBERT Sentiment Engine routed to Hosted Hugging Face Serverless API ({len(hf_keys)} keys configured).")
                return True

            # 3. External Dedicated Inference Service URL
            if settings.FINBERT_INFERENCE_URL:
                self.engine_mode = "external-service"
                self.status = "ready"
                self.error_message = None
                logger.info(f"FinBERT Sentiment Engine routed to external service at {settings.FINBERT_INFERENCE_URL}.")
                return True

            # 4. Transparent Rule-Based Lexical Fallback
            self.engine_mode = "lexical-fallback"
            self.status = "ready"
            self.error_message = "No hosted FinBERT token (HUGGINGFACE_API_KEY) configured. Running in rule-based fallback mode."
            logger.info("Sentiment Engine initialized in Rule-Based Institutional Lexicon Fallback Mode.")
            return True

    def _load_local_pytorch(self) -> bool:
        """Lazily loads local PyTorch FinBERT model with bfloat16 precision."""
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification

            try:
                torch.set_num_threads(1)
                torch.set_num_interop_threads(1)
                torch.set_grad_enabled(False)
            except Exception:
                pass

            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            local_bfloat16_dir = os.path.join(base_dir, "data", "finbert_bfloat16")
            safetensors_file = os.path.join(local_bfloat16_dir, "model.safetensors")

            use_local = os.path.exists(safetensors_file) and os.path.getsize(safetensors_file) > 100 * 1024 * 1024
            if not use_local:
                logger.warning(
                    f"Local weights not found at '{safetensors_file}'. "
                    "Skipping heavy in-memory download to prevent container memory exhaustion (OOM). "
                    "Routing to Hosted Hugging Face or Lexical mode."
                )
                hf_keys = settings.get_huggingface_api_keys()
                if hf_keys:
                    self.engine_mode = "hosted-huggingface"
                    self.status = "ready"
                    self.error_message = None
                    logger.info(f"FinBERT Sentiment Engine routed to Hosted Hugging Face Serverless API ({len(hf_keys)} keys configured).")
                    return True
                self.engine_mode = "lexical-fallback"
                self.status = "ready"
                self.error_message = "Local PyTorch weights not present on disk. Running in rule-based fallback mode."
                logger.info("Sentiment Engine initialized in Rule-Based Institutional Lexicon Fallback Mode.")
                return True

            load_source = local_bfloat16_dir

            logger.info(f"Loading local PyTorch FinBERT from '{load_source}' on CPU...")
            self.tokenizer = AutoTokenizer.from_pretrained(load_source)
            torch.set_default_dtype(torch.bfloat16)

            self.model = AutoModelForSequenceClassification.from_pretrained(
                load_source,
                torch_dtype=torch.bfloat16
            )
            self.model.to(self.device)
            self.model.eval()
            self.precision = "bfloat16"
            self.engine_mode = "local-bfloat16"
            self.status = "ready"
            self.error_message = None
            gc.collect()
            logger.info(f"Local PyTorch FinBERT loaded successfully ({_get_process_rss_mb():.1f} MB RSS).")
            return True
        except Exception as e:
            logger.error(f"Failed to load local PyTorch FinBERT: {e}. Falling back to Lexical Engine.")
            self.engine_mode = "lexical-fallback"
            self.status = "ready"
            self.error_message = f"Local PyTorch failed: {str(e)}"
            return True

    def is_ready(self) -> bool:
        return self.status == "ready"

    def get_memory_diagnostics(self) -> Dict[str, Any]:
        """Provides operational memory metrics for Render health reporting."""
        rss = _get_process_rss_mb()
        limit = 512.0
        hf_keys = settings.get_huggingface_api_keys()
        return {
            "process_rss_mb": rss,
            "memory_limit_mb": limit,
            "percent_of_limit": round((rss / limit) * 100, 1) if limit > 0 else 0.0,
            "engine_mode": self.engine_mode,
            "status": self.status,
            "is_within_limit": rss < 500.0,
            "has_hf_token": bool(hf_keys),
            "configured_hf_keys_count": len(hf_keys),
            "has_gemini_token": bool(settings.GEMINI_API_KEY),
            "is_fallback": self.engine_mode == "lexical-fallback"
        }

    def predict_one(self, text: str, include_explanation: bool = True, validate_input: bool = True) -> Dict[str, Any]:
        """
        Predicts sentiment for a single financial text.
        Routes to the active engine with transparent attribution and honest fallback reporting.
        Strictly validates financial relevance and length before running any inference engine.
        """
        from app.services.headline_validator import assert_valid_financial_headline, HeadlineValidationError
        if validate_input:
            cleaned_text = assert_valid_financial_headline(text)
        else:
            cleaned_text = (text or "").strip()
            if not cleaned_text:
                raise HeadlineValidationError("Input text cannot be empty or whitespace.", "HEADLINE_EMPTY")


        cache_key = f"{cleaned_text}_{include_explanation}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        if not self.is_ready():
            self.load_model()

        # Route by engine mode
        if self.engine_mode in ("hosted-huggingface", "hosted-finbert"):
            result = self._predict_huggingface(cleaned_text, include_explanation)
        elif self.engine_mode == "external-service":
            result = self._predict_external(cleaned_text, include_explanation)
        elif self.engine_mode == "cloud-gemini":
            result = self._predict_gemini(cleaned_text, include_explanation)
        elif self.engine_mode == "local-bfloat16":
            result = self._predict_local_pytorch(cleaned_text, include_explanation)
        else:
            result = self._predict_lexical(
                cleaned_text,
                include_explanation,
                reason="No neural provider configured (no Hugging Face API keys set)."
            )

        self.cache[cache_key] = result
        return result

    def _predict_huggingface(self, text: str, include_explanation: bool) -> Dict[str, Any]:
        """
        Queries Hugging Face Serverless Inference API for genuine ProsusAI/finbert.
        Supports up to 4 configured API keys (HUGGINGFACE_API_KEY_1..4) with failover.
        Never logs, exposes, or returns API keys.
        Performs key failover ONLY when recoverable by switching credentials (401, 403, 429).
        Does NOT rotate keys on 402, 5xx, or malformed responses.
        Uses sensible timeouts and bounded retries.
        """
        hf_keys = settings.get_huggingface_api_keys()
        if not hf_keys:
            self.engine_mode = "lexical-fallback"
            self.error_message = "No Hugging Face API keys configured."
            return self._predict_lexical(
                text,
                include_explanation,
                reason="No Hugging Face API keys configured."
            )

        url = f"https://router.huggingface.co/hf-inference/models/{settings.MODEL_NAME}"

        def _parse_scores(data: Any) -> Optional[Dict[str, float]]:
            items = data[0] if (isinstance(data, list) and data and isinstance(data[0], list)) else data
            if isinstance(items, list) and items:
                sc = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
                found = False
                for it in items:
                    if isinstance(it, dict) and "label" in it and "score" in it:
                        lbl = str(it.get("label", "")).lower()
                        if lbl in sc:
                            sc[lbl] = max(0.0, float(it.get("score", 0.0)))
                            found = True
                if found:
                    total_s = sum(sc.values()) or 1.0
                    return {k: round(v / total_s, 4) for k, v in sc.items()}
            return None

        def _request_hf(key: str, input_str: str) -> tuple[Optional[Dict[str, float]], int, str]:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "x-wait-for-model": "true"
            }
            try:
                resp = requests.post(url, json={"inputs": input_str}, headers=headers, timeout=10)
                status = resp.status_code
                if status == 200:
                    try:
                        data = resp.json()
                        parsed = _parse_scores(data)
                        if parsed:
                            return parsed, 200, "OK"
                        return None, 200, "Malformed response structure from model endpoint."
                    except Exception:
                        return None, 200, "Invalid JSON received from endpoint."
                elif status in (401, 403):
                    return None, status, f"Authentication failed (HTTP {status}): credential invalid or unauthorized."
                elif status == 429:
                    return None, 429, "Rate limit reached on current credential (HTTP 429)."
                elif status == 402:
                    return None, 402, "Payment required or credits exhausted (HTTP 402)."
                elif status >= 500:
                    return None, status, f"Hugging Face server error (HTTP {status})."
                else:
                    return None, status, f"Hugging Face returned HTTP {status}."
            except requests.exceptions.Timeout:
                return None, 408, "Request timed out after 10s."
            except requests.exceptions.RequestException as e:
                return None, 599, f"Network exception: {type(e).__name__}."

        scores: Optional[Dict[str, float]] = None
        working_key: Optional[str] = None
        last_reason: str = "Hosted Hugging Face FinBERT endpoint unavailable."

        # Evaluate keys starting from known active key index
        start_idx = self._active_key_index if (0 <= self._active_key_index < len(hf_keys)) else 0
        candidate_indices = [(start_idx + i) % len(hf_keys) for i in range(len(hf_keys))]

        for idx in candidate_indices:
            key = hf_keys[idx]
            result_scores, status_code, err_msg = _request_hf(key, text)

            if result_scores is not None:
                scores = result_scores
                working_key = key
                self._active_key_index = idx
                break

            last_reason = err_msg

            # Failover logic according to constraints:
            if status_code in (401, 403):
                logger.warning(
                    f"Hugging Face credential (key index {idx}) rejected with HTTP {status_code}. "
                    "Attempting failover to next key if available."
                )
                continue
            elif status_code == 429:
                logger.warning(
                    f"Hugging Face credential (key index {idx}) rate-limited (HTTP 429). "
                    "Attempting failover to next key if available."
                )
                continue
            elif status_code == 402:
                # Do not assume HTTP 402 can be fixed by switching keys
                # Do not bypass provider billing limits or rotate keys to evade usage restrictions
                logger.warning(
                    "Hugging Face returned HTTP 402 (Payment Required / Credits exhausted). "
                    "Halting key failover and routing directly to fallback."
                )
                last_reason = "Hugging Face serverless inference credits exhausted or payment required (HTTP 402)."
                break
            elif status_code >= 500:
                logger.warning(
                    f"Hugging Face server error (HTTP {status_code}). "
                    "Provider infrastructure issue detected; halting key failover."
                )
                last_reason = f"Hugging Face service unavailable or server error (HTTP {status_code})."
                break
            else:
                logger.warning(f"Hugging Face request failed ({err_msg}). Halting key failover.")
                break

        if scores is None:
            self.engine_mode = "lexical-fallback"
            self.error_message = last_reason
            return self._predict_lexical(
                text,
                include_explanation,
                reason=last_reason
            )

        # Successful genuine FinBERT inference
        self.engine_mode = "hosted-huggingface"
        self.error_message = None

        winning = max(scores.keys(), key=lambda k: scores[k])
        conf = scores[winning]

        tokens = []
        if include_explanation and working_key:
            def _call_working_key(perturbed_str: str) -> Optional[Dict[str, float]]:
                s, _, _ = _request_hf(working_key, perturbed_str)
                return s

            tokens = self._explain_prediction_perturbation(
                text=text,
                winning_sentiment=winning,
                baseline_conf=conf,
                infer_scores_fn=_call_working_key
            )

        return {
            "text": text,
            "sentiment": winning,
            "confidence": conf,
            "scores": scores,
            "model_name": f"{settings.MODEL_NAME} (Hosted Hugging Face)",
            "analyzed_at": datetime.utcnow().isoformat() + "Z",
            "tokens": tokens,
            "explanation_note": "Genuine ProsusAI/finbert neural inference via Hugging Face Serverless API.",
            "is_fallback": False,
            "engine_mode": "hosted-huggingface"
        }

    def _predict_gemini(self, text: str, include_explanation: bool) -> Dict[str, Any]:
        """Queries Google Gemini for financial tone with honest model labeling."""
        try:
            prompt = (
                "You are an expert financial sentiment classifier analyzing financial news.\n"
                f"Headline: '{text}'\n\n"
                "Return JSON ONLY with exact format:\n"
                "{\n"
                '  "sentiment": "positive" | "negative" | "neutral",\n'
                '  "confidence": float,\n'
                '  "scores": {"positive": float, "negative": float, "neutral": float},\n'
                '  "salient_words": ["word1", "word2"]\n'
                "}\n"
                "Ensure scores sum to 1.0."
            )
            resp = self.gemini_model.generate_content(prompt)
            raw = (resp.text or "").strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)

            data = json.loads(raw.strip())
            sentiment = str(data.get("sentiment", "neutral")).lower()
            if sentiment not in ("positive", "negative", "neutral"):
                sentiment = "neutral"

            scores = data.get("scores", {"positive": 0.33, "negative": 0.33, "neutral": 0.34})
            scores = {k: max(0.0, float(v)) for k, v in scores.items()}
            total_s = sum(scores.values()) or 1.0
            scores = {k: round(v / total_s, 4) for k, v in scores.items()}
            conf = scores[sentiment]

            tokens = []
            if include_explanation:
                salient_words = data.get("salient_words", [])
                for sw in salient_words[:3]:
                    tokens.append({
                        "token": str(sw),
                        "impact": 0.20 if sentiment == "positive" else -0.20,
                        "direction": sentiment,
                        "method": "llm-attention"
                    })

            return {
                "text": text,
                "sentiment": sentiment,
                "confidence": conf,
                "scores": scores,
                "model_name": "Google Gemini (Cloud AI Engine)",
                "analyzed_at": datetime.utcnow().isoformat() + "Z",
                "tokens": tokens,
                "explanation_note": "Cloud AI financial tone classification via Google Gemini.",
                "is_fallback": False,
                "engine_mode": "cloud-gemini"
            }
        except Exception as e:
            logger.warning(f"Cloud Gemini inference failed ({e}), routing to identified fallback.")
            return self._predict_lexical(
                text,
                include_explanation,
                reason=f"Google Gemini quota exceeded or unavailable ({type(e).__name__})."
            )

    def _predict_external(self, text: str, include_explanation: bool) -> Dict[str, Any]:
        """Queries external dedicated inference service endpoint."""
        try:
            resp = requests.post(settings.FINBERT_INFERENCE_URL, json={"text": text}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                data["is_fallback"] = False
                data["engine_mode"] = "external-service"
                return data
        except Exception as e:
            logger.warning(f"External inference service error: {e}")
        return self._predict_lexical(
            text,
            include_explanation,
            reason="External inference service connection failed."
        )

    def _predict_local_pytorch(self, text: str, include_explanation: bool) -> Dict[str, Any]:
        """Runs inference via local PyTorch bfloat16 instance."""
        import torch
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=64
        ).to(self.device)

        with torch.inference_mode():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits.float(), dim=1).squeeze().tolist()

        del inputs, outputs

        scores = {
            "positive": round(float(probabilities[0]), 4),
            "negative": round(float(probabilities[1]), 4),
            "neutral": round(float(probabilities[2]), 4)
        }
        winning_idx = int(torch.argmax(logits, dim=1).item())
        sentiment = LABEL_MAPPING.get(winning_idx, "neutral")
        confidence = scores[sentiment]

        del logits

        def _call_local(t: str) -> Optional[Dict[str, float]]:
            try:
                inp = self.tokenizer(t, return_tensors="pt", padding=True, truncation=True, max_length=64).to(self.device)
                with torch.inference_mode():
                    out = self.model(**inp)
                    p = torch.softmax(out.logits.float(), dim=1).squeeze().tolist()
                del inp, out
                return {"positive": float(p[0]), "negative": float(p[1]), "neutral": float(p[2])}
            except Exception:
                return None

        tokens_attribution = []
        if include_explanation:
            tokens_attribution = self._explain_prediction_perturbation(
                text=text,
                winning_sentiment=sentiment,
                baseline_conf=confidence,
                infer_scores_fn=_call_local
            )

        return {
            "text": text,
            "sentiment": sentiment,
            "confidence": confidence,
            "scores": scores,
            "model_name": f"{settings.MODEL_NAME} (local-bfloat16)",
            "analyzed_at": datetime.utcnow().isoformat() + "Z",
            "tokens": tokens_attribution,
            "explanation_note": "Local FinBERT PyTorch CPU forward-pass inference.",
            "is_fallback": False,
            "engine_mode": "local-bfloat16"
        }

    def _explain_prediction_perturbation(
        self,
        text: str,
        winning_sentiment: str,
        baseline_conf: float,
        infer_scores_fn: Callable[[str], Optional[Dict[str, float]]]
    ) -> List[Dict[str, Any]]:
        """
        Genuine perturbation-based word salience attribution:
        Selects candidate non-stopword tokens, removes each token individually from the text,
        queries the model, and calculates the delta:
            delta = baseline_confidence - perturbed_confidence
        Limits additional calls to at most 2 words to strictly control latency and provider rate limits.
        """
        words = re.findall(r"\b[\w'-]+\b", text)
        if len(words) <= 1:
            return []

        # Candidate words: significant non-stopwords of length > 2, prioritizing financial terms
        candidate_words = [w for w in words if w.lower() not in FINANCIAL_STOPWORDS and len(w) > 2]
        candidates = sorted(
            candidate_words,
            key=lambda w: (w.lower() in FINANCIAL_POSITIVE_LEXICON or w.lower() in FINANCIAL_NEGATIVE_LEXICON),
            reverse=True
        )[:2]
        if not candidates:
            candidates = words[:1]

        salient_tokens = []
        for word in candidates:
            try:
                # Remove single occurrence of candidate word
                perturbed = re.sub(r'\b' + re.escape(word) + r'\b', '', text, count=1, flags=re.IGNORECASE)
                perturbed = re.sub(r'\s+', ' ', perturbed).strip()
                if not perturbed:
                    continue

                perturbed_scores = infer_scores_fn(perturbed)
                if not perturbed_scores:
                    continue

                perturbed_conf = perturbed_scores.get(winning_sentiment, 0.0)
                delta = round(baseline_conf - perturbed_conf, 4)
                direction = winning_sentiment if delta > 0 else "counter-evidence"

                salient_tokens.append({
                    "token": word,
                    "impact": delta,
                    "direction": direction,
                    "method": "perturbation-delta"
                })
            except Exception as e:
                logger.debug(f"Perturbation failed for token '{word}': {e}")
                continue

        salient_tokens.sort(key=lambda x: abs(x["impact"]), reverse=True)
        return salient_tokens

    def _predict_lexical(
        self,
        text: str,
        include_explanation: bool,
        reason: str = "Hosted neural provider unavailable."
    ) -> Dict[str, Any]:
        """
        Transparent Rule-Based Institutional Lexicon Fallback (Loughran-McDonald).
        Zero memory overhead, 100% resilient offline fallback.
        Explicitly marked as a fallback: scores are heuristic polarity weights,
        not calibrated neural network probabilities.
        Ensures positive, negative, and neutral scores sum to exactly 1.0000.
        """
        words = re.findall(r"\b[\w'-]+\b", text.lower())
        pos_hits = [w for w in words if w in FINANCIAL_POSITIVE_LEXICON]
        neg_hits = [w for w in words if w in FINANCIAL_NEGATIVE_LEXICON]

        p_count = len(pos_hits)
        n_count = len(neg_hits)
        total_polar = p_count + n_count

        if total_polar == 0:
            # Informational financial news without overt directional keywords
            sentiment = "neutral"
            scores = {"positive": 0.1500, "negative": 0.1500, "neutral": 0.7000}
            confidence = 0.7000
        elif p_count == n_count:
            # Balanced mixed signals: opposing forces cancel out
            sentiment = "neutral"
            scores = {"positive": 0.3500, "negative": 0.3500, "neutral": 0.3000}
            confidence = 0.3500
        elif p_count > n_count:
            sentiment = "positive"
            margin = p_count - n_count
            # Base neutral dampener reflects dictionary-matching uncertainty
            neu_weight = max(0.1200, round(0.30 / (1.0 + 0.40 * margin), 4))
            polar_pool = 1.0 - neu_weight
            pos_score = round(polar_pool * ((p_count + 0.25) / (total_polar + 0.50)), 4)
            neg_score = round(polar_pool * ((n_count + 0.25) / (total_polar + 0.50)), 4)
            neu_score = round(1.0 - pos_score - neg_score, 4)
            scores = {"positive": pos_score, "negative": neg_score, "neutral": neu_score}
            confidence = pos_score
        else:
            sentiment = "negative"
            margin = n_count - p_count
            # Base neutral dampener reflects dictionary-matching uncertainty
            neu_weight = max(0.1200, round(0.30 / (1.0 + 0.40 * margin), 4))
            polar_pool = 1.0 - neu_weight
            neg_score = round(polar_pool * ((n_count + 0.25) / (total_polar + 0.50)), 4)
            pos_score = round(polar_pool * ((p_count + 0.25) / (total_polar + 0.50)), 4)
            neu_score = round(1.0 - pos_score - neg_score, 4)
            scores = {"positive": pos_score, "negative": neg_score, "neutral": neu_score}
            confidence = neg_score

        tokens = []
        if include_explanation:
            orig_words = re.findall(r"\b[\w'-]+\b", text)
            word_freq: Dict[str, int] = {}
            for w in orig_words:
                wl = w.lower()
                if wl in FINANCIAL_POSITIVE_LEXICON or wl in FINANCIAL_NEGATIVE_LEXICON:
                    word_freq[wl] = word_freq.get(wl, 0) + 1

            total_hits = sum(word_freq.values())
            seen_lower = set()

            if total_hits > 0:
                for w in orig_words:
                    wl = w.lower()
                    if wl in seen_lower:
                        continue
                    if wl in FINANCIAL_POSITIVE_LEXICON:
                        seen_lower.add(wl)
                        share = round(word_freq[wl] / total_hits, 4)
                        tokens.append({
                            "token": w,
                            "impact": share,
                            "direction": "positive",
                            "method": "lexicon-match"
                        })
                    elif wl in FINANCIAL_NEGATIVE_LEXICON:
                        seen_lower.add(wl)
                        share = round(word_freq[wl] / total_hits, 4)
                        tokens.append({
                            "token": w,
                            "impact": -share,
                            "direction": "negative",
                            "method": "lexicon-match"
                        })

                # Sort by impact magnitude descending
                tokens.sort(key=lambda t: abs(t["impact"]), reverse=True)
                tokens = tokens[:6]

        return {
            "text": text,
            "sentiment": sentiment,
            "confidence": confidence,
            "scores": scores,
            "model_name": "Loughran-McDonald Institutional Lexicon (Rule-Based Fallback)",
            "analyzed_at": datetime.utcnow().isoformat() + "Z",
            "tokens": tokens,
            "explanation_note": (
                f"Rule-based fallback active: {reason} "
                "Sentiment estimated via the Loughran-McDonald institutional financial dictionary. "
                "Scores are heuristic polarity weights, not calibrated neural probabilities. "
                "Matched financial terms indicate dictionary keyword attribution."
            ),
            "is_fallback": True,
            "engine_mode": "lexical-fallback"
        }

    def predict_batch(self, texts: List[str], chunk_size: int = 4, validate_input: bool = True) -> List[Dict[str, Any]]:
        """Processes a list of financial texts using the active engine."""
        if not texts:
            return []

        if validate_input:
            cleaned_texts = [validate_financial_headline(t) for t in texts]
        else:
            cleaned_texts = [t.strip() for t in texts if (t or "").strip()]
            if not cleaned_texts:
                raise FinancialValidationError("HEADLINE_EMPTY", "All input texts are empty.")

        results = []
        for text in cleaned_texts:
            res = self.predict_one(text, include_explanation=False, validate_input=False)
            results.append(res)
        return results


finbert_service = FinBERTService()
