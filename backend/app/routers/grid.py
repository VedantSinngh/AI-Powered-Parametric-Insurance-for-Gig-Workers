"""
GridGuard AI — Grid / Workability Router
Endpoints for workability scores, event ingestion, and management
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
import redis.asyncio as aioredis

from app.config import settings
from app.models.grid_event import GridEvent
from app.models.partner import Partner
from app.schemas.schemas import (
    GridEventIngest,
    GridEventResponse,
    WorkabilityResponse,
)
from app.services.workability import workability_service
from app.core.dependencies import get_current_partner, admin_only, internal_only
from app.core.websocket_manager import manager
from app.utils.h3_helpers import get_city_cells

router = APIRouter(prefix="/grid", tags=["grid"])


async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


@router.get("/workability/{h3_cell}", response_model=WorkabilityResponse)
async def get_workability(
    h3_cell: str,
    partner: Partner = Depends(get_current_partner),
):
    """
    Get current workability score for an H3 cell.
    Checks Redis cache first (TTL 900s), falls back to DB query.
    """
    r = await _get_redis()

    # Check Redis cache
    cached = await r.get(f"grid:{h3_cell}")
    if cached:
        data = json.loads(cached)
        # Check if partner has active coverage
        from app.models.policy import Policy

        today = datetime.utcnow().strftime("%Y-%m-%d")
        active_policy = await Policy.find_one(
            Policy.partner_id == partner.id,
            Policy.status == "active",
            Policy.week_start <= today,
            Policy.week_end >= today,
        )
        data["coverage_active"] = active_policy is not None
        return WorkabilityResponse(**data)

    # Query active events
    active_events = await GridEvent.find(
        GridEvent.h3_cell == h3_cell,
        GridEvent.resolved_at == None,  # noqa: E711
    ).to_list()

    event_dicts = [
        {
            "event_type": e.event_type,
            "severity": e.severity,
            "raw_value": e.raw_value,
        }
        for e in active_events
    ]

    score = workability_service.calculate_score(event_dicts)
    status_str = workability_service.get_status(score)

    dominant = workability_service.get_dominant_event_type(event_dicts)
    payout_rate = workability_service.get_payout_rate(dominant) if dominant else 0.0

    # Check coverage
    from app.models.policy import Policy

    today = datetime.utcnow().strftime("%Y-%m-%d")
    active_policy = await Policy.find_one(
        Policy.partner_id == partner.id,
        Policy.status == "active",
        Policy.week_start <= today,
        Policy.week_end >= today,
    )

    result = {
        "h3_cell": h3_cell,
        "workability_score": score,
        "status": status_str,
        "active_events": event_dicts,
        "payout_rate_hr": payout_rate,
        "coverage_active": active_policy is not None,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Cache in Redis (15 min TTL)
    await r.setex(f"grid:{h3_cell}", 900, json.dumps(result, default=str))
    await r.aclose()

    return WorkabilityResponse(**result)


@router.get("/workability/city/{city}")
async def get_city_workability(city: str):
    """
    Get workability scores for all cells in a city.
    No auth required — used for public map rendering.
    """
    cells = get_city_cells(city)
    if not cells:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown city: {city}",
        )

    r = await _get_redis()
    results = []

    for cell in cells:
        cached = await r.get(f"grid:{cell}")
        if cached:
            results.append(json.loads(cached))
        else:
            # Query active events for this cell
            active_events = await GridEvent.find(
                GridEvent.h3_cell == cell,
                GridEvent.resolved_at == None,  # noqa: E711
            ).to_list()

            event_dicts = [
                {"event_type": e.event_type, "severity": e.severity, "raw_value": e.raw_value}
                for e in active_events
            ]

            score = workability_service.calculate_score(event_dicts)
            result = {
                "h3_cell": cell,
                "workability_score": score,
                "status": workability_service.get_status(score),
                "active_events": event_dicts,
                "timestamp": datetime.utcnow().isoformat(),
            }
            results.append(result)

    await r.aclose()
    return {"city": city, "cells": results, "total": len(results)}


@router.post("/events/ingest", response_model=GridEventResponse)
async def ingest_event(
    req: GridEventIngest,
    background_tasks: BackgroundTasks,
    _: bool = Depends(internal_only),
):
    """
    Ingest a new grid event (internal API only).
    1. Insert grid_event document
    2. Recalculate workability for h3_cell
    3. Cache in Redis
    4. Publish WS updates
    5. If score < 0.40: trigger payout eligibility check
    """
    # Get existing active events for this cell
    existing_events = await GridEvent.find(
        GridEvent.h3_cell == req.h3_cell,
        GridEvent.resolved_at == None,  # noqa: E711
    ).to_list()

    event_dicts = [
        {"event_type": e.event_type, "severity": e.severity, "raw_value": e.raw_value}
        for e in existing_events
    ]
    # Add the new event
    event_dicts.append({
        "event_type": req.event_type,
        "severity": req.severity,
        "raw_value": req.raw_value,
    })

    score = workability_service.calculate_score(event_dicts)

    # Insert event
    grid_event = GridEvent(
        h3_cell=req.h3_cell,
        city=req.city,
        event_type=req.event_type,
        severity=req.severity,
        raw_value=req.raw_value,
        workability_score=score,
        event_time=datetime.utcnow(),
        source_api=req.source_api,
    )
    await grid_event.insert()

    # Update Redis cache
    status_str = workability_service.get_status(score)
    dominant = workability_service.get_dominant_event_type(event_dicts)
    payout_rate = workability_service.get_payout_rate(dominant) if dominant else 0.0

    cache_data = {
        "h3_cell": req.h3_cell,
        "workability_score": score,
        "status": status_str,
        "active_events": event_dicts,
        "payout_rate_hr": payout_rate,
        "timestamp": datetime.utcnow().isoformat(),
    }

    r = await _get_redis()
    await r.setex(f"grid:{req.h3_cell}", 900, json.dumps(cache_data, default=str))

    # Publish WS updates
    ws_msg = {
        "type": "workability_update",
        **cache_data,
    }
    await r.publish(f"ws:grid:{req.h3_cell}", json.dumps(ws_msg, default=str))
    await r.publish("ws:admin:feed", json.dumps({
        "type": "new_grid_event",
        "event_id": grid_event.id,
        "h3_cell": req.h3_cell,
        "event_type": req.event_type,
        "severity": req.severity,
        "workability_score": score,
        "city": req.city,
        "timestamp": datetime.utcnow().isoformat(),
    }, default=str))
    await r.aclose()

    # Trigger payout eligibility if disrupted
    payout_triggered = False
    if score < 0.40:
        payout_triggered = True
        # Schedule Celery task (imported lazily to avoid circular imports)
        try:
            from app.tasks.payout_eligibility import check_payout_eligibility
            check_payout_eligibility.delay(req.h3_cell, grid_event.id)
        except Exception as e:
            print(f"⚠️  Celery task dispatch failed: {e}")

    return GridEventResponse(
        event_id=grid_event.id,
        workability_score=score,
        payout_triggered=payout_triggered,
    )


@router.patch("/events/{event_id}/resolve")
async def resolve_event(
    event_id: str,
    _admin: Partner = Depends(admin_only),
):
    """Resolve a grid event (admin only)."""
    event = await GridEvent.get(event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    event.resolved_at = datetime.utcnow()
    await event.save()

    # Clear Redis cache
    r = await _get_redis()
    await r.delete(f"grid:{event.h3_cell}")

    # Publish resolved status
    await r.publish(f"ws:grid:{event.h3_cell}", json.dumps({
        "type": "event_resolved",
        "event_id": event_id,
        "h3_cell": event.h3_cell,
        "event_type": event.event_type,
        "timestamp": datetime.utcnow().isoformat(),
    }, default=str))
    await r.aclose()

    return {"status": "resolved", "event_id": event_id}


@router.get("/events/active")
async def get_active_events(
    _admin: Partner = Depends(admin_only),
):
    """Get all unresolved grid events (admin only)."""
    events = await GridEvent.find(
        GridEvent.resolved_at == None,  # noqa: E711
    ).sort(-GridEvent.event_time).to_list()

    return {
        "events": [e.dict() for e in events],
        "total": len(events),
    }
