"""
GridGuard AI — H3 Helpers
Utility functions for H3 hexagonal grid operations
"""

import h3


CITY_CENTROIDS = {
    "bengaluru": (12.9716, 77.5946),
    "mumbai": (19.0760, 72.8777),
    "chennai": (13.0827, 80.2707),
    "delhi": (28.6139, 77.2090),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
    "kolkata": (22.5726, 88.3639),
}


def latlng_to_h3(lat: float, lng: float, resolution: int = 9) -> str:
    """Convert lat/lng to H3 cell ID."""
    return h3.latlng_to_cell(lat, lng, resolution)


def h3_to_latlng(h3_cell: str) -> tuple[float, float]:
    """Get center lat/lng of an H3 cell."""
    return h3.cell_to_latlng(h3_cell)


def get_neighbors(h3_cell: str, k: int = 1) -> set[str]:
    """Get k-ring neighbors of an H3 cell."""
    return h3.grid_disk(h3_cell, k)


def h3_distance(cell_a: str, cell_b: str) -> int:
    """Get grid distance between two H3 cells."""
    try:
        return h3.grid_distance(cell_a, cell_b)
    except Exception:
        return 999  # cells not comparable


def city_to_h3(city: str, resolution: int = 9) -> str | None:
    """Get H3 cell for city centroid."""
    coords = CITY_CENTROIDS.get(city.lower())
    if coords:
        return h3.latlng_to_cell(coords[0], coords[1], resolution)
    return None


def get_city_cells(city: str, resolution: int = 8) -> list[str]:
    """
    Get all H3 cells covering a city area.
    Uses k-ring around centroid (approximation).
    Resolution 8 cells ≈ 0.7 km² each.
    """
    coords = CITY_CENTROIDS.get(city.lower())
    if not coords:
        return []
    center = h3.latlng_to_cell(coords[0], coords[1], resolution)
    # k=5 gives ~91 cells covering city center
    return list(h3.grid_disk(center, 5))
