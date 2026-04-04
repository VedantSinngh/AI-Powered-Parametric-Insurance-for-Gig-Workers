"""
GridGuard AI — System Health Broadcaster Task
Runs every 60 seconds — broadcasts health metrics to admin feed
"""

import asyncio
import json
from datetime import datetime

from app.tasks.celery_app import app


@app.task(name="app.tasks.health_broadcaster.system_health_broadcast")
def system_health_broadcast():
    """Broadcast system health metrics to admin WebSocket feed."""
    asyncio.run(_broadcast_health())


async def _broadcast_health():
    from app.config import settings
    from pymongo import AsyncMongoClient

    import redis.asyncio as aioredis

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    health = {
        "type": "system_health_metrics",
        "ws_connections": 0,
        "redis_ping_ms": -1,
        "db_ping_ms": -1,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Redis ping
    try:
        start = datetime.utcnow()
        await r.ping()
        health["redis_ping_ms"] = int(
            (datetime.utcnow() - start).total_seconds() * 1000
        )
    except Exception:
        pass

    # MongoDB ping
    try:
        client = AsyncMongoClient(settings.MONGODB_URL)
        db = client[settings.MONGODB_DB_NAME]
        start = datetime.utcnow()
        await db.command("ping")
        health["db_ping_ms"] = int(
            (datetime.utcnow() - start).total_seconds() * 1000
        )
        client.close()
    except Exception:
        pass

    # Publish to admin feed
    try:
        await r.publish("ws:admin:feed", json.dumps(health))
    except Exception:
        pass

    await r.aclose()
