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
