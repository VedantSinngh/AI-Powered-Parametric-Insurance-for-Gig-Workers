"""
GridGuard AI — Pydantic v2 Request/Response Schemas
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal, List
from datetime import datetime


# ── Auth Schemas ──

class RegisterRequest(BaseModel):
    device_id: str
    email: str
    full_name: str
    platform: Literal["zomato", "swiggy", "zepto", "blinkit", "other"]
    city: str


class RegisterResponse(BaseModel):
    partner_id: str
    otp_session_id: str
    message: str = "OTP sent to your email"


class VerifyOTPRequest(BaseModel):
    otp_session_id: str
    otp_code: str


class VerifyOTPResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    partner_id: str
    wallet_balance: float


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Partner Schemas ──

class PartnerProfile(BaseModel):
    id: str
    device_id: str
    full_name: str
    email: str
    upi_handle: Optional[str] = None
    primary_zone_h3: Optional[str] = None
    city: str
    platform: str
    risk_tier: str
    is_active: bool
    mock_wallet_balance: float
    onboarded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PartnerWithPolicy(BaseModel):
    partner: PartnerProfile
    active_policy: Optional[dict] = None


# ── Grid / Workability Schemas ──

class GridEventIngest(BaseModel):
    h3_cell: str
    city: str
    event_type: Literal["rainfall", "heat", "aqi", "road_saturation", "app_outage"]
    severity: float = Field(ge=0.0, le=1.0)
    raw_value: float
    source_api: str


class GridEventResponse(BaseModel):
    event_id: str
    workability_score: float
    payout_triggered: bool


class WorkabilityResponse(BaseModel):
    h3_cell: str
    workability_score: float
    status: str
    active_events: List[dict] = []
    payout_rate_hr: float = 0.0
    coverage_active: bool = False
    timestamp: datetime


# ── Payout Schemas ──

class PayoutTriggerRequest(BaseModel):
    partner_id: str
    grid_event_id: str
    duration_hours: float = 1.0


class PayoutResponse(BaseModel):
    id: str
    partner_id: str
    amount: float
    status: str
    mock_reference: str
    event_type: Optional[str] = None
    paid_at: Optional[datetime] = None


class PayoutHistoryParams(BaseModel):
    event_type: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: int = 20
    offset: int = 0


# ── Fraud Schemas ──

class FraudFlagUpdate(BaseModel):
    status: Literal["pending", "dismissed", "escalated", "confirmed"]
    reviewer_note: Optional[str] = None


class FraudFlagResponse(BaseModel):
    id: str
    partner_id: str
    flag_type: str
    severity: str
    fraud_score: float
    checks_failed: List[str]
    status: str
    flagged_at: datetime
    reviewed_by: Optional[str] = None
    reviewer_note: Optional[str] = None


# ── Activity Schemas ──

class ActivityLogRequest(BaseModel):
    gps_lat: float
    gps_lng: float
    is_online: bool
    accelerometer_variance: float
    platform_status: Literal["online", "offline", "on_delivery", "idle"]


# ── Admin Schemas ──

class AdminPartnerFilters(BaseModel):
    city: Optional[str] = None
    risk_tier: Optional[str] = None
    status: Optional[str] = None
    search: Optional[str] = None
    limit: int = 20
    offset: int = 0


class AnalyticsSummary(BaseModel):
    active_partners: int
    payouts_today_amount: float
    payouts_today_count: int
    loss_ratio_30d: float
    fraud_flags_pending: int
    premium_collected_this_week: float
    top_disrupted_zones: List[dict]
    system_health: dict


class LossRatioParams(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    city: Optional[str] = None
    granularity: Literal["day", "week", "month"] = "week"
