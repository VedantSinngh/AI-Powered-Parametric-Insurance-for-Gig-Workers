"""
GridGuard AI — Payout Schemas
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PayoutTriggerRequest(BaseModel):
    partner_id: UUID
    grid_event_id: UUID
    duration_hours: Decimal


class PayoutResponse(BaseModel):
    id: UUID
    partner_id: UUID
    policy_id: UUID
    grid_event_id: UUID
    amount: Decimal
    duration_hours: Decimal | None = None
    rate_per_hour: Decimal | None = None
    upi_reference: str | None = None
    status: str
    paid_at: datetime | None = None
    failure_reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PayoutDetailResponse(PayoutResponse):
    """Full detail with event info."""
    event_type: str | None = None
    h3_cell: str | None = None
    severity: Decimal | None = None
    partner_name: str | None = None


class PayoutHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    payouts: list[PayoutDetailResponse]
