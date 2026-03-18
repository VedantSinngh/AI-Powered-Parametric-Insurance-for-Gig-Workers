"""
GridGuard AI — Activity Ingestion Router
"""

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.partner import Partner
from app.models.activity_log import PartnerActivityLog, PlatformStatusEnum
from app.schemas.activity import ActivityLogRequest, ActivityLogResponse
from app.utils.dependencies import get_current_partner
from app.utils.h3_helpers import gps_to_h3

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/activity", tags=["Activity"])


@router.post("/log", response_model=ActivityLogResponse)
async def log_activity(
    request: ActivityLogRequest,
    partner: Partner = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Log partner activity (called by mobile app every 5 minutes).
    1. Reverse geocode GPS → assign H3 cell (resolution 9)
    2. Insert into partner_activity_logs
    3. Update partner's primary_zone_h3 if 80%+ of last 7-day logs are in new zone
    🔒 Auth required.
    """
    # Assign H3 cell from GPS
    h3_cell = gps_to_h3(float(request.gps_lat), float(request.gps_lng))

    # Validate platform_status
    try:
        platform_status = PlatformStatusEnum(request.platform_status)
    except ValueError:
        platform_status = PlatformStatusEnum.idle

    # Insert activity log
    log = PartnerActivityLog(
        partner_id=partner.id,
        h3_cell=h3_cell,
        gps_lat=request.gps_lat,
        gps_lng=request.gps_lng,
        is_online=request.is_online,
        accelerometer_variance=request.accelerometer_variance,
        platform_status=platform_status,
        logged_at=datetime.now(timezone.utc),
    )
    db.add(log)
    await db.flush()

    # ── Zone update logic ──
    # Check if 80%+ of last 7-day logs are in a new zone
    zone_updated = False
    new_zone = None

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(
        select(PartnerActivityLog.h3_cell)
        .where(
            and_(
                PartnerActivityLog.partner_id == partner.id,
                PartnerActivityLog.logged_at >= seven_days_ago,
                PartnerActivityLog.h3_cell.is_not(None),
            )
        )
    )
    recent_cells = [row[0] for row in result.all()]

    if recent_cells:
        cell_counts = Counter(recent_cells)
        most_common_cell, count = cell_counts.most_common(1)[0]
        threshold = len(recent_cells) * 0.8

        if count >= threshold and most_common_cell != partner.primary_zone_h3:
            partner.primary_zone_h3 = most_common_cell
            await db.flush()
            zone_updated = True
            new_zone = most_common_cell
            logger.info(f"Partner {partner.id} zone updated to {most_common_cell}")

    return ActivityLogResponse(
        id=log.id,
        partner_id=log.partner_id,
        h3_cell=h3_cell,
        gps_lat=log.gps_lat,
        gps_lng=log.gps_lng,
        is_online=log.is_online,
        platform_status=platform_status.value,
        logged_at=log.logged_at,
        zone_updated=zone_updated,
        new_zone_h3=new_zone,
    )
