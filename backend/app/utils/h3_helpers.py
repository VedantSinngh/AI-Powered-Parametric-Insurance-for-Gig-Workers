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


# Wider rings for city-level map coverage so outskirts are included.
CITY_CORE_RING_K = {
    "bengaluru": 7,
    "mumbai": 8,
    "chennai": 7,
    "delhi": 8,
    "hyderabad": 7,
    "pune": 7,
    "kolkata": 7,
}


# Outskirts anchors improve city spread instead of clustering only around the center.
CITY_OUTSKIRT_ANCHORS: dict[str, list[tuple[float, float]]] = {
    "bengaluru": [
        (13.0990, 77.5963),  # Yelahanka
        (13.0760, 77.7981),  # Hoskote side
        (12.7835, 77.7730),  # Attibele
        (12.9056, 77.4820),  # Kengeri
        (13.2425, 77.7132),  # Devanahalli
    ],
    "mumbai": [
        (19.2870, 72.8700),  # Mira Road
        (19.0760, 72.9980),  # Vashi
        (18.9894, 73.1175),  # Panvel
        (19.2183, 72.9781),  # Thane
        (19.4550, 72.8120),  # Virar
        (19.2403, 73.1305),  # Kalyan
    ],
    "chennai": [
        (12.9249, 80.1275),  # Tambaram
        (13.1143, 80.1015),  # Avadi
        (12.9007, 80.2279),  # Sholinganallur
        (13.2140, 80.3203),  # Ennore
        (13.0480, 80.1082),  # Poonamallee
    ],
    "delhi": [
        (28.4595, 77.0266),  # Gurugram
        (28.5355, 77.3910),  # Noida
        (28.6692, 77.4538),  # Ghaziabad
        (28.4089, 77.3178),  # Faridabad
        (28.6921, 76.9335),  # Bahadurgarh
        (28.8526, 77.0929),  # Narela side
    ],
    "hyderabad": [
        (17.2511, 78.4294),  # Shamshabad
        (17.3457, 78.5522),  # LB Nagar
        (17.6290, 78.4818),  # Medchal
        (17.5288, 78.2668),  # Patancheru
        (17.4058, 78.5591),  # Uppal
    ],
    "pune": [
        (18.6298, 73.7997),  # Pimpri
        (18.7357, 73.6757),  # Talegaon
        (18.5793, 73.9890),  # Wagholi
        (18.4497, 73.9155),  # Undri
        (18.5912, 73.7389),  # Hinjawadi outskirts
    ],
    "kolkata": [
        (22.5958, 88.2636),  # Howrah
        (22.6225, 88.4500),  # Rajarhat
        (22.7600, 88.3700),  # Barrackpore
        (22.3594, 88.4370),  # Baruipur
        (22.7056, 88.3459),  # Konnagar side
    ],
}

CITY_OUTSKIRT_RING_K = 2


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
    Get H3 cells covering a city and its outskirts.
    Uses a wider center k-ring plus outskirts anchors.
    Resolution 8 cells ≈ 0.7 km² each.
    """
    city_key = city.lower().strip()
    coords = CITY_CENTROIDS.get(city_key)
    if not coords:
        return []

    center = h3.latlng_to_cell(coords[0], coords[1], resolution)
    core_ring = CITY_CORE_RING_K.get(city_key, 6)
    cells = set(h3.grid_disk(center, core_ring))

    for lat, lng in CITY_OUTSKIRT_ANCHORS.get(city_key, []):
        anchor_cell = h3.latlng_to_cell(lat, lng, resolution)
        cells.update(h3.grid_disk(anchor_cell, CITY_OUTSKIRT_RING_K))

    return sorted(cells)
