"""
GridGuard AI — Fraud Detection Schemas
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class FraudEvaluateRequest(BaseModel):
    partner_id: UUID
    h3_cell: str
    gps_lat: Decimal
    gps_lng: Decimal
    accelerometer_variance: Decimal
    event_id: UUID


class FraudCheckResult(BaseModel):
    check_name: str
    weight: float
    passed: bool
    detail: str


class FraudEvaluateResponse(BaseModel):
    fraud_score: Decimal
    checks_failed: list[str]
    checks_detail: list[FraudCheckResult]
    recommendation: str  # "approve" | "flag" | "block"


class FraudFlagResponse(BaseModel):
    id: UUID
    partner_id: UUID
    payout_id: UUID | None = None
    flag_type: str
    severity: str
    gps_lat: Decimal | None = None
    gps_lng: Decimal | None = None
    accelerometer_variance: Decimal | None = None
    rule_triggered: str | None = None
    status: str
    flagged_at: datetime | None = None
    reviewed_by: str | None = None
    created_at: datetime

    # Partner details (joined)
    partner_name: str | None = None
    partner_phone: str | None = None

    model_config = {"from_attributes": True}


class FraudFlagListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    flags: list[FraudFlagResponse]


class UpdateFraudFlagRequest(BaseModel):
    status: str = Field(..., description="dismissed|escalated|confirmed")
    reviewer_note: str | None = None
