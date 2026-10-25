import os

# Enforce minimal memory footprint for PyTorch/OpenMP/CUDA runtimes on restricted containers (e.g. Render 512MB)
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("PYTORCH_NO_CUDA_MEMORY_CACHING", "1")

from pydantic_settings import BaseSettings
from typing import Optional

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
    MODEL_NAME: str = "ProsusAI/finbert"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
