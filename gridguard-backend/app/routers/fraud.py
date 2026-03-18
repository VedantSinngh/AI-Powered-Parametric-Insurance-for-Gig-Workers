"""
GridGuard AI — Fraud Detection Router
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
from app.models.policy import Policy, PolicyStatusEnum
from app.models.fraud_flag import FraudFlag, FraudFlagStatusEnum
from app.schemas.fraud import (
    FraudEvaluateRequest,
    FraudEvaluateResponse,
    FraudCheckResult,
    FraudFlagResponse,
    FraudFlagListResponse,
    UpdateFraudFlagRequest,
)
from app.services.fraud_eye import evaluate_fraud
from app.utils.dependencies import get_admin_partner, verify_internal_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fraud", tags=["Fraud Detection"])


@router.post("/evaluate", response_model=FraudEvaluateResponse)
async def evaluate_fraud_endpoint(
    request: FraudEvaluateRequest,
    _api_key: bool = Depends(verify_internal_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluate fraud for a payout request.
    Internal endpoint — called synchronously before every payout.
    """
    result = await evaluate_fraud(
        partner_id=request.partner_id,
        h3_cell=request.h3_cell,
        gps_lat=float(request.gps_lat),
        gps_lng=float(request.gps_lng),
        accelerometer_variance=float(request.accelerometer_variance),
        event_id=request.event_id,
        db=db,
    )

    return FraudEvaluateResponse(
        fraud_score=Decimal(result["fraud_score"]),
        checks_failed=result["checks_failed"],
        checks_detail=[FraudCheckResult(**c) for c in result["checks_detail"]],
        recommendation=result["recommendation"],
    )


@router.get("/flags", response_model=FraudFlagListResponse)
async def get_fraud_flags(
    severity: str | None = Query(None, description="Filter: info|warning|critical"),
    flag_status: str | None = Query(None, alias="status", description="Filter: pending|dismissed|escalated|confirmed"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: Partner = Depends(get_admin_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    List fraud flags with pagination and filters.
    🔒 Admin only.
    """
    conditions = []
    if severity:
        conditions.append(FraudFlag.severity == severity)
    if flag_status:
        conditions.append(FraudFlag.status == flag_status)
    if date_from:
        conditions.append(FraudFlag.flagged_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        conditions.append(FraudFlag.flagged_at <= datetime.combine(date_to, datetime.max.time()))

    # Count total
    count_query = select(func.count(FraudFlag.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Fetch flags with partner details
    query = (
        select(FraudFlag, Partner)
        .outerjoin(Partner, FraudFlag.partner_id == Partner.id)
    )
    if conditions:
        query = query.where(and_(*conditions))
    query = query.order_by(FraudFlag.flagged_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    flags = []
    for flag, partner in rows:
        flags.append(FraudFlagResponse(
            id=flag.id,
            partner_id=flag.partner_id,
            payout_id=flag.payout_id,
            flag_type=flag.flag_type.value,
            severity=flag.severity.value,
            gps_lat=flag.gps_lat,
            gps_lng=flag.gps_lng,
            accelerometer_variance=flag.accelerometer_variance,
            rule_triggered=flag.rule_triggered,
            status=flag.status.value,
            flagged_at=flag.flagged_at,
            reviewed_by=flag.reviewed_by,
            created_at=flag.created_at,
            partner_name=partner.full_name if partner else None,
            partner_phone=partner.phone_number if partner else None,
        ))

    return FraudFlagListResponse(total=total, limit=limit, offset=offset, flags=flags)


@router.patch("/flags/{flag_id}", response_model=FraudFlagResponse)
async def update_fraud_flag(
    flag_id: UUID,
    request: UpdateFraudFlagRequest,
    admin: Partner = Depends(get_admin_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Update fraud flag status. If confirmed → suspend partner policy.
    🔒 Admin only.
    """
    result = await db.execute(select(FraudFlag).where(FraudFlag.id == flag_id))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Fraud flag not found")

    # Validate status
    try:
        new_status = FraudFlagStatusEnum(request.status)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status. Must be one of: {[e.value for e in FraudFlagStatusEnum]}",
        )

    flag.status = new_status
    flag.reviewed_by = admin.full_name or str(admin.id)

    # If confirmed → suspend the partner's active policy
    if new_status == FraudFlagStatusEnum.confirmed:
        policy_result = await db.execute(
            select(Policy)
            .where(
                and_(
                    Policy.partner_id == flag.partner_id,
                    Policy.status == PolicyStatusEnum.active,
                )
            )
        )
        active_policies = policy_result.scalars().all()
        for policy in active_policies:
            policy.status = PolicyStatusEnum.suspended
        logger.warning(f"Partner {flag.partner_id} policies suspended due to confirmed fraud")

    await db.flush()

    # Re-fetch with partner details
    partner_result = await db.execute(select(Partner).where(Partner.id == flag.partner_id))
    partner = partner_result.scalar_one_or_none()

    return FraudFlagResponse(
        id=flag.id,
        partner_id=flag.partner_id,
        payout_id=flag.payout_id,
        flag_type=flag.flag_type.value,
        severity=flag.severity.value,
        gps_lat=flag.gps_lat,
        gps_lng=flag.gps_lng,
        accelerometer_variance=flag.accelerometer_variance,
        rule_triggered=flag.rule_triggered,
        status=flag.status.value,
        flagged_at=flag.flagged_at,
        reviewed_by=flag.reviewed_by,
        created_at=flag.created_at,
        partner_name=partner.full_name if partner else None,
        partner_phone=partner.phone_number if partner else None,
    )
