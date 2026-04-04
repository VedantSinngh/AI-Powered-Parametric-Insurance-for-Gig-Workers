"""
GridGuard AI — Weekly Policy Generator Task
Runs Sunday 22:00 IST (16:30 UTC) — generates policies for next week
"""

import asyncio
from datetime import datetime, timedelta

from app.tasks.celery_app import app


@app.task(name="app.tasks.policy_generator.generate_weekly_policies")
def generate_weekly_policies():
    """Generate weekly policies for all active partners."""
    asyncio.run(_generate_policies())


async def _generate_policies():
    from pymongo import AsyncMongoClient
    from beanie import init_beanie
    from app.config import settings
    from app.models.partner import Partner
    from app.models.policy import Policy
    from app.models.premium_prediction import PremiumPrediction
    from app.services.risk_engine import risk_engine
    from app.database import DOCUMENT_MODELS

    # Init DB connection for Celery worker
    client = AsyncMongoClient(settings.MONGODB_URL)
    await init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=DOCUMENT_MODELS,
    )

    # Calculate next week dates
    now = datetime.utcnow()
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = now + timedelta(days=days_until_monday)
    next_sunday = next_monday + timedelta(days=6)

    week_start = next_monday.strftime("%Y-%m-%d")
    week_end = next_sunday.strftime("%Y-%m-%d")

    # Batch process partners
    batch_size = 100
    skip = 0
    total_generated = 0

    while True:
        partners = (
            await Partner.find(Partner.is_active == True)  # noqa: E712
            .skip(skip)
            .limit(batch_size)
            .to_list()
        )

        if not partners:
            break

        for partner in partners:
            try:
                # Extract features
                h3_cell = partner.primary_zone_h3 or ""
                features = await risk_engine.extract_features(partner.id, h3_cell)

                # Predict risk
                risk_score = risk_engine.predict_risk_score(features)
                premium_tier, premium_amount = risk_engine.score_to_premium(risk_score)

                # Update partner risk tier
                partner.risk_tier = risk_engine.score_to_risk_tier(risk_score)
                partner.updated_at = datetime.utcnow()
                await partner.save()

                # Store prediction
                prediction = PremiumPrediction(
                    partner_id=partner.id,
                    h3_cell=h3_cell,
                    predicted_for_week=week_start,
                    risk_score=risk_score,
                    premium_tier=premium_tier,
                    premium_amount=premium_amount,
                    model_version=settings.MODEL_VERSION,
                    feature_vector=features,
                )
                await prediction.insert()

                # Create policy
                policy = Policy(
                    partner_id=partner.id,
                    week_start=week_start,
                    week_end=week_end,
                    premium_amount=premium_amount,
                    risk_score=risk_score,
                    status="active",
                )
                await policy.insert()

                total_generated += 1

            except Exception as e:
                print(f"⚠️  Policy generation failed for {partner.id}: {e}")

        skip += batch_size

    print(f"✅ Generated {total_generated} weekly policies")
    client.close()
