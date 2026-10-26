import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict

# Enforce minimal memory footprint for PyTorch/OpenMP/CUDA runtimes on restricted containers (e.g. Render 512MB)
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("PYTORCH_NO_CUDA_MEMORY_CACHING", "1")

# Explicitly resolve path to backend/.env so it works regardless of process working directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = str(BACKEND_DIR / ".env")


class Settings(BaseSettings):
    NEWS_API_KEY: Optional[str] = None
    MONGODB_URI: Optional[str] = None
    MONGODB_DATABASE: str = "financial_sentiment"
    GEMINI_API_KEY: Optional[str] = None
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    USE_DEMO_DATA: bool = False
    USE_LOCAL_FINBERT: bool = False
    FINBERT_INFERENCE_URL: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = None
    HUGGINGFACE_API_KEY_1: Optional[str] = None
    HUGGINGFACE_API_KEY_2: Optional[str] = None
    HUGGINGFACE_API_KEY_3: Optional[str] = None
    HUGGINGFACE_API_KEY_4: Optional[str] = None
    MODEL_NAME: str = "ProsusAI/finbert"
    MAX_HEADLINE_LENGTH: int = 1000
    MIN_HEADLINE_LENGTH: int = 15
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    def get_huggingface_api_keys(self) -> List[str]:
        """
        Securely collects configured Hugging Face API keys in priority order:
        HUGGINGFACE_API_KEY_1, HUGGINGFACE_API_KEY_2, HUGGINGFACE_API_KEY_3, HUGGINGFACE_API_KEY_4,
        and legacy HUGGINGFACE_API_KEY.
        Strips whitespace and eliminates duplicates while preserving order.
        Never logs or exposes key values.
        """
        keys: List[str] = []
        # Support both underscore and hyphen forms (e.g. HUGGINGFACE_API_KEY_1 and HUGGINGFACE_API_KEY-1)
        raw_k1 = self.HUGGINGFACE_API_KEY_1 or os.getenv("HUGGINGFACE_API_KEY_1") or os.getenv("HUGGINGFACE_API_KEY-1")
        raw_k2 = self.HUGGINGFACE_API_KEY_2 or os.getenv("HUGGINGFACE_API_KEY_2") or os.getenv("HUGGINGFACE_API_KEY-2")
        raw_k3 = self.HUGGINGFACE_API_KEY_3 or os.getenv("HUGGINGFACE_API_KEY_3") or os.getenv("HUGGINGFACE_API_KEY-3")
        raw_k4 = self.HUGGINGFACE_API_KEY_4 or os.getenv("HUGGINGFACE_API_KEY_4") or os.getenv("HUGGINGFACE_API_KEY-4")

        candidates = [
            raw_k1,
            raw_k2,
            raw_k3,
            raw_k4,
            self.HUGGINGFACE_API_KEY or os.getenv("HUGGINGFACE_API_KEY"),
        ]
        for candidate in candidates:
            if candidate and isinstance(candidate, str):
                cleaned = candidate.strip()
                if cleaned and cleaned not in keys:
                    keys.append(cleaned)
        return keys

    model_config = SettingsConfigDict(
        env_file=ENV_PATH if os.path.exists(ENV_PATH) else ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

