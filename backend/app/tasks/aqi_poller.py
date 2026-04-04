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


async def _ingest_aqi_event(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    h3_cell: str,
    city: str,
    severity: float,
    raw_value: float,
    source_api: str,
    internal_key: str,
):
    await client.post(
        f"{base_url}/grid/events/ingest",
        json={
            "h3_cell": h3_cell,
            "city": city,
            "event_type": "aqi",
            "severity": round(severity, 4),
            "raw_value": float(raw_value),
            "source_api": source_api,
        },
        headers={"X-Internal-Key": internal_key},
    )


async def _poll_aqi():
    import h3
    from app.config import settings
    base_url = settings.INTERNAL_API_BASE_URL.rstrip("/")

    waqi_configured = bool(
        settings.WAQI_API_TOKEN
        and settings.WAQI_API_TOKEN != "your-waqi-token"
    )

    if not waqi_configured:
        print("⚠️  WAQI API token not configured, using Open-Meteo AQI fallback")

    async with httpx.AsyncClient(timeout=15.0) as client:
        for city, waqi_name in CITY_NAMES.items():
            try:
                lat, lng = CITY_COORDS[city]
                h3_cell = h3.latlng_to_cell(lat, lng, 9)

                if waqi_configured:
                    response = await client.get(
                        f"https://api.waqi.info/feed/{waqi_name}/",
                        params={"token": settings.WAQI_API_TOKEN},
                    )
                    data = response.json()

                    if data.get("status") != "ok":
                        continue

                    aqi = float(data.get("data", {}).get("aqi", 0) or 0)
                    source_api = "waqi"
                    severity = min(aqi / 300.0, 1.0)
                else:
                    response = await client.get(
                        "https://air-quality-api.open-meteo.com/v1/air-quality",
                        params={
                            "latitude": lat,
                            "longitude": lng,
                            "current": "us_aqi",
                            "timezone": "Asia/Kolkata",
                        },
                    )
                    data = response.json()
                    current = data.get("current", {})
                    aqi = float(current.get("us_aqi", 0) or 0)
                    source_api = "open-meteo-air-quality"
                    # Open-Meteo US AQI range is 0-500; normalize toward 300+ severe conditions.
                    severity = min(aqi / 300.0, 1.0)

                if aqi >= 50 and severity >= 0.12:
                    await _ingest_aqi_event(
                        client,
                        base_url=base_url,
                        h3_cell=h3_cell,
                        city=city,
                        severity=severity,
                        raw_value=aqi,
                        source_api=source_api,
                        internal_key=settings.INTERNAL_API_KEY,
                    )

            except Exception as e:
                print(f"⚠️  AQI poll failed for {city}: {e}")
