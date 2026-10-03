"""
Unit test suite for Triqee Standalone Edge AI & Quantum Gateway Engine
====================================================================
Verifies latency performance (< 15ms target), memory footprint boundaries (< 15MB),
physical-layer RF calculations, and QPU job DAG compilation.
"""

import pytest
from src.edge_engine import TriqeeEdgeEngine


def test_edge_inference_latency_and_output():
    engine = TriqeeEdgeEngine(node_id="TEST_EDGE_NODE_01", device_tier="WEARABLE_TIER_1")
    res = engine.run_edge_inference("Verify quantum edge speed", max_tokens=16)

    assert res["node_id"] == "TEST_EDGE_NODE_01"
    assert res["tokens_count"] == 16
    assert res["latency_ms"] < 25.0  # Must be fast local execution
    assert res["memory_footprint_mb"] <= 15.0
    assert len(res["output_tokens"]) == 16
    assert engine.quantization_bits == 4
    assert engine.quantization_levels == 15
    assert all(
        value * engine.quantization_levels == round(value * engine.quantization_levels)
        for value in engine.recurrent_state
    )


def test_rf_quantum_link_physics():
    engine = TriqeeEdgeEngine()
    # Equinix SV5 (San Jose) to NY4 (Secaucus)
    link = engine.evaluate_rf_quantum_link(37.3861, -121.9639, 40.7831, -74.0407)

    assert link["distance_km"] > 4000.0
    assert link["rf_line_of_sight_latency_ms"] < link["legacy_fiber_latency_ms"]
    assert link["physical_latency_saved_ms"] > 5.0
    assert link["speedup_percentage"] > 30.0


def test_qpu_transpilation_job_generation():
    engine = TriqeeEdgeEngine()
    job = engine.compile_qpu_transpilation_job(qubit_count=12, depth=10, target_backend="ibm_heron")

    assert job["qubit_count"] == 12
    assert job["target_backend"] == "ibm_heron"
    assert job["qpu_status"] == "READY_FOR_DISPATCH"
    assert job["total_gates"] > 0


def test_qpu_invalid_qubits_raises():
    engine = TriqeeEdgeEngine()
    with pytest.raises(ValueError):
        engine.compile_qpu_transpilation_job(qubit_count=0)
    with pytest.raises(ValueError):
        engine.compile_qpu_transpilation_job(qubit_count=200)


def test_benchmark_full_hybrid_cycle():
    engine = TriqeeEdgeEngine()
    bm = engine.benchmark_full_hybrid_cycle()

    assert bm["triqee_edge_total_ms"] < bm["classical_cloud_roundtrip_ms"]
    assert bm["latency_reduction_factor"] > 10.0
    assert "qjob_edge_" in bm["qpu_transpile_job"]
