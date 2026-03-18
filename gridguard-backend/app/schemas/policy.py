"""
GridGuard AI — Policy Schemas
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PolicyResponse(BaseModel):
    id: UUID
    partner_id: UUID
    week_start: date
    week_end: date
    premium_amount: Decimal | None = None
    risk_score: Decimal | None = None
    status: str
    deducted_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PolicyHistoryItem(BaseModel):
    id: UUID
    week_start: date
    week_end: date
    premium_amount: Decimal | None = None
    risk_score: Decimal | None = None
    status: str
    payout_count: int = 0
    total_payout_amount: Decimal = Decimal("0.00")
    created_at: datetime

    model_config = {"from_attributes": True}


class PolicyHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    policies: list[PolicyHistoryItem]


class GenerateWeeklyPoliciesResponse(BaseModel):
    policies_created: int
    notifications_sent: int
