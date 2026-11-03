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
    NEWS_PROVIDER: str = "auto"  # "auto", "rss", "newsapi"
    MONGODB_URI: Optional[str] = None
    MONGODB_DATABASE: str = "financial_sentiment"
    GEMINI_API_KEY: Optional[str] = None
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    FRONTEND_URL: Optional[str] = None
    PRODUCTION_FRONTEND_URL: str = "https://market-tracker-umber.vercel.app"
    USE_DEMO_DATA: bool = False
    USE_LOCAL_FINBERT: bool = False
    FINBERT_INFERENCE_URL: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = None
    HUGGINGFACE_API_KEY_1: Optional[str] = None
    HUGGINGFACE_API_KEY_2: Optional[str] = None
    HUGGINGFACE_API_KEY_3: Optional[str] = None
    HUGGINGFACE_API_KEY_4: Optional[str] = None
    MODEL_NAME: str = "ProsusAI/finbert"
    MAX_HEADLINE_LENGTH: int = 300
    MIN_HEADLINE_LENGTH: int = 15
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Authentication & Security Settings
    JWT_SECRET_KEY: str = "fin-sentiment-secure-jwt-secret-key-32bytes-min!"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REMEMBER_ME_EXPIRE_MINUTES: int = 43200  # 30 days
    COOKIE_NAME: str = "session_token"
    COOKIE_SECURE: Optional[bool] = None  # None = auto-detect
    COOKIE_SAMESITE: Optional[str] = None  # None = auto-detect ("none" for prod, "lax" for dev)

    # Resend HTTPS Email API Configuration
    RESEND_API_KEY: Optional[str] = None
    RESEND_FROM_EMAIL: Optional[str] = None

    @property
    def resend_api_key(self) -> Optional[str]:
        val = self.RESEND_API_KEY or os.getenv("RESEND_API_KEY")
        return val.strip() if val and isinstance(val, str) else None

    @property
    def resend_from_email(self) -> Optional[str]:
        val = self.RESEND_FROM_EMAIL or os.getenv("RESEND_FROM_EMAIL")
        return val.strip() if val and isinstance(val, str) else None

    @property
    def is_email_service_configured(self) -> bool:
        return bool(self.resend_api_key and self.resend_from_email) or self.is_smtp_configured

    @property
    def frontend_url(self) -> str:
        val = (
            self.FRONTEND_URL 
            or os.getenv("FRONTEND_URL") 
            or self.PRODUCTION_FRONTEND_URL 
            or os.getenv("PRODUCTION_FRONTEND_URL")
        )
        if val and isinstance(val, str) and val.strip():
            return val.strip().rstrip("/")
        return "https://market-tracker-umber.vercel.app"

    # Password Recovery (SMTP) Configuration & Flexible Aliases
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USERNAME: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    SMTP_TLS: Optional[bool] = None
    SMTP_SSL: Optional[bool] = None

    @property
    def smtp_host(self) -> Optional[str]:
        val = self.SMTP_HOST or os.getenv("SMTP_HOST")
        return val.strip() if val and isinstance(val, str) else None

    @property
    def smtp_port(self) -> int:
        raw = self.SMTP_PORT or os.getenv("SMTP_PORT")
        if raw is not None:
            try:
                return int(raw)
            except (ValueError, TypeError):
                pass
        if self.smtp_use_ssl:
            return 465
        return 587

    @property
    def smtp_username(self) -> Optional[str]:
        val = (
            self.SMTP_USERNAME 
            or self.SMTP_USER 
            or os.getenv("SMTP_USERNAME") 
            or os.getenv("SMTP_USER")
        )
        return val.strip() if val and isinstance(val, str) else None

    @property
    def smtp_password(self) -> Optional[str]:
        val = (
            self.SMTP_PASSWORD 
            or self.SMTP_PASS 
            or os.getenv("SMTP_PASSWORD") 
            or os.getenv("SMTP_PASS")
        )
        if not val or not isinstance(val, str):
            return None
        cleaned = val.strip()
        host = (self.smtp_host or "").lower()
        if "gmail" in host or "google" in host or len(cleaned.replace(" ", "")) == 16:
            cleaned = cleaned.replace(" ", "")
        return cleaned

    @property
    def smtp_from_email(self) -> Optional[str]:
        val = (
            self.SMTP_FROM_EMAIL 
            or self.SMTP_FROM 
            or os.getenv("SMTP_FROM_EMAIL") 
            or os.getenv("SMTP_FROM")
        )
        if val and isinstance(val, str) and val.strip():
            return val.strip()
        # Fallback to smtp_username if configured (vital for Gmail which forbids mismatched sender)
        return self.smtp_username

    @property
    def smtp_use_ssl(self) -> bool:
        if self.SMTP_SSL is not None:
            return bool(self.SMTP_SSL)
        env_val = os.getenv("SMTP_SSL")
        if env_val is not None:
            return env_val.strip().lower() in ("true", "1", "yes")
        raw_port = self.SMTP_PORT or os.getenv("SMTP_PORT")
        if raw_port:
            try:
                return int(raw_port) == 465
            except Exception:
                pass
        return False

    @property
    def smtp_use_tls(self) -> bool:
        if self.smtp_use_ssl:
            return False
        if self.SMTP_TLS is not None:
            return bool(self.SMTP_TLS)
        env_val = os.getenv("SMTP_TLS")
        if env_val is not None:
            return env_val.strip().lower() in ("true", "1", "yes")
        return True

    @property
    def is_smtp_configured(self) -> bool:
        return bool(self.smtp_host)

    # GoldAPI.io Configuration
    GOLDAPI_API_KEY: Optional[str] = None
    GOLDAPI_API_KEY1: Optional[str] = None
    GOLDAPI_API_KEY2: Optional[str] = None

    def get_goldapi_key(self) -> Optional[str]:
        """
        Securely collects configured GoldAPI key in priority order:
        GOLDAPI_API_KEY, GOLDAPI_API_KEY1, GOLDAPI_API_KEY2.
        Never logs or exposes key values.
        """
        for k in [
            self.GOLDAPI_API_KEY or os.getenv("GOLDAPI_API_KEY"),
            self.GOLDAPI_API_KEY1 or os.getenv("GOLDAPI_API_KEY1"),
            self.GOLDAPI_API_KEY2 or os.getenv("GOLDAPI_API_KEY2")
        ]:
            if k and isinstance(k, str) and k.strip():
                return k.strip()
        return None

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

