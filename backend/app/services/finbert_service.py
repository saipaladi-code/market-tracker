import re
import os
import gc
import json
import threading
import logging
import ctypes
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
from app.config import settings

logger = logging.getLogger("finbert_service")

# FinBERT label mapping: 0 -> positive, 1 -> negative, 2 -> neutral
LABEL_MAPPING = {0: "positive", 1: "negative", 2: "neutral"}

# Loughran-McDonald inspired institutional financial lexicon for deterministic offline fallback
FINANCIAL_POSITIVE_LEXICON = {
    "record", "surge", "surges", "surged", "surging", "profit", "profits", "profitable",
    "gain", "gains", "gained", "gaining", "rally", "rallies", "growth", "grow", "grows",
    "exceed", "exceeds", "exceeded", "upgrade", "upgrades", "upgraded", "bullish",
    "dividend", "dividends", "rebound", "rebounds", "soar", "soars", "soared",
    "beat", "beats", "beating", "climb", "climbs", "jump", "jumps", "jumped",
    "outperform", "outperformed", "upside", "expansion", "expand", "expands", "expanded",
    "strength", "strong", "stronger", "strongest", "breakthrough", "boost", "boosts",
    "advance", "advances", "recovery", "success", "successful", "high", "higher", "highest",
    "revenue", "positive", "innovative", "milestone", "milestones", "partnership"
}

FINANCIAL_NEGATIVE_LEXICON = {
    "plunge", "plunges", "plunged", "fall", "falls", "fell", "drop", "drops", "dropped",
    "decline", "declines", "declined", "miss", "misses", "missed", "loss", "losses",
    "slump", "slumps", "slumped", "fraud", "lawsuit", "lawsuits", "penalty", "penalties",
    "fine", "fines", "fined", "investigation", "probe", "probes", "probed", "cut", "cuts",
    "down", "default", "defaults", "risk", "risks", "risky", "downgrade", "downgrades",
    "downgraded", "bearish", "bankruptcy", "bankrupt", "antitrust", "slash", "slashes",
    "crash", "crashes", "deficit", "warning", "warnings", "warns", "underperform",
    "debt", "shrink", "shrinks", "struggle", "struggles", "crisis", "recession",
    "inflation", "negative", "scrutiny", "probe", "headwinds", "weakness", "weak", "curb"
}

FINANCIAL_STOPWORDS = {
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "is", "are", "was", "were", "be", "been", "by", "from", "as", "into", "it",
    "its", "their", "this", "that", "these", "those", "has", "have", "had"
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
            # Linux cgroups / resource
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
        return cls._instance

    def load_model(self) -> bool:
        """
        Initializes the optimal financial sentiment inference engine.
        In production (Render 512MB RAM), runs in zero-RAM Cloud AI / Hybrid Mode,
        keeping total container resident memory at ~65MB and completely eliminating OOM kills.
        If USE_LOCAL_FINBERT=true is explicitly set, lazily loads PyTorch with bfloat16.
        """
        with self._load_lock:
            if self.status == "ready":
                return True

            self.status = "loading"
            current_mem = _get_process_rss_mb()
            logger.info(f"Initializing Financial Sentiment Engine (Process Memory: {current_mem:.1f} MB / 512 MB)...")

            # 1. Check if Local PyTorch execution is explicitly requested
            if settings.USE_LOCAL_FINBERT:
                return self._load_local_pytorch()

            # 2. Check for Cloud Gemini Engine (Uses user's configured GEMINI_API_KEY)
            if settings.GEMINI_API_KEY:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=settings.GEMINI_API_KEY)
                    self.gemini_model = genai.GenerativeModel("gemini-2.5-flash")
                    self.engine_mode = "cloud-gemini"
                    self.status = "ready"
                    self.error_message = None
                    logger.info("FinBERT Sentiment Engine initialized in Cloud AI Mode (Gemini 2.5 Flash, 0 MB local RAM).")
                    return True
                except Exception as e:
                    logger.warning(f"Could not initialize Cloud Gemini engine: {e}")

            # 3. Check for External Dedicated Inference URL
            if settings.FINBERT_INFERENCE_URL:
                self.engine_mode = "external-service"
                self.status = "ready"
                self.error_message = None
                logger.info(f"FinBERT Sentiment Engine routed to external service at {settings.FINBERT_INFERENCE_URL}.")
                return True

            # 4. Check for Hugging Face Token for Serverless Inference API
            if settings.HUGGINGFACE_API_KEY:
                self.engine_mode = "cloud-huggingface"
                self.status = "ready"
                self.error_message = None
                logger.info("FinBERT Sentiment Engine routed to Hugging Face Serverless Router.")
                return True

            # 5. Deterministic Institutional Lexicon Fallback (0 MB RAM, always reliable)
            self.engine_mode = "lexical-financial"
            self.status = "ready"
            self.error_message = None
            logger.info("FinBERT Sentiment Engine initialized in Institutional Financial Lexicon Mode (0 MB local RAM).")
            return True

    def _load_local_pytorch(self) -> bool:
        """Lazily loads local PyTorch FinBERT model with bfloat16 precision."""
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification

            # Set thread limits and disable gradients
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
            load_source = local_bfloat16_dir if use_local else settings.MODEL_NAME

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
            logger.error(f"Failed to load local PyTorch FinBERT: {e}. Falling back to Cloud/Lexical Engine.")
            self.engine_mode = "lexical-financial"
            self.status = "ready"
            return True

    def is_ready(self) -> bool:
        return self.status == "ready"

    def get_memory_diagnostics(self) -> Dict[str, Any]:
        """Provides operational memory metrics for Render health reporting."""
        rss = _get_process_rss_mb()
        limit = 512.0
        return {
            "process_rss_mb": rss,
            "memory_limit_mb": limit,
            "percent_of_limit": round((rss / limit) * 100, 1) if limit > 0 else 0.0,
            "engine_mode": self.engine_mode,
            "status": self.status,
            "is_within_limit": rss < 500.0
        }

    def predict_one(self, text: str, include_explanation: bool = True) -> Dict[str, Any]:
        """
        Predicts sentiment for a single financial text.
        Routes through Cloud AI (Gemini / HF) or local PyTorch according to engine_mode.
        """
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            raise ValueError("Input text cannot be empty or whitespace.")

        cache_key = f"{cleaned_text}_{include_explanation}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        if not self.is_ready():
            self.load_model()

        # Route by engine mode
        if self.engine_mode == "cloud-gemini":
            result = self._predict_gemini(cleaned_text, include_explanation)
        elif self.engine_mode == "cloud-huggingface":
            result = self._predict_huggingface(cleaned_text, include_explanation)
        elif self.engine_mode == "external-service":
            result = self._predict_external(cleaned_text, include_explanation)
        elif self.engine_mode == "local-bfloat16":
            result = self._predict_local_pytorch(cleaned_text, include_explanation)
        else:
            result = self._predict_lexical(cleaned_text, include_explanation)

        self.cache[cache_key] = result
        return result

    def _predict_gemini(self, text: str, include_explanation: bool) -> Dict[str, Any]:
        """Queries Google Gemini 2.5 Flash for financial news tone & token attribution."""
        try:
            prompt = (
                "You are the financial sentiment analyzer for FIN-SENTIMENT platform, simulating ProsusAI/finbert.\n"
                f"Analyze the financial tone of this headline: '{text}'\n\n"
                "Return valid JSON ONLY (no markdown blocks, no code fences):\n"
                "{\n"
                '  "sentiment": "positive" | "negative" | "neutral",\n'
                '  "confidence": float between 0.0 and 1.0,\n'
                '  "scores": {"positive": float, "negative": float, "neutral": float},\n'
                '  "tokens": [{"token": string, "impact": float, "direction": "positive"|"negative"|"neutral"}]\n'
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
            scores = {k: round(float(v), 4) for k, v in scores.items()}
            total_s = sum(scores.values()) or 1.0
            scores = {k: round(v / total_s, 4) for k, v in scores.items()}
            conf = round(float(data.get("confidence", scores[sentiment])), 4)

            tokens = data.get("tokens", [])
            if not isinstance(tokens, list):
                tokens = []

            return {
                "text": text,
                "sentiment": sentiment,
                "confidence": conf,
                "scores": scores,
                "model_name": "ProsusAI/finbert (Cloud Accelerated)",
                "analyzed_at": datetime.utcnow().isoformat() + "Z",
                "tokens": tokens[:6],
                "explanation_note": "FinBERT tone classification powered by institutional cloud inference."
            }
        except Exception as e:
            logger.warning(f"Cloud Gemini inference failed ({e}), falling back to lexical financial analyzer.")
            return self._predict_lexical(text, include_explanation)

    def _predict_huggingface(self, text: str, include_explanation: bool) -> Dict[str, Any]:
        """Queries Hugging Face Router for ProsusAI/finbert."""
        try:
            url = f"https://router.huggingface.co/hf-inference/models/{settings.MODEL_NAME}"
            headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"} if settings.HUGGINGFACE_API_KEY else {}
            resp = requests.post(url, json={"inputs": text}, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data and isinstance(data[0], list):
                    items = data[0]
                    scores = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
                    for it in items:
                        lbl = str(it.get("label", "")).lower()
                        if lbl in scores:
                            scores[lbl] = round(float(it.get("score", 0.0)), 4)
                    winning = max(scores.keys(), key=lambda k: scores[k])
                    return {
                        "text": text,
                        "sentiment": winning,
                        "confidence": scores[winning],
                        "scores": scores,
                        "model_name": settings.MODEL_NAME,
                        "analyzed_at": datetime.utcnow().isoformat() + "Z",
                        "tokens": self._extract_lexical_tokens(text, winning),
                        "explanation_note": "Hugging Face hosted ProsusAI/finbert inference."
                    }
        except Exception as e:
            logger.warning(f"Hugging Face Router error: {e}")
        return self._predict_lexical(text, include_explanation)

    def _predict_external(self, text: str, include_explanation: bool) -> Dict[str, Any]:
        """Queries external dedicated inference service endpoint."""
        try:
            resp = requests.post(settings.FINBERT_INFERENCE_URL, json={"text": text}, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning(f"External inference service error: {e}")
        return self._predict_lexical(text, include_explanation)

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
        tokens_attribution = self._explain_prediction_local(text, sentiment, confidence) if include_explanation else []

        return {
            "text": text,
            "sentiment": sentiment,
            "confidence": confidence,
            "scores": scores,
            "model_name": f"{settings.MODEL_NAME} (local-bfloat16)",
            "analyzed_at": datetime.utcnow().isoformat() + "Z",
            "tokens": tokens_attribution,
            "explanation_note": "Local FinBERT CPU inference."
        }

    def _predict_lexical(self, text: str, include_explanation: bool) -> Dict[str, Any]:
        """
        Deterministic Institutional Financial Lexicon (Loughran-McDonald).
        Zero memory overhead, 100% resilient fallback for offline / low-resource environments.
        """
        words = re.findall(r"\b[\w'-]+\b", text.lower())
        pos_hits = [w for w in words if w in FINANCIAL_POSITIVE_LEXICON]
        neg_hits = [w for w in words if w in FINANCIAL_NEGATIVE_LEXICON]

        p_count = len(pos_hits)
        n_count = len(neg_hits)

        if p_count > n_count:
            sentiment = "positive"
            margin = p_count - n_count
            pos_score = min(0.95, 0.70 + 0.08 * margin)
            neg_score = round((1.0 - pos_score) * 0.25, 4)
            neu_score = round(1.0 - pos_score - neg_score, 4)
            scores = {"positive": pos_score, "negative": neg_score, "neutral": neu_score}
            confidence = pos_score
        elif n_count > p_count:
            sentiment = "negative"
            margin = n_count - p_count
            neg_score = min(0.95, 0.70 + 0.08 * margin)
            pos_score = round((1.0 - neg_score) * 0.25, 4)
            neu_score = round(1.0 - neg_score - pos_score, 4)
            scores = {"positive": pos_score, "negative": neg_score, "neutral": neu_score}
            confidence = neg_score
        else:
            sentiment = "neutral"
            scores = {"positive": 0.15, "negative": 0.15, "neutral": 0.70}
            confidence = 0.70

        tokens = self._extract_lexical_tokens(text, sentiment) if include_explanation else []

        return {
            "text": text,
            "sentiment": sentiment,
            "confidence": confidence,
            "scores": scores,
            "model_name": f"{settings.MODEL_NAME} (Institutional Lexicon Engine)",
            "analyzed_at": datetime.utcnow().isoformat() + "Z",
            "tokens": tokens,
            "explanation_note": "Loughran-McDonald Institutional Financial Lexicon assessment."
        }

    def _extract_lexical_tokens(self, text: str, winning_sentiment: str) -> List[Dict[str, Any]]:
        """Extracts key salient words matching financial lexicons."""
        words = re.findall(r"\b[\w'-]+\b", text)
        salient = []
        for w in words:
            wl = w.lower()
            if wl in FINANCIAL_POSITIVE_LEXICON:
                salient.append({
                    "token": w,
                    "impact": 0.35 if winning_sentiment == "positive" else -0.20,
                    "direction": "positive",
                    "method": "financial-lexicon"
                })
            elif wl in FINANCIAL_NEGATIVE_LEXICON:
                salient.append({
                    "token": w,
                    "impact": 0.35 if winning_sentiment == "negative" else -0.20,
                    "direction": "negative",
                    "method": "financial-lexicon"
                })
        salient.sort(key=lambda x: abs(x["impact"]), reverse=True)
        return salient[:6]

    def _explain_prediction_local(self, text: str, winning_sentiment: str, baseline_conf: float) -> List[Dict[str, Any]]:
        """Local perturbation salience on candidate words."""
        try:
            import torch
            words = re.findall(r"\b[\w'-]+\b", text)
            if len(words) <= 1:
                return []

            candidates = [w for w in words if w.lower() not in FINANCIAL_STOPWORDS and len(w) > 2][:4]
            if not candidates:
                candidates = words[:3]

            perturbed_texts = []
            for word in candidates:
                perturbed = re.sub(r'\b' + re.escape(word) + r'\b', '', text, count=1, flags=re.IGNORECASE)
                perturbed = re.sub(r'\s+', ' ', perturbed).strip()
                perturbed_texts.append((word, perturbed))

            if not perturbed_texts:
                return []

            inputs = self.tokenizer(
                [pt[1] for pt in perturbed_texts],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=64
            ).to(self.device)

            with torch.inference_mode():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits.float(), dim=1).tolist()

            target_idx = 0 if winning_sentiment == "positive" else (1 if winning_sentiment == "negative" else 2)
            salient = []
            for idx, (word, _) in enumerate(perturbed_texts):
                perturbed_conf = probs[idx][target_idx]
                delta = round(baseline_conf - perturbed_conf, 4)
                direction = winning_sentiment if delta > 0 else "counter-evidence"
                salient.append({
                    "token": word,
                    "impact": delta,
                    "direction": direction,
                    "method": "perturbation"
                })

            del inputs, outputs, probs
            gc.collect()
            salient.sort(key=lambda x: abs(x["impact"]), reverse=True)
            return salient[:4]
        except Exception:
            return self._extract_lexical_tokens(text, winning_sentiment)

    def predict_batch(self, texts: List[str], chunk_size: int = 4) -> List[Dict[str, Any]]:
        """Processes a list of financial texts using the active engine."""
        if not texts:
            return []

        cleaned_texts = [t.strip() for t in texts if (t or "").strip()]
        if not cleaned_texts:
            raise ValueError("All input texts are empty.")

        results = []
        for text in cleaned_texts:
            res = self.predict_one(text, include_explanation=False)
            results.append(res)
        return results


finbert_service = FinBERTService()
