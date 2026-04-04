"""
GridGuard AI — Traffic Poller Task
Polls OpenRouteService every 15 minutes for congestion data
"""

import httpx
from app.tasks.celery_app import app

CITY_CORRIDORS = {
    "bengaluru": [
        [77.5946, 12.9716], [77.6100, 12.9800],
        [77.5800, 12.9600], [77.6200, 12.9500], [77.5700, 12.9900],
    ],
    "mumbai": [
        [72.8777, 19.0760], [72.8900, 19.0650],
        [72.8650, 19.0850], [72.8500, 19.0950], [72.9000, 19.0560],
    ],
    "delhi": [
        [77.2090, 28.6139], [77.2200, 28.6250],
        [77.1950, 28.6050], [77.2300, 28.5950], [77.1800, 28.6350],
    ],
    "chennai": [
        [80.2707, 13.0827], [80.2600, 13.0750],
        [80.2800, 13.0900], [80.2500, 13.0650], [80.2900, 13.0950],
    ],
    "hyderabad": [
        [78.4867, 17.3850], [78.4700, 17.3750],
        [78.5000, 17.3950], [78.4600, 17.3650], [78.5100, 17.4050],
    ],
}

FREE_FLOW_BASELINE = 600.0  # seconds for baseline route duration


@app.task(name="app.tasks.traffic_poller.poll_traffic_events")
def poll_traffic_events():
    """Poll ORS for traffic data and ingest road saturation events."""
    import asyncio
    asyncio.run(_poll_traffic())


async def _get_congestion_ratio_ors(
    client: httpx.AsyncClient,
    corridors: list[list[float]],
    ors_api_key: str,
) -> float | None:
    response = await client.post(
        "https://api.openrouteservice.org/v2/matrix/driving-car",
        json={
            "locations": corridors,
            "metrics": ["duration"],
        },
        headers={
            "Authorization": ors_api_key,
            "Content-Type": "application/json",
        },
    )

    data = response.json()
    durations = data.get("durations", [])
    if not durations:
        return None

    flat = [duration for row in durations for duration in row if duration and duration > 0]
    if not flat:
        return None

    avg_duration = sum(flat) / len(flat)
    return avg_duration / FREE_FLOW_BASELINE


async def _get_congestion_ratio_tomtom(
    client: httpx.AsyncClient,
    lat: float,
    lng: float,
    tomtom_api_key: str,
) -> float | None:
    response = await client.get(
        "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json",
        params={
            "key": tomtom_api_key,
            "point": f"{lat},{lng}",
            "unit": "KMPH",
        },
    )
    data = response.json().get("flowSegmentData", {})

    current_speed = float(data.get("currentSpeed", 0) or 0)
    free_flow_speed = float(data.get("freeFlowSpeed", 0) or 0)
    if free_flow_speed <= 0:
        return None

    effective_current = max(current_speed, 5.0)
    return free_flow_speed / effective_current


async def _ingest_traffic_event(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    h3_cell: str,
    city: str,
    congestion_ratio: float,
    source_api: str,
    internal_key: str,
) -> None:
    severity = min(max((congestion_ratio - 1.0) / 1.2, 0.0), 1.0)
    await client.post(
        f"{base_url}/grid/events/ingest",
        json={
            "h3_cell": h3_cell,
            "city": city,
            "event_type": "road_saturation",
            "severity": round(severity, 4),
            "raw_value": round(congestion_ratio, 4),
            "source_api": source_api,
        },
        headers={"X-Internal-Key": internal_key},
    )


async def _poll_traffic():
    import h3
    from app.config import settings
    base_url = settings.INTERNAL_API_BASE_URL.rstrip("/")

    ors_enabled = bool(settings.ORS_API_KEY and settings.ORS_API_KEY != "your-ors-key")
    tomtom_enabled = bool(settings.TOMTOM_API_KEY)

    if not ors_enabled and not tomtom_enabled:
        print("⚠️  ORS and TOMTOM keys are not configured, skipping traffic poll")
        return

    async with httpx.AsyncClient(timeout=20.0) as client:
        for city, corridors in CITY_CORRIDORS.items():
            try:
                congestion_ratio = None
                source_api = ""

                if ors_enabled:
                    try:
                        congestion_ratio = await _get_congestion_ratio_ors(
                            client,
                            corridors,
                            settings.ORS_API_KEY,
                        )
                        if congestion_ratio is not None:
                            source_api = "openrouteservice"
                    except Exception as ors_error:
                        print(f"⚠️  ORS traffic poll failed for {city}: {ors_error}")

                if congestion_ratio is None and tomtom_enabled:
                    try:
                        lat, lng = corridors[0][1], corridors[0][0]
                        congestion_ratio = await _get_congestion_ratio_tomtom(
                            client,
                            lat,
                            lng,
                            settings.TOMTOM_API_KEY,
                        )
                        if congestion_ratio is not None:
                            source_api = "tomtom"
                    except Exception as tomtom_error:
                        print(f"⚠️  TomTom traffic poll failed for {city}: {tomtom_error}")

                if congestion_ratio is None:
                    continue

                if congestion_ratio >= 1.0:
                    lat, lng = corridors[0][1], corridors[0][0]
                    h3_cell = h3.latlng_to_cell(lat, lng, 9)
                    await _ingest_traffic_event(
                        client,
                        base_url=base_url,
                        h3_cell=h3_cell,
                        city=city,
                        congestion_ratio=congestion_ratio,
                        source_api=source_api,
                        internal_key=settings.INTERNAL_API_KEY,
                    )

            except Exception as e:
                print(f"⚠️  Traffic poll failed for {city}: {e}")
