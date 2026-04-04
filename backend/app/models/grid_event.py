"""
GridEvent Document — Environmental disruption events
Collection: grid_events
"""

from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from uuid import uuid4
from typing import Optional, Literal


class GridEvent(Document):
    id: str = Field(default_factory=lambda: str(uuid4()))
    h3_cell: str = Indexed()
    city: str
    event_type: Literal["rainfall", "heat", "aqi", "road_saturation", "app_outage"]
    severity: float  # 0.0–1.0
    raw_value: float
    workability_score: float
    event_time: datetime = Indexed()
    resolved_at: Optional[datetime] = None
    source_api: str
    consecutive_low_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "grid_events"
        indexes = ["resolved_at"]
