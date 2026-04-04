"""
GridGuard AI — Fraud Router
Fraud flag management for admin
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.fraud_flag import FraudFlag
from app.models.policy import Policy
from app.models.partner import Partner
from app.schemas.schemas import FraudFlagUpdate
from app.core.dependencies import admin_only
from app.core.websocket_manager import manager

router = APIRouter(prefix="/fraud", tags=["fraud"])


@router.get("/flags")
async def get_fraud_flags(
    severity: str | None = Query(None),
    flag_status: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: Partner = Depends(admin_only),
):
    """Get paginated fraud flags enriched with partner + payout context (admin only)."""
    from app.database import get_database

    db = get_database()

    match_filter: dict = {}
    if severity:
        match_filter["severity"] = severity
    if flag_status:
        match_filter["status"] = flag_status

    date_filter: dict = {}
    try:
        if date_from:
            date_filter["$gte"] = datetime.fromisoformat(date_from)
        if date_to:
            date_filter["$lte"] = datetime.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from/date_to must be valid ISO datetime strings",
        )

    if date_filter:
        match_filter["flagged_at"] = date_filter

    pipeline: list[dict] = [{"$match": match_filter}]

    pipeline.extend([
        {
            "$lookup": {
                "from": "partners",
                "localField": "partner_id",
                "foreignField": "_id",
                "as": "partner",
            }
        },
        {
            "$unwind": {
                "path": "$partner",
                "preserveNullAndEmptyArrays": True,
            }
        },
        {
            "$lookup": {
                "from": "payouts",
                "localField": "payout_id",
                "foreignField": "_id",
                "as": "payout",
            }
        },
        {
            "$unwind": {
                "path": "$payout",
                "preserveNullAndEmptyArrays": True,
            }
        },
    ])

    if search:
        search_regex = {"$regex": search, "$options": "i"}
        pipeline.append(
            {
                "$match": {
                    "$or": [
                        {"partner_id": search_regex},
                        {"partner.full_name": search_regex},
                        {"partner.email": search_regex},
                        {"flag_type": search_regex},
                    ]
                }
            }
        )

    pipeline.extend([
        {"$sort": {"flagged_at": -1}},
        {
            "$facet": {
                "data": [
                    {"$skip": offset},
                    {"$limit": limit},
                    {
                        "$project": {
                            "_id": 0,
                            "id": "$_id",
                            "partner_id": "$partner_id",
                            "partner_name": "$partner.full_name",
                            "partner_email": "$partner.email",
                            "city": "$partner.city",
                            "primary_zone_h3": "$partner.primary_zone_h3",
                            "payout_id": "$payout_id",
                            "payout_amount": "$payout.amount",
                            "flag_type": "$flag_type",
                            "severity": "$severity",
                            "rule_triggered": "$rule_triggered",
                            "fraud_score": "$fraud_score",
                            "checks_failed": "$checks_failed",
                            "status": "$status",
                            "flagged_at": "$flagged_at",
                            "reviewed_by": "$reviewed_by",
                            "reviewer_note": "$reviewer_note",
                        }
                    },
                ],
                "meta": [{"$count": "total"}],
            }
        },
    ])

    cursor = await db["fraud_flags"].aggregate(pipeline)
    result = await cursor.to_list(length=1)
    payload = result[0] if result else {"data": [], "meta": []}
    total = payload["meta"][0]["total"] if payload["meta"] else 0

    return {
        "flags": payload["data"],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/flags/{flag_id}")
async def update_fraud_flag(
    flag_id: str,
    update: FraudFlagUpdate,
    admin: Partner = Depends(admin_only),
):
    """Update fraud flag status (admin only)."""
    flag = await FraudFlag.get(flag_id)
    if flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fraud flag not found",
        )

    flag.status = update.status
    flag.reviewed_by = admin.id
    if update.reviewer_note:
        flag.reviewer_note = update.reviewer_note
    await flag.save()

    # If confirmed: suspend partner's policy
    if update.status == "confirmed":
        # Suspend active policy
        today = datetime.utcnow().strftime("%Y-%m-%d")
        active_policy = await Policy.find_one(
            Policy.partner_id == flag.partner_id,
            Policy.status == "active",
            Policy.week_start <= today,
            Policy.week_end >= today,
        )
        if active_policy:
            active_policy.status = "suspended"
            await active_policy.save()

        # Notify partner
        try:
            await manager.publish_to_redis(
                f"ws:partner:{flag.partner_id}",
                {
                    "type": "fraud_confirmed",
                    "flag_id": flag_id,
                    "message": "Your account has been flagged for review",
                    "sound": "alert",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception:
            pass

    return {"status": "updated", "flag_id": flag_id}
