"""
GridGuard AI — Application Configuration
Uses pydantic-settings to load from .env
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # MongoDB Atlas
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "gridguard"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 30

    # Email OTP — Gmail SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "GridGuard AI <noreply@gridguard.ai>"

    # Firebase FCM
    FIREBASE_SERVER_KEY: str = ""
    FIREBASE_PROJECT_ID: str = ""

    # Free External APIs
    WAQI_API_TOKEN: str = ""
    ORS_API_KEY: str = ""

    # Internal security
    INTERNAL_API_KEY: str = ""

    # ML Model
    MODEL_PATH: str = "models/risk_model.pkl"
    MODEL_VERSION: str = "1.0.0"

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    ENVIRONMENT: str = "development"

    # Deploy
    RAILWAY_URL: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
