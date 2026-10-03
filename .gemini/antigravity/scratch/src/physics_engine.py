"""
Triqee Core Physics & Geodesic Calculation Engine
==================================================
Provides pure, deterministic calculations for:
- Haversine great-circle surface distance
- Atmospheric speed-of-light propagation latency
- Optical fiber propagation latency with refractive index
- Microsecond and nanosecond timing conversion utilities
"""

import math
from typing import Dict, Any, Tuple

# Physical constants
C_LIGHT_KM_S: float = 299792.458
DEFAULT_FIBER_INDEX_N: float = 1.4682
EARTH_RADIUS_KM: float = 6371.0

# Verified exchange reference coordinates
KNOWN_NODES: Dict[str, Tuple[float, float]] = {
    "CHICAGO_CME": (41.8781, -87.6298),
    "SEATTLE_PACIFIC": (47.6062, -122.3321),
    "TOKYO_JPX": (35.6762, 139.6503),
    "SECAUCUS_NY4": (40.7895, -74.0565),
    "LONDON_LD4": (51.5074, -0.1278),
    "FRANKFURT_FR2": (50.1109, 8.6821)
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes the great-circle surface distance between two geographic coordinates
    on a spherical Earth using the Haversine formula.

    Args:
        lat1: Latitude of point 1 in degrees (-90.0 to 90.0).
        lon1: Longitude of point 1 in degrees (-180.0 to 180.0).
        lat2: Latitude of point 2 in degrees (-90.0 to 90.0).
        lon2: Longitude of point 2 in degrees (-180.0 to 180.0).

    Returns:
        Distance in kilometers (float >= 0.0).

    Raises:
        ValueError: If any coordinate exceeds valid geographic bounds.
    """
    if not (-90.0 <= lat1 <= 90.0 and -90.0 <= lat2 <= 90.0):
        raise ValueError("Latitude must be between -90.0 and 90.0 degrees.")
    if not (-180.0 <= lon1 <= 180.0 and -180.0 <= lon2 <= 180.0):
        raise ValueError("Longitude must be between -180.0 and 180.0 degrees.")

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def calculate_propagation_latencies(
    distance_km: float,
    slant_factor: float = 1.0075,
    fiber_routing_factor: float = 1.22,
    fiber_index_n: float = DEFAULT_FIBER_INDEX_N,
    hardware_delay_ns: float = 0.0
) -> Dict[str, float]:
    """
    Calculates theoretical one-way and round-trip propagation times for both
    free-space light transmission and single-mode optical fiber.

    Args:
        distance_km: Geodesic distance in kilometers.
        slant_factor: Geometric expansion factor for atmospheric/ionospheric bounce.
        fiber_routing_factor: Physical terrestrial/subsea cable routing expansion.
        fiber_index_n: Refractive index of fiber glass core.
        hardware_delay_ns: Additional hardware demodulation/processing delay in nanoseconds.

    Returns:
        Dictionary containing one-way and RTT latencies in milliseconds.
    """
    if distance_km < 0.0:
        raise ValueError("Distance cannot be negative.")
    if fiber_index_n <= 1.0:
        raise ValueError("Refractive index of fiber must be greater than 1.0.")

    fiber_speed_km_s = C_LIGHT_KM_S / fiber_index_n
    hw_delay_ms = hardware_delay_ns / 1_000_000.0

    # Free-space atmospheric light transmission
    free_space_one_way_ms = (distance_km * slant_factor / C_LIGHT_KM_S) * 1000.0 + hw_delay_ms
    free_space_rtt_ms = free_space_one_way_ms * 2.0

    # Subsea/terrestrial fiber optic transmission
    fiber_one_way_ms = (distance_km * fiber_routing_factor / fiber_speed_km_s) * 1000.0
    fiber_rtt_ms = fiber_one_way_ms * 2.0

    latency_advantage_ms = fiber_one_way_ms - free_space_one_way_ms

    return {
        "distance_km": round(distance_km, 2),
        "free_space_one_way_ms": round(free_space_one_way_ms, 3),
        "free_space_rtt_ms": round(free_space_rtt_ms, 3),
        "fiber_one_way_ms": round(fiber_one_way_ms, 3),
        "fiber_rtt_ms": round(fiber_rtt_ms, 3),
        "latency_advantage_ms": round(latency_advantage_ms, 3),
        "latency_advantage_us": round(latency_advantage_ms * 1000.0, 1)
    }
