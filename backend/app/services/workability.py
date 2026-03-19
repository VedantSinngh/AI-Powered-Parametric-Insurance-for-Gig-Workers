"""
GridGuard AI — Workability Score Engine
Calculates workability from environmental events with weighted scoring
"""

from typing import List, Optional


THRESHOLDS = {
    "rainfall": 15.0,     # mm/hr
    "aqi": 300.0,         # AQI index
    "heat": 45.0,         # °C max (38°C baseline)
    "traffic": 2.0,       # congestion ratio
}

WEIGHTS = {
    "rainfall": 0.40,
    "aqi": 0.30,
    "heat": 0.20,
    "traffic": 0.10,
}

PAYOUT_RATES = {
    "rainfall": 50.0,
    "heat": 35.0,
    "aqi": 40.0,
    "road_saturation": 30.0,
    "app_outage": 45.0,
}


class WorkabilityService:
    """Calculates workability scores from environmental events."""

    @staticmethod
    def calculate_score(active_events: list) -> float:
        """
        Calculate workability score from active events.
        Score 1.0 = fully workable, 0.0 = completely disrupted.
        """
        rainfall_norm = 0.0
        aqi_norm = 0.0
        heat_norm = 0.0
        traffic_norm = 0.0

        for event in active_events:
            event_type = event.get("event_type", "")
            raw_value = event.get("raw_value", 0.0)

            if event_type == "rainfall":
                rainfall_norm = max(rainfall_norm, min(raw_value / 15.0, 1.0))
            elif event_type == "aqi":
                aqi_norm = max(aqi_norm, min(raw_value / 300.0, 1.0))
            elif event_type == "heat":
                heat_norm = max(heat_norm, min(max(raw_value - 38.0, 0) / 7.0, 1.0))
            elif event_type in ("road_saturation", "traffic"):
                traffic_norm = max(traffic_norm, min(raw_value, 1.0))

        score = 1.0 - (
            0.40 * rainfall_norm
            + 0.30 * aqi_norm
            + 0.20 * heat_norm
            + 0.10 * traffic_norm
        )
        return max(0.0, min(1.0, round(score, 4)))

    @staticmethod
    def get_status(score: float) -> str:
        """Map workability score to status string."""
        if score >= 0.70:
            return "safe"
        elif score >= 0.40:
            return "caution"
        else:
            return "disrupted"

    @staticmethod
    def get_payout_rate(event_type: str) -> float:
        """Get hourly payout rate for event type."""
        return PAYOUT_RATES.get(event_type, 30.0)

    @staticmethod
    def get_dominant_event_type(active_events: list) -> Optional[str]:
        """Return the event type with highest severity."""
        if not active_events:
            return None
        return max(active_events, key=lambda e: e.get("severity", 0)).get("event_type")


workability_service = WorkabilityService()
