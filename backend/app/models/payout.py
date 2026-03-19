"""
Payout Document — Payouts to partners
Collection: payouts
"""

from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from uuid import uuid4
from typing import Optional, Literal


class Payout(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))
    partner_id: str = Indexed()
    policy_id: str
    grid_event_id: str = Indexed()
    amount: float
    duration_hours: float
    rate_per_hour: float
    mock_reference: str = ""
    status: Literal["pending", "processing", "paid", "failed", "reversed"] = Indexed()
    paid_at: Optional[datetime] = Indexed()
    failure_reason: Optional[str] = None
    ws_notified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "payouts"
