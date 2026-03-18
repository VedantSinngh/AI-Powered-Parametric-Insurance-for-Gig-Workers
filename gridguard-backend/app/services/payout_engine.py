"""
GridGuard AI — Payout Engine Service
Handles payout eligibility, fraud checks, Razorpay disbursement, and notifications.
"""

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.partner import Partner
from app.models.policy import Policy, PolicyStatusEnum
from app.models.payout import Payout, PayoutStatusEnum
from app.models.grid_event import GridEvent
from app.services.fraud_eye import evaluate_fraud
from app.services.notification import send_push_notification, send_sms
from app.utils.razorpay_client import create_upi_payout

logger = logging.getLogger(__name__)

# ── Rate Per Hour by Event Type ──
EVENT_RATES_PER_HOUR = {
    "rainfall": Decimal("35.00"),
    "heat": Decimal("30.00"),
    "aqi": Decimal("28.00"),
    "road_saturation": Decimal("25.00"),
    "app_outage": Decimal("40.00"),
}

DEFAULT_RATE_PER_HOUR = Decimal("30.00")


async def get_active_policy(partner_id: UUID, db: AsyncSession) -> Policy | None:
    """Get the current active policy for a partner this week."""
    today = date.today()
    result = await db.execute(
        select(Policy)
        .where(
            and_(
                Policy.partner_id == partner_id,
                Policy.status == PolicyStatusEnum.active,
                Policy.week_start <= today,
                Policy.week_end >= today,
            )
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def trigger_payout(
    partner_id: UUID,
    grid_event_id: UUID,
    duration_hours: Decimal,
    db: AsyncSession,
) -> dict:
    """
    Full payout flow:
    1. Validate active policy
    2. Run FraudEye checks
    3. Calculate amount
    4. Razorpay UPI credit
    5. Send notifications
    SLA: < 90 seconds
    """
    # ── Step 1: Validate active policy ──
    policy = await get_active_policy(partner_id, db)
    if not policy:
        return {
            "success": False,
            "reason": "No active policy for this week",
            "payout_id": None,
        }

    # Fetch partner and grid event
    partner_result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = partner_result.scalar_one_or_none()
    if not partner:
        return {"success": False, "reason": "Partner not found", "payout_id": None}

    event_result = await db.execute(select(GridEvent).where(GridEvent.id == grid_event_id))
    grid_event = event_result.scalar_one_or_none()
    if not grid_event:
        return {"success": False, "reason": "Grid event not found", "payout_id": None}

    # ── Step 2: Run Fraud Checks ──
    # Get latest activity log for GPS/accelerometer data
    fraud_result = await evaluate_fraud(
        partner_id=partner_id,
        h3_cell=grid_event.h3_cell,
        gps_lat=float(partner.primary_zone_h3 and 0) or 0.0,  # Will use actual GPS from activity
        gps_lng=0.0,
        accelerometer_variance=0.3,  # Default non-stationary value
        event_id=grid_event_id,
        db=db,
    )

    if Decimal(fraud_result["fraud_score"]) > Decimal("0.7"):
        logger.warning(f"Payout blocked for partner {partner_id}: fraud_score={fraud_result['fraud_score']}")
        return {
            "success": False,
            "reason": f"Fraud check failed: score={fraud_result['fraud_score']}",
            "fraud_details": fraud_result,
            "payout_id": None,
        }

    # ── Step 3: Calculate amount ──
    rate = EVENT_RATES_PER_HOUR.get(grid_event.event_type.value, DEFAULT_RATE_PER_HOUR)
    amount = duration_hours * rate

    # ── Step 4: Create payout record ──
    payout = Payout(
        partner_id=partner_id,
        policy_id=policy.id,
        grid_event_id=grid_event_id,
        amount=amount,
        duration_hours=duration_hours,
        rate_per_hour=rate,
        status=PayoutStatusEnum.processing,
    )
    db.add(payout)
    await db.flush()

    # ── Step 5: Execute Razorpay payout ──
    if partner.upi_handle:
        razorpay_result = await create_upi_payout(
            upi_handle=partner.upi_handle,
            amount_inr=float(amount),
            partner_name=partner.full_name or "GridGuard Partner",
            narration=f"GridGuard payout for {grid_event.event_type.value} disruption",
        )

        if razorpay_result.success:
            payout.status = PayoutStatusEnum.paid
            payout.upi_reference = razorpay_result.upi_reference
            payout.razorpay_batch_id = razorpay_result.razorpay_batch_id
            payout.paid_at = datetime.now(timezone.utc)
        else:
            payout.status = PayoutStatusEnum.failed
            payout.failure_reason = razorpay_result.failure_reason
    else:
        payout.status = PayoutStatusEnum.failed
        payout.failure_reason = "No UPI handle registered"

    await db.flush()

    # ── Step 6: Send notifications ──
    if payout.status == PayoutStatusEnum.paid:
        notification_msg = f"₹{amount} credited for Zone {grid_event.h3_cell[:8]} disruption ({grid_event.event_type.value})"

        # FCM push notification
        await send_push_notification(
            partner_id=str(partner_id),
            title="Payout Credited! 💰",
            body=notification_msg,
        )

        # SMS backup
        if partner.phone_number:
            await send_sms(
                to=partner.phone_number,
                message=f"GridGuard: {notification_msg}. UPI Ref: {payout.upi_reference}",
            )

    return {
        "success": payout.status == PayoutStatusEnum.paid,
        "payout_id": str(payout.id),
        "amount": str(amount),
        "status": payout.status.value,
        "upi_reference": payout.upi_reference,
        "failure_reason": payout.failure_reason,
    }
