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


async def _fetch_open_meteo_weather(
    client: httpx.AsyncClient,
    lat: float,
    lng: float,
) -> tuple[float, float, str]:
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
    temperature = float(current.get("temperature", 0) or 0)

    hourly = data.get("hourly", {})
    precip_values = hourly.get("precipitation", [])
    precipitation = float(precip_values[0] if precip_values else 0)

    return precipitation, temperature, "open-meteo"


async def _fetch_openweather_weather(
    client: httpx.AsyncClient,
    lat: float,
    lng: float,
    api_key: str,
) -> tuple[float, float, str]:
    response = await client.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={
            "lat": lat,
            "lon": lng,
            "appid": api_key,
            "units": "metric",
        },
    )
    data = response.json()

    temperature = float(data.get("main", {}).get("temp", 0) or 0)
    precipitation = float((data.get("rain") or {}).get("1h", 0) or 0)

    return precipitation, temperature, "openweather"


async def _poll_weather():
    import h3
    from app.config import settings

    openweather_enabled = bool(settings.OPENWEATHER_API_KEY)
    if not openweather_enabled:
        print("⚠️  OPENWEATHER_API_KEY not configured; weather fallback disabled")

    async with httpx.AsyncClient(timeout=15.0) as client:
        for city, (lat, lng) in CITY_COORDS.items():
            try:
                try:
                    precipitation, temperature, source_api = await _fetch_open_meteo_weather(
                        client,
                        lat,
                        lng,
                    )
                except Exception as meteo_error:
                    if not openweather_enabled:
                        print(f"⚠️  Weather poll failed for {city}: {meteo_error}")
                        continue

                    try:
                        precipitation, temperature, source_api = await _fetch_openweather_weather(
                            client,
                            lat,
                            lng,
                            settings.OPENWEATHER_API_KEY,
                        )
                    except Exception as fallback_error:
                        print(
                            "⚠️  Weather poll failed for "
                            f"{city}: primary={meteo_error} fallback={fallback_error}"
                        )
                        continue

                h3_cell = h3.latlng_to_cell(lat, lng, 9)

                # Ingest rainfall stress (continuous signal from light to severe rain)
                rainfall_severity = min(precipitation / 12.0, 1.0)
                if precipitation >= 0.2 and rainfall_severity >= 0.02:
                    await _ingest_event(
                        h3_cell=h3_cell,
                        city=city,
                        event_type="rainfall",
                        severity=rainfall_severity,
                        raw_value=precipitation,
                        source_api=source_api,
                    )

                # Ingest heat stress continuously from warm to extreme temperatures.
                heat_severity = min(max(temperature - 30.0, 0) / 12.0, 1.0)
                if temperature >= 30.0 and heat_severity >= 0.05:
                    await _ingest_event(
                        h3_cell=h3_cell,
                        city=city,
                        event_type="heat",
                        severity=heat_severity,
                        raw_value=temperature,
                        source_api=source_api,
                    )

            except Exception as e:
                print(f"⚠️  Weather poll failed for {city}: {e}")


async def _ingest_event(h3_cell, city, event_type, severity, raw_value, source_api):
    """Call the internal event ingest endpoint."""
    from app.config import settings
    base_url = settings.INTERNAL_API_BASE_URL.rstrip("/")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(
                f"{base_url}/grid/events/ingest",
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
