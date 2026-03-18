"""
GridGuard AI — H3 Geospatial Helpers
Utility functions for Uber H3 operations.
"""

import h3


H3_RESOLUTION = 9  # ~174m edge length, ideal for urban delivery zones


def gps_to_h3(lat: float, lng: float, resolution: int = H3_RESOLUTION) -> str:
    """Convert GPS coordinates to an H3 cell index."""
    return h3.geo_to_h3(lat, lng, resolution)


def h3_to_center(h3_cell: str) -> tuple[float, float]:
    """Get the center lat/lng of an H3 cell."""
    lat, lng = h3.h3_to_geo(h3_cell)
    return lat, lng


def h3_distance_km(cell_a: str, cell_b: str) -> float:
    """Approximate distance in km between two H3 cell centers."""
    lat_a, lng_a = h3.h3_to_geo(cell_a)
    lat_b, lng_b = h3.h3_to_geo(cell_b)
    return haversine_km(lat_a, lng_a, lat_b, lng_b)


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance between two GPS points in km."""
    import math
    R = 6371.0  # Earth's radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def gps_distance_to_h3_center_m(lat: float, lng: float, h3_cell: str) -> float:
    """Distance in meters from a GPS point to the center of an H3 cell."""
    center_lat, center_lng = h3_to_center(h3_cell)
    return haversine_km(lat, lng, center_lat, center_lng) * 1000


def get_neighboring_cells(h3_cell: str, ring_size: int = 1) -> list[str]:
    """Get H3 cells within a ring around the given cell."""
    return list(h3.k_ring(h3_cell, ring_size))


def get_city_cells(city: str) -> list[str]:
    """
    Get H3 cells covering a city. Uses approximate city center coords.
    In production, this would use proper city boundary polygons.
    """
    CITY_CENTERS = {
        "mumbai": (19.0760, 72.8777),
        "delhi": (28.6139, 77.2090),
        "bangalore": (12.9716, 77.5946),
        "hyderabad": (17.3850, 78.4867),
        "chennai": (13.0827, 80.2707),
        "pune": (18.5204, 73.8567),
        "kolkata": (22.5726, 88.3639),
        "ahmedabad": (23.0225, 72.5714),
        "jaipur": (26.9124, 75.7873),
        "lucknow": (26.8467, 80.9462),
    }

    city_lower = city.lower()
    if city_lower not in CITY_CENTERS:
        return []

    lat, lng = CITY_CENTERS[city_lower]
    center_cell = gps_to_h3(lat, lng)
    # Return a 3-ring area around city center (~area of ~37 cells)
    return get_neighboring_cells(center_cell, ring_size=3)
