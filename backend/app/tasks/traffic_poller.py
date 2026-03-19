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


async def _poll_traffic():
    import h3
    from app.config import settings

    if not settings.ORS_API_KEY or settings.ORS_API_KEY == "your-ors-key":
        print("⚠️  ORS API key not configured, skipping traffic poll")
        return

    async with httpx.AsyncClient(timeout=20.0) as client:
        for city, corridors in CITY_CORRIDORS.items():
            try:
                response = await client.post(
                    "https://api.openrouteservice.org/v2/matrix/driving-car",
                    json={
                        "locations": corridors,
                        "metrics": ["duration"],
                    },
                    headers={
                        "Authorization": settings.ORS_API_KEY,
                        "Content-Type": "application/json",
                    },
                )

                data = response.json()
                durations = data.get("durations", [])

                if not durations:
                    continue

                # Calculate average duration
                flat = [d for row in durations for d in row if d and d > 0]
                avg_duration = sum(flat) / len(flat) if flat else 0

                congestion_ratio = avg_duration / FREE_FLOW_BASELINE

                if congestion_ratio > 1.5:
                    lat, lng = corridors[0][1], corridors[0][0]
                    h3_cell = h3.latlng_to_cell(lat, lng, 9)

                    async with httpx.AsyncClient(timeout=10.0) as ingest_client:
                        await ingest_client.post(
                            "http://localhost:8000/grid/events/ingest",
                            json={
                                "h3_cell": h3_cell,
                                "city": city,
                                "event_type": "road_saturation",
                                "severity": min(congestion_ratio / 3.0, 1.0),
                                "raw_value": round(congestion_ratio, 4),
                                "source_api": "openrouteservice",
                            },
                            headers={"X-Internal-Key": settings.INTERNAL_API_KEY},
                        )

            except Exception as e:
                print(f"⚠️  Traffic poll failed for {city}: {e}")
