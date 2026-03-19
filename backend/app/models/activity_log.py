"""
PartnerActivityLog Document — GPS and activity tracking
Collection: partner_activity_logs
Note: Uses raw Motor for time-series inserts (performance)
"""

from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from uuid import uuid4
from typing import Literal


class PartnerActivityLog(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))
    partner_id: str = Indexed()
    h3_cell: str
    gps_lat: float
    gps_lng: float
    is_online: bool
    accelerometer_variance: float
    platform_status: Literal["online", "offline", "on_delivery", "idle"]
    logged_at: datetime = Indexed(default_factory=datetime.utcnow)

    class Settings:
        name = "partner_activity_logs"
