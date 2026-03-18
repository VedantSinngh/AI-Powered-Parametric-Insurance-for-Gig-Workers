"""
GridGuard AI — Grid Event Schemas
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class GridEventIngestRequest(BaseModel):
    source: str = Field(..., max_length=64)
    h3_cell: str = Field(..., max_length=16)
    event_type: str = Field(..., description="rainfall|heat|aqi|road_saturation|app_outage")
    raw_value: Decimal
    severity: Decimal = Field(..., ge=0, le=1)
    event_time: datetime
    city: str | None = None


class GridEventIngestResponse(BaseModel):
    event_id: UUID
    workability_score: Decimal
    payout_triggered: bool


class WorkabilityResponse(BaseModel):
    h3_cell: str
    workability_score: Decimal
    status: str  # "normal", "degraded", "critical"
    active_events: list["ActiveEventSummary"]
    last_updated: datetime


class ActiveEventSummary(BaseModel):
    event_id: UUID
    event_type: str
    severity: Decimal
    raw_value: Decimal | None = None
    event_time: datetime

    model_config = {"from_attributes": True}


class CellWorkability(BaseModel):
    h3_cell: str
    score: Decimal
    status: str
    lat: float
    lng: float


class CityWorkabilityResponse(BaseModel):
    city: str
    cells: list[CellWorkability]


class GridEventResponse(BaseModel):
    id: UUID
    h3_cell: str
    city: str | None = None
    event_type: str
    severity: Decimal
    raw_value: Decimal | None = None
    workability_score: Decimal | None = None
    event_time: datetime
    resolved_at: datetime | None = None
    source_api: str | None = None

    model_config = {"from_attributes": True}


# Rebuild forward refs
WorkabilityResponse.model_rebuild()
