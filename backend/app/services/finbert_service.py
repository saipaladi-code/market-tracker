import re
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

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FinBERTService, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.tokenizer = None
            cls._instance.device = "cpu"
            cls._instance.status = "uninitialized"
            cls._instance.error_message = None
            cls._instance.cache = {}
        return cls._instance

    def load_model(self):
        """Loads ProsusAI/finbert model weights and tokenizer into memory."""
        if self.status == "ready" and self.model is not None:
            return True

        try:
            logger.info(f"Loading {settings.MODEL_NAME} on {self.device}...")
            self.status = "loading"
            self.tokenizer = AutoTokenizer.from_pretrained(settings.MODEL_NAME)
            self.model = AutoModelForSequenceClassification.from_pretrained(settings.MODEL_NAME)
            self.model.to(self.device)
            self.model.eval()
            self.status = "ready"
            self.error_message = None
            logger.info("FinBERT model loaded successfully.")
            return True
        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
            logger.error(f"Failed to load FinBERT model: {e}")
            return False

    def is_ready(self) -> bool:
        return self.status == "ready" and self.model is not None

    def predict_one(self, text: str, include_explanation: bool = True) -> Dict[str, Any]:
        """Predicts sentiment for a single financial text."""
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

        # Tokenize and run forward pass
        inputs = self.tokenizer(
            cleaned_text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        ).to(self.device)

        with torch.no_grad():
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

    def predict_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Efficient batch inference on a list of texts."""
        if not texts:
            return []

        cleaned_texts = [t.strip() for t in texts if (t or "").strip()]
        if not cleaned_texts:
            raise ValueError("All input texts are empty.")

        if not self.is_ready():
            success = self.load_model()
            if not success:
                raise RuntimeError(f"FinBERT model is not available: {self.error_message}")

        inputs = self.tokenizer(
            cleaned_texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=1).tolist()

        results = []
        for i, text in enumerate(cleaned_texts):
            prob = probabilities[i]
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
        return results

    def _explain_prediction(self, text: str, winning_sentiment: str, baseline_conf: float) -> List[Dict[str, Any]]:
        """
        Perturbation-based word salience:
        For candidate words in the headline, removes each word one by one and computes
        the delta in confidence for the winning class:
        delta = baseline_confidence - perturbed_confidence.
        A positive delta implies the word supported the sentiment.
        """
        words = re.findall(r"\b[\w'-]+\b", text)
        if len(words) <= 1:
            return []

        salient_tokens = []
        # Test up to 10 most candidate non-trivial words
        candidates = [w for w in words if w.lower() not in FINANCIAL_STOPWORDS and len(w) > 2][:10]

        if not candidates:
            candidates = words[:6]

        # Generate perturbed texts
        perturbed_texts = []
        for word in candidates:
            # Mask or remove word
            perturbed = re.sub(r'\b' + re.escape(word) + r'\b', '', text, count=1, flags=re.IGNORECASE)
            perturbed = re.sub(r'\s+', ' ', perturbed).strip()
            perturbed_texts.append((word, perturbed))

        if not perturbed_texts:
            return []

        # Run batch inference for perturbed sentences
        try:
            inputs = self.tokenizer(
                [pt[1] for pt in perturbed_texts],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=1).tolist()

            target_idx = 0 if winning_sentiment == "positive" else (1 if winning_sentiment == "negative" else 2)

            for idx, (word, _) in enumerate(perturbed_texts):
                perturbed_conf = probs[idx][target_idx]
                delta = round(baseline_conf - perturbed_conf, 4)
                
                # If delta > 0.02, word strongly contributes to winning sentiment
                direction = winning_sentiment if delta > 0 else "counter-evidence"
                salient_tokens.append({
                    "token": word,
                    "impact": delta,
                    "direction": direction,
                    "method": "perturbation"
                })

            # Sort by absolute impact descending
            salient_tokens.sort(key=lambda x: abs(x["impact"]), reverse=True)
            return salient_tokens[:6]
        except Exception as e:
            logger.warning(f"Perturbation explanation error: {e}")
            return []

finbert_service = FinBERTService()
