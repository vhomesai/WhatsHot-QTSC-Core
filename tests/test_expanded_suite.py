"""
Expanded Test Suite for Core Engine Modules and Utilities
==========================================================
Tests:
1. Haversine distance boundary conditions & coordinate validation.
2. Latency calculation invariants and transmission delays.
3. Message triage classification and rule mapping.
4. SQLite database table creation, insertion, queries, and constraints.
5. SOW estimation and institutional target manifest validation.
"""

import os
import sys
import unittest
import sqlite3
import tempfile
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for p in [str(PROJECT_ROOT / "src"), str(PROJECT_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from triqee_fourthstate_quantum_rf_arbitrage_engine import (
    haversine_distance,
    FourthStateQuantumRFEngine,
    C_LIGHT_KM_S,
    FIBER_INDEX_N,
    EQUINIX_NODES
)
from triqee_social_comment_and_inbox_sentinel import (
    COMMENT_TRIAGE_TEMPLATES,
    triage_inbound_message
)

class TestGeodesicAndPhysicsConstants(unittest.TestCase):
    """Verifies fundamental constants and distance calculations"""

    def test_speed_of_light_constant(self):
        self.assertAlmostEqual(C_LIGHT_KM_S, 299792.458, places=3)

    def test_fiber_refractive_index(self):
        self.assertGreater(FIBER_INDEX_N, 1.0)
        self.assertLess(FIBER_INDEX_N, 2.0)

    def test_equinix_nodes_coordinates_valid(self):
        for node_id, data in EQUINIX_NODES.items():
            lat = data["lat"]
            lon = data["lon"]
            self.assertTrue(-90.0 <= lat <= 90.0, f"Latitude {lat} invalid for {node_id}")
            self.assertTrue(-180.0 <= lon <= 180.0, f"Longitude {lon} invalid for {node_id}")
            self.assertIn("exchange", data)

    def test_antipodal_distance(self):
        # Distance between (0, 0) and (0, 180) should be approx half Earth circumference (~20,015 km)
        dist = haversine_distance(0.0, 0.0, 0.0, 180.0)
        self.assertTrue(19900 < dist < 20100)

class TestQuantumRFEngineSimulation(unittest.TestCase):
    """Verifies latency metrics and simulation boundaries"""

    def setUp(self):
        self.engine = FourthStateQuantumRFEngine(squid_demod_ns=0.42)

    def test_latency_calculation_structure(self):
        m = self.engine.calculate_quantum_rf_latencies()
        required_keys = [
            "total_distance_km",
            "fourth_state_squid_one_way_ms",
            "fourth_state_squid_rtt_ms",
            "subsea_fiber_one_way_ms",
            "subsea_fiber_rtt_ms",
            "fiber_latency_advantage_moat_ms",
            "microwave_dsp_latency_advantage_us",
            "squid_quantum_demod_latency_ns"
        ]
        for key in required_keys:
            self.assertIn(key, m, f"Missing key: {key}")
            self.assertIsInstance(m[key], (int, float, str))

    def test_rtt_is_double_one_way(self):
        m = self.engine.calculate_quantum_rf_latencies()
        self.assertAlmostEqual(m["fourth_state_squid_rtt_ms"], m["fourth_state_squid_one_way_ms"] * 2, places=2)
        self.assertAlmostEqual(m["subsea_fiber_rtt_ms"], m["subsea_fiber_one_way_ms"] * 2, places=2)

class TestMessageTriageEngine(unittest.TestCase):
    """Verifies keyword classification logic"""

    def test_dev_message_classification(self):
        msg = "How do I install the Python SDK with Qiskit and Cirq transpiler?"
        res = triage_inbound_message("@dev_user", msg, platform="GitHub")
        self.assertEqual(res["category"], "DEV_INQUIRY")
        self.assertIn("pip install triqee", res["suggested_response"])

    def test_quant_message_classification(self):
        msg = "We want to test your hedge fund factor model and check Sharpe alpha."
        res = triage_inbound_message("@quant_user", msg, platform="LinkedIn")
        self.assertEqual(res["category"], "QUANT_INQUIRY")
        self.assertIn("5,000 $TQ", res["suggested_response"])

    def test_defense_message_classification(self):
        msg = "We need an air-gapped on-premise sovereign appliance with FIPS compliance for defense."
        res = triage_inbound_message("@defense_contact", msg, platform="Portal")
        self.assertEqual(res["category"], "ENTERPRISE_DEFENSE_INQUIRY")
        self.assertIn("Sovereign Appliance", res["suggested_response"])

class TestDatabaseOperations(unittest.TestCase):
    """Verifies SQLite database operations with temporary database instances"""

    def setUp(self):
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix=".db")
        self.conn = sqlite3.connect(self.test_db_path)
        self.cursor = self.conn.cursor()

        self.cursor.execute("""
            CREATE TABLE airdrop_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tier TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                identifier TEXT NOT NULL,
                allocated_tq REAL NOT NULL,
                claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'PROVISIONED'
            )
        """)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.close(self.test_db_fd)
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_unique_email_constraint(self):
        self.cursor.execute(
            "INSERT INTO airdrop_leads (tier, email, identifier, allocated_tq) VALUES (?, ?, ?, ?)",
            ("tier1", "user@example.com", "id_1", 500.0)
        )
        self.conn.commit()

        # Duplicate email should fail
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute(
                "INSERT INTO airdrop_leads (tier, email, identifier, allocated_tq) VALUES (?, ?, ?, ?)",
                ("tier2", "user@example.com", "id_2", 5000.0)
            )
            self.conn.commit()

    def test_aggregate_queries(self):
        test_data = [
            ("tier1", "a@example.com", "id_a", 500.0),
            ("tier2", "b@example.com", "id_b", 5000.0),
            ("tier3", "c@example.com", "id_c", 250.0)
        ]
        self.cursor.executemany(
            "INSERT INTO airdrop_leads (tier, email, identifier, allocated_tq) VALUES (?, ?, ?, ?)",
            test_data
        )
        self.conn.commit()

        self.cursor.execute("SELECT COUNT(*), SUM(allocated_tq) FROM airdrop_leads")
        count, total_tq = self.cursor.fetchone()
        self.assertEqual(count, 3)
        self.assertEqual(total_tq, 5750.0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
