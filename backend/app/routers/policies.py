"""
GridGuard AI — Policies Router
Policy management: current, history, generate-weekly, deduct-premium
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.policy import Policy
from app.models.partner import Partner
from app.core.dependencies import get_current_partner, admin_only

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("/current")
async def get_current_policy(
    partner: Partner = Depends(get_current_partner),
):
    """Get the current active policy for the authenticated partner."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    policy = await Policy.find_one(
        Policy.partner_id == partner.id,
        Policy.status == "active",
        Policy.week_start <= today,
        Policy.week_end >= today,
    )

    if policy is None:
        return {"policy": None, "message": "No active policy for this week"}

    return {"policy": policy.dict()}


@router.get("/history")
async def get_policy_history(
    limit: int = 20,
    offset: int = 0,
    partner: Partner = Depends(get_current_partner),
):
    """Get paginated policy history with payout counts."""
    from app.database import get_database

    db = get_database()

    # Aggregation: policies with payout counts
    pipeline = [
        {"$match": {"partner_id": partner.id}},
        {"$sort": {"week_start": -1}},
        {"$skip": offset},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "payouts",
                "let": {"pid": "$_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$policy_id", "$$pid"]}}},
                    {"$count": "count"},
                ],
                "as": "payout_info",
            }
        },
        {
            "$addFields": {
                "payout_count": {
                    "$ifNull": [{"$arrayElemAt": ["$payout_info.count", 0]}, 0]
                }
            }
        },
        {"$project": {"payout_info": 0}},
    ]

    results = await db["policies"].aggregate(pipeline).to_list(length=limit)

    total = await Policy.find(
        Policy.partner_id == partner.id
    ).count()

    return {
        "policies": results,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
