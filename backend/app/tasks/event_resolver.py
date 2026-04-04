"""
GridGuard AI — Stale Event Resolver Task
Runs every 2 hours — resolves events not refreshed within staleness window
"""

import asyncio
import json
from datetime import datetime, timedelta

from app.tasks.celery_app import app


@app.task(name="app.tasks.event_resolver.resolve_stale_events")
def resolve_stale_events():
    """Resolve stale events that have not been refreshed recently."""
    asyncio.run(_resolve_events())


async def _resolve_events():
    from pymongo import AsyncMongoClient
    from beanie import init_beanie
    from app.config import settings
    from app.models.grid_event import GridEvent
    from app.database import DOCUMENT_MODELS

    import redis.asyncio as aioredis

    client = AsyncMongoClient(settings.MONGODB_URL)
    await init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=DOCUMENT_MODELS,
    )

    stale_before = datetime.utcnow() - timedelta(minutes=settings.STALE_EVENT_MINUTES)

    # Find unresolved events that are stale by event_time freshness
    events = await GridEvent.find(
        GridEvent.resolved_at == None,  # noqa: E711
        GridEvent.event_time <= stale_before,
    ).to_list()

    resolved_count = 0
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    for event in events:
        event.resolved_at = datetime.utcnow()
        await event.save()
        resolved_count += 1

        # Clear Redis cache for both data modes.
        await r.delete(
            f"grid:{event.h3_cell}",
            f"grid:real:{event.h3_cell}",
            f"grid:demo:{event.h3_cell}",
        )

        # Push WS update
        try:
            await r.publish(f"ws:grid:{event.h3_cell}", json.dumps({
                "type": "event_resolved",
                "event_id": event.id,
                "h3_cell": event.h3_cell,
                "event_type": event.event_type,
                "timestamp": datetime.utcnow().isoformat(),
            }))
        except Exception:
            pass

    await r.aclose()
    print(f"✅ Resolved {resolved_count} stale events")
    client.close()
