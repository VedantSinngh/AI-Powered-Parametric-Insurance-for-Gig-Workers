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
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: Partner = Depends(admin_only),
):
    """Get paginated fraud flags (admin only)."""
    filters = []

    if severity:
        filters.append(FraudFlag.severity == severity)
    if flag_status:
        filters.append(FraudFlag.status == flag_status)
    if date_from:
        filters.append(
            FraudFlag.flagged_at >= datetime.fromisoformat(date_from)
        )
    if date_to:
        filters.append(
            FraudFlag.flagged_at <= datetime.fromisoformat(date_to)
        )

    flags = (
        await FraudFlag.find(*filters)
        .sort(-FraudFlag.flagged_at)
        .skip(offset)
        .limit(limit)
        .to_list()
    )

    total = await FraudFlag.find(*filters).count()

    return {
        "flags": [f.dict() for f in flags],
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
