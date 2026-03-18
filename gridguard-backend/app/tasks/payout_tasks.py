"""
GridGuard AI — Payout Eligibility Task
Triggered by /grid/events/ingest when workability score drops below 0.4.
"""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, and_

from app.tasks.celery_app import celery_app
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="app.tasks.payout_tasks.check_payout_eligibility", bind=True, max_retries=3)
def check_payout_eligibility(self, h3_cell: str, event_id: str):
    """
    Find all eligible partners in the affected H3 cell and trigger payouts.
    Triggered by: /grid/events/ingest when workability score < 0.4.
    """
    import asyncio
    asyncio.run(_check_eligibility_async(h3_cell, event_id))


async def _check_eligibility_async(h3_cell: str, event_id: str):
    """Async implementation of payout eligibility check."""
    from app.database import async_session_factory
    from app.models.partner import Partner
    from app.services.payout_engine import trigger_payout
    from app.utils.h3_helpers import get_neighboring_cells

    async with async_session_factory() as db:
        try:
            # Get cells to check (affected cell + 1-ring neighbors)
            cells_to_check = get_neighboring_cells(h3_cell, ring_size=1)

            # Find active partners in affected cells
            result = await db.execute(
                select(Partner)
                .where(
                    and_(
                        Partner.is_active == True,
                        Partner.primary_zone_h3.in_(cells_to_check),
                    )
                )
            )
            eligible_partners = result.scalars().all()

            logger.info(
                f"Payout eligibility check for cell {h3_cell}: "
                f"{len(eligible_partners)} eligible partners found"
            )

            payouts_triggered = 0
            for partner in eligible_partners:
                try:
                    # Trigger payout with default 1-hour duration
                    # In production, duration would be calculated from event duration
                    result = await trigger_payout(
                        partner_id=partner.id,
                        grid_event_id=UUID(event_id),
                        duration_hours=Decimal("1.0"),
                        db=db,
                    )

                    if result.get("success"):
                        payouts_triggered += 1
                        logger.info(
                            f"Payout triggered for partner {partner.id}: "
                            f"₹{result.get('amount')}"
                        )
                    else:
                        logger.info(
                            f"Payout skipped for partner {partner.id}: "
                            f"{result.get('reason')}"
                        )

                except Exception as e:
                    logger.error(f"Payout trigger failed for partner {partner.id}: {e}")

            await db.commit()
            logger.info(
                f"Payout eligibility complete for cell {h3_cell}: "
                f"{payouts_triggered}/{len(eligible_partners)} payouts triggered"
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"Payout eligibility check failed for cell {h3_cell}: {e}")
            raise
