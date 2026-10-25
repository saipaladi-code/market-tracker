import re
import gc
import threading
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from app.config import settings

logger = logging.getLogger("finbert_service")

# FinBERT label mapping: 0 -> positive, 1 -> negative, 2 -> neutral
LABEL_MAPPING = {0: "positive", 1: "negative", 2: "neutral"}

# Common financial lexicon for perturbation/heuristic fallbacks
FINANCIAL_STOPWORDS = {
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "is", "are", "was", "were", "be", "been", "by", "from", "as", "into", "it",
    "its", "their", "this", "that", "these", "those", "has", "have", "had"
}


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
            cls._instance.error_message = None
            cls._instance.cache = {}
            cls._instance.is_quantized = False
        return cls._instance

    def load_model(self):
        """Loads ProsusAI/finbert model weights and tokenizer into memory with memory-conscious settings."""
        with self._load_lock:
            if self.status == "ready" and self.model is not None:
                return True

            try:
                # Limit PyTorch CPU thread pools to reduce memory overhead and thread-local buffers
                try:
                    torch.set_num_threads(1)
                    torch.set_num_interop_threads(1)
                except Exception:
                    pass

                logger.info(f"Loading {settings.MODEL_NAME} on {self.device}...")
                self.status = "loading"
                self.tokenizer = AutoTokenizer.from_pretrained(settings.MODEL_NAME)

                # bfloat16 directly streams model weights into half-precision (~210MB instead of ~440MB).
                # This prevents exceeding Render's 512 MiB container limit without the duplicate allocation spike
                # of in-memory dynamic quantization.
                try:
                    logger.info("Loading FinBERT with torch_dtype=torch.bfloat16 for low-memory CPU inference...")
                    self.model = AutoModelForSequenceClassification.from_pretrained(
                        settings.MODEL_NAME,
                        torch_dtype=torch.bfloat16
                    )
                    self.model.to(self.device)
                    self.model.eval()
                    self.precision = "bfloat16"
                    logger.info("FinBERT model loaded with bfloat16 precision (~210MB weights).")
                except Exception as bf_err:
                    logger.warning(f"bfloat16 direct loading failed ({bf_err}), attempting standard load...")
                    self.model = AutoModelForSequenceClassification.from_pretrained(settings.MODEL_NAME)
                    self.model.to(self.device)
                    self.model.eval()
                    self.precision = "fp32"

                self.status = "ready"
                self.error_message = None
                logger.info("FinBERT model loaded and ready.")
                return True
            except Exception as e:
                self.status = "error"
                self.error_message = str(e)
                logger.error(f"Failed to load FinBERT model: {e}")
                return False

    def is_ready(self) -> bool:
        return self.status == "ready" and self.model is not None

    def predict_one(self, text: str, include_explanation: bool = True) -> Dict[str, Any]:
        """Predicts sentiment for a single financial text using torch.inference_mode()."""
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            raise ValueError("Input text cannot be empty or whitespace.")

        # Check local in-memory cache
        cache_key = f"{cleaned_text}_{include_explanation}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        if not self.is_ready():
            # Try to load on-demand
            success = self.load_model()
            if not success:
                raise RuntimeError(f"FinBERT model is not available: {self.error_message}")

        # Tokenize with max_length=64 (financial headlines average 15-20 tokens; 64 prevents quadratic attention bloat)
        inputs = self.tokenizer(
            cleaned_text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=64
        ).to(self.device)

        with torch.inference_mode():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=1).squeeze().tolist()

        scores = {
            "positive": round(float(probabilities[0]), 4),
            "negative": round(float(probabilities[1]), 4),
            "neutral": round(float(probabilities[2]), 4)
        }

        # Determine winning class
        winning_idx = int(torch.argmax(logits, dim=1).item())
        sentiment = LABEL_MAPPING.get(winning_idx, "neutral")
        confidence = scores[sentiment]

        del inputs, outputs, logits

        tokens_attribution = []
        if include_explanation:
            tokens_attribution = self._explain_prediction(cleaned_text, sentiment, confidence)

        result = {
            "text": cleaned_text,
            "sentiment": sentiment,
            "confidence": confidence,
            "scores": scores,
            "model_name": settings.MODEL_NAME,
            "analyzed_at": datetime.utcnow().isoformat() + "Z",
            "tokens": tokens_attribution,
            "explanation_note": (
                "FinBERT is trained to assess textual sentiment and tone. "
                "It does not evaluate financial fundamentals or predict future stock returns."
            )
        }

        self.cache[cache_key] = result
        return result

    def predict_batch(self, texts: List[str], chunk_size: int = 4) -> List[Dict[str, Any]]:
        """
        Memory-conscious batch inference on a list of texts.
        Processes in micro-batches (chunk_size=4) to prevent intermediate tensor memory spikes.
        """
        if not texts:
            return []

        cleaned_texts = [t.strip() for t in texts if (t or "").strip()]
        if not cleaned_texts:
            raise ValueError("All input texts are empty.")

        if not self.is_ready():
            success = self.load_model()
            if not success:
                raise RuntimeError(f"FinBERT model is not available: {self.error_message}")

        results = []
        for i in range(0, len(cleaned_texts), chunk_size):
            chunk = cleaned_texts[i:i + chunk_size]
            inputs = self.tokenizer(
                chunk,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=64
            ).to(self.device)

            with torch.inference_mode():
                outputs = self.model(**inputs)
                probabilities = torch.softmax(outputs.logits, dim=1).tolist()

            for j, text in enumerate(chunk):
                prob = probabilities[j]
                scores = {
                    "positive": round(float(prob[0]), 4),
                    "negative": round(float(prob[1]), 4),
                    "neutral": round(float(prob[2]), 4)
                }
                winning_idx = max(range(3), key=lambda idx: prob[idx])
                sentiment = LABEL_MAPPING[winning_idx]
                results.append({
                    "text": text,
                    "sentiment": sentiment,
                    "confidence": scores[sentiment],
                    "scores": scores,
                    "model_name": settings.MODEL_NAME,
                    "analyzed_at": datetime.utcnow().isoformat() + "Z",
                    "tokens": [],
                    "explanation_note": "FinBERT tone analysis (Batch mode)."
                })

            del inputs, outputs, probabilities

        gc.collect()
        return results

    def _explain_prediction(self, text: str, winning_sentiment: str, baseline_conf: float) -> List[Dict[str, Any]]:
        """
        Perturbation-based word salience:
        Masks candidate words one by one and computes delta in confidence for the winning class.
        Uses max_length=64 and torch.inference_mode() for minimal memory.
        """
        words = re.findall(r"\b[\w'-]+\b", text)
        if len(words) <= 1:
            return []

        salient_tokens = []
        # Test up to 6 candidate non-trivial words to limit intermediate tensors
        candidates = [w for w in words if w.lower() not in FINANCIAL_STOPWORDS and len(w) > 2][:6]

        if not candidates:
            candidates = words[:4]

        # Generate perturbed texts
        perturbed_texts = []
        for word in candidates:
            perturbed = re.sub(r'\b' + re.escape(word) + r'\b', '', text, count=1, flags=re.IGNORECASE)
            perturbed = re.sub(r'\s+', ' ', perturbed).strip()
            perturbed_texts.append((word, perturbed))

        if not perturbed_texts:
            return []

        try:
            inputs = self.tokenizer(
                [pt[1] for pt in perturbed_texts],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=64
            ).to(self.device)

            with torch.inference_mode():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=1).tolist()

            target_idx = 0 if winning_sentiment == "positive" else (1 if winning_sentiment == "negative" else 2)

            for idx, (word, _) in enumerate(perturbed_texts):
                perturbed_conf = probs[idx][target_idx]
                delta = round(baseline_conf - perturbed_conf, 4)
                direction = winning_sentiment if delta > 0 else "counter-evidence"
                salient_tokens.append({
                    "token": word,
                    "impact": delta,
                    "direction": direction,
                    "method": "perturbation"
                })

            del inputs, outputs, probs
            gc.collect()

            salient_tokens.sort(key=lambda x: abs(x["impact"]), reverse=True)
            return salient_tokens[:6]
        except Exception as e:
            logger.warning(f"Perturbation explanation error: {e}")
            return []

finbert_service = FinBERTService()

