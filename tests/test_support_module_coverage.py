import json
import runpy
import sqlite3

import pytest
from fastapi import HTTPException

import src.api_server as api
import src.arxiv_patent_pipeline as arxiv
import src.edge_engine as edge
import src.triqee_fourthstate_quantum_rf_arbitrage_engine as fourth_state
import src.triqee_social_comment_and_inbox_sentinel as social
from src.db_manager import DatabaseManager
from src.headline_taxonomy import evaluate_headline_relevance


def test_api_validation_and_registration_error_paths(monkeypatch):
    distance_request = api.DistanceRequest(lat1=0, lon1=0, lat2=1, lon2=1)
    latency_request = api.LatencyRequest(distance_km=10)

    monkeypatch.setattr(api, "haversine_distance", lambda *args: (_ for _ in ()).throw(ValueError("bad coordinates")))
    with pytest.raises(HTTPException) as exc:
        api.compute_distance(distance_request)
    assert exc.value.status_code == 400
    assert exc.value.detail == "bad coordinates"

    monkeypatch.setattr(
        api,
        "calculate_propagation_latencies",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("bad latency")),
    )
    with pytest.raises(HTTPException) as exc:
        api.compute_latencies(latency_request)
    assert exc.value.status_code == 400
    assert exc.value.detail == "bad latency"

    request = api.LeadRegistrationRequest(
        tier="tier1",
        email="lead@example.com",
        identifier="lead",
        allocated_tq=500,
    )
    monkeypatch.setattr(api.db, "record_lead", lambda **kwargs: 41)
    assert api.register_lead(request)["lead_id"] == 41

    monkeypatch.setattr(
        api.db,
        "record_lead",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("invalid lead")),
    )
    with pytest.raises(HTTPException) as exc:
        api.register_lead(request)
    assert exc.value.status_code == 400
    assert exc.value.detail == "invalid lead"

    monkeypatch.setattr(
        api.db,
        "record_lead",
        lambda **kwargs: (_ for _ in ()).throw(sqlite3.IntegrityError("duplicate")),
    )
    with pytest.raises(HTTPException) as exc:
        api.register_lead(request)
    assert exc.value.status_code == 409


@pytest.mark.parametrize(
    ("identifier", "firm_name", "message", "expected_identifier", "expected_category"),
    [
        ("named-contact", "Firm A", "Need a hedge fund alpha model", "named-contact", "QUANT_INQUIRY"),
        ("", "Firm B", "", "Firm B", "ENTERPRISE_INQUIRY"),
        ("", "", "", "fallback", "ENTERPRISE_INQUIRY"),
    ],
)
def test_api_capture_identifier_and_category_paths(
    monkeypatch,
    identifier,
    firm_name,
    message,
    expected_identifier,
    expected_category,
):
    captured = {}

    def record_lead(**kwargs):
        captured.update(kwargs)
        return 7

    monkeypatch.setattr(api.db, "record_lead", record_lead)
    request = api.CRMLeadCaptureRequest(
        email="fallback@example.com",
        identifier=identifier,
        firm_name=firm_name,
        message=message,
    )
    result = api.capture_institutional_lead(request)
    assert captured["identifier"] == expected_identifier
    assert result["category_tag"] == expected_category
    assert result["statutory_reference"] == "Wyoming W.S. § 34-29-106"
    assert result["merkle_receipt"].startswith("0x")


def test_api_capture_and_si_failures(monkeypatch):
    request = api.CRMLeadCaptureRequest(email="lead@example.com")

    monkeypatch.setattr(
        api.db,
        "record_lead",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("invalid capture")),
    )
    with pytest.raises(HTTPException) as exc:
        api.capture_institutional_lead(request)
    assert exc.value.status_code == 400

    monkeypatch.setattr(
        api.db,
        "record_lead",
        lambda **kwargs: (_ for _ in ()).throw(sqlite3.IntegrityError("duplicate")),
    )
    with pytest.raises(HTTPException) as exc:
        api.capture_institutional_lead(request)
    assert exc.value.status_code == 409
    assert "duplicate" in exc.value.detail

    monkeypatch.setattr(
        api.si_agent,
        "generate_response",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("engine offline")),
    )
    with pytest.raises(HTTPException) as exc:
        api.sovereign_si_chat_endpoint(api.SIChatRequest(prompt="hello"))
    assert exc.value.status_code == 500
    assert "engine offline" in exc.value.detail


def test_api_admin_authentication_and_cors_configuration(monkeypatch):
    from fastapi.testclient import TestClient
    from fastapi.middleware.cors import CORSMiddleware

    client = TestClient(api.app)
    monkeypatch.delenv("TRIQEE_ADMIN_KEY", raising=False)
    assert client.get("/api/v1/crm/export/json").status_code == 503

    monkeypatch.setenv("TRIQEE_ADMIN_KEY", "operator-secret")
    assert client.get("/api/v1/crm/export/json").status_code == 401
    assert client.get(
        "/api/v1/crm/export/json",
        headers={"X-Admin-Key": "wrong-secret"},
    ).status_code == 403
    response = client.get(
        "/api/v1/crm/export/json",
        headers={"X-Admin-Key": "operator-secret"},
    )
    assert response.status_code == 200
    assert response.json()["total_count"] >= 0

    compared = {}

    def compare_digest(provided, configured):
        compared["values"] = (provided, configured)
        return True

    monkeypatch.setattr(api.hmac, "compare_digest", compare_digest)
    api.require_admin_key("presented")
    assert compared["values"] == ("presented", "operator-secret")

    cors_middleware = next(
        middleware
        for middleware in api.app.user_middleware
        if middleware.cls is CORSMiddleware
    )
    assert cors_middleware.kwargs["allow_origins"] == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    assert cors_middleware.kwargs["allow_credentials"] is False
    assert "*" not in cors_middleware.kwargs["allow_headers"]


def test_api_database_path_and_cors_parsing(tmp_path, monkeypatch):
    monkeypatch.delenv("TRIQEE_DB_PATH", raising=False)
    assert api.resolve_database_path() == str(api.DEFAULT_DB_PATH)
    assert api.resolve_database_path(str(tmp_path / "absolute.db")) == str(
        (tmp_path / "absolute.db").resolve()
    )
    assert api.resolve_database_path("data/relative.db") == str(
        (api.PROJECT_ROOT / "data/relative.db").resolve()
    )
    with pytest.raises(ValueError, match="filesystem path"):
        api.resolve_database_path("sqlite:////app/data/operational.db")

    assert api.parse_cors_origins("") == list(api.DEFAULT_CORS_ORIGINS)
    assert api.parse_cors_origins(
        "https://cockpit.example/, http://localhost:3000"
    ) == ["https://cockpit.example", "http://localhost:3000"]
    with pytest.raises(ValueError, match="wildcard"):
        api.parse_cors_origins("*")
    with pytest.raises(ValueError, match="http"):
        api.parse_cors_origins("file://local")


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.payload


ATOM_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1234.5678</id>
    <title>  Diamond   NV center  </title>
    <summary> Room temperature quantum hardware. </summary>
    <published>2026-01-01T00:00:00Z</published>
    <link title="pdf" href="http://arxiv.org/pdf/1234.5678"/>
  </entry>
  <entry><id>http://arxiv.org/abs/9999.0001</id></entry>
  <entry><title>Untethered title</title></entry>
</feed>
"""


def test_arxiv_fetch_parse_and_network_failure(tmp_path, monkeypatch):
    pipeline = arxiv.ArxivPatentIntelligencePipeline(DatabaseManager(str(tmp_path / "arxiv.db")))
    seen = {}

    def urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return _Response(ATOM_FEED)

    monkeypatch.setattr(arxiv.urllib.request, "urlopen", urlopen)
    papers = pipeline.fetch_arxiv_papers(query="diamond nv", max_results=3)
    assert seen["timeout"] == 12
    assert "max_results=3" in seen["url"]
    assert papers[0]["title"] == "Diamond NV center"
    assert papers[0]["pdf_url"].endswith("1234.5678")
    assert papers[1]["title"] == "Untitled"
    assert papers[1]["pdf_url"] == "http://arxiv.org/pdf/9999.0001"
    assert papers[2]["external_id"] == ""
    assert papers[2]["pdf_url"] == ""

    monkeypatch.setattr(
        arxiv.urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("timed out")),
    )
    assert pipeline.fetch_arxiv_papers() == []


def test_arxiv_evaluation_inbox_and_pipeline(tmp_path, monkeypatch):
    db = DatabaseManager(str(tmp_path / "intelligence.db"))
    pipeline = arxiv.ArxivPatentIntelligencePipeline(db)
    items = [
        {
            "source": "arXiv",
            "external_id": "match-1",
            "title": "Room temperature diamond NV center",
            "summary": "Photonic chip waveguide",
            "url": "https://example.test/match",
        },
        {"external_id": "skip-1", "title": "Unrelated botany", "summary": "Plant growth"},
    ]
    indexed = pipeline.evaluate_and_index_entries(items)
    assert len(indexed) == 1
    assert indexed[0]["priority"] == "P0_CRITICAL"
    assert indexed[0]["matched_keywords"]

    monkeypatch.setattr(
        arxiv,
        "evaluate_headline_relevance",
        lambda text: {"matched": True, "categories": []},
    )
    fallback = pipeline.evaluate_and_index_entries(
        [{"external_id": "fallback", "title": "Fallback item", "source": "Inbox"}]
    )
    assert fallback[0]["primary_category"] == "GENERAL_QUANTUM"
    assert fallback[0]["priority"] == "P2_MEDIUM"

    assert pipeline.ingest_inbox_scan_file(str(tmp_path / "missing.json")) == []
    inbox_path = tmp_path / "inbox.json"
    inbox_path.write_text(
        json.dumps(
            [
                {
                    "index": 1,
                    "date": "2026-01-01",
                    "resolved_title": "",
                    "subject": "SQUID quantum RF sensing",
                    "final_url": "https://example.test/rf",
                    "evaluation": {"matched": True},
                },
                {"index": 2, "date": "2026-01-02", "evaluation": {"matched": False}},
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        arxiv,
        "evaluate_headline_relevance",
        lambda text: {
            "matched": True,
            "categories": [
                {
                    "category_key": "QUANTUM_RF_SENSING",
                    "priority": "P0_CRITICAL",
                    "matched_keywords": ["squid"],
                }
            ],
        },
    )
    assert pipeline.ingest_inbox_scan_file(str(inbox_path))[0]["title"] == "SQUID quantum RF sensing"

    monkeypatch.setattr(pipeline, "ingest_inbox_scan_file", lambda path: [{"id": 1}])
    monkeypatch.setattr(pipeline, "fetch_arxiv_papers", lambda max_results: [{"title": "paper"}])
    monkeypatch.setattr(pipeline, "evaluate_and_index_entries", lambda entries: [{"id": 2}])
    result = pipeline.run_full_pipeline()
    assert result["inbox_items_indexed"] == 1
    assert result["arxiv_items_indexed"] == 1
    assert result["total_indexed_session"] == 2


def test_arxiv_command_line_entrypoint(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TRIQEE_DB_PATH", str(tmp_path / "cli.db"))
    monkeypatch.setenv("TRIQEE_INTELLIGENCE_JSON", str(tmp_path / "missing.json"))
    monkeypatch.setattr(arxiv.urllib.request, "urlopen", lambda *args, **kwargs: _Response(b'<feed xmlns="http://www.w3.org/2005/Atom"/>'))
    runpy.run_path(arxiv.__file__, run_name="__main__")
    output = capsys.readouterr().out
    assert "Full Intelligence Pipeline Ingestion Complete" in output
    assert '"total_indexed_session": 0' in output


def test_database_priority_filter_and_empty_taxonomy(tmp_path):
    db = DatabaseManager(str(tmp_path / "filter.db"))
    db.record_intelligence_article(
        source="arXiv",
        external_id="p0",
        title="Critical",
        primary_category="EDGE_QUANTUM_HARDWARE",
        priority="P0_CRITICAL",
    )
    db.record_intelligence_article(
        source="arXiv",
        external_id="p1",
        title="High",
        primary_category="EDGE_AI_AND_KERNEL_OPTIMIZATION",
        priority="P1_HIGH",
    )
    rows = db.get_latest_intelligence_articles(min_priority="P1_HIGH")
    assert [row["external_id"] for row in rows] == ["p1"]
    assert evaluate_headline_relevance("") == {"matched": False, "categories": []}


def test_edge_benchmark_and_command_line(monkeypatch, capsys):
    engine = edge.TriqeeEdgeEngine(node_id="test-node")
    benchmark = engine.benchmark_full_hybrid_cycle()
    assert benchmark["triqee_edge_total_ms"] < benchmark["classical_cloud_roundtrip_ms"]
    assert benchmark["latency_reduction_factor"] > 1
    assert benchmark["qpu_transpile_job"].startswith("qjob_edge_")
    with pytest.raises(ValueError, match="between 1 and 127"):
        engine.compile_qpu_transpilation_job(qubit_count=0)
    with pytest.raises(ValueError, match="between 1 and 127"):
        engine.compile_qpu_transpilation_job(qubit_count=128)

    runpy.run_path(edge.__file__, run_name="__main__")
    assert "TRIQEE EDGE ENGINE BENCHMARK SUMMARY" in capsys.readouterr().out


def test_fourth_state_simulation_success_miss_and_cli(tmp_path, monkeypatch, capsys):
    engine = fourth_state.FourthStateQuantumRFEngine()
    result_path = tmp_path / "result.json"
    monkeypatch.setenv("TRIQEE_RF_RESULTS_PATH", str(result_path))
    monkeypatch.setattr(fourth_state.random, "gauss", lambda mean, sigma: 10.0)
    monkeypatch.setattr(fourth_state.random, "random", lambda: 0.0)
    monkeypatch.setattr(fourth_state.random, "randint", lambda low, high: 20)
    won = engine.simulate_quantum_rf_arbitrage(num_bursts=2)
    assert won["signals_detected"] == 1
    assert won["squid_speed_wins"] == 1
    assert won["total_simulated_pnl_usd"] > 0
    assert json.loads(result_path.read_text(encoding="utf-8"))["simulation_bursts"] == 2

    monkeypatch.setattr(fourth_state.random, "random", lambda: 1.0)
    missed = engine.simulate_quantum_rf_arbitrage(num_bursts=1)
    assert missed["signals_detected"] == 1
    assert missed["squid_speed_wins"] == 0

    monkeypatch.setattr(fourth_state.random, "gauss", lambda mean, sigma: 0.0)
    no_signal = engine.simulate_quantum_rf_arbitrage(num_bursts=1)
    assert no_signal["signals_detected"] == 0
    assert no_signal["win_rate_percent"] == 0.0

    runpy.run_path(fourth_state.__file__, run_name="__main__")
    output = capsys.readouterr().out
    assert "QUANTUM RF SENSING" in output
    assert "10,000 BURST SIMULATION RESULTS" in output


def test_social_sentinel_storage_and_command_line(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "social.db"
    monkeypatch.setattr(social, "DB_PATH", str(db_path))
    result = social.triage_inbound_message("@user", "hello", platform="Web")
    assert result["category"] == "DEV_INQUIRY"
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM social_triage_log").fetchone()[0] == 1

    cli_db = tmp_path / "social-cli.db"
    monkeypatch.setenv("TRIQEE_DB_PATH", str(cli_db))
    runpy.run_path(social.__file__, run_name="__main__")
    output = capsys.readouterr().out
    assert "SENTINEL INITIALIZED" in output
    assert "QUANT_INQUIRY" in output


def test_si_agent_command_line_entrypoint(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TRIQEE_DB_PATH", str(tmp_path / "si-cli.db"))
    runpy.run_path("src/si_agent_core.py", run_name="__main__")
    output = capsys.readouterr().out
    assert '"mode": "SOVEREIGN_QUANTUM_EDGE_MODE"' in output
    assert '"qpu_status": "READY_FOR_DISPATCH"' in output
