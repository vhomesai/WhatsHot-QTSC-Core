"""
API Integration Tests using FastAPI TestClient
==============================================
Validates HTTP endpoints, request serialization, validation errors,
and status codes.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.api_server import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


def test_list_known_nodes():
    response = client.get("/api/v1/nodes")
    assert response.status_code == 200
    nodes = response.json()
    assert "CHICAGO_CME" in nodes
    assert "TOKYO_JPX" in nodes


def test_compute_distance_valid():
    payload = {
        "lat1": 41.8781,
        "lon1": -87.6298,
        "lat2": 47.6062,
        "lon2": -122.3321
    }
    response = client.post("/api/v1/geodesic/distance", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "distance_km" in data
    assert 2700 < data["distance_km"] < 2900


def test_compute_distance_invalid_coordinates():
    payload = {
        "lat1": 95.0,  # Invalid latitude (> 90)
        "lon1": -87.6298,
        "lat2": 47.6062,
        "lon2": -122.3321
    }
    response = client.post("/api/v1/geodesic/distance", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_compute_latency_valid():
    payload = {
        "distance_km": 1000.0,
        "slant_factor": 1.0075,
        "fiber_routing_factor": 1.22
    }
    response = client.post("/api/v1/physics/latency", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["free_space_one_way_ms"] > 0
    assert data["fiber_one_way_ms"] > data["free_space_one_way_ms"]


def test_triage_classification_endpoint():
    payload = {
        "user_handle": "@test_developer",
        "message_text": "How do I install with python using pip?",
        "platform": "GitHub"
    }
    response = client.post("/api/v1/triage/classify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "DEV_INQUIRY"
    assert "@test_developer" in data["user_handle"]


def test_intelligence_endpoints():
    response = client.get("/api/v1/intelligence/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "articles" in data

    stats_resp = client.get("/api/v1/intelligence/stats")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    assert stats_data["status"] == "success"
    assert "stats" in stats_data


def test_edge_infer_endpoint():
    payload = {"prompt": "Test Edge Gateway Prompt", "max_tokens": 8}
    response = client.post("/api/v1/edge/infer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["tokens_count"] == 8
    assert data["latency_ms"] < 25.0


def test_benchmark_compare_endpoint():
    payload = {
        "lat1": 37.3861,
        "lon1": -121.9639,
        "lat2": 40.7831,
        "lon2": -74.0407,
        "qubits": 8
    }
    response = client.post("/api/v1/benchmark/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    bm = data["benchmark"]
    assert bm["speedup_factor"] > 10.0
    assert bm["triqee_edge_total_ms"] < bm["classical_cloud_roundtrip_ms"]
    assert bm["qpu_transpiled_job"]["qubit_count"] == 8


def test_sovereign_si_chat_endpoint():
    payload = {
        "prompt": "Calculate RF latency to NY4 and compile a 12-qubit circuit",
        "mode": "SOVEREIGN_QUANTUM_EDGE_MODE",
        "session_id": "test_session_123"
    }
    response = client.post("/api/v1/si/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["session_id"] == "test_session_123"
    result = data["result"]
    assert result["mode"] == "SOVEREIGN_QUANTUM_EDGE_MODE"
    assert result["latency_ms"] < 50.0
    assert result["qpu_artifact"]["qubit_count"] == 12
    assert len(result["tools_executed"]) >= 2
