"""
GridGuard AI — Weather Poller Task
Polls Open-Meteo API every 15 minutes for all Indian cities
"""

import httpx
from app.tasks.celery_app import app

CITY_COORDS = {
    "bengaluru": (12.9716, 77.5946),
    "mumbai": (19.0760, 72.8777),
    "chennai": (13.0827, 80.2707),
    "delhi": (28.6139, 77.2090),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
    "kolkata": (22.5726, 88.3639),
}


@app.task(name="app.tasks.weather_poller.poll_weather_events")
def poll_weather_events():
    """Poll Open-Meteo for weather data and ingest events if thresholds exceeded."""
    import asyncio
    asyncio.run(_poll_weather())


async def _poll_weather():
    import h3
    from app.config import settings

    async with httpx.AsyncClient(timeout=15.0) as client:
        for city, (lat, lng) in CITY_COORDS.items():
            try:
                response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lng,
                        "current_weather": "true",
                        "hourly": "precipitation,apparent_temperature",
                        "timezone": "Asia/Kolkata",
                        "forecast_days": 1,
                    },
                )
                data = response.json()

                current = data.get("current_weather", {})
                temperature = current.get("temperature", 0)

                # Check hourly data for current hour precipitation
                hourly = data.get("hourly", {})
                precip_values = hourly.get("precipitation", [])
                precipitation = precip_values[0] if precip_values else 0

                h3_cell = h3.latlng_to_cell(lat, lng, 9)

                # Ingest rainfall event
                if precipitation > 2.0:
                    severity = min(precipitation / 30.0, 1.0)
                    await _ingest_event(
                        h3_cell=h3_cell,
                        city=city,
                        event_type="rainfall",
                        severity=severity,
                        raw_value=precipitation,
                        source_api="open-meteo",
                    )

                # Ingest heat event
                if temperature > 38.0:
                    severity = min((temperature - 38.0) / 7.0, 1.0)
                    await _ingest_event(
                        h3_cell=h3_cell,
                        city=city,
                        event_type="heat",
                        severity=severity,
                        raw_value=temperature,
                        source_api="open-meteo",
                    )

            except Exception as e:
                print(f"⚠️  Weather poll failed for {city}: {e}")


async def _ingest_event(h3_cell, city, event_type, severity, raw_value, source_api):
    """Call the internal event ingest endpoint."""
    from app.config import settings

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(
                f"http://localhost:8000/grid/events/ingest",
                json={
                    "h3_cell": h3_cell,
                    "city": city,
                    "event_type": event_type,
                    "severity": round(severity, 4),
                    "raw_value": raw_value,
                    "source_api": source_api,
                },
                headers={"X-Internal-Key": settings.INTERNAL_API_KEY},
            )
        except Exception as e:
            print(f"⚠️  Event ingest failed: {e}")
