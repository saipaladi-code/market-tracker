import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    NEWS_API_KEY: Optional[str] = None
    MONGODB_URI: Optional[str] = None
    MONGODB_DATABASE: str = "financial_sentiment"
    GEMINI_API_KEY: Optional[str] = None
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    USE_DEMO_DATA: bool = False
    MODEL_NAME: str = "ProsusAI/finbert"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
