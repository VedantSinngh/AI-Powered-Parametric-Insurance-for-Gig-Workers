"""
GridGuard AI — Policy Tasks
Weekly policy generation and premium deduction.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.celery_app import celery_app
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="app.tasks.policy_tasks.generate_weekly_policies", bind=True, max_retries=2)
def generate_weekly_policies(self):
    """
    Generate weekly policies for all active partners.
    Runs every Sunday 22:00 IST.
    1. For each active partner: call TFT model → get risk_score
    2. Map score to premium tier
    3. Insert into premium_predictions
    4. Create policy records for upcoming Monday–Sunday
    5. Send push notification
    """
    import asyncio
    asyncio.run(_generate_policies_async())


async def _generate_policies_async():
    """Async implementation of weekly policy generation."""
    from app.database import async_session_factory
    from app.models.partner import Partner
    from app.models.policy import Policy, PolicyStatusEnum
    from app.models.premium_prediction import PremiumPrediction
    from app.services.risk_engine import get_risk_score, score_to_premium_tier
    from app.services.notification import send_premium_notification

    async with async_session_factory() as db:
        try:
            # Calculate next week's dates (Monday to Sunday)
            today = date.today()
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7  # Next Monday
            next_monday = today + timedelta(days=days_until_monday)
            next_sunday = next_monday + timedelta(days=6)

            # Fetch all active partners
            result = await db.execute(
                select(Partner).where(Partner.is_active == True)
            )
            partners = result.scalars().all()

            policies_created = 0
            notifications_sent = 0

            for partner in partners:
                try:
                    # Get risk score from ML model
                    risk_score = await get_risk_score(
                        partner_id=str(partner.id),
                        h3_cell=partner.primary_zone_h3 or "",
                    )

                    # Map to premium tier
                    tier, amount = score_to_premium_tier(risk_score)

                    # Create premium prediction record
                    prediction = PremiumPrediction(
                        partner_id=partner.id,
                        h3_cell=partner.primary_zone_h3,
                        predicted_for_week=next_monday,
                        risk_score=Decimal(str(round(risk_score, 3))),
                        premium_tier=tier,
                        premium_amount=amount,
                        model_version="tft-v1.0",
                        generated_at=datetime.now(timezone.utc),
                    )
                    db.add(prediction)

                    # Create policy record
                    policy = Policy(
                        partner_id=partner.id,
                        week_start=next_monday,
                        week_end=next_sunday,
                        premium_amount=amount,
                        risk_score=Decimal(str(round(risk_score, 3))),
                        status=PolicyStatusEnum.active,
                    )
                    db.add(policy)
                    policies_created += 1

                    # Send notification
                    week_label = f"{next_monday.strftime('%d %b')} – {next_sunday.strftime('%d %b')}"
                    await send_premium_notification(
                        partner_id=str(partner.id),
                        phone_number=partner.phone_number,
                        premium_amount=float(amount),
                        week_label=week_label,
                    )
                    notifications_sent += 1

                except Exception as e:
                    logger.error(f"Failed to generate policy for partner {partner.id}: {e}")

            await db.commit()
            logger.info(
                f"Weekly policies generated: {policies_created} policies, "
                f"{notifications_sent} notifications sent"
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"Weekly policy generation failed: {e}")
            raise


@celery_app.task(name="app.tasks.policy_tasks.deduct_weekly_premiums", bind=True, max_retries=2)
def deduct_weekly_premiums(self):
    """
    Deduct premiums for all active policies.
    Runs every Monday 06:00 IST.
    """
    import asyncio
    asyncio.run(_deduct_premiums_async())


async def _deduct_premiums_async():
    """Async implementation of premium deduction."""
    from app.database import async_session_factory
    from app.models.partner import Partner
    from app.models.policy import Policy, PolicyStatusEnum
    from app.utils.razorpay_client import create_wallet_debit
    from app.services.notification import send_sms

    async with async_session_factory() as db:
        try:
            today = date.today()

            # Fetch active policies for current week
            result = await db.execute(
                select(Policy, Partner)
                .join(Partner, Policy.partner_id == Partner.id)
                .where(
                    Policy.status == PolicyStatusEnum.active,
                    Policy.week_start <= today,
                    Policy.week_end >= today,
                    Policy.deducted_at.is_(None),
                )
            )
            rows = result.all()

            deducted = 0
            for policy, partner in rows:
                try:
                    if not partner.upi_handle:
                        logger.warning(f"No UPI handle for partner {partner.id}, skipping deduction")
                        continue

                    # Debit via Razorpay
                    debit_result = await create_wallet_debit(
                        upi_handle=partner.upi_handle,
                        amount_inr=float(policy.premium_amount or 0),
                        narration=f"GridGuard Premium Week {policy.week_start}",
                    )

                    if debit_result.success:
                        policy.deducted_at = datetime.now(timezone.utc)
                        deducted += 1

                        # Send SMS confirmation
                        if partner.phone_number:
                            await send_sms(
                                to=partner.phone_number,
                                message=(
                                    f"GridGuard: ₹{policy.premium_amount} premium deducted. "
                                    f"You're covered for {policy.week_start} to {policy.week_end}. "
                                    f"Ref: {debit_result.upi_reference}"
                                ),
                            )
                    else:
                        logger.error(
                            f"Premium deduction failed for partner {partner.id}: "
                            f"{debit_result.failure_reason}"
                        )

                except Exception as e:
                    logger.error(f"Premium deduction error for partner {partner.id}: {e}")

            await db.commit()
            logger.info(f"Weekly premium deduction complete: {deducted}/{len(rows)} deducted")

        except Exception as e:
            await db.rollback()
            logger.error(f"Premium deduction batch failed: {e}")
            raise
