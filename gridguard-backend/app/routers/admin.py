"""
GridGuard AI — Admin Router
Partner management and analytics.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.partner import Partner
from app.models.policy import Policy, PolicyStatusEnum
from app.models.payout import Payout, PayoutStatusEnum
from app.models.fraud_flag import FraudFlag, FraudFlagStatusEnum
from app.models.grid_event import GridEvent
from app.schemas.partner import (
    PartnerListItem,
    PartnerListResponse,
    PartnerDetailAdmin,
    SuspendPartnerResponse,
)
from app.schemas.analytics import (
    AnalyticsSummary,
    DisruptedZone,
    LossRatioDataPoint,
    LossRatioResponse,
)
from app.services.notification import send_sms
from app.utils.dependencies import get_admin_partner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Partner Management ──


@router.get("/partners", response_model=PartnerListResponse)
async def list_partners(
    city: str | None = Query(None),
    risk_tier: str | None = Query(None),
    status: str | None = Query(None, description="active|inactive"),
    search: str | None = Query(None, description="Search by name or phone"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: Partner = Depends(get_admin_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    List partners with filters and pagination.
    🔒 Admin only.
    """
    conditions = []
    if city:
        conditions.append(Partner.city == city)
    if risk_tier:
        conditions.append(Partner.risk_tier == risk_tier)
    if status:
        conditions.append(Partner.is_active == (status == "active"))
    if search:
        conditions.append(
            (Partner.full_name.ilike(f"%{search}%"))
            | (Partner.phone_number.ilike(f"%{search}%"))
        )

    # Count
    count_query = select(func.count(Partner.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Fetch
    query = select(Partner)
    if conditions:
        query = query.where(and_(*conditions))
    query = query.order_by(Partner.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    partners = result.scalars().all()

    return PartnerListResponse(
        total=total,
        limit=limit,
        offset=offset,
        partners=[PartnerListItem.model_validate(p) for p in partners],
    )


@router.get("/partners/{partner_id}", response_model=PartnerDetailAdmin)
async def get_partner_detail(
    partner_id: UUID,
    admin: Partner = Depends(get_admin_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Full partner profile with policy history, payout info, and fraud flags.
    🔒 Admin only.
    """
    result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    # Active policy
    today = date.today()
    policy_result = await db.execute(
        select(Policy.id)
        .where(
            and_(
                Policy.partner_id == partner_id,
                Policy.status == PolicyStatusEnum.active,
                Policy.week_start <= today,
                Policy.week_end >= today,
            )
        )
        .limit(1)
    )
    active_policy = policy_result.scalar_one_or_none()

    # Payout stats
    payout_result = await db.execute(
        select(
            func.count(Payout.id),
            func.coalesce(func.sum(Payout.amount), 0),
        ).where(Payout.partner_id == partner_id)
    )
    total_payouts, total_payout_amount = payout_result.one()

    # Pending fraud flags
    fraud_result = await db.execute(
        select(func.count(FraudFlag.id))
        .where(
            and_(
                FraudFlag.partner_id == partner_id,
                FraudFlag.status == FraudFlagStatusEnum.pending,
            )
        )
    )
    pending_flags = fraud_result.scalar() or 0

    detail = PartnerDetailAdmin.model_validate(partner)
    detail.active_policy_id = active_policy
    detail.total_payouts = total_payouts
    detail.total_payout_amount = float(total_payout_amount)
    detail.pending_fraud_flags = pending_flags

    return detail


@router.patch("/partners/{partner_id}/suspend", response_model=SuspendPartnerResponse)
async def suspend_partner(
    partner_id: UUID,
    admin: Partner = Depends(get_admin_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Suspend a partner: set is_active=false, cancel active policy, send SMS.
    🔒 Admin only.
    """
    result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = result.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    partner.is_active = False

    # Cancel active policies
    policy_result = await db.execute(
        select(Policy)
        .where(
            and_(
                Policy.partner_id == partner_id,
                Policy.status == PolicyStatusEnum.active,
            )
        )
    )
    for policy in policy_result.scalars().all():
        policy.status = PolicyStatusEnum.cancelled

    await db.flush()

    # Send SMS notification
    if partner.phone_number:
        await send_sms(
            to=partner.phone_number,
            message="GridGuard: Your account has been suspended. Contact support for details.",
        )

    logger.info(f"Partner {partner_id} suspended by admin {admin.id}")

    return SuspendPartnerResponse(
        partner_id=partner.id,
        is_active=False,
        message="Partner suspended, active policies cancelled, SMS sent",
    )


# ── Analytics ──


@router.get("/analytics/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    admin: Partner = Depends(get_admin_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Dashboard analytics summary.
    🔒 Admin only.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = now - timedelta(days=30)
    week_start = now - timedelta(days=now.weekday())  # Monday

    # Active partners
    active_result = await db.execute(
        select(func.count(Partner.id)).where(Partner.is_active == True)
    )
    active_partners = active_result.scalar() or 0

    # Payouts today
    payout_today_result = await db.execute(
        select(
            func.count(Payout.id),
            func.coalesce(func.sum(Payout.amount), 0),
        ).where(
            and_(
                Payout.paid_at >= today_start,
                Payout.status == PayoutStatusEnum.paid,
            )
        )
    )
    payouts_today_count, payouts_today_amount = payout_today_result.one()

    # Loss ratio (30 days): payouts / premiums collected
    premiums_30d = await db.execute(
        select(func.coalesce(func.sum(Policy.premium_amount), 1))
        .where(
            and_(
                Policy.deducted_at >= thirty_days_ago,
                Policy.status.in_([PolicyStatusEnum.active, PolicyStatusEnum.expired]),
            )
        )
    )
    total_premiums = premiums_30d.scalar() or Decimal("1")

    payouts_30d = await db.execute(
        select(func.coalesce(func.sum(Payout.amount), 0))
        .where(
            and_(
                Payout.paid_at >= thirty_days_ago,
                Payout.status == PayoutStatusEnum.paid,
            )
        )
    )
    total_payouts = payouts_30d.scalar() or Decimal("0")
    loss_ratio = round(total_payouts / max(total_premiums, Decimal("1")), 3)

    # Pending fraud flags
    fraud_result = await db.execute(
        select(func.count(FraudFlag.id))
        .where(FraudFlag.status == FraudFlagStatusEnum.pending)
    )
    fraud_flags_pending = fraud_result.scalar() or 0

    # Premium collected this week
    premium_week_result = await db.execute(
        select(func.coalesce(func.sum(Policy.premium_amount), 0))
        .where(
            and_(
                Policy.deducted_at >= week_start,
                Policy.status.in_([PolicyStatusEnum.active, PolicyStatusEnum.expired]),
            )
        )
    )
    premium_this_week = premium_week_result.scalar() or Decimal("0")

    # Top disrupted zones (active events)
    zone_result = await db.execute(
        select(
            GridEvent.h3_cell,
            GridEvent.city,
            func.count(GridEvent.id).label("event_count"),
            func.avg(GridEvent.workability_score).label("avg_score"),
        )
        .where(GridEvent.resolved_at.is_(None))
        .group_by(GridEvent.h3_cell, GridEvent.city)
        .order_by(func.count(GridEvent.id).desc())
        .limit(10)
    )
    top_zones = [
        DisruptedZone(
            h3_cell=row.h3_cell,
            city=row.city,
            active_events_count=row.event_count,
            avg_workability_score=Decimal(str(round(row.avg_score or 0, 3))),
        )
        for row in zone_result.all()
    ]

    return AnalyticsSummary(
        active_partners=active_partners,
        payouts_today_amount=payouts_today_amount,
        payouts_today_count=payouts_today_count,
        loss_ratio_30d=loss_ratio,
        fraud_flags_pending=fraud_flags_pending,
        premium_collected_this_week=premium_this_week,
        top_disrupted_zones=top_zones,
    )


@router.get("/analytics/loss-ratio", response_model=LossRatioResponse)
async def get_loss_ratio(
    date_from: date = Query(...),
    date_to: date = Query(...),
    city: str | None = Query(None),
    granularity: str = Query("week", description="day|week|month"),
    admin: Partner = Depends(get_admin_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Time-series loss ratio data for charting.
    🔒 Admin only.
    """
    # Generate date buckets based on granularity
    data_points = []
    current = date_from

    if granularity == "day":
        delta = timedelta(days=1)
    elif granularity == "month":
        delta = timedelta(days=30)
    else:  # week
        delta = timedelta(weeks=1)

    while current <= date_to:
        period_end = min(current + delta, date_to)
        start_dt = datetime.combine(current, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(period_end, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Premiums in period
        premium_query = select(func.coalesce(func.sum(Policy.premium_amount), 0)).where(
            and_(
                Policy.deducted_at >= start_dt,
                Policy.deducted_at <= end_dt,
            )
        )
        if city:
            premium_query = premium_query.join(Partner, Policy.partner_id == Partner.id).where(
                Partner.city == city
            )
        premium_result = await db.execute(premium_query)
        premiums = premium_result.scalar() or Decimal("0")

        # Payouts in period
        payout_query = select(func.coalesce(func.sum(Payout.amount), 0)).where(
            and_(
                Payout.paid_at >= start_dt,
                Payout.paid_at <= end_dt,
                Payout.status == PayoutStatusEnum.paid,
            )
        )
        if city:
            payout_query = payout_query.join(Partner, Payout.partner_id == Partner.id).where(
                Partner.city == city
            )
        payout_result = await db.execute(payout_query)
        payouts = payout_result.scalar() or Decimal("0")

        ratio = round(payouts / max(premiums, Decimal("1")), 3)

        data_points.append(LossRatioDataPoint(
            period=current.isoformat(),
            premiums_collected=premiums,
            payouts_disbursed=payouts,
            loss_ratio=ratio,
        ))

        current = period_end + timedelta(days=1)

    return LossRatioResponse(
        date_from=date_from,
        date_to=date_to,
        city=city,
        granularity=granularity,
        data=data_points,
    )
