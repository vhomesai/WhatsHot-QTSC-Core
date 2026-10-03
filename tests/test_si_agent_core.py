"""
Unit test suite for Sovereign SI Agent Core
===========================================
Validates dual-brain reasoning, intent routing, tool execution,
and comparison between classical simulation and sovereign edge mode.
"""

import pytest
from src.si_agent_core import SovereignSIAgent
from src.db_manager import DatabaseManager


def test_si_agent_classical_mode():
    agent = SovereignSIAgent()
    res = agent.generate_response("Test query", mode="CLASSICAL_CLOUD_MODE")

    assert res["mode"] == "CLASSICAL_CLOUD_MODE"
    assert res["latency_ms"] >= 800.0
    assert res["telemetry"]["edge_execution"] is False
    assert "Cloud Server LLM" in res["response_text"]


def test_si_agent_sovereign_edge_mode():
    agent = SovereignSIAgent()
    res = agent.generate_response("What is the distance and latency between nodes?", mode="SOVEREIGN_QUANTUM_EDGE_MODE")

    assert res["mode"] == "SOVEREIGN_QUANTUM_EDGE_MODE"
    assert res["latency_ms"] < 50.0  # Fast local synthesis
    assert res["memory_mb"] <= 15.0
    assert res["telemetry"]["edge_execution"] is True
    assert len(res["tools_executed"]) > 0


def test_si_agent_qpu_transpilation_tool():
    agent = SovereignSIAgent()
    res = agent.generate_response("Please compile a 16-qubit quantum circuit DAG", mode="SOVEREIGN_QUANTUM_EDGE_MODE")

    assert res["qpu_artifact"] is not None
    assert res["qpu_artifact"]["qubit_count"] == 16
    assert res["qpu_artifact"]["qpu_status"] == "READY_FOR_DISPATCH"
    assert "QPU DAG Compiled" in res["response_text"]


def test_si_agent_research_lookup_tool(tmp_path):
    db_file = str(tmp_path / "test_si_db.db")
    db = DatabaseManager(db_file)
    db.record_intelligence_article(
        source="ArXiv",
        title="Diamond NV Spin Qubit Coherence at Room Temperature",
        primary_category="EDGE_QUANTUM_HARDWARE",
        priority="P0_CRITICAL",
        summary="Experimental demonstration of room temperature diamond qubit gates."
    )

    agent = SovereignSIAgent(db_manager=db)
    res = agent.generate_response("Show me latest research paper headlines on diamond qubits", mode="SOVEREIGN_QUANTUM_EDGE_MODE")

    assert len(res["tools_executed"]) > 0
    assert any(t["tool_name"] == "search_intelligence_breakthroughs" for t in res["tools_executed"])


def test_next_best_move_advances_sequentially():
    agent = SovereignSIAgent()
    session_id = "test_seq_session"

    expected_stages = [
        (1, "Deploy Live Cross-Exchange Arbitrage & Zero-Trust Defense Pilot"),
        (2, "Export Wyoming Institutional Compliance Pack & SHA-256 Merkle Certificate"),
        (3, "Run 500-Node QKD Laser Mesh & Quantum Eavesdropping Defense Stress Test"),
        (4, "Dispatch Piermont Bank Institutional Retainer Binders to 37 Active CRM Nodes"),
        (5, "Trigger Continuous ArXiv Scientific Ingestion & RLHF Retraining Loop"),
        (6, "Transpile Multi-Vendor QPU DAGs for IBM Heron, IonQ Forte & Rigetti Ankaa"),
    ]

    for stage_num, title in expected_stages:
        res = agent.generate_response("next best move", session_id=session_id)
        assert f"STAGE {stage_num}/6" in res["response_text"]
        assert title in res["response_text"]

    # Cycles back to stage 1
    res_cycle = agent.generate_response("what next?", session_id=session_id)
    assert "STAGE 1/6" in res_cycle["response_text"]


def test_executing_directive_advances_stage():
    agent = SovereignSIAgent()
    session_id = "test_directive_exec"

    # Step 1: Execute Arbitrage Pilot (Directive 1)
    res_pilot = agent.generate_response("Execute Arbitrage Pilot", session_id=session_id)
    assert "LIVE PILOT INITIALIZED" in res_pilot["response_text"]

    # Step 2: Next best move should now be Stage 2 (Compliance Dossier)
    res_next = agent.generate_response("next best move", session_id=session_id)
    assert "STAGE 2/6" in res_next["response_text"]
    assert "Export Wyoming Institutional Compliance Pack" in res_next["response_text"]
    assert "✓ [COMPLETED]" in res_next["response_text"]  # Stage 1 marked completed


def test_different_sessions_have_isolated_states():
    agent = SovereignSIAgent()
    session_a = "session_alpha"
    session_b = "session_beta"

    # Advance session A to stage 2
    res_a1 = agent.generate_response("next best move", session_id=session_a)
    assert "STAGE 1/6" in res_a1["response_text"]

    # Session B starts at stage 1
    res_b1 = agent.generate_response("next best move", session_id=session_b)
    assert "STAGE 1/6" in res_b1["response_text"]

    # Session A advances to stage 2
    res_a2 = agent.generate_response("next best move", session_id=session_a)
    assert "STAGE 2/6" in res_a2["response_text"]
