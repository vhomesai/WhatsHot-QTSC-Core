"""
Package Initialization for Triqee Core Source Modules
"""

from .physics_engine import (
    haversine_distance,
    calculate_propagation_latencies,
    C_LIGHT_KM_S,
    DEFAULT_FIBER_INDEX_N,
    KNOWN_NODES
)
from .triage_engine import (
    classify_message,
    generate_triage_payload,
    CATEGORIES
)
from .db_manager import (
    DatabaseManager
)

__all__ = [
    "haversine_distance",
    "calculate_propagation_latencies",
    "C_LIGHT_KM_S",
    "DEFAULT_FIBER_INDEX_N",
    "KNOWN_NODES",
    "classify_message",
    "generate_triage_payload",
    "CATEGORIES",
    "DatabaseManager"
]
