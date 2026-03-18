"""
GridGuard AI — Maintenance Tasks
Resolves stale events and performs cleanup.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_, func

from app.tasks.celery_app import celery_app
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Event type thresholds for auto-resolution
RESOLUTION_THRESHOLDS = {
    "rainfall": 2.0,       # mm/hr below this → resolved
    "heat": 38.0,          # °C below this → resolved
    "aqi": 150,            # AQI below this → resolved
    "road_saturation": 1.2, # congestion ratio below this → resolved
    "app_outage": 0,       # manual resolution only
}

STALE_EVENT_HOURS = 6  # Auto-resolve events older than 6 hours with no recent data


@celery_app.task(name="app.tasks.maintenance.resolve_stale_events", bind=True, max_retries=2)
def resolve_stale_events(self):
    """
    Mark events as resolved if stale or conditions have improved.
    Runs every 2 hours.
    """
    import asyncio
    asyncio.run(_resolve_stale_async())


async def _resolve_stale_async():
    """Async implementation of stale event resolution."""
    from app.database import async_session_factory
    from app.models.grid_event import GridEvent
    from app.services.workability import recalculate_and_cache

    async with async_session_factory() as db:
        try:
            now = datetime.now(timezone.utc)
            stale_cutoff = now - timedelta(hours=STALE_EVENT_HOURS)

            # Find unresolved events older than STALE_EVENT_HOURS
            result = await db.execute(
                select(GridEvent)
                .where(
                    and_(
                        GridEvent.resolved_at.is_(None),
                        GridEvent.event_time < stale_cutoff,
                    )
                )
            )
            stale_events = result.scalars().all()

            resolved_count = 0
            affected_cells = set()

            for event in stale_events:
                # Check if there's a recent event of the same type for this cell
                recent_check = await db.execute(
                    select(func.count(GridEvent.id))
                    .where(
                        and_(
                            GridEvent.h3_cell == event.h3_cell,
                            GridEvent.event_type == event.event_type,
                            GridEvent.event_time >= stale_cutoff,
                            GridEvent.resolved_at.is_(None),
                            GridEvent.id != event.id,
                        )
                    )
                )
                recent_count = recent_check.scalar() or 0

                # If no recent events of the same type, resolve this one
                if recent_count == 0:
                    event.resolved_at = now
                    resolved_count += 1
                    affected_cells.add(event.h3_cell)

            # Recalculate workability for affected cells
            for cell in affected_cells:
                await recalculate_and_cache(cell, db)

            await db.commit()
            logger.info(
                f"Stale event resolution complete: {resolved_count} events resolved, "
                f"{len(affected_cells)} cells recalculated"
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"Stale event resolution failed: {e}")
            raise
