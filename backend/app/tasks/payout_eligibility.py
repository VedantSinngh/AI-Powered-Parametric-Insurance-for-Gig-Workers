"""
GridGuard AI — Payout Eligibility Task
Triggered ad hoc when workability drops below 0.40
"""

import asyncio
import json
from datetime import datetime

import h3
from app.tasks.celery_app import app


@app.task(name="app.tasks.payout_eligibility.check_payout_eligibility")
def check_payout_eligibility(h3_cell: str, event_id: str):
    """Check which partners are eligible for payout in disrupted zone."""
    asyncio.run(_check_eligibility(h3_cell, event_id))


async def _check_eligibility(h3_cell: str, event_id: str):
    from pymongo import AsyncMongoClient
    from beanie import init_beanie
    from app.config import settings
    from app.models.partner import Partner
    from app.models.policy import Policy
    from app.services.payout_engine import payout_engine
    from app.database import DOCUMENT_MODELS

    import redis.asyncio as aioredis

    client = AsyncMongoClient(settings.MONGODB_URL)
    await init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=DOCUMENT_MODELS,
    )

    # Get k-ring neighbors
    neighbors = h3.grid_disk(h3_cell, 1)
    all_cells = list(neighbors | {h3_cell})

    # Find eligible partners
    today = datetime.utcnow().strftime("%Y-%m-%d")
    partners = await Partner.find(
        {"primary_zone_h3": {"$in": all_cells}},
        Partner.is_active == True,  # noqa: E712
    ).to_list()

    triggered = 0
    for partner in partners:
        # Check active policy
        active_policy = await Policy.find_one(
            Policy.partner_id == partner.id,
            Policy.status == "active",
            Policy.week_start <= today,
            Policy.week_end >= today,
        )

        if active_policy:
            result = await payout_engine.trigger_payout(
                partner.id, event_id, 1.0
            )
            if result.get("status") == "paid":
                triggered += 1

    # Publish batch summary
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.publish("ws:admin:feed", json.dumps({
            "type": "payout_batch_completed",
            "h3_cell": h3_cell,
            "event_id": event_id,
            "partners_triggered": triggered,
            "total_eligible": len(partners),
            "timestamp": datetime.utcnow().isoformat(),
        }))
        await r.aclose()
    except Exception:
        pass

    print(f"✅ Payout eligibility: {triggered}/{len(partners)} triggered for {h3_cell}")
    client.close()
