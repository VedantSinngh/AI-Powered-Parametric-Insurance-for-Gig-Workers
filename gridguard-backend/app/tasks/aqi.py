"""
GridGuard AI — AQI Polling Task
Polls CPCB (Central Pollution Control Board) AQI API.
"""

import logging
from datetime import datetime, timezone

import httpx

from app.tasks.celery_app import celery_app
from app.config import get_settings
from app.utils.h3_helpers import get_city_cells

logger = logging.getLogger(__name__)
settings = get_settings()

MONITORED_CITIES = [
    "mumbai", "delhi", "bangalore", "hyderabad", "chennai",
    "pune", "kolkata", "ahmedabad", "jaipur", "lucknow",
]

AQI_THRESHOLD = 200  # AQI > 200 → hazardous for outdoor work


@celery_app.task(name="app.tasks.aqi.poll_aqi_events", bind=True, max_retries=3)
def poll_aqi_events(self):
    """
    Poll CPCB AQI API for all monitored cities.
    Runs every 30 minutes.
    """
    import asyncio
    asyncio.run(_poll_aqi_async())


async def _poll_aqi_async():
    """Async implementation of AQI polling."""
    if not settings.cpcb_api_key:
        logger.warning("CPCB API key not configured; skipping AQI poll")
        return

    internal_api_url = "http://localhost:8000/api/v1/grid/events/ingest"
    headers = {"X-API-Key": settings.internal_api_key}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for city in MONITORED_CITIES:
            try:
                # CPCB API call (in production, use actual CPCB endpoint)
                response = await client.get(
                    f"https://api.data.gov.in/resource/cpcb-aqi",
                    params={
                        "api-key": settings.cpcb_api_key,
                        "format": "json",
                        "filters[city]": city,
                        "limit": 1,
                    },
                )

                if response.status_code != 200:
                    logger.error(f"CPCB API error for {city}: {response.status_code}")
                    continue

                data = response.json()
                records = data.get("records", [])
                if not records:
                    continue

                aqi_value = float(records[0].get("aqi", 0))

                if aqi_value >= AQI_THRESHOLD:
                    severity = min(1.0, (aqi_value - AQI_THRESHOLD) / 300.0 + 0.3)
                    cells = get_city_cells(city)

                    for cell in cells:
                        await client.post(
                            internal_api_url,
                            headers=headers,
                            json={
                                "source": "cpcb",
                                "h3_cell": cell,
                                "event_type": "aqi",
                                "raw_value": aqi_value,
                                "severity": round(severity, 3),
                                "event_time": datetime.now(timezone.utc).isoformat(),
                                "city": city,
                            },
                        )

                    logger.info(f"AQI event ingested for {city}: AQI={aqi_value}")

            except Exception as e:
                logger.error(f"AQI polling failed for {city}: {e}")
