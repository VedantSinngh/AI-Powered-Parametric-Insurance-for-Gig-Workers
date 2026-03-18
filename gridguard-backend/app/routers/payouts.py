"""
GridGuard AI — Payout Router
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.partner import Partner
from app.models.payout import Payout, PayoutStatusEnum
from app.models.grid_event import GridEvent
from app.schemas.payout import (
    PayoutTriggerRequest,
    PayoutResponse,
    PayoutDetailResponse,
    PayoutHistoryResponse,
)
from app.services.payout_engine import trigger_payout
from app.utils.dependencies import get_current_partner, verify_internal_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payouts", tags=["Payouts"])


@router.post("/trigger")
async def trigger_payout_endpoint(
    request: PayoutTriggerRequest,
    _api_key: bool = Depends(verify_internal_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger a payout (internal — called by Celery).
    Validates policy, runs fraud checks, processes Razorpay UPI credit.
    SLA: < 90 seconds.
    """
    result = await trigger_payout(
        partner_id=request.partner_id,
        grid_event_id=request.grid_event_id,
        duration_hours=request.duration_hours,
        db=db,
    )
    return result


@router.get("/my-history", response_model=PayoutHistoryResponse)
async def get_my_payout_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    event_type: str | None = Query(None, description="Filter by event type"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    partner: Partner = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated payout history for the authenticated partner.
    🔒 Auth required.
    """
    # Build query
    conditions = [Payout.partner_id == partner.id]
    if date_from:
        conditions.append(Payout.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        conditions.append(Payout.created_at <= datetime.combine(date_to, datetime.max.time()))

    # Count total
    count_query = select(func.count(Payout.id)).where(and_(*conditions))
    if event_type:
        count_query = count_query.join(GridEvent, Payout.grid_event_id == GridEvent.id).where(
            GridEvent.event_type == event_type
        )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Fetch payouts with event details
    query = (
        select(Payout, GridEvent)
        .outerjoin(GridEvent, Payout.grid_event_id == GridEvent.id)
        .where(and_(*conditions))
    )
    if event_type:
        query = query.where(GridEvent.event_type == event_type)

    query = query.order_by(Payout.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    payouts = []
    for payout, event in rows:
        payouts.append(PayoutDetailResponse(
            id=payout.id,
            partner_id=payout.partner_id,
            policy_id=payout.policy_id,
            grid_event_id=payout.grid_event_id,
            amount=payout.amount,
            duration_hours=payout.duration_hours,
            rate_per_hour=payout.rate_per_hour,
            upi_reference=payout.upi_reference,
            status=payout.status.value,
            paid_at=payout.paid_at,
            failure_reason=payout.failure_reason,
            created_at=payout.created_at,
            event_type=event.event_type.value if event else None,
            h3_cell=event.h3_cell if event else None,
            severity=event.severity if event else None,
        ))

    return PayoutHistoryResponse(
        total=total,
        limit=limit,
        offset=offset,
        payouts=payouts,
    )


@router.get("/{payout_id}", response_model=PayoutDetailResponse)
async def get_payout_detail(
    payout_id: UUID,
    partner: Partner = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Get full payout detail with event, zone, and duration breakdown.
    🔒 Auth required.
    """
    result = await db.execute(
        select(Payout, GridEvent)
        .outerjoin(GridEvent, Payout.grid_event_id == GridEvent.id)
        .where(
            and_(
                Payout.id == payout_id,
                Payout.partner_id == partner.id,
            )
        )
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Payout not found")

    payout, event = row
    return PayoutDetailResponse(
        id=payout.id,
        partner_id=payout.partner_id,
        policy_id=payout.policy_id,
        grid_event_id=payout.grid_event_id,
        amount=payout.amount,
        duration_hours=payout.duration_hours,
        rate_per_hour=payout.rate_per_hour,
        upi_reference=payout.upi_reference,
        status=payout.status.value,
        paid_at=payout.paid_at,
        failure_reason=payout.failure_reason,
        created_at=payout.created_at,
        event_type=event.event_type.value if event else None,
        h3_cell=event.h3_cell if event else None,
        severity=event.severity if event else None,
        partner_name=partner.full_name,
    )
