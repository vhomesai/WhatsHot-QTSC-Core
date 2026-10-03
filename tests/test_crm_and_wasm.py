"""
Test Suite for Institutional CRM Pipeline & WebAssembly Silicon Kernel
======================================================================
Verifies lead capture, automated triage categorization, CSV/JSON export,
CRM pipeline metrics, and WebAssembly bytecode binary generation.
"""

import pytest
import os
import json
import sqlite3
from fastapi.testclient import TestClient
from src.api_server import app, db
from src.silicon_kernel_wasm import (
    build_silicon_wasm_binary,
    get_silicon_wasm_base64,
    simulate_silicon_execution
)


@pytest.fixture
def client():
    return TestClient(app)


class TestWebAssemblySiliconKernel:
    """Validates WebAssembly compilation and physical mathematical accuracy."""

    def test_wasm_binary_header_and_exports(self):
        wasm_bytes = build_silicon_wasm_binary()
        assert len(wasm_bytes) > 100
        # WebAssembly Magic Header "\0asm" and version 1
        assert wasm_bytes[:4] == b"\x00asm"
        assert wasm_bytes[4:8] == b"\x01\x00\x00\x00"

        # Verify exported symbols exist in binary payload
        assert b"geodesic_rf_latency" in wasm_bytes
        assert b"fiber_optical_latency" in wasm_bytes
        assert b"photonic_mac" in wasm_bytes
        assert b"qber_rate" in wasm_bytes
        assert b"photonic_mac_batch_10000" in wasm_bytes
        assert b"geodesic_rf_latency_batch_10000" in wasm_bytes

        # The f64 encoding must be the exact statutory physics constant,
        # not the previously mistyped 299672.458375 value.
        assert bytes.fromhex("b6f3fdd4414c1241") in wasm_bytes
        assert bytes.fromhex("894160d5614a1241") not in wasm_bytes

    def test_wasm_base64_string(self):
        b64 = get_silicon_wasm_base64()
        assert isinstance(b64, str)
        assert len(b64) > 100
        # Starts with Base64 encoding of \0asm\x01\0\0\0 -> AGFzbQEAAAA...
        assert b64.startswith("AGFzbQEAAAA")

    def test_simulate_silicon_execution_physics(self):
        res = simulate_silicon_execution(distance_km=3900.0)
        assert res["status"] == "success"
        assert res["distance_km"] == 3900.0
        # RF latency: ~13.1 ms
        assert 12.0 < res["rf_latency_ms"] < 14.0
        # Fiber latency: ~23.3 ms
        assert 22.0 < res["fiber_latency_ms"] < 25.0
        # Physical speedup > 1.5x
        assert res["speedup_factor"] > 1.5
        assert res["physical_latency_saved_ms"] > 9.0


class TestInstitutionalCRMPipeline:
    """Validates lead capture, triage tagging, database persistence, and exports."""

    def test_db_manager_crm_methods(self, tmp_path):
        from src.db_manager import DatabaseManager
        temp_db_path = str(tmp_path / "test_crm.db")
        temp_db = DatabaseManager(temp_db_path)

        lead_id = temp_db.record_lead(
            tier="tier1",
            email="allocator@citadel.com",
            identifier="Alex Vance",
            allocated_tq=25000.0,
            firm_name="Citadel Quantum",
            deployment_scale="Global Low-Latency Triangle (Tokyo-Chicago-London)",
            category_tag="ENTERPRISE_INQUIRY",
            notes="Need sub-millisecond RF routing"
        )
        assert lead_id is not None
        assert lead_id > 0

        leads = temp_db.get_all_leads()
        assert len(leads) == 1
        assert leads[0]["email"] == "allocator@citadel.com"
        assert leads[0]["firm_name"] == "Citadel Quantum"
        assert leads[0]["allocated_tq"] == 25000.0

        csv_str = temp_db.export_leads_csv()
        assert "allocator@citadel.com" in csv_str
        assert "Citadel Quantum" in csv_str
        assert "Allocated $TQ" in csv_str

        json_str = temp_db.export_leads_json()
        parsed = json.loads(json_str)
        assert parsed["total_count"] == 1
        assert parsed["leads"][0]["email"] == "allocator@citadel.com"

        stats = temp_db.get_crm_pipeline_stats()
        assert stats["total_leads"] == 1
        assert stats["total_tq_allocated"] == 25000.0
        assert stats["by_tier"]["tier1"] == 1

    def test_api_crm_lead_capture_endpoint(self, client):
        import uuid
        unique_email = f"lead_{uuid.uuid4().hex[:8]}@bridgewater.com"
        payload = {
            "email": unique_email,
            "tier": "tier2",
            "identifier": "Ray Dalio Team",
            "firm_name": "Bridgewater Macro Quantum",
            "deployment_scale": "SCIF Defense On-Premise Sovereign Node",
            "message": "Requesting information for SCIF on-premise defense deployment.",
            "wallet_address": "0x71C83638379185a0895520284719293120194821",
            "allocated_tq": 50000.0
        }
        resp = client.post("/api/v1/leads/capture", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["email"] == unique_email
        assert data["allocated_tq"] == 50000.0
        assert data["category_tag"] == "ENTERPRISE_INQUIRY"
        assert data["statutory_reference"] == "Wyoming W.S. § 34-29-106"
        assert data["merkle_receipt"].startswith("0x")

    def test_api_crm_export_endpoints(self, client, monkeypatch):
        monkeypatch.setenv("TRIQEE_ADMIN_KEY", "test-admin-key")
        headers = {"X-Admin-Key": "test-admin-key"}
        resp_csv = client.get("/api/v1/crm/export/csv", headers=headers)
        assert resp_csv.status_code == 200
        assert "text/csv" in resp_csv.headers["content-type"]
        assert "Email" in resp_csv.text

        resp_json = client.get("/api/v1/crm/export/json", headers=headers)
        assert resp_json.status_code == 200
        assert "application/json" in resp_json.headers["content-type"]
        data = resp_json.json()
        assert "leads" in data
        assert "total_count" in data

    def test_api_crm_pipeline_stats_endpoint(self, client):
        resp = client.get("/api/v1/crm/pipeline")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "pipeline" in data
        assert "total_leads" in data["pipeline"]
        assert "total_tq_allocated" in data["pipeline"]
