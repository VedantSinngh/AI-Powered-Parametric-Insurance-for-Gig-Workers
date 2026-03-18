"""
GridGuard AI — Workability Engine Service
Calculates and caches workability scores for H3 grid cells.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.grid_event import GridEvent, EventTypeEnum
from app.utils.redis_client import (
    get_cached_workability,
    set_cached_workability,
    invalidate_workability_cache,
)
from app.utils.h3_helpers import h3_to_center, get_city_cells

logger = logging.getLogger(__name__)

# Event type weights for workability calculation
EVENT_WEIGHTS = {
    EventTypeEnum.rainfall: 0.30,
    EventTypeEnum.heat: 0.20,
    EventTypeEnum.aqi: 0.20,
    EventTypeEnum.road_saturation: 0.20,
    EventTypeEnum.app_outage: 0.10,
}


def workability_status(score: Decimal) -> str:
    """Map workability score to status label."""
    if score >= Decimal("0.7"):
        return "normal"
    elif score >= Decimal("0.4"):
        return "degraded"
    else:
        return "critical"


async def calculate_workability_score(
    h3_cell: str, db: AsyncSession
) -> tuple[Decimal, list[GridEvent]]:
    """
    Calculate the workability score for an H3 cell based on active (unresolved) events.
    Returns (score, active_events).
    Score = 1.0 - weighted sum of event severities.
    """
    result = await db.execute(
        select(GridEvent)
        .where(
            and_(
                GridEvent.h3_cell == h3_cell,
                GridEvent.resolved_at.is_(None),
            )
        )
        .order_by(GridEvent.event_time.desc())
    )
    active_events = list(result.scalars().all())

    if not active_events:
        return Decimal("1.000"), []

    # Calculate weighted severity impact
    total_impact = Decimal("0.000")
    for event in active_events:
        weight = Decimal(str(EVENT_WEIGHTS.get(event.event_type, 0.1)))
        total_impact += event.severity * weight

    # Cap total impact at 1.0
    total_impact = min(total_impact, Decimal("1.000"))

    # Workability = 1.0 - impact
    score = max(Decimal("0.000"), Decimal("1.000") - total_impact)
    score = round(score, 3)

    return score, active_events


async def get_workability(
    h3_cell: str, db: AsyncSession, force_recalc: bool = False
) -> dict:
    """
    Get workability score for an H3 cell.
    Uses cached value if fresh, otherwise recalculates.
    """
    if not force_recalc:
        cached = await get_cached_workability(h3_cell)
        if cached:
            return cached

    score, active_events = await calculate_workability_score(h3_cell, db)

    response = {
        "h3_cell": h3_cell,
        "workability_score": str(score),
        "status": workability_status(score),
        "active_events": [
            {
                "event_id": str(event.id),
                "event_type": event.event_type.value,
                "severity": str(event.severity),
                "raw_value": str(event.raw_value) if event.raw_value else None,
                "event_time": event.event_time.isoformat(),
            }
            for event in active_events
        ],
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    # Cache the result
    await set_cached_workability(h3_cell, response)

    return response


async def get_city_workability(city: str, db: AsyncSession) -> dict:
    """Get workability scores for all H3 cells in a city."""
    cells = get_city_cells(city)
    cell_data = []

    for cell in cells:
        workability = await get_workability(cell, db)
        lat, lng = h3_to_center(cell)
        cell_data.append({
            "h3_cell": cell,
            "score": workability["workability_score"],
            "status": workability["status"],
            "lat": lat,
            "lng": lng,
        })

    return {"city": city, "cells": cell_data}


async def recalculate_and_cache(h3_cell: str, db: AsyncSession) -> Decimal:
    """Force recalculate workability score and update cache."""
    await invalidate_workability_cache(h3_cell)
    result = await get_workability(h3_cell, db, force_recalc=True)
    return Decimal(result["workability_score"])
