import sqlite3

import pytest

from src.db_manager import DatabaseManager
from src.si_agent_core import SovereignSIAgent


@pytest.fixture
def agent(tmp_path):
    db = DatabaseManager(str(tmp_path / "si-agent.db"))
    db.record_intelligence_article(
        source="arXiv",
        external_id="nv-1",
        title="Diamond NV center breakthrough",
        primary_category="EDGE_QUANTUM_HARDWARE",
        priority="P0_CRITICAL",
        matched_keywords=["diamond", "nv center"],
    )
    db.record_intelligence_article(
        source="arXiv",
        external_id="rf-1",
        title="SQUID quantum RF sensing",
        primary_category="QUANTUM_RF_SENSING",
        priority="P0_CRITICAL",
        matched_keywords=["squid", "quantum rf"],
    )
    return SovereignSIAgent(db_manager=db)


def test_execute_tool_catalog_and_invariants(agent):
    geodesic = agent.execute_tool(
        "calculate_geodesic_rf",
        {"lat1": 41.8781, "lon1": -87.6298, "lat2": 51.5074, "lon2": -0.1278},
    )
    assert geodesic["distance_km"] > 6_000
    assert geodesic["legacy_fiber_latency_ms"] > geodesic["rf_line_of_sight_latency_ms"]

    all_articles = agent.execute_tool("search_intelligence_breakthroughs", {"limit": 5})
    filtered = agent.execute_tool(
        "search_intelligence_breakthroughs",
        {"limit": 5, "category": "EDGE_QUANTUM_HARDWARE"},
    )
    assert all_articles["count"] == 5
    assert all_articles["matched_count"] == 5
    assert filtered["count"] == 1
    assert all(
        article["category"] == "DIAMOND_NV"
        for article in filtered["articles"]
    )

    qpu = agent.execute_tool(
        "transpile_qpu_circuit",
        {"qubits": 4, "depth": 7, "backend": "ionq_forte"},
    )
    assert qpu["qubit_count"] == 4
    assert qpu["total_gates"] == 7
    assert qpu["target_backend"] == "ionq_forte"

    qkd = agent.execute_tool(
        "design_qkd_architecture",
        {"distance_km": 150, "protocol": "requested-protocol"},
    )
    assert qkd["distance_km"] == 150
    assert qkd["fiber_loss_db"] == 30.0
    assert len(qkd["comparison_models"]) == 3

    defense = agent.execute_tool(
        "simulate_qkd_eavesdropping",
        {"nodes": 12, "attack": "BEAM_SPLITTER"},
    )
    assert defense["nodes_evaluated"] == 12
    assert defense["tampered_qber_pct"] > defense["security_threshold_pct"]
    assert defense["compromised_keys_leaked"] == 0

    grant = agent.execute_tool(
        "claim_token_grant",
        {
            "email": "developer@example.com",
            "wallet": "0x1234",
            "tier": "TIER_TEST",
            "amount": 750,
        },
    )
    assert grant["lead_id"] > 0
    assert grant["status"] == "GRANT_ALLOCATED"
    assert grant["settlement_chain"] == "Base L2 / Wyoming Sovereign Ledger"
    assert grant["cryptographic_receipt_sha256"].startswith("0x")

    benchmark = agent.execute_tool("benchmark_multivendor_qpu", {"qubits": 24})
    assert benchmark["qubits"] == 24
    assert [item["backend"] for item in benchmark["backends_compared"]] == [
        "IBM Heron (156 Qubits)",
        "IonQ Forte (36 Algorithmic Qubits)",
        "Rigetti Ankaa-9Q / 84Q",
    ]
    assert benchmark["backends_compared"][1]["swap_overhead_pct"] == 0.0

    triangle = agent.execute_tool("calculate_global_triangle_rf", {})
    assert len(triangle["legs"]) == 3
    assert triangle["triangle_perimeter_km"] > 20_000
    assert triangle["total_fiber_rtt_ms"] > triangle["total_rf_rtt_ms"]
    assert triangle["rtt_latency_saved_ms"] > 0

    with pytest.raises(ValueError, match="Unknown tool"):
        agent.execute_tool("unsupported", {})


def test_execute_tool_defaults_and_persistence_failure(agent):
    qpu = agent.execute_tool("transpile_qpu_circuit", {})
    qkd = agent.execute_tool("design_qkd_architecture", {})
    defense = agent.execute_tool("simulate_qkd_eavesdropping", {})
    benchmark = agent.execute_tool("benchmark_multivendor_qpu", {})
    grant = agent.execute_tool("claim_token_grant", {})

    assert qpu["qubit_count"] == 8
    assert qkd["distance_km"] == 120.0
    assert defense["nodes_evaluated"] == 500
    assert benchmark["qubits"] == 16
    assert grant["email"] == "developer@triqee.com"

    with pytest.raises(sqlite3.IntegrityError):
        agent.execute_tool(
            "claim_token_grant",
            {"email": "developer@triqee.com", "wallet": "0x9999"},
        )


@pytest.mark.parametrize(
    ("prompt", "expected_tools"),
    [
        ("execute arbitrage pilot", ["calculate_global_triangle_rf", "transpile_qpu_circuit"]),
        (
            "generate compliance dossier",
            ["search_intelligence_breakthroughs", "benchmark_multivendor_qpu", "claim_token_grant"],
        ),
        (
            "simulate qkd interception defense",
            ["simulate_qkd_eavesdropping", "transpile_qpu_circuit"],
        ),
        ("what should we do next", ["calculate_global_triangle_rf", "transpile_qpu_circuit"]),
        ("issue cryptographic state certificate", ["claim_token_grant", "transpile_qpu_circuit"]),
        ("highest and best use", ["calculate_global_triangle_rf", "benchmark_multivendor_qpu"]),
        (
            "deploy all three capabilities",
            ["benchmark_multivendor_qpu", "transpile_qpu_circuit", "search_intelligence_breakthroughs"],
        ),
        (
            "three priority enhancements roadmap",
            ["search_intelligence_breakthroughs", "benchmark_multivendor_qpu"],
        ),
        ("CME triangle QAOA", ["calculate_global_triangle_rf", "transpile_qpu_circuit"]),
        ("execute option 1 and option 2", ["search_intelligence_breakthroughs", "benchmark_multivendor_qpu"]),
        ("optimize self-improvement", ["search_intelligence_breakthroughs", "transpile_qpu_circuit"]),
        ("simulate Eve interception", ["simulate_qkd_eavesdropping", "transpile_qpu_circuit"]),
    ],
)
def test_route_intent_priority_paths(agent, prompt, expected_tools):
    requests = agent.route_intent_and_tools(prompt)
    assert [request["tool_name"] for request in requests] == expected_tools


def test_route_intent_extracts_grant_and_accumulates_general_tools(agent, monkeypatch):
    grant = agent.route_intent_and_tools("claim grant for user@example.com wallet 0xA1b2C3d4")
    assert grant == [
        {
            "tool_name": "claim_token_grant",
            "params": {
                "email": "user@example.com",
                "wallet": "0xA1b2C3d4",
                "tier": "TIER_1_DEVELOPER",
                "amount": 500.0,
            },
        }
    ]

    monkeypatch.setattr("src.si_agent_core.time.time", lambda: 1234)
    default_grant = agent.route_intent_and_tools("claim token grant")
    assert default_grant[0]["params"]["email"] == "dev_1234@triqee.com"
    assert default_grant[0]["params"]["wallet"] == "0x71C...b89A"

    requests = agent.route_intent_and_tools(
        "QKD encryption latency research paper and compile a 200-qubit circuit"
    )
    assert [request["tool_name"] for request in requests] == [
        "design_qkd_architecture",
        "calculate_geodesic_rf",
        "search_intelligence_breakthroughs",
        "transpile_qpu_circuit",
    ]
    assert requests[-1]["params"]["qubits"] == 64

    default_qpu = agent.route_intent_and_tools("transpile a quantum circuit")
    assert default_qpu[-1]["params"]["qubits"] == 8
    assert agent.route_intent_and_tools("ordinary greeting") == []


@pytest.mark.parametrize(
    ("prompt", "expected_text"),
    [
        ("execute arbitrage pilot", "LIVE PILOT INITIALIZED"),
        ("executive morning briefing", "EXECUTIVE MORNING BRIEFING"),
        ("simulate qkd interception defense", "500-NODE QKD"),
        ("next best move", "NEXT BEST MOVE"),
        ("state certificate", "ROOT STATE CERTIFICATE HASH"),
        ("highest and best use", "HIGHEST & BEST USE"),
        ("all three capabilities", "ALL 3 ENGINES COMPILED"),
        ("priority enhancement roadmap", "Strategic Capability Blueprint"),
        ("executive brief whitepaper", "Executive Sovereign Intelligence Brief"),
        ("hello sovereign system", "Execution Summary"),
    ],
)
def test_synthesize_deep_reasoning_paths(agent, monkeypatch, prompt, expected_text):
    monkeypatch.setattr("src.si_agent_core.time.gmtime", lambda: (2026, 1, 2, 3, 4, 5, 0, 2, 0))
    text = agent.synthesize_deep_reasoning(prompt, [], 1.0)
    assert expected_text in text
    if "brief" in prompt or "best" in prompt:
        assert "299,792.458" in text or "Sovereign" in text


@pytest.mark.parametrize(
    ("prompt", "expected_tool", "expected_narrative"),
    [
        ("latency between CME and NY4", "calculate_geodesic_rf", "Physical Geodesic Link Verified"),
        ("latest diamond research paper", "search_intelligence_breakthroughs", "Active Research Grounding"),
        ("compile a 12-qubit circuit", "transpile_qpu_circuit", "QPU DAG Compiled"),
        ("design QKD encryption", "design_qkd_architecture", "Sovereign QKD Protocol"),
        (
            "simulate qkd interception defense",
            "simulate_qkd_eavesdropping",
            "Eavesdropping Defense Simulation",
        ),
        ("claim grant for unique@example.com 0x12345678", "claim_token_grant", "Token Grant Provisioned"),
        ("priority enhancement roadmap", "benchmark_multivendor_qpu", "Multi-Vendor QPU"),
        ("execute arbitrage pilot", "calculate_global_triangle_rf", "Global Financial Geodesic Triangle"),
    ],
)
def test_generate_response_tool_narratives(agent, prompt, expected_tool, expected_narrative):
    response = agent.generate_response(prompt)
    assert response["mode"] == "SOVEREIGN_QUANTUM_EDGE_MODE"
    assert response["telemetry"]["edge_execution"] is True
    assert response["memory_mb"] == 4.2
    assert any(tool["tool_name"] == expected_tool for tool in response["tools_executed"])
    assert expected_narrative in response["response_text"]
    if any(tool["tool_name"] == "transpile_qpu_circuit" for tool in response["tools_executed"]):
        assert response["qpu_artifact"]["qpu_status"] == "READY_FOR_DISPATCH"


def test_generate_response_without_tools_and_classical_mode(agent):
    sovereign = agent.generate_response("ordinary greeting")
    assert sovereign["tools_executed"] == []
    assert "Execution Summary" in sovereign["response_text"]
    assert sovereign["telemetry"]["speedup_factor"] >= 12.5

    classical = agent.generate_response("ordinary greeting", mode="CLASSICAL_CLOUD_MODE")
    assert classical["latency_ms"] == 845.0
    assert classical["tools_executed"] == []
    assert classical["telemetry"]["edge_execution"] is False


@pytest.mark.parametrize(
    "prompt",
    [
        "execute arbitrage pilot",
        "executive morning briefing",
        "next best move",
        "highest and best use",
        "executive brief whitepaper",
    ],
)
def test_triangle_narratives_use_exact_deterministic_result(agent, prompt):
    triangle = agent.execute_tool("calculate_global_triangle_rf", {})
    response = agent.generate_response(prompt)
    expected = f"{triangle['rtt_latency_saved_ms']:.2f} ms"
    assert expected in response["response_text"]
    assert "81.44 ms" not in response["response_text"]
