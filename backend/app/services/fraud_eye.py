"""
GridGuard AI — FraudEye Engine
4-check weighted fraud scoring system
"""

from datetime import datetime, timedelta

import h3

from app.models.fraud_flag import FraudFlag
from app.models.partner import Partner
from app.core.websocket_manager import manager


class FraudEye:
    """4-check weighted fraud detection engine."""

    async def evaluate(
        self,
        partner_id: str,
        h3_cell: str,
        gps_lat: float,
        gps_lng: float,
        accelerometer_variance: float,
        event_id: str,
        event_time: datetime,
    ) -> dict:
        """
        Evaluate fraud risk with 4 weighted checks:
        1. GPS Zone Match (0.35)
        2. Pre-Activity Window (0.30)
        3. Accelerometer Motion (0.20)
        4. Device Fingerprint (0.15)
        """
        fraud_score = 0.0
        checks_failed = []
        details = {}

        # CHECK 1 — GPS Zone Match (weight 0.35)
        if gps_lat != 0.0 and gps_lng != 0.0:
            try:
                partner_h3 = h3.latlng_to_cell(gps_lat, gps_lng, 9)
                distance = h3.grid_distance(partner_h3, h3_cell)
                details["gps_distance"] = distance
                if distance > 1:
                    fraud_score += 0.35
                    checks_failed.append("wrong_zone")
            except Exception:
                details["gps_check"] = "skipped_incomparable_cells"

        # CHECK 2 — Pre-Activity Window (weight 0.30)
        try:
            from app.database import get_database

            db = get_database()
            window_start = event_time - timedelta(hours=2)

            pipeline = [
                {
                    "$match": {
                        "partner_id": partner_id,
                        "logged_at": {"$gte": window_start, "$lte": event_time},
                        "is_online": True,
                    }
                },
                {"$count": "online_logs"},
            ]
            cursor = await db["partner_activity_logs"].aggregate(pipeline)
            result = await cursor.to_list(length=1)

            online_logs = result[0]["online_logs"] if result else 0
            online_minutes = online_logs * 5  # 5-min intervals
            details["pre_activity_minutes"] = online_minutes

            if online_minutes < 45:
                fraud_score += 0.30
                checks_failed.append("no_pre_activity")
        except Exception as e:
            details["pre_activity_check"] = f"error: {str(e)}"

        # CHECK 3 — Accelerometer Motion (weight 0.20)
        details["accelerometer_variance"] = accelerometer_variance
        if accelerometer_variance <= 0.15:
            fraud_score += 0.20
            checks_failed.append("stationary_device")

        # CHECK 4 — Device Fingerprint (weight 0.15)
        try:
            partner = await Partner.get(partner_id)
            if partner:
                same_device_count = await Partner.find(
                    Partner.device_id == partner.device_id
                ).count()
                details["same_device_count"] = same_device_count
                if same_device_count > 1:
                    fraud_score += 0.15
                    checks_failed.append("multi_account")
        except Exception as e:
            details["device_check"] = f"error: {str(e)}"

        # Round fraud score
        fraud_score = round(fraud_score, 2)

        # Determine recommendation
        if fraud_score < 0.30:
            recommendation = "approve"
        elif fraud_score < 0.70:
            recommendation = "flag"
        else:
            recommendation = "block"

        # Insert fraud flag if score >= 0.30
        if fraud_score >= 0.30:
            severity = "critical" if fraud_score >= 0.70 else "warning"
            flag_type = checks_failed[0] if checks_failed else "velocity_abuse"

            flag = FraudFlag(
                partner_id=partner_id,
                payout_id=event_id,
                flag_type=flag_type,
                severity=severity,
                gps_lat=gps_lat if gps_lat != 0.0 else None,
                gps_lng=gps_lng if gps_lng != 0.0 else None,
                accelerometer_variance=accelerometer_variance,
                rule_triggered=", ".join(checks_failed),
                fraud_score=fraud_score,
                checks_failed=checks_failed,
                status="pending",
            )
            await flag.insert()

            # Publish critical to admin
            if fraud_score >= 0.70:
                try:
                    await manager.publish_to_redis("ws:admin:feed", {
                        "type": "fraud_flag_raised",
                        "flag_id": flag.id,
                        "partner_id": partner_id,
                        "fraud_score": fraud_score,
                        "checks_failed": checks_failed,
                        "severity": "critical",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                except Exception:
                    pass

        return {
            "fraud_score": fraud_score,
            "checks_failed": checks_failed,
            "recommendation": recommendation,
            "details": details,
        }


fraud_eye = FraudEye()
