"""
GridGuard AI — Activity Log Schemas
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ActivityLogRequest(BaseModel):
    gps_lat: Decimal = Field(..., description="GPS latitude")
    gps_lng: Decimal = Field(..., description="GPS longitude")
    is_online: bool
    accelerometer_variance: Decimal = Field(default=Decimal("0.0"))
    platform_status: str = Field(..., description="online|offline|on_delivery|idle")


class ActivityLogResponse(BaseModel):
    id: UUID
    partner_id: UUID
    h3_cell: str | None = None
    gps_lat: Decimal | None = None
    gps_lng: Decimal | None = None
    is_online: bool | None = None
    platform_status: str | None = None
    logged_at: datetime
    zone_updated: bool = False
    new_zone_h3: str | None = None

    model_config = {"from_attributes": True}
