"""
Pytest Comprehensive Test Suite for Triqee Core Package
========================================================
Validates:
1. Physics engine mathematical accuracy, boundary conditions, and error raising.
2. Triage engine text classification rules, edge cases, and response generators.
3. Database manager CRUD operations, uniqueness constraints, and transactions.
"""

import sys
import pytest
import sqlite3
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.physics_engine import (
    haversine_distance,
    calculate_propagation_latencies,
    C_LIGHT_KM_S,
    DEFAULT_FIBER_INDEX_N,
    KNOWN_NODES
)
from src.triage_engine import (
    classify_message,
    generate_triage_payload,
    CATEGORIES
)
from src.db_manager import (
    DatabaseManager
)


# ==========================================
# 1. Physics Engine Tests
# ==========================================

class TestPhysicsEngine:

    def test_haversine_zero_distance(self):
        dist = haversine_distance(37.7749, -122.4194, 37.7749, -122.4194)
        assert dist == pytest.approx(0.0, abs=1e-5)

    def test_haversine_known_benchmark(self):
        # London (51.5074, -0.1278) to Frankfurt (50.1109, 8.6821) is ~635 km
        dist = haversine_distance(51.5074, -0.1278, 50.1109, 8.6821)
        assert 620 < dist < 650

    def test_haversine_out_of_bounds_latitude(self):
        with pytest.raises(ValueError, match="Latitude must be between"):
            haversine_distance(95.0, 0.0, 0.0, 0.0)

    def test_haversine_out_of_bounds_longitude(self):
        with pytest.raises(ValueError, match="Longitude must be between"):
            haversine_distance(0.0, -185.0, 0.0, 0.0)

    def test_latency_calculation_validity(self):
        res = calculate_propagation_latencies(distance_km=2800.0)
        assert res["free_space_one_way_ms"] > 0
        assert res["free_space_rtt_ms"] == pytest.approx(res["free_space_one_way_ms"] * 2.0, abs=1e-3)
        assert res["fiber_one_way_ms"] > res["free_space_one_way_ms"]
        assert res["latency_advantage_ms"] > 0

    def test_latency_negative_distance_error(self):
        with pytest.raises(ValueError, match="Distance cannot be negative"):
            calculate_propagation_latencies(distance_km=-100.0)

    def test_latency_invalid_fiber_index_error(self):
        with pytest.raises(ValueError, match="Refractive index"):
            calculate_propagation_latencies(distance_km=100.0, fiber_index_n=0.9)


# ==========================================
# 2. Triage Engine Tests
# ==========================================

class TestTriageEngine:

    @pytest.mark.parametrize("input_text, expected_category", [
        ("How do I install the SDK via python and use with Qiskit?", "DEV_INQUIRY"),
        ("We are a hedge fund looking to test the portfolio alpha model.", "QUANT_INQUIRY"),
        ("What is the legal status under Wyoming token law for $TQ?", "LEGAL_UTILITY_INQUIRY"),
        ("Requesting information for SCIF on-premise defense deployment.", "ENTERPRISE_INQUIRY"),
        ("Hello, I am interested in learning more.", "DEV_INQUIRY"),  # default fallback
        ("", "DEV_INQUIRY"),  # empty string handling
    ])
    def test_classification_rules(self, input_text, expected_category):
        category = classify_message(input_text)
        assert category == expected_category

    def test_generate_triage_payload_fields(self):
        payload = generate_triage_payload(
            user_handle="@analyst",
            message_text="Testing alpha factor models.",
            platform="LinkedIn"
        )
        assert payload["user_handle"] == "@analyst"
        assert payload["platform"] == "LinkedIn"
        assert payload["category"] == "QUANT_INQUIRY"
        assert "response_template" in CATEGORIES["QUANT_INQUIRY"]
        assert payload["suggested_response"] == CATEGORIES["QUANT_INQUIRY"]["response_template"]
        assert "timestamp_utc" in payload


# ==========================================
# 3. Database Manager Tests
# ==========================================

class TestDatabaseManager:

    @pytest.fixture
    def temp_db(self, tmp_path):
        db_file = tmp_path / "test_operational.db"
        db = DatabaseManager(str(db_file))
        return db

    def test_record_lead_and_retrieve(self, temp_db):
        lead_id = temp_db.record_lead(
            tier="tier1",
            email="developer@example.com",
            identifier="gh_handle",
            allocated_tq=500.0
        )
        assert lead_id > 0

        lead = temp_db.get_lead_by_email("developer@example.com")
        assert lead is not None
        assert lead["email"] == "developer@example.com"
        assert lead["allocated_tq"] == 500.0
        assert lead["tier"] == "tier1"

    def test_duplicate_email_rejection(self, temp_db):
        temp_db.record_lead("tier1", "unique@example.com", "id1", 500.0)
        with pytest.raises(sqlite3.IntegrityError):
            temp_db.record_lead("tier2", "unique@example.com", "id2", 5000.0)

    def test_invalid_email_format(self, temp_db):
        with pytest.raises(ValueError, match="Valid email address is required"):
            temp_db.record_lead("tier1", "invalid_no_at_sign", "id1", 500.0)

    def test_leads_summary_aggregation(self, temp_db):
        temp_db.record_lead("tier1", "a@test.com", "id_a", 500.0)
        temp_db.record_lead("tier2", "b@test.com", "id_b", 5000.0)
        temp_db.record_lead("tier3", "c@test.com", "id_c", 250.0)

        summary = temp_db.get_leads_summary()
        assert summary["total_records"] == 3
        assert summary["total_tq_allocated"] == 5750.0

    def test_event_logging(self, temp_db):
        evt_id = temp_db.log_event("SYSTEM_BOOT", '{"status": "OK"}')
        assert evt_id > 0
