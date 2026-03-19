"""
GridGuard AI — Activity Ingestion Router
POST /activity/log — GPS and activity logging with rate limit
"""

from datetime import datetime, timedelta

import h3
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Request, status

from app.models.partner import Partner
from app.schemas.schemas import ActivityLogRequest
from app.core.dependencies import get_current_partner
from app.core.rate_limiter import limiter

router = APIRouter(prefix="/activity", tags=["activity"])


async def _log_activity_and_check_zone(
    partner_id: str, h3_cell: str, data: dict
):
    """Background task: insert activity log + check zone dominance."""
    from app.database import get_database

    db = get_database()

    # Insert via raw Motor for performance
    await db["partner_activity_logs"].insert_one({
        "_id": data["id"],
        "partner_id": partner_id,
        "h3_cell": h3_cell,
        "gps_lat": data["gps_lat"],
        "gps_lng": data["gps_lng"],
        "is_online": data["is_online"],
        "accelerometer_variance": data["accelerometer_variance"],
        "platform_status": data["platform_status"],
        "logged_at": datetime.utcnow(),
    })

    # Check zone dominance (80%+ logs in last 7d in new zone)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    pipeline = [
        {
            "$match": {
                "partner_id": partner_id,
                "logged_at": {"$gte": seven_days_ago},
            }
        },
        {
            "$group": {
                "_id": "$h3_cell",
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
    ]

    zone_counts = await db["partner_activity_logs"].aggregate(pipeline).to_list(length=10)

    if zone_counts:
        total = sum(z["count"] for z in zone_counts)
        dominant_zone = zone_counts[0]
        if total > 0 and (dominant_zone["count"] / total) >= 0.80:
            new_zone = dominant_zone["_id"]
            # Update partner's primary zone if different
            partner = await db["partners"].find_one({"_id": partner_id})
            if partner and partner.get("primary_zone_h3") != new_zone:
                await db["partners"].update_one(
                    {"_id": partner_id},
                    {
                        "$set": {
                            "primary_zone_h3": new_zone,
                            "updated_at": datetime.utcnow(),
                        }
                    },
                )


@router.post("/log")
@limiter.limit("1/5minutes")
async def log_activity(
    request: Request,
    req: ActivityLogRequest,
    background_tasks: BackgroundTasks,
    partner: Partner = Depends(get_current_partner),
):
    """
    Log partner activity (GPS, online status, accelerometer).
    Rate limited: 1 call per 5 minutes per partner.
    DB write runs in background (non-blocking).
    """
    h3_cell = h3.latlng_to_cell(req.gps_lat, req.gps_lng, 9)

    from uuid import uuid4

    log_data = {
        "id": str(uuid4()),
        "gps_lat": req.gps_lat,
        "gps_lng": req.gps_lng,
        "is_online": req.is_online,
        "accelerometer_variance": req.accelerometer_variance,
        "platform_status": req.platform_status,
    }

    # Non-blocking background insert + zone check
    background_tasks.add_task(
        _log_activity_and_check_zone,
        partner.id,
        h3_cell,
        log_data,
    )

    return {
        "status": "logged",
        "h3_cell": h3_cell,
    }
