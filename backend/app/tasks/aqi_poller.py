"""
GridGuard AI — AQI Poller Task
Polls WAQI API every 30 minutes for air quality data
"""

import httpx
from app.tasks.celery_app import app

CITY_NAMES = {
    "bengaluru": "bangalore",
    "mumbai": "mumbai",
    "chennai": "chennai",
    "delhi": "delhi",
    "hyderabad": "hyderabad",
    "pune": "pune",
    "kolkata": "kolkata",
}

CITY_COORDS = {
    "bengaluru": (12.9716, 77.5946),
    "mumbai": (19.0760, 72.8777),
    "chennai": (13.0827, 80.2707),
    "delhi": (28.6139, 77.2090),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
    "kolkata": (22.5726, 88.3639),
}


@app.task(name="app.tasks.aqi_poller.poll_aqi_events")
def poll_aqi_events():
    """Poll WAQI API for AQI data and ingest events if threshold exceeded."""
    import asyncio
    asyncio.run(_poll_aqi())


async def _poll_aqi():
    import h3
    from app.config import settings

    if not settings.WAQI_API_TOKEN or settings.WAQI_API_TOKEN == "your-waqi-token":
        print("⚠️  WAQI API token not configured, skipping AQI poll")
        return

    async with httpx.AsyncClient(timeout=15.0) as client:
        for city, waqi_name in CITY_NAMES.items():
            try:
                response = await client.get(
                    f"https://api.waqi.info/feed/{waqi_name}/",
                    params={"token": settings.WAQI_API_TOKEN},
                )
                data = response.json()

                if data.get("status") != "ok":
                    continue

                aqi = data.get("data", {}).get("aqi", 0)

                if aqi > 150:
                    lat, lng = CITY_COORDS[city]
                    h3_cell = h3.latlng_to_cell(lat, lng, 9)
                    severity = min(aqi / 400.0, 1.0)

                    async with httpx.AsyncClient(timeout=10.0) as ingest_client:
                        await ingest_client.post(
                            "http://localhost:8000/grid/events/ingest",
                            json={
                                "h3_cell": h3_cell,
                                "city": city,
                                "event_type": "aqi",
                                "severity": round(severity, 4),
                                "raw_value": float(aqi),
                                "source_api": "waqi",
                            },
                            headers={"X-Internal-Key": settings.INTERNAL_API_KEY},
                        )

            except Exception as e:
                print(f"⚠️  AQI poll failed for {city}: {e}")
