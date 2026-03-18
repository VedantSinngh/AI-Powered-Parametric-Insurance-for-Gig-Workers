"""
GridGuard AI — Application Configuration
Uses pydantic-settings for validation and .env loading.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──
    database_url: str = "postgresql+asyncpg://gridguard:gridguard_secret@localhost:5432/gridguard_db"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── JWT Auth ──
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_days: int = 30
    refresh_token_expire_days: int = 90

    # ── Razorpay ──
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    # ── External APIs ──
    openweather_api_key: str = ""
    google_maps_api_key: str = ""
    cpcb_api_key: str = ""

    # ── Twilio ──
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # ── Firebase ──
    firebase_server_key: str = ""

    # ── TorchServe ──
    torchserve_url: str = "http://localhost:8080"

    # ── Internal API ──
    internal_api_key: str = "change-me-in-production"

    # ── Sentry ──
    sentry_dsn: str = ""

    # ── Environment ──
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
