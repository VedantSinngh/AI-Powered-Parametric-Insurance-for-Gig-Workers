"""
GridGuard AI — FraudEye Service
Composite fraud scoring with 4 weighted checks before every payout.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.partner import Partner
from app.models.activity_log import PartnerActivityLog
from app.models.fraud_flag import (
    FraudFlag,
    FraudFlagTypeEnum,
    FraudSeverityEnum,
    FraudFlagStatusEnum,
)
from app.utils.h3_helpers import gps_distance_to_h3_center_m

logger = logging.getLogger(__name__)

# ── Fraud Check Weights ──
CHECK_WEIGHTS = {
    "gps_zone_match": 0.35,
    "pre_activity_window": 0.30,
    "accelerometer_motion": 0.20,
    "device_fingerprint": 0.15,
}

# ── Thresholds ──
GPS_ZONE_DISTANCE_THRESHOLD_M = 750.0  # Must be within 750m of event cell
PRE_ACTIVITY_MIN_MINUTES = 45           # Must be online ≥45 min
PRE_ACTIVITY_WINDOW_HOURS = 2           # In the 2 hours before event
ACCELEROMETER_MIN_VARIANCE = 0.15       # Non-stationary threshold
MAX_PARTNER_ACCOUNTS_PER_DEVICE = 3     # Device fingerprint limit


async def evaluate_fraud(
    partner_id: UUID,
    h3_cell: str,
    gps_lat: float,
    gps_lng: float,
    accelerometer_variance: float,
    event_id: UUID,
    db: AsyncSession,
) -> dict:
    """
    Run all 4 fraud checks and return a composite fraud score.
    Returns: { fraud_score, checks_failed, checks_detail, recommendation }
    """
    fraud_score = Decimal("0.000")
    checks_failed = []
    checks_detail = []

    # ── CHECK 1: GPS Zone Match (weight: 0.35) ──
    distance_m = gps_distance_to_h3_center_m(gps_lat, gps_lng, h3_cell)
    gps_passed = distance_m <= GPS_ZONE_DISTANCE_THRESHOLD_M
    checks_detail.append({
        "check_name": "gps_zone_match",
        "weight": CHECK_WEIGHTS["gps_zone_match"],
        "passed": gps_passed,
        "detail": f"Distance to cell center: {distance_m:.0f}m (threshold: {GPS_ZONE_DISTANCE_THRESHOLD_M}m)",
    })
    if not gps_passed:
        fraud_score += Decimal(str(CHECK_WEIGHTS["gps_zone_match"]))
        checks_failed.append("gps_zone_match")

    # ── CHECK 2: Pre-Activity Window (weight: 0.30) ──
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=PRE_ACTIVITY_WINDOW_HOURS)

    result = await db.execute(
        select(PartnerActivityLog)
        .where(
            and_(
                PartnerActivityLog.partner_id == partner_id,
                PartnerActivityLog.logged_at >= window_start,
                PartnerActivityLog.logged_at <= now,
                PartnerActivityLog.is_online == True,
            )
        )
    )
    online_logs = result.scalars().all()

    # Each log represents ~5 min of online time
    online_minutes = len(online_logs) * 5
    activity_passed = online_minutes >= PRE_ACTIVITY_MIN_MINUTES
    checks_detail.append({
        "check_name": "pre_activity_window",
        "weight": CHECK_WEIGHTS["pre_activity_window"],
        "passed": activity_passed,
        "detail": f"Online for {online_minutes} min in last {PRE_ACTIVITY_WINDOW_HOURS}h (required: {PRE_ACTIVITY_MIN_MINUTES} min)",
    })
    if not activity_passed:
        fraud_score += Decimal(str(CHECK_WEIGHTS["pre_activity_window"]))
        checks_failed.append("pre_activity_window")

    # ── CHECK 3: Accelerometer Motion (weight: 0.20) ──
    accel_passed = accelerometer_variance > ACCELEROMETER_MIN_VARIANCE
    checks_detail.append({
        "check_name": "accelerometer_motion",
        "weight": CHECK_WEIGHTS["accelerometer_motion"],
        "passed": accel_passed,
        "detail": f"Variance: {accelerometer_variance} (threshold: {ACCELEROMETER_MIN_VARIANCE})",
    })
    if not accel_passed:
        fraud_score += Decimal(str(CHECK_WEIGHTS["accelerometer_motion"]))
        checks_failed.append("accelerometer_motion")

    # ── CHECK 4: Device Fingerprint (weight: 0.15) ──
    # Check if device_id is linked to multiple partner accounts
    partner_result = await db.execute(
        select(Partner).where(Partner.id == partner_id)
    )
    partner = partner_result.scalar_one_or_none()

    device_count = 0
    if partner:
        device_result = await db.execute(
            select(func.count(Partner.id))
            .where(Partner.device_id == partner.device_id)
        )
        device_count = device_result.scalar() or 0

    fingerprint_passed = device_count <= MAX_PARTNER_ACCOUNTS_PER_DEVICE
    checks_detail.append({
        "check_name": "device_fingerprint",
        "weight": CHECK_WEIGHTS["device_fingerprint"],
        "passed": fingerprint_passed,
        "detail": f"Device linked to {device_count} accounts (max: {MAX_PARTNER_ACCOUNTS_PER_DEVICE})",
    })
    if not fingerprint_passed:
        fraud_score += Decimal(str(CHECK_WEIGHTS["device_fingerprint"]))
        checks_failed.append("device_fingerprint")

    # ── Recommendation ──
    fraud_score = round(fraud_score, 3)
    if fraud_score >= Decimal("0.7"):
        recommendation = "block"
    elif fraud_score >= Decimal("0.5"):
        recommendation = "flag"
    else:
        recommendation = "approve"

    # ── Auto-insert fraud flag if score >= 0.5 ──
    if fraud_score >= Decimal("0.5"):
        # Determine severity based on fraud score
        if fraud_score >= Decimal("0.7"):
            severity = FraudSeverityEnum.critical
        elif fraud_score >= Decimal("0.5"):
            severity = FraudSeverityEnum.warning
        else:
            severity = FraudSeverityEnum.info

        # Map first failed check to flag type
        flag_type_map = {
            "gps_zone_match": FraudFlagTypeEnum.wrong_zone,
            "pre_activity_window": FraudFlagTypeEnum.no_pre_activity,
            "accelerometer_motion": FraudFlagTypeEnum.stationary_device,
            "device_fingerprint": FraudFlagTypeEnum.multi_account,
        }
        primary_flag_type = flag_type_map.get(
            checks_failed[0] if checks_failed else "gps_zone_match",
            FraudFlagTypeEnum.wrong_zone,
        )

        fraud_flag = FraudFlag(
            partner_id=partner_id,
            flag_type=primary_flag_type,
            severity=severity,
            gps_lat=Decimal(str(gps_lat)),
            gps_lng=Decimal(str(gps_lng)),
            accelerometer_variance=Decimal(str(accelerometer_variance)),
            rule_triggered=", ".join(checks_failed),
            status=FraudFlagStatusEnum.pending,
            flagged_at=datetime.now(timezone.utc),
        )
        db.add(fraud_flag)
        await db.flush()
        logger.warning(
            f"Fraud flag created for partner {partner_id}: score={fraud_score}, "
            f"checks_failed={checks_failed}"
        )

    return {
        "fraud_score": str(fraud_score),
        "checks_failed": checks_failed,
        "checks_detail": checks_detail,
        "recommendation": recommendation,
    }
