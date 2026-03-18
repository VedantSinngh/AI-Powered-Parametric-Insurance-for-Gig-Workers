"""
GridGuard AI — Policy Router
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.partner import Partner
from app.models.policy import Policy, PolicyStatusEnum
from app.models.payout import Payout
from app.schemas.policy import PolicyResponse, PolicyHistoryItem, PolicyHistoryResponse
from app.utils.dependencies import get_current_partner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/policies", tags=["Policies"])


@router.get("/current", response_model=PolicyResponse)
async def get_current_policy(
    partner: Partner = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the active policy for the authenticated partner this week.
    🔒 Auth required.
    """
    today = date.today()
    result = await db.execute(
        select(Policy)
        .where(
            and_(
                Policy.partner_id == partner.id,
                Policy.status == PolicyStatusEnum.active,
                Policy.week_start <= today,
                Policy.week_end >= today,
            )
        )
        .limit(1)
    )
    policy = result.scalar_one_or_none()

    if not policy:
        raise HTTPException(
            status_code=404,
            detail="No active policy found for this week",
        )

    return PolicyResponse.model_validate(policy)


@router.get("/history", response_model=PolicyHistoryResponse)
async def get_policy_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    partner: Partner = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated history of past policies with payout counts per week.
    🔒 Auth required.
    """
    # Count total
    count_result = await db.execute(
        select(func.count(Policy.id)).where(Policy.partner_id == partner.id)
    )
    total = count_result.scalar() or 0

    # Fetch policies
    result = await db.execute(
        select(Policy)
        .where(Policy.partner_id == partner.id)
        .order_by(Policy.week_start.desc())
        .offset(offset)
        .limit(limit)
    )
    policies = result.scalars().all()

    # Get payout counts/amounts per policy
    items = []
    for policy in policies:
        payout_result = await db.execute(
            select(
                func.count(Payout.id),
                func.coalesce(func.sum(Payout.amount), 0),
            ).where(Payout.policy_id == policy.id)
        )
        payout_count, payout_amount = payout_result.one()

        items.append(PolicyHistoryItem(
            id=policy.id,
            week_start=policy.week_start,
            week_end=policy.week_end,
            premium_amount=policy.premium_amount,
            risk_score=policy.risk_score,
            status=policy.status.value,
            payout_count=payout_count,
            total_payout_amount=payout_amount,
            created_at=policy.created_at,
        ))

    return PolicyHistoryResponse(
        total=total,
        limit=limit,
        offset=offset,
        policies=items,
    )
