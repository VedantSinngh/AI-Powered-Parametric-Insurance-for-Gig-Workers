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
    primary_zone_h3: Optional[str] = Indexed()
    city: str = Indexed()
    platform: Literal["zomato", "swiggy", "zepto", "blinkit", "other"]
    risk_tier: Literal["low", "medium", "high", "critical"] = "low"
    is_active: bool = Indexed(default=True)
    mock_wallet_balance: float = 100.0
    onboarded_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "partners"
