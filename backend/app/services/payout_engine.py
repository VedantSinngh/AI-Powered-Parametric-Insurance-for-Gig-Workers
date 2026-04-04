"""
GridGuard AI — Payout Engine Service
Full payout flow with SLA tracking (< 90 seconds)
"""

from datetime import datetime

from app.config import settings
from app.models.payout import Payout
from app.models.policy import Policy
from app.models.grid_event import GridEvent
from app.models.partner import Partner
from app.utils.mock_wallet import mock_wallet
from app.services.notification import notification_service
from app.core.websocket_manager import manager
from app.services.workability import workability_service
from app.services.razorpay_payouts import (
    razorpay_payout_service,
    RazorpayPayoutError,
)


class PayoutEngine:
    """Handles the full payout lifecycle with SLA tracking."""

    async def trigger_payout(
        self,
        partner_id: str,
        grid_event_id: str,
        duration_hours: float = 1.0,
    ) -> dict:
        """
        Full payout flow — SLA target < 90 seconds.
        Steps: policy check → duplicate check → fraud check →
               amount calc → wallet credit → WS + FCM + email.
        """
        start_time = datetime.utcnow()

        # 1. Find active policy
        today = datetime.utcnow().strftime("%Y-%m-%d")
        policy = await Policy.find_one(
            Policy.partner_id == partner_id,
            Policy.status == "active",
            Policy.week_start <= today,
            Policy.week_end >= today,
        )
        if policy is None:
            return {"status": "skipped", "reason": "no_active_policy"}

        # 2. Check duplicate payout
        existing = await Payout.find_one(
            Payout.partner_id == partner_id,
            Payout.grid_event_id == grid_event_id,
        )
        if existing:
            return {"status": "skipped", "reason": "duplicate_payout"}

        # 3. Fraud check
        partner = await Partner.get(partner_id)
        if partner is None:
            return {"status": "skipped", "reason": "partner_not_found"}

        grid_event = await GridEvent.get(grid_event_id)
        if grid_event is None:
            return {"status": "skipped", "reason": "event_not_found"}

        requested_provider = settings.PAYOUT_PROVIDER.lower().strip()
        if requested_provider not in {"mock", "razorpay"}:
            requested_provider = "mock"

        # Run fraud evaluation (lazy import to avoid circular)
        try:
            from app.services.fraud_eye import fraud_eye

            fraud_result = await fraud_eye.evaluate(
                partner_id=partner_id,
                h3_cell=grid_event.h3_cell,
                gps_lat=0.0,  # Will use partner's zone for background checks
                gps_lng=0.0,
                accelerometer_variance=1.0,  # Default for background trigger
                event_id=grid_event_id,
                event_time=grid_event.event_time,
            )

            if fraud_result["fraud_score"] >= 0.70:
                # Blocked by fraud
                await manager.publish_to_redis("ws:admin:feed", {
                    "type": "fraud_flag_raised",
                    "partner_id": partner_id,
                    "fraud_score": fraud_result["fraud_score"],
                    "checks_failed": fraud_result["checks_failed"],
                    "severity": "critical",
                    "timestamp": datetime.utcnow().isoformat(),
                })
                return {
                    "status": "blocked",
                    "reason": "fraud",
                    "fraud_score": fraud_result["fraud_score"],
                }
        except Exception as e:
            print(f"⚠️  Fraud check failed, proceeding: {e}")

        # 4. Calculate amount
        rate = workability_service.get_payout_rate(grid_event.event_type)
        amount = duration_hours * rate

        # 5. Create payout (processing)
        payout = Payout(
            partner_id=partner_id,
            policy_id=policy.id,
            grid_event_id=grid_event_id,
            amount=amount,
            duration_hours=duration_hours,
            rate_per_hour=rate,
            provider=requested_provider,
            status="processing",
        )
        await payout.insert()

        description = f"GridGuard payout: {grid_event.event_type} Zone {grid_event.h3_cell}"

        # 6. Disburse via selected provider
        try:
            if requested_provider == "razorpay":
                try:
                    razorpay_result = await razorpay_payout_service.create_payout(
                        partner=partner,
                        amount_inr=amount,
                        description=description,
                    )
                    payout.provider = "razorpay"
                    payout.provider_payout_id = razorpay_result.payout_id
                    payout.provider_status = razorpay_result.status
                    payout.provider_reference = razorpay_result.reference
                    payout.mock_reference = razorpay_result.reference

                    mapped_status = razorpay_payout_service.to_internal_status(
                        razorpay_result.status
                    )
                    payout.status = mapped_status
                    if mapped_status == "paid":
                        payout.paid_at = datetime.utcnow()
                    elif mapped_status == "failed":
                        payout.failure_reason = (
                            f"Razorpay payout failed (status={razorpay_result.status})"
                        )
                except RazorpayPayoutError as e:
                    if settings.RAZORPAY_FALLBACK_TO_MOCK:
                        requested_provider = "mock"
                    else:
                        payout.provider = "razorpay"
                        payout.provider_status = "failed"
                        payout.status = "failed"
                        payout.failure_reason = str(e)
                        await payout.save()
                        return {"status": "failed", "reason": str(e)}

            if requested_provider == "mock":
                wallet_result = await mock_wallet.credit(
                    partner_id,
                    amount,
                    description,
                )
                payout.provider = "mock"
                payout.provider_status = "processed"
                payout.provider_reference = wallet_result.reference
                payout.status = "paid"
                payout.paid_at = datetime.utcnow()
                payout.mock_reference = wallet_result.reference

            await payout.save()
        except Exception as e:
            payout.status = "failed"
            payout.failure_reason = str(e)
            await payout.save()
            return {"status": "failed", "reason": str(e)}

        if payout.status == "failed":
            return {
                "status": "failed",
                "reason": payout.failure_reason or "payout_failed",
            }

        reference = payout.provider_reference or payout.mock_reference

        # 7. WebSocket notification
        try:
            partner_event_type = (
                "payout_credited" if payout.status == "paid" else "payout_processing"
            )
            partner_sound = "success" if payout.status == "paid" else "info"
            await manager.publish_to_redis(f"ws:partner:{partner_id}", {
                "type": partner_event_type,
                "amount": amount,
                "zone": grid_event.h3_cell,
                "event_type": grid_event.event_type,
                "reference": reference,
                "provider": payout.provider,
                "provider_status": payout.provider_status,
                "sound": partner_sound,
                "timestamp": datetime.utcnow().isoformat(),
            })

            admin_event_type = (
                "payout_completed" if payout.status == "paid" else "payout_initiated"
            )
            await manager.publish_to_redis("ws:admin:feed", {
                "type": admin_event_type,
                "payout_id": payout.id,
                "partner_id": partner_id,
                "amount": amount,
                "event_type": grid_event.event_type,
                "provider": payout.provider,
                "provider_status": payout.provider_status,
                "timestamp": datetime.utcnow().isoformat(),
            })
            payout.ws_notified = True
            await payout.save()
        except Exception:
            pass

        if payout.status == "paid":
            # 8. FCM push
            try:
                await notification_service.send_fcm_push(
                    partner.device_id,
                    "💰 Payout Credited!",
                    f"₹{amount:.0f} credited! Zone {grid_event.h3_cell[:8]} disruption.",
                    {"payout_id": payout.id, "amount": str(amount)},
                )
            except Exception:
                pass

            # 9. Email backup
            try:
                await notification_service.send_payout_notification(
                    partner.email,
                    partner.full_name,
                    amount,
                    grid_event.event_type,
                    grid_event.h3_cell,
                    reference,
                )
            except Exception:
                pass

        # SLA check
        total_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        if total_ms > 90000:
            try:
                import sentry_sdk
                sentry_sdk.capture_message(
                    f"SLA breach: payout took {total_ms:.0f}ms (partner={partner_id})"
                )
            except Exception:
                pass
            print(f"⚠️  SLA BREACH: payout took {total_ms:.0f}ms")

        return {
            "status": payout.status,
            "payout_id": payout.id,
            "amount": amount,
            "reference": reference,
            "provider": payout.provider,
            "provider_status": payout.provider_status,
            "processing_ms": round(total_ms, 2),
        }


payout_engine = PayoutEngine()
