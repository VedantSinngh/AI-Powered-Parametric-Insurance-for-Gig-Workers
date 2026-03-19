"""
FraudFlag Document — Fraud detection flags
Collection: fraud_flags
"""

from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from uuid import uuid4
from typing import Optional, Literal, List


class FraudFlag(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))
    partner_id: str = Indexed()
    payout_id: Optional[str] = None
    flag_type: Literal[
        "stationary_device",
        "no_pre_activity",
        "wrong_zone",
        "multi_account",
        "velocity_abuse",
    ]
    severity: Literal["info", "warning", "critical"] = Indexed()
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    accelerometer_variance: float = 0.0
    rule_triggered: str = ""
    fraud_score: float = 0.0
    checks_failed: List[str] = Field(default_factory=list)
    status: Literal["pending", "dismissed", "escalated", "confirmed"] = Indexed()
    flagged_at: datetime = Indexed(default_factory=datetime.utcnow)
    reviewed_by: Optional[str] = None
    reviewer_note: Optional[str] = None

    class Settings:
        name = "fraud_flags"
