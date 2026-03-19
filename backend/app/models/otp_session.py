"""
OTPSession Document — Email OTP verification sessions
Collection: otp_sessions
TTL index on expires_at auto-deletes after 5 minutes
"""

from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime, timedelta
from uuid import uuid4


class OTPSession(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))
    email: str = Indexed()
    otp_hash: str  # bcrypt hashed 6-digit code
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(minutes=5)
    )
    verified: bool = False
    attempts: int = 0

    class Settings:
        name = "otp_sessions"
