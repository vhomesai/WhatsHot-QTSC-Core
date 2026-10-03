"""
Tests for Triqee QEC Experimental Prototype & Algebra Verification Engine
========================================================================
Validates:
1. GF(2) matrix operations, ranks, and commutativity algebra.
2. Exact CSS code invariants: H_X * H_Z^T = 0 mod 2, k=12, n=72.
3. Stabilizer extraction and OpenQASM 3.0 / Stim generator semantics.
4. Statistical confidence interval calculations and simulation bounds.
5. Static compiler estimates and artifact export with SHA-256 validation.
"""

import pytest
import json
from pathlib import Path
from src.triqee_qec_engine import (
    gf2_rank,
    gf2_matmul,
    gf2_transpose,
    TriqeeQECEngine,
    qec_engine,
    CodeAlgebraProof,
    QECStabilizerCheck
)


def test_gf2_rank_basic_and_edge_cases():
    assert gf2_rank([]) == 0
    assert gf2_rank([[]]) == 0

    # 3x3 Identity
    identity = [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1]
    ]
    assert gf2_rank(identity) == 3

    # Dependent rows over GF(2)
    dependent = [
        [1, 1, 0],
        [0, 1, 1],
        [1, 0, 1]  # row 1 + row 2 = row 3 over GF(2)
    ]
    assert gf2_rank(dependent) == 2


def test_gf2_matmul_and_transpose():
    a = [
        [1, 1],
        [0, 1]
    ]
    b = [
        [1, 0],
        [1, 1]
    ]
    # In GF(2):
    # [1*1 + 1*1, 1*0 + 1*1] = [0, 1]
    # [0*1 + 1*1, 0*0 + 1*1] = [1, 1]
    c = gf2_matmul(a, b)
    assert c == [[0, 1], [1, 1]]

    # Dimension mismatch error
    with pytest.raises(ValueError, match="Incompatible matrix dimensions"):
        gf2_matmul([[1, 0]], [[1, 0]])

    # Transpose
    t = gf2_transpose([[1, 0, 1], [0, 1, 1]])
    assert t == [[1, 0], [0, 1], [1, 1]]


def test_bivariate_bicycle_algebra_proof():
    engine = TriqeeQECEngine(l_param=6, m_param=6)
    proof = engine.verify_code_algebra()

    assert isinstance(proof, CodeAlgebraProof)
    assert proof.physical_qubits == 72
    assert proof.logical_qubits == 12
    assert proof.code_distance == 6
    assert proof.h_x_rank == 30
    assert proof.h_z_rank == 30
    assert proof.commutativity_verified is True
    assert proof.is_valid_css_code is True
    assert proof.data_qubit_overhead_ratio == 6.0
    assert proof.total_qubit_overhead_ratio_during_extraction == 12.0


def test_stabilizer_checks_generation():
    engine = TriqeeQECEngine()
    checks = engine.synthesize_stabilizer_checks()

    assert len(checks) == 72
    x_checks = [c for c in checks if c.check_type == "X"]
    z_checks = [c for c in checks if c.check_type == "Z"]
    assert len(x_checks) == 36
    assert len(z_checks) == 36

    # Verify check properties
    for c in checks:
        assert isinstance(c, QECStabilizerCheck)
        assert c.ancilla_qubit >= 72
        assert len(c.data_qubits) == 6  # Row weight of 6 for each stabilizer
        assert all(0 <= d < 72 for d in c.data_qubits)


def test_openqasm3_and_stim_generators():
    engine = TriqeeQECEngine()
    qasm = engine.generate_openqasm3()
    stim = engine.generate_stim_circuit()

    assert "OPENQASM 3.0;" in qasm
    assert "qubit[72] data;" in qasm
    assert "qubit[72] ancilla;" in qasm
    assert "syndrome_r1" in qasm
    assert "logical_meas" in qasm

    assert "DETECTOR" in stim
    assert "OBSERVABLE_INCLUDE(0)" in stim
    assert "OBSERVABLE_INCLUDE(11)" in stim


def test_statistical_simulation_bounds():
    engine = TriqeeQECEngine()
    sim = engine.run_statistically_rigorous_simulation(
        physical_error_rates=[0.01, 0.02],
        shots_per_point=1000,
        seed=123
    )

    assert sim["status"] == "COMPLETED"
    assert sim["total_shots_simulated"] == 2000
    assert "finite_size_scaling_notice" in sim
    assert len(sim["data_points"]) == 2
    for dp in sim["data_points"]:
        assert 0.0 <= dp["ci_95_lower"] <= dp["empirical_error_rate"] <= dp["ci_95_upper"] <= 1.0
        assert dp["rule_of_three_zero_error_bound_95"] == 0.003


def test_static_compiler_estimates():
    engine = TriqeeQECEngine()
    estimates = engine.generate_static_compiler_estimates()

    assert estimates["compiler_status"] == "STATIC_ESTIMATES_ONLY_NO_HARDWARE_EXECUTION"
    assert "ibm_heron_156q" in estimates["target_modalities"]
    assert "harvard_quera_neutral_atoms" in estimates["target_modalities"]
    assert "quantinuum_h2" in estimates["target_modalities"]
    assert "qubit_overhead_accounting" in estimates
    assert estimates["qubit_overhead_accounting"]["data_encoding_ratio"] == "6:1 (72 data / 12 logical)"
    assert estimates["qubit_overhead_accounting"]["total_footprint_ratio_during_extraction"] == "12:1 (144 total / 12 logical)"


def test_export_verified_artifacts(tmp_path: Path):
    engine = TriqeeQECEngine()
    res = engine.export_verified_artifacts(tmp_path)

    assert res["status"] == "ARTIFACTS_EXPORTED_WITH_SHA256"
    assert len(res["proof_sha256"]) == 64
    assert len(res["qasm_sha256"]) == 64
    assert len(res["stim_sha256"]) == 64
    assert len(res["sim_sha256"]) == 64
    assert len(res["compiler_sha256"]) == 64

    for path_str in res["paths"].values():
        p = Path(path_str)
        assert p.exists()
        assert p.stat().st_size > 0


def test_qec_engine_main(tmp_path: Path, capsys):
    from src.triqee_qec_engine import main
    res = main(tmp_path)
    captured = capsys.readouterr()
    assert "QEC Prototype Verification Complete" in captured.out
    assert res["status"] == "ARTIFACTS_EXPORTED_WITH_SHA256"


def test_qec_engine_run_path_main(monkeypatch, capsys):
    import runpy
    monkeypatch.setattr("src.triqee_qec_engine.qec_engine.export_verified_artifacts", lambda p: {"status": "TEST_OK"})
    runpy.run_path("src/triqee_qec_engine.py", run_name="__main__")
    captured = capsys.readouterr()
    assert "QEC Prototype Verification Complete" in captured.out


