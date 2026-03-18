"""
GridGuard AI — Analytics Schemas (Admin)
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    active_partners: int
    payouts_today_amount: Decimal
    payouts_today_count: int
    loss_ratio_30d: Decimal
    fraud_flags_pending: int
    premium_collected_this_week: Decimal
    top_disrupted_zones: list["DisruptedZone"]


class DisruptedZone(BaseModel):
    h3_cell: str
    city: str | None = None
    active_events_count: int
    avg_workability_score: Decimal


class LossRatioDataPoint(BaseModel):
    period: str  # date or week label
    premiums_collected: Decimal
    payouts_disbursed: Decimal
    loss_ratio: Decimal


class LossRatioResponse(BaseModel):
    date_from: date
    date_to: date
    city: str | None = None
    granularity: str  # day|week|month
    data: list[LossRatioDataPoint]


# Rebuild forward refs
AnalyticsSummary.model_rebuild()
