"""
GridGuard AI — Payouts Router
Payout history and detail endpoints
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.payout import Payout
from app.models.grid_event import GridEvent
from app.models.partner import Partner
from app.schemas.schemas import PayoutResponse
from app.core.dependencies import get_current_partner, internal_only
from app.services.payout_engine import payout_engine

router = APIRouter(prefix="/payouts", tags=["payouts"])


@router.post("/trigger")
async def trigger_payout(
    partner_id: str,
    grid_event_id: str,
    duration_hours: float = 1.0,
    _: bool = Depends(internal_only),
):
    """Trigger a payout (internal Celery task only)."""
    result = await payout_engine.trigger_payout(
        partner_id, grid_event_id, duration_hours
    )
    return result


@router.get("/my-history")
async def get_my_history(
    event_type: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    partner: Partner = Depends(get_current_partner),
):
    """Get payout history for the authenticated partner."""
    filters = [Payout.partner_id == partner.id]

    if date_from:
        filters.append(
            Payout.created_at >= datetime.fromisoformat(date_from)
        )
    if date_to:
        filters.append(
            Payout.created_at <= datetime.fromisoformat(date_to)
        )

    payouts = (
        await Payout.find(*filters)
        .sort(-Payout.created_at)
        .skip(offset)
        .limit(limit)
        .to_list()
    )

    # Enrich with event details
    results = []
    for p in payouts:
        data = p.dict()
        event = await GridEvent.get(p.grid_event_id)
        if event:
            data["event_type"] = event.event_type
            data["h3_cell"] = event.h3_cell
            data["event_severity"] = event.severity

        # Filter by event_type if specified
        if event_type and data.get("event_type") != event_type:
            continue

        results.append(data)

    total = await Payout.find(Payout.partner_id == partner.id).count()

    return {
        "payouts": results,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{payout_id}")
async def get_payout_detail(
    payout_id: str,
    partner: Partner = Depends(get_current_partner),
):
    """Get full payout detail with event + zone + duration breakdown."""
    payout = await Payout.get(payout_id)
    if payout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payout not found",
        )

    # Verify ownership
    if payout.partner_id != partner.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your payout",
        )

    data = payout.dict()

    # Enrich with event details
    event = await GridEvent.get(payout.grid_event_id)
    if event:
        data["event"] = {
            "id": event.id,
            "type": event.event_type,
            "severity": event.severity,
            "h3_cell": event.h3_cell,
            "city": event.city,
            "raw_value": event.raw_value,
            "event_time": event.event_time.isoformat() if event.event_time else None,
        }

    return data
