"""
Policy Document — Weekly insurance policies
Collection: policies
"""

from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from uuid import uuid4
from typing import Optional, Literal


class Policy(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))
    partner_id: str = Indexed()
    week_start: str  # ISO date YYYY-MM-DD
    week_end: str  # ISO date YYYY-MM-DD
    premium_amount: float
    risk_score: float  # 0.0–1.0
    status: Literal["active", "expired", "cancelled", "suspended"] = Indexed()
    deducted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "policies"
