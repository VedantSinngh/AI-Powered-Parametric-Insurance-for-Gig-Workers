"""
GridGuard AI — Policies Router
Policy management: current, history, generate-weekly, deduct-premium
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.models.policy import Policy
from app.models.premium_prediction import PremiumPrediction
from app.models.partner import Partner
from app.core.dependencies import get_current_partner, admin_only
from app.services.risk_engine import risk_engine

router = APIRouter(prefix="/policies", tags=["policies"])

PREMIUM_TO_RISK_SCORE: dict[float, float] = {
    12.0: 0.15,
    18.0: 0.30,
    24.0: 0.50,
    36.0: 0.70,
    48.0: 0.90,
}

PRICING_TIER_ROWS = [
    {"tier": "Tier 1", "premium_amount": 12.0, "risk_band": "0.00 - 0.20", "note": "Stable zones"},
    {"tier": "Tier 2", "premium_amount": 18.0, "risk_band": "0.20 - 0.40", "note": "Low disruption"},
    {"tier": "Tier 3", "premium_amount": 24.0, "risk_band": "0.40 - 0.60", "note": "Moderate risk"},
    {"tier": "Tier 4", "premium_amount": 36.0, "risk_band": "0.60 - 0.80", "note": "High disruption"},
    {"tier": "Tier 5", "premium_amount": 48.0, "risk_band": "0.80 - 1.00", "note": "Severe risk"},
]


class ActivatePolicyRequest(BaseModel):
    premium_amount: float = Field(gt=0)


def _week_window(anchor: datetime) -> tuple[str, str]:
    week_start_dt = (anchor - timedelta(days=anchor.weekday())).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    week_end_dt = week_start_dt + timedelta(days=6)
    return week_start_dt.strftime("%Y-%m-%d"), week_end_dt.strftime("%Y-%m-%d")


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

    cursor = await db["policies"].aggregate(pipeline)
    results = await cursor.to_list(length=limit)

    total = await Policy.find(
        Policy.partner_id == partner.id
    ).count()

    return {
        "policies": results,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/pricing-summary")
async def get_pricing_summary(
    partner: Partner = Depends(get_current_partner),
):
    """Return current and next-week policy pricing driven by live risk signals."""
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")

    current_week_start, current_week_end = _week_window(now)
    next_week_start_dt = (now - timedelta(days=now.weekday())).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    ) + timedelta(days=7)
    next_week_start, next_week_end = _week_window(next_week_start_dt)

    current_policy = await Policy.find_one(
        Policy.partner_id == partner.id,
        Policy.status == "active",
        Policy.week_start <= today,
        Policy.week_end >= today,
    )

    if current_policy is None:
        current_policy = await Policy.find_one(
            Policy.partner_id == partner.id,
            Policy.week_start == current_week_start,
            Policy.week_end == current_week_end,
        )

    next_policy = await Policy.find_one(
        Policy.partner_id == partner.id,
        Policy.week_start == next_week_start,
        Policy.week_end == next_week_end,
    )

    current_payload = None
    if current_policy is not None:
        current_payload = {
            "week_start": current_policy.week_start,
            "week_end": current_policy.week_end,
            "premium_amount": current_policy.premium_amount,
            "risk_score": current_policy.risk_score,
            "risk_tier": risk_engine.score_to_risk_tier(current_policy.risk_score),
            "status": current_policy.status,
            "source": "policy",
        }

    next_risk_score: float | None = None
    next_premium_amount: float | None = None
    next_status = "projected"
    next_source = "live_estimate"

    if next_policy is not None:
        next_risk_score = next_policy.risk_score
        next_premium_amount = next_policy.premium_amount
        next_status = next_policy.status
        next_source = "policy"
    else:
        prediction_docs = await PremiumPrediction.find(
            PremiumPrediction.partner_id == partner.id,
            PremiumPrediction.predicted_for_week == next_week_start,
        ).sort(-PremiumPrediction.generated_at).limit(1).to_list()

        if prediction_docs:
            prediction = prediction_docs[0]
            next_risk_score = prediction.risk_score
            next_premium_amount = prediction.premium_amount
            next_source = "prediction"
        else:
            try:
                features = await risk_engine.extract_features(
                    partner.id,
                    partner.primary_zone_h3 or "",
                )
                next_risk_score = risk_engine.predict_risk_score(features)
                _, next_premium_amount = risk_engine.score_to_premium(next_risk_score)
            except Exception:
                baseline = current_payload["risk_score"] if current_payload else 0.35
                next_risk_score = float(baseline)
                _, next_premium_amount = risk_engine.score_to_premium(next_risk_score)

    next_payload = None
    if next_risk_score is not None and next_premium_amount is not None:
        next_payload = {
            "week_start": next_week_start,
            "week_end": next_week_end,
            "premium_amount": float(next_premium_amount),
            "risk_score": float(next_risk_score),
            "risk_tier": risk_engine.score_to_risk_tier(float(next_risk_score)),
            "status": next_status,
            "source": next_source,
            "note": "Next week pricing updates with live risk activity and may change before Monday.",
        }

    return {
        "as_of": datetime.utcnow().isoformat(),
        "current_week": current_payload,
        "next_week": next_payload,
        "pricing_tiers": PRICING_TIER_ROWS,
        "message": "Weekly pricing is assigned automatically from risk levels.",
    }


@router.post("/activate")
async def activate_policy(
    _req: ActivatePolicyRequest,
    _partner: Partner = Depends(get_current_partner),
):
    """Manual activation is disabled; pricing is assigned from live risk signals."""
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Manual policy activation is disabled. Weekly pricing is auto-assigned "
            "based on risk and may update before the next week starts."
        ),
    )
