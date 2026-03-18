"""
GridGuard AI — Grid (Workability Engine) Router
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.grid_event import GridEvent, EventTypeEnum
from app.models.partner import Partner
from app.schemas.grid_event import (
    GridEventIngestRequest,
    GridEventIngestResponse,
    WorkabilityResponse,
    CityWorkabilityResponse,
    GridEventResponse,
)
from app.services.workability import (
    get_workability,
    get_city_workability,
    recalculate_and_cache,
)
from app.utils.dependencies import get_current_partner, get_admin_partner, verify_internal_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/grid", tags=["Workability Engine"])


@router.get("/workability/{h3_cell}", response_model=WorkabilityResponse)
async def get_cell_workability(
    h3_cell: str,
    partner: Partner = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Get cached workability score for an H3 cell.
    If stale, recalculates from latest grid events.
    🔒 Auth required.
    """
    result = await get_workability(h3_cell, db)
    return WorkabilityResponse(
        h3_cell=result["h3_cell"],
        workability_score=Decimal(result["workability_score"]),
        status=result["status"],
        active_events=result["active_events"],
        last_updated=datetime.fromisoformat(result["last_updated"]),
    )


@router.get("/workability/city/{city}", response_model=CityWorkabilityResponse)
async def get_city_workability_endpoint(
    city: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all H3 cells for a city with current workability scores.
    Public endpoint — no auth required.
    """
    result = await get_city_workability(city, db)
    return CityWorkabilityResponse(**result)


@router.post("/events/ingest", response_model=GridEventIngestResponse)
async def ingest_grid_event(
    request: GridEventIngestRequest,
    _api_key: bool = Depends(verify_internal_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest a grid event from an external source.
    Internal endpoint (API key auth, not JWT).
    1. Insert into grid_events
    2. Recalculate workability score
    3. Update Redis cache
    4. If score < 0.4: trigger payout eligibility check
    """
    # Validate event type
    try:
        event_type = EventTypeEnum(request.event_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid event_type. Must be one of: {[e.value for e in EventTypeEnum]}",
        )

    # Insert grid event
    event = GridEvent(
        h3_cell=request.h3_cell,
        city=request.city,
        event_type=event_type,
        severity=request.severity,
        raw_value=request.raw_value,
        event_time=request.event_time,
        source_api=request.source,
    )
    db.add(event)
    await db.flush()

    # Recalculate workability score
    new_score = await recalculate_and_cache(request.h3_cell, db)
    event.workability_score = new_score
    await db.flush()

    # If score < 0.4, trigger payout eligibility check via Celery
    payout_triggered = False
    if new_score < Decimal("0.4"):
        payout_triggered = True
        # Import here to avoid circular imports
        try:
            from app.tasks.payout_tasks import check_payout_eligibility
            check_payout_eligibility.delay(request.h3_cell, str(event.id))
        except Exception as e:
            logger.error(f"Failed to trigger payout eligibility task: {e}")

    logger.info(
        f"Grid event ingested: {event.id}, cell={request.h3_cell}, "
        f"type={event_type.value}, score={new_score}, payout_triggered={payout_triggered}"
    )

    return GridEventIngestResponse(
        event_id=event.id,
        workability_score=new_score,
        payout_triggered=payout_triggered,
    )


@router.get("/events/active", response_model=list[GridEventResponse])
async def get_active_events(
    admin: Partner = Depends(get_admin_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all active (unresolved) grid events.
    🔒 Admin only.
    """
    result = await db.execute(
        select(GridEvent)
        .where(GridEvent.resolved_at.is_(None))
        .order_by(GridEvent.event_time.desc())
    )
    events = result.scalars().all()
    return [GridEventResponse.model_validate(e) for e in events]


@router.patch("/events/{event_id}/resolve", response_model=GridEventResponse)
async def resolve_event(
    event_id: UUID,
    admin: Partner = Depends(get_admin_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve a grid event — sets resolved_at and stops payout accumulation.
    🔒 Admin only.
    """
    result = await db.execute(select(GridEvent).where(GridEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event.resolved_at = datetime.now(timezone.utc)
    await db.flush()

    # Recalculate workability for the affected cell
    await recalculate_and_cache(event.h3_cell, db)

    logger.info(f"Grid event resolved: {event_id}")
    return GridEventResponse.model_validate(event)
