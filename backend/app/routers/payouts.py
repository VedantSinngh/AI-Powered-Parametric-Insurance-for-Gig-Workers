"""
GridGuard AI — Payouts Router
Payout history and detail endpoints
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header, status

from app.models.payout import Payout
from app.models.grid_event import GridEvent
from app.models.partner import Partner
from app.schemas.schemas import PayoutResponse
from app.core.dependencies import get_current_partner, internal_only
from app.services.payout_engine import payout_engine
from app.services.razorpay_payouts import razorpay_payout_service
from app.config import settings

router = APIRouter(prefix="/payouts", tags=["payouts"])


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
):
    """Handle Razorpay payout webhooks and sync payout lifecycle state."""
    raw_body = await request.body()

    if settings.RAZORPAY_WEBHOOK_SECRET:
        if not razorpay_payout_service.verify_signature(raw_body, x_razorpay_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Razorpay webhook signature",
            )

    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        )
    payout_entity = (
        payload.get("payload", {})
        .get("payout", {})
        .get("entity", {})
    )
    provider_payout_id = payout_entity.get("id")
    if not provider_payout_id:
        return {"status": "ignored", "reason": "missing_payout_id"}

    payout = await Payout.find_one(Payout.provider_payout_id == provider_payout_id)
    if payout is None:
        payout = await Payout.find_one(Payout.mock_reference == provider_payout_id)
    if payout is None:
        return {
            "status": "ignored",
            "reason": "payout_not_found",
            "provider_payout_id": provider_payout_id,
        }

    provider_status = (payout_entity.get("status") or "").lower()
    internal_status = razorpay_payout_service.to_internal_status(provider_status)

    payout.provider = "razorpay"
    payout.provider_payout_id = provider_payout_id
    payout.provider_status = provider_status
    payout.provider_reference = payout_entity.get("utr") or payout.provider_reference
    if payout.provider_reference:
        payout.mock_reference = payout.provider_reference

    payout.status = internal_status
    if internal_status == "paid" and payout.paid_at is None:
        payout.paid_at = datetime.utcnow()
    if internal_status == "failed":
        status_details = payout_entity.get("status_details", {})
        payout.failure_reason = (
            status_details.get("description")
            or status_details.get("reason")
            or "Razorpay payout failed"
        )

    await payout.save()

    return {
        "status": "ok",
        "event": payload.get("event"),
        "payout_id": payout.id,
        "provider_payout_id": provider_payout_id,
        "internal_status": internal_status,
    }


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
        try:
            filters.append(Payout.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_from must be a valid ISO datetime",
            )
    if date_to:
        try:
            filters.append(Payout.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_to must be a valid ISO datetime",
            )

    if event_type:
        matching_event_ids = [
            event.id
            for event in await GridEvent.find(GridEvent.event_type == event_type).to_list()
        ]
        if not matching_event_ids:
            return {
                "payouts": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
            }
        filters.append({"grid_event_id": {"$in": matching_event_ids}})

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

        results.append(data)

    total = await Payout.find(*filters).count()

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
