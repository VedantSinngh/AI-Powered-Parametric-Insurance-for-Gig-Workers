"""
GridGuard AI — Premium Deduction Task
Runs Monday 06:00 IST (00:30 UTC) — deducts premiums from wallets
"""

import asyncio
import json
from datetime import datetime

from app.tasks.celery_app import app


@app.task(name="app.tasks.premium_deductor.deduct_weekly_premiums")
def deduct_weekly_premiums():
    """Deduct weekly premiums for all active policies."""
    asyncio.run(_deduct_premiums())


async def _deduct_premiums():
    from pymongo import AsyncMongoClient
    from beanie import init_beanie
    from app.config import settings
    from app.models.policy import Policy
    from app.models.partner import Partner
    from app.utils.mock_wallet import mock_wallet, InsufficientFundsError
    from app.services.notification import notification_service
    from app.database import DOCUMENT_MODELS

    import redis.asyncio as aioredis

    client = AsyncMongoClient(settings.MONGODB_URL)
    await init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=DOCUMENT_MODELS,
    )

    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Find all policies for this week not yet deducted
    policies = await Policy.find(
        Policy.status == "active",
        Policy.week_start <= today,
        Policy.week_end >= today,
        Policy.deducted_at == None,  # noqa: E711
    ).to_list()

    deducted = 0
    suspended = 0

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    for policy in policies:
        partner = await Partner.get(policy.partner_id)
        if not partner or not partner.is_active:
            continue

        try:
            result = await mock_wallet.debit(
                policy.partner_id,
                policy.premium_amount,
                f"GridGuard weekly premium — Week {policy.week_start}",
            )

            policy.deducted_at = datetime.utcnow()
            policy.updated_at = datetime.utcnow()
            await policy.save()
            deducted += 1

            # WS notification
            try:
                await r.publish(
                    f"ws:partner:{policy.partner_id}",
                    json.dumps({
                        "type": "premium_deducted",
                        "amount": policy.premium_amount,
                        "week": policy.week_start,
                        "sound": "info",
                        "timestamp": datetime.utcnow().isoformat(),
                    }),
                )
            except Exception:
                pass

            # Email
            try:
                await notification_service.send_premium_notification(
                    partner.email,
                    partner.full_name,
                    policy.premium_amount,
                    policy.week_start,
                )
            except Exception:
                pass

        except InsufficientFundsError:
            policy.status = "suspended"
            policy.updated_at = datetime.utcnow()
            await policy.save()
            suspended += 1

            try:
                await r.publish(
                    f"ws:partner:{policy.partner_id}",
                    json.dumps({
                        "type": "policy_suspended",
                        "reason": "insufficient_funds",
                        "sound": "alert",
                        "timestamp": datetime.utcnow().isoformat(),
                    }),
                )
            except Exception:
                pass

    await r.aclose()
    print(f"✅ Premium deduction: {deducted} deducted, {suspended} suspended")
    client.close()
