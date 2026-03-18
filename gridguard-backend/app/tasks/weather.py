"""
GridGuard AI — Weather Polling Task
Polls OpenWeather API for monitored cities and ingests events.
"""

import logging
from datetime import datetime, timezone

import httpx

from app.tasks.celery_app import celery_app
from app.config import get_settings
from app.utils.h3_helpers import get_city_cells, h3_to_center

logger = logging.getLogger(__name__)
settings = get_settings()

MONITORED_CITIES = [
    "mumbai", "delhi", "bangalore", "hyderabad", "chennai",
    "pune", "kolkata", "ahmedabad", "jaipur", "lucknow",
]

# Weather thresholds for event generation
RAINFALL_THRESHOLD_MM = 7.5      # mm/hr → triggers rainfall event
HEAT_THRESHOLD_C = 42.0          # °C → triggers heat event


@celery_app.task(name="app.tasks.weather.poll_weather_events", bind=True, max_retries=3)
def poll_weather_events(self):
    """
    Poll OpenWeather API for all monitored cities.
    Runs every 15 minutes.
    """
    import asyncio
    asyncio.run(_poll_weather_async())


async def _poll_weather_async():
    """Async implementation of weather polling."""
    if not settings.openweather_api_key:
        logger.warning("OpenWeather API key not configured; skipping poll")
        return

    internal_api_url = "http://localhost:8000/api/v1/grid/events/ingest"
    headers = {"X-API-Key": settings.internal_api_key}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for city in MONITORED_CITIES:
            try:
                cells = get_city_cells(city)
                if not cells:
                    continue

                # Get weather for city center
                center_cell = cells[len(cells) // 2]
                lat, lng = h3_to_center(center_cell)

                response = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "lat": lat,
                        "lon": lng,
                        "appid": settings.openweather_api_key,
                        "units": "metric",
                    },
                )

                if response.status_code != 200:
                    logger.error(f"OpenWeather API error for {city}: {response.status_code}")
                    continue

                data = response.json()
                main = data.get("main", {})
                rain = data.get("rain", {})
                temp = main.get("temp", 0)
                rainfall_mm = rain.get("1h", 0)

                # Check rainfall threshold
                if rainfall_mm >= RAINFALL_THRESHOLD_MM:
                    severity = min(1.0, rainfall_mm / 50.0)  # Normalize to 0–1
                    for cell in cells:
                        await client.post(
                            internal_api_url,
                            headers=headers,
                            json={
                                "source": "openweather",
                                "h3_cell": cell,
                                "event_type": "rainfall",
                                "raw_value": rainfall_mm,
                                "severity": round(severity, 3),
                                "event_time": datetime.now(timezone.utc).isoformat(),
                                "city": city,
                            },
                        )
                    logger.info(f"Rainfall event ingested for {city}: {rainfall_mm}mm/hr")

                # Check heat threshold
                if temp >= HEAT_THRESHOLD_C:
                    severity = min(1.0, (temp - HEAT_THRESHOLD_C) / 10.0 + 0.3)
                    for cell in cells:
                        await client.post(
                            internal_api_url,
                            headers=headers,
                            json={
                                "source": "openweather",
                                "h3_cell": cell,
                                "event_type": "heat",
                                "raw_value": temp,
                                "severity": round(severity, 3),
                                "event_time": datetime.now(timezone.utc).isoformat(),
                                "city": city,
                            },
                        )
                    logger.info(f"Heat event ingested for {city}: {temp}°C")

            except Exception as e:
                logger.error(f"Weather polling failed for {city}: {e}")
