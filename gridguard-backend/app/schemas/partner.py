"""
GridGuard AI — Partner Schemas
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PartnerProfile(BaseModel):
    id: UUID
    device_id: str
    full_name: str | None = None
    phone_number: str | None = None
    upi_handle: str | None = None
    primary_zone_h3: str | None = None
    city: str | None = None
    platform: str | None = None
    risk_tier: str | None = None
    is_active: bool = True
    onboarded_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PartnerListItem(BaseModel):
    id: UUID
    full_name: str | None = None
    phone_number: str | None = None
    city: str | None = None
    platform: str | None = None
    risk_tier: str | None = None
    is_active: bool
    primary_zone_h3: str | None = None
    onboarded_at: datetime | None = None

    model_config = {"from_attributes": True}


class PartnerListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    partners: list[PartnerListItem]


class PartnerDetailAdmin(PartnerProfile):
    """Full partner detail for admin view — includes policy/payout counts."""
    active_policy_id: UUID | None = None
    total_payouts: int = 0
    total_payout_amount: float = 0.0
    pending_fraud_flags: int = 0


class SuspendPartnerResponse(BaseModel):
    partner_id: UUID
    is_active: bool
    message: str
