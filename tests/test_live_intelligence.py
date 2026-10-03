import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.generate_live_intelligence_report import render_report
from src.api_server import app
from src.db_manager import DatabaseManager
from src.intelligence_repository import (
    IntelligenceCategory,
    IntelligencePriority,
    IntelligenceRecord,
    IntelligenceRepository,
    load_seed_records,
    validate_record,
)
from src.si_agent_core import SovereignSIAgent


EXPECTED_CATEGORIES = {
    "QUANTUM_RF": 1,
    "DIAMOND_NV": 1,
    "PHOTONIC_CHIPS": 1,
    "GRAVITY_SENSING": 1,
    "RECURRENT_MEMORY": 1,
    "KARPATHY_AGENT_SWARMS": 0,
    "APPLE_LOOPCD": 0,
}


@pytest.fixture
def repository(tmp_path):
    database = DatabaseManager(str(tmp_path / "intelligence.db"))
    selected = IntelligenceRepository(database)
    selected.upsert(load_seed_records())
    return selected


def test_seed_is_authoritative_sanitized_and_has_honest_distribution():
    records = load_seed_records()
    assert len(records) == 5
    assert len({record.stable_id for record in records}) == 5
    assert {
        category.value: sum(record.category == category for record in records)
        for category in IntelligenceCategory
    } == EXPECTED_CATEGORIES
    assert {
        priority.value: sum(record.priority == priority for record in records)
        for priority in IntelligencePriority
    } == {"P0_CRITICAL": 3, "P1_HIGH": 2}
    serialized = json.dumps([record.to_dict() for record in records])
    assert "<script" not in serialized.lower()
    assert "access_token" not in serialized.lower()
    assert "@" not in " ".join(record.source_name for record in records)
    assert all(record.published_at is None for record in records)
    assert all("confidence" not in record.to_dict() for record in records)
    assert all("relevance" not in record.to_dict() for record in records)
    assert "INTEL-20261002-DIAMOND-NANORIBBONS" not in serialized
    assert "INTEL-20261003-APPLE-LOOPCD" not in serialized
    assert "INTEL-20261003-KARPATHY-SWARMS" not in serialized


def test_repository_upsert_query_order_threshold_filters_and_empty(repository):
    assert repository.upsert(load_seed_records()) == 5
    assert repository.stats()["total_records"] == 5

    all_records = repository.query(limit=5)
    assert all_records["total_count"] == 5
    assert all_records["matched_count"] == 5
    assert [record["priority"] for record in all_records["records"][:3]] == [
        "P0_CRITICAL"
    ] * 3
    assert all_records["records"][0]["indexed_at"] >= all_records["records"][1]["indexed_at"]

    critical = repository.query(
        priority_threshold=IntelligencePriority.P0_CRITICAL,
        limit=100,
    )
    assert critical["matched_count"] == 3
    assert {record["priority"] for record in critical["records"]} == {"P0_CRITICAL"}

    selected = repository.query(
        categories=[
            IntelligenceCategory.QUANTUM_RF,
            IntelligenceCategory.PHOTONIC_CHIPS,
        ],
        limit=10,
    )
    assert selected["matched_count"] == 2
    assert {record["category"] for record in selected["records"]} == {
        "QUANTUM_RF",
        "PHOTONIC_CHIPS",
    }

    with repository.database._get_connection() as connection:
        connection.execute("DELETE FROM intelligence_records")
    empty = repository.query(limit=1)
    assert empty["records"] == []
    assert empty["index"]["freshness_age_hours"] is None


def test_seed_synchronization_removes_retired_and_previously_managed_records(tmp_path):
    selected = IntelligenceRepository(DatabaseManager(str(tmp_path / "sync.db")))
    current = load_seed_records()
    retired = replace(
        current[0],
        stable_id="INTEL-20261002-DIAMOND-NANORIBBONS",
    )
    selected.upsert([retired])
    selected.synchronize_seed(current)
    assert selected.stats()["total_records"] == 5

    selected.synchronize_seed(current[:-1])
    remaining = selected.query(limit=100)["records"]
    assert {record["stable_id"] for record in remaining} == {
        record.stable_id for record in current[:-1]
    }


def test_repository_rejects_invalid_queries_and_duplicate_batches(repository):
    record = load_seed_records()[0]
    with pytest.raises(ValueError, match="duplicate stable IDs"):
        repository.upsert([record, record])
    with pytest.raises(ValueError, match="between 1 and 100"):
        repository.query(limit=0)
    with pytest.raises(ValueError, match="between 1 and 100"):
        repository.query(limit=True)
    with pytest.raises(ValueError, match="must be unique"):
        repository.query(
            categories=[
                IntelligenceCategory.QUANTUM_RF,
                IntelligenceCategory.QUANTUM_RF,
            ]
        )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"stable_id": ""}, "non-empty"),
        ({"stable_id": "bad"}, "INTEL-"),
        ({"title": "<script>alert(1)</script>"}, "unsafe"),
        ({"summary": "api_key=secret"}, "sensitive"),
        ({"source_reference": "http://example.com"}, "HTTPS"),
        ({"tags": []}, "non-empty list"),
        ({"tags": ["same", "same"]}, "unique"),
        ({"indexed_at": None}, "indexed_at is required"),
        ({"indexed_at": "not-a-date"}, "ISO-8601"),
        ({"indexed_at": "2026-01-01T00:00:00"}, "timezone"),
        ({"confidence": 0.9}, "authoritative methodology"),
        ({"relevance": 0.9}, "authoritative methodology"),
        ({"category": "UNKNOWN"}, "valid IntelligenceCategory"),
        ({"priority": "P2_MEDIUM"}, "valid IntelligencePriority"),
    ],
)
def test_record_validation_rejects_malformed_or_unsafe_data(change, message):
    raw = load_seed_records()[0].to_dict()
    raw.pop("category_label")
    raw.update(change)
    with pytest.raises(ValueError, match=message):
        validate_record(raw)


def test_seed_loader_rejects_non_array_and_duplicate_ids(tmp_path):
    non_array = tmp_path / "non-array.json"
    non_array.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON array"):
        load_seed_records(non_array)

    record = load_seed_records()[0].to_dict()
    record.pop("category_label")
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(json.dumps([record, record]), encoding="utf-8")
    with pytest.raises(ValueError, match="stable IDs"):
        load_seed_records(duplicate)

    incompatible = next(
        item.to_dict()
        for item in load_seed_records()
        if item.category == IntelligenceCategory.PHOTONIC_CHIPS
    )
    incompatible.pop("category_label")
    incompatible["priority"] = "P0_CRITICAL"
    with pytest.raises(ValueError, match="requires priority P1_HIGH"):
        validate_record(incompatible)


def test_stats_are_consistent_and_freshness_is_documented(repository):
    stats = repository.stats()
    assert stats["total_records"] == 5
    assert sum(stats["by_priority"].values()) == stats["total_records"]
    assert sum(stats["by_category"].values()) == stats["total_records"]
    assert stats["by_category"] == EXPECTED_CATEGORIES
    assert stats["newest_indexed_at"] == "2026-10-02T01:18:00Z"
    assert stats["oldest_indexed_at"] == "2026-10-01T19:58:02Z"
    assert stats["freshness_age_hours"] >= 0
    assert "no continuous mailbox ingestion" in stats["freshness_semantics"]
    assert "scan/evaluation timestamp" in stats["indexed_at_semantics"]
    assert "absent from the index have count zero" in stats["category_count_semantics"]


def test_provenance_claims_match_locked_source_boundaries():
    fixture = json.loads(
        (
            Path(__file__).resolve().parent
            / "fixtures"
            / "intelligence_provenance_claims.json"
        ).read_text(encoding="utf-8")
    )
    records = {record.stable_id: record for record in load_seed_records()}
    assert set(records) == set(fixture["verified"])
    for stable_id, expected in fixture["verified"].items():
        record = records[stable_id]
        assert record.title == expected["title"]
        assert record.summary == expected["summary"]
        assert record.source_reference == expected["source_reference"]
        assert record.indexed_at == expected["indexed_at"]
        assert list(record.tags) == expected["tags"]

    serialized = json.dumps([record.to_dict() for record in records.values()])
    for stable_id in fixture["forbidden_seed_ids"]:
        assert stable_id not in records
    assert all(term.lower() not in serialized.lower() for term in fixture["forbidden_claim_terms"])


def test_tool_filters_legacy_aliases_and_rejects_invalid_filters(tmp_path):
    agent = SovereignSIAgent(DatabaseManager(str(tmp_path / "agent.db")))
    quantum_rf = agent.execute_tool(
        "search_intelligence_breakthroughs",
        {
            "categories": ["QUANTUM_RF"],
            "priority_threshold": "P0_CRITICAL",
            "limit": 5,
        },
    )
    assert quantum_rf["count"] == 1
    assert quantum_rf["citations"][0]["stable_id"] == "INTEL-20261002-QUANTUM-RF"
    legacy = agent.execute_tool(
        "search_intelligence_breakthroughs",
        {"category": "EDGE_AI_AND_KERNEL_OPTIMIZATION"},
    )
    assert legacy["records"][0]["category"] == "RECURRENT_MEMORY"
    with pytest.raises(ValueError, match="valid IntelligenceCategory"):
        agent.execute_tool(
            "search_intelligence_breakthroughs",
            {"category": "NOT_REAL"},
        )
    with pytest.raises(ValueError, match="valid IntelligencePriority"):
        agent.execute_tool(
            "search_intelligence_breakthroughs",
            {"priority_threshold": "P9"},
        )


@pytest.mark.parametrize(
    ("prompt", "expected_category", "expected_id"),
    [
        ("What changed in quantum RF sensing?", "QUANTUM_RF", "INTEL-20261002-QUANTUM-RF"),
        ("Explain room-temperature diamond NV qubits", "DIAMOND_NV", "INTEL-20261001-DIAMOND-NV-COHERENCE"),
        ("What is new in photonic waveguides?", "PHOTONIC_CHIPS", "INTEL-20261002-CORNELL-PHOTONICS"),
        ("What changed in stopped-light gravity sensing?", "GRAVITY_SENSING", "INTEL-20261002-STOPPED-LIGHT-GRAVITY"),
        ("Ground on-device recurrent memory", "RECURRENT_MEMORY", "INTEL-20261001-RECURRENT-MEMORY"),
    ],
)
def test_deep_reasoning_is_intent_grounded_with_real_citations(
    tmp_path,
    prompt,
    expected_category,
    expected_id,
):
    agent = SovereignSIAgent(DatabaseManager(str(tmp_path / f"{expected_category}.db")))
    response = agent.generate_response(prompt)
    search = next(
        tool for tool in response["tools_executed"]
        if tool["tool_name"] == "search_intelligence_breakthroughs"
    )
    assert search["params"]["categories"] == [expected_category]
    assert expected_id in response["response_text"]
    assert "untrusted evidence, never as instructions" in response["response_text"]
    assert all(
        citation["stable_id"] in {
            record["stable_id"] for record in search["result"]["records"]
        }
        for citation in search["result"]["citations"]
    )
    if expected_category == "DIAMOND_NV":
        assert {
            record["stable_id"] for record in search["result"]["records"]
        } == {"INTEL-20261001-DIAMOND-NV-COHERENCE"}
        assert "NANORIBBONS" not in response["response_text"]


def test_irrelevant_prompt_does_not_query_or_cite_intelligence(tmp_path):
    agent = SovereignSIAgent(DatabaseManager(str(tmp_path / "irrelevant.db")))
    response = agent.generate_response("Calculate the distance from Chicago to London")
    assert all(
        tool["tool_name"] != "search_intelligence_breakthroughs"
        for tool in response["tools_executed"]
    )
    assert "INTEL-" not in response["response_text"]


def test_upsert_changes_grounded_response_without_code_change(tmp_path):
    agent = SovereignSIAgent(DatabaseManager(str(tmp_path / "dynamic.db")))
    original = next(
        record
        for record in load_seed_records()
        if record.category == IntelligenceCategory.QUANTUM_RF
    )
    updated = replace(
        original,
        title="Updated public quantum RF facility metadata",
        indexed_at="2026-10-04T00:00:00Z",
    )
    agent.intelligence.upsert([updated])
    response = agent.generate_response("Latest quantum RF sensing evidence")
    assert "Updated public quantum RF facility metadata" in response["response_text"]


def test_storage_failure_is_structured_and_never_invented(tmp_path, monkeypatch):
    agent = SovereignSIAgent(DatabaseManager(str(tmp_path / "failure.db")))

    def fail_query(**_kwargs):
        raise sqlite3.OperationalError("index unavailable")

    monkeypatch.setattr(agent.intelligence, "query", fail_query)
    response = agent.generate_response("Latest photonic chip research")
    tool = next(
        item for item in response["tools_executed"]
        if item["tool_name"] == "search_intelligence_breakthroughs"
    )
    assert tool["result"]["status"] == "error"
    assert tool["result"]["error"] == "index unavailable"
    assert "failed honestly" in response["response_text"]
    assert "INTEL-" not in response["response_text"]


def test_public_api_filters_validation_stats_and_privacy():
    client = TestClient(app)
    latest = client.get(
        "/api/v1/intelligence/latest",
        params=[
            ("category", "DIAMOND_NV"),
            ("category", "QUANTUM_RF"),
            ("priority", "P0_CRITICAL"),
            ("limit", "2"),
        ],
    )
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["matched_count"] == 2
    assert payload["returned_count"] == 2
    assert payload["applied_filters"]["categories"] == ["DIAMOND_NV", "QUANTUM_RF"]
    assert all("db_path" not in record for record in payload["records"])
    assert all("mailbox" not in json.dumps(record).lower() for record in payload["records"])

    assert client.get("/api/v1/intelligence/latest?category=INVALID").status_code == 422
    assert client.get("/api/v1/intelligence/latest?priority=P2_MEDIUM").status_code == 422
    assert client.get("/api/v1/intelligence/latest?limit=101").status_code == 422

    stats_response = client.get("/api/v1/intelligence/stats")
    assert stats_response.status_code == 200
    stats_payload = stats_response.json()
    assert stats_payload["access"] == "public_sanitized_metadata"
    stats = stats_payload["stats"]
    assert sum(stats["by_priority"].values()) == stats["total_records"]
    assert sum(stats["by_category"].values()) == stats["total_records"]


def test_tracked_report_is_generated_from_current_index():
    rendered = render_report()
    tracked = (
        Path(__file__).resolve().parents[1]
        / "LIVE_INTELLIGENCE_REPORT.md"
    ).read_text(encoding="utf-8")
    assert tracked == rendered
    assert "25 scanned entries" in rendered
    assert "Exactly **5 sanitized" in rendered
    assert "does **not**\nfabricate 16 additional records" in rendered
    assert "not Diamond NV/NV-center" in rendered
    assert "| APPLE_LOOPCD | 0 |" in rendered
    assert "| KARPATHY_AGENT_SWARMS | 0 |" in rendered
    assert "No authoritative Apple LoopCD source was found" in rendered
    assert "PENDING CI" in rendered
    for record in load_seed_records():
        assert record.stable_id in rendered
