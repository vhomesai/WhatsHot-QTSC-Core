"""
Unit test suite for Sovereign SI Agent Core
===========================================
Validates dual-brain reasoning, intent routing, deterministic tool execution,
and dynamic sequential progression of the 6-stage Next Best Move state machine.
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


def test_next_best_move_sequential_progression():
    """
    Verifies that calling 'next best move' repeatedly progresses sequentially
    through Stage 1 -> Stage 2 -> Stage 3 -> Stage 4 -> Stage 5 -> Stage 6 -> Stage 1.
    """
    agent = SovereignSIAgent()
    session_id = "test_seq_session_01"

    # Call 1: Should propose Stage 1
    r1 = agent.generate_response("next best move?", session_id=session_id)
    assert "STAGE 1/6" in r1["response_text"]
    assert "Deploy Live Cross-Exchange Arbitrage" in r1["response_text"]
    assert "Execute Arbitrage Pilot" in r1["response_text"]

    # Call 2: Should advance to Stage 2
    r2 = agent.generate_response("next best move", session_id=session_id)
    assert "STAGE 2/6" in r2["response_text"]
    assert "Export Wyoming Institutional Compliance Pack" in r2["response_text"]
    assert "Generate Compliance Dossier" in r2["response_text"]

    # Call 3: Should advance to Stage 3
    r3 = agent.generate_response("what's next?", session_id=session_id)
    assert "STAGE 3/6" in r3["response_text"]
    assert "Run 500-Node QKD Laser Mesh" in r3["response_text"]
    assert "Simulate QKD Interception Defense" in r3["response_text"]

    # Call 4: Should advance to Stage 4
    r4 = agent.generate_response("what should we do next", session_id=session_id)
    assert "STAGE 4/6" in r4["response_text"]
    assert "Dispatch Piermont Bank Institutional Retainer Binders" in r4["response_text"]
    assert "Fulfill All Deployments" in r4["response_text"]

    # Call 5: Should advance to Stage 5
    r5 = agent.generate_response("recommended next move", session_id=session_id)
    assert "STAGE 5/6" in r5["response_text"]
    assert "Trigger Continuous ArXiv Scientific Ingestion" in r5["response_text"]
    assert "Ingest ArXiv Breakthroughs" in r5["response_text"]

    # Call 6: Should advance to Stage 6
    r6 = agent.generate_response("optimal next step", session_id=session_id)
    assert "STAGE 6/6" in r6["response_text"]
    assert "Transpile Multi-Vendor QPU DAGs" in r6["response_text"]
    assert "Benchmark Multivendor QPU" in r6["response_text"]

    # Call 7: Cycles back to Stage 1
    r7 = agent.generate_response("next move", session_id=session_id)
    assert "STAGE 1/6" in r7["response_text"]


def test_next_best_move_reflects_executed_directives():
    """
    Verifies that executing a specific directive marks it as completed
    and sets the stage pointer to the subsequent action.
    """
    agent = SovereignSIAgent()
    session_id = "test_executed_directives_02"

    # User executes Directive 1 directly
    res_d1 = agent.generate_response("Execute Arbitrage Pilot", session_id=session_id)
    assert "LIVE PILOT INITIALIZED" in res_d1["response_text"]
    assert 1 in agent.get_session_state(session_id)["executed_stages"]

    # Next query for 'next best move' should recommend Stage 2 and show Stage 1 as [COMPLETED]
    res_next = agent.generate_response("next best move?", session_id=session_id)
    assert "STAGE 2/6" in res_next["response_text"]
    assert "Stage 1: Deploy Live Cross-Exchange Arbitrage & Zero-Trust Defense Pilot** — `✓ [COMPLETED]`" in res_next["response_text"]
    assert "Stage 2: Export Wyoming Institutional Compliance Pack & SHA-256 Merkle Certificate** — `🎯 [ACTIVE NEXT MOVE]`" in res_next["response_text"]

    # User executes Directive 2
    res_d2 = agent.generate_response("Generate Compliance Dossier", session_id=session_id)
    assert "EXECUTIVE MORNING BRIEFING FOR TIER-1 ALLOCATORS" in res_d2["response_text"]
    assert 2 in agent.get_session_state(session_id)["executed_stages"]

    # User executes Directive 3
    res_d3 = agent.generate_response("Simulate QKD Interception Defense", session_id=session_id)
    assert "500-NODE QKD LASER MESH EAVESDROPPING DEFENSE REPORT" in res_d3["response_text"]
    assert 3 in agent.get_session_state(session_id)["executed_stages"]

    # User executes Directive 4
    res_d4 = agent.generate_response("Fulfill All Deployments", session_id=session_id)
    assert "INSTITUTIONAL ALLOCATOR WIRE & RETAINER FULFILLMENT COMPLETED" in res_d4["response_text"]
    assert 4 in agent.get_session_state(session_id)["executed_stages"]

    # User executes Directive 5
    res_d5 = agent.generate_response("Ingest ArXiv Breakthroughs", session_id=session_id)
    assert "AUTONOMOUS ARXIV SCIENTIFIC INGESTION" in res_d5["response_text"]
    assert 5 in agent.get_session_state(session_id)["executed_stages"]

    # User executes Directive 6
    res_d6 = agent.generate_response("Benchmark Multivendor QPU", session_id=session_id)
    assert "MULTI-VENDOR QPU COMPILER & TRANSPILATION BENCHMARK" in res_d6["response_text"]
    assert 6 in agent.get_session_state(session_id)["executed_stages"]


def test_session_state_isolation():
    """
    Verifies that separate sessions maintain independent progression states.
    """
    agent = SovereignSIAgent()
    s1 = "session_alpha"
    s2 = "session_beta"

    # In session 1, advance to Stage 3
    agent.generate_response("next best move", session_id=s1)  # 1 -> 2
    agent.generate_response("next best move", session_id=s1)  # 2 -> 3

    # In session 2, initial query should still be Stage 1
    r_s2 = agent.generate_response("next best move", session_id=s2)
    assert "STAGE 1/6" in r_s2["response_text"]

    # Session 1 should now be at Stage 3
    r_s1 = agent.generate_response("next best move", session_id=s1)
    assert "STAGE 3/6" in r_s1["response_text"]


def test_other_intents_handled_correctly():
    """
    Verifies state certificates, highest & best use, and batch deployments.
    """
    agent = SovereignSIAgent()
    
    # State certificate
    r_cert = agent.generate_response("Issue cryptographic SHA-256 state certificate")
    assert "OFFICIAL WYOMING STATUTORY STATE CERTIFICATE" in r_cert["response_text"]
    assert "W.S. § 34-29-106" in r_cert["response_text"]

    # Highest & Best use
    r_use = agent.generate_response("What is the highest and best use of Triqee?")
    assert "HIGHEST & BEST USE OF TRIQEE" in r_use["response_text"]

    # All 3 capabilities
    r_all = agent.generate_response("deploy all 3 capabilities")
    assert "ALL 3 ENGINES COMPILED" in r_all["response_text"]
    assert "Triqee-OptoTensor" in r_all["response_text"]
    assert "Triqee-AgentGrid" in r_all["response_text"]
    assert "Triqee-NeuroState" in r_all["response_text"]
