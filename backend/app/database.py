"""
GridGuard AI — Database Connection & Beanie Initialization
Uses AsyncMongoClient (Beanie 2.0 / pymongo 4.x pattern)
"""

from pymongo import AsyncMongoClient
from beanie import init_beanie

from app.config import settings
from app.models.partner import Partner
from app.models.policy import Policy
from app.models.grid_event import GridEvent
from app.models.payout import Payout
from app.models.fraud_flag import FraudFlag
from app.models.activity_log import PartnerActivityLog
from app.models.premium_prediction import PremiumPrediction
from app.models.otp_session import OTPSession
from app.models.wallet_transaction import WalletTransaction

# All document models for Beanie registration
DOCUMENT_MODELS = [
    Partner,
    Policy,
    GridEvent,
    Payout,
    FraudFlag,
    PartnerActivityLog,
    PremiumPrediction,
    OTPSession,
    WalletTransaction,
]

# Module-level client reference for shutdown
_client: AsyncMongoClient | None = None


async def init_db() -> AsyncMongoClient:
    """Initialize MongoDB connection and Beanie ODM."""
    global _client
    _client = AsyncMongoClient(
        settings.MONGODB_URL,
        maxPoolSize=100,
        minPoolSize=10,
    )
    await init_beanie(
        database=_client[settings.MONGODB_DB_NAME],
        document_models=DOCUMENT_MODELS,
    )

    # Create TTL index on otp_sessions.expires_at
    db = _client[settings.MONGODB_DB_NAME]
    otp_col = db["otp_sessions"]
    await otp_col.create_index("expires_at", expireAfterSeconds=0)

    # Create compound index on partner_activity_logs
    activity_col = db["partner_activity_logs"]
    await activity_col.create_index([("partner_id", 1), ("logged_at", -1)])

    return _client


async def close_db():
    """Close MongoDB connection."""
    global _client
    if _client:
        _client.close()
        _client = None


def get_database():
    """Get the raw MongoDB database for Motor operations."""
    if _client is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _client[settings.MONGODB_DB_NAME]
