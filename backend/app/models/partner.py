"""
Partner Document — Gig delivery partners
Collection: partners
"""

from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from uuid import uuid4
from typing import Optional, Literal


class Partner(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))
    device_id: str = Indexed(unique=True)
    full_name: str
    email: str = Indexed(unique=True)
    upi_handle: Optional[str] = None
    razorpay_contact_id: Optional[str] = None
    razorpay_fund_account_id: Optional[str] = None
    primary_zone_h3: Optional[str] = None
    city: str = Indexed()
    platform: Literal["zomato", "swiggy", "zepto", "blinkit", "other"]
    risk_tier: Literal["low", "medium", "high", "critical"] = "low"
    preferred_language: Literal["en", "hi", "ta", "te"] = "en"
    auto_premium_deduction: bool = True
    is_admin: bool = False
    is_active: bool = True
    mock_wallet_balance: float = 100.0
    onboarded_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "partners"
        indexes = ["primary_zone_h3", "is_admin", "is_active"]
