"""
GridGuard AI — Traffic Polling Task
Polls Google Maps Traffic API for key corridors.
"""

import logging
from datetime import datetime, timezone

import httpx

from app.tasks.celery_app import celery_app
from app.config import get_settings
from app.utils.h3_helpers import gps_to_h3

logger = logging.getLogger(__name__)
settings = get_settings()

# Key delivery corridors to monitor (lat, lng, city, name)
MONITORED_CORRIDORS = [
    (19.0760, 72.8777, "mumbai", "Mumbai Central"),
    (19.0176, 72.8561, "mumbai", "Bandra-Kurla"),
    (28.6139, 77.2090, "delhi", "Connaught Place"),
    (28.5355, 77.2090, "delhi", "South Delhi"),
    (12.9716, 77.5946, "bangalore", "MG Road"),
    (12.9352, 77.6245, "bangalore", "Koramangala"),
    (17.3850, 78.4867, "hyderabad", "Hyderabad Central"),
    (13.0827, 80.2707, "chennai", "Chennai Central"),
    (18.5204, 73.8567, "pune", "Pune Central"),
    (22.5726, 88.3639, "kolkata", "Kolkata Central"),
]

CONGESTION_THRESHOLD = 1.5  # Duration ratio > 1.5x normal → congestion event


@celery_app.task(name="app.tasks.traffic.poll_traffic_events", bind=True, max_retries=3)
def poll_traffic_events(self):
    """
    Poll Google Maps Traffic API for key corridors.
    Runs every 15 minutes.
    """
    import asyncio
    asyncio.run(_poll_traffic_async())


async def _poll_traffic_async():
    """Async implementation of traffic polling."""
    if not settings.google_maps_api_key:
        logger.warning("Google Maps API key not configured; skipping traffic poll")
        return

    internal_api_url = "http://localhost:8000/api/v1/grid/events/ingest"
    headers = {"X-API-Key": settings.internal_api_key}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for lat, lng, city, name in MONITORED_CORRIDORS:
            try:
                # Use Google Maps Distance Matrix API to check congestion
                response = await client.get(
                    "https://maps.googleapis.com/maps/api/distancematrix/json",
                    params={
                        "origins": f"{lat},{lng}",
                        "destinations": f"{lat + 0.01},{lng + 0.01}",
                        "departure_time": "now",
                        "traffic_model": "best_guess",
                        "key": settings.google_maps_api_key,
                    },
                )

                if response.status_code != 200:
                    logger.error(f"Google Maps API error for {name}: {response.status_code}")
                    continue

                data = response.json()
                rows = data.get("rows", [{}])
                elements = rows[0].get("elements", [{}]) if rows else [{}]

                if not elements or elements[0].get("status") != "OK":
                    continue

                duration = elements[0].get("duration", {}).get("value", 0)
                duration_in_traffic = elements[0].get("duration_in_traffic", {}).get("value", 0)

                if duration > 0:
                    congestion_ratio = duration_in_traffic / duration
                else:
                    congestion_ratio = 0

                if congestion_ratio >= CONGESTION_THRESHOLD:
                    severity = min(1.0, (congestion_ratio - 1.0) / 2.0)
                    h3_cell = gps_to_h3(lat, lng)

                    await client.post(
                        internal_api_url,
                        headers=headers,
                        json={
                            "source": "google_maps",
                            "h3_cell": h3_cell,
                            "event_type": "road_saturation",
                            "raw_value": round(congestion_ratio, 2),
                            "severity": round(severity, 3),
                            "event_time": datetime.now(timezone.utc).isoformat(),
                            "city": city,
                        },
                    )

                    logger.info(
                        f"Road saturation event: {name} ({city}), "
                        f"congestion={congestion_ratio:.1f}x"
                    )

            except Exception as e:
                logger.error(f"Traffic polling failed for {name}: {e}")
