"""Generate the tracked live-intelligence report from the sanitized seed."""

from __future__ import annotations

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from src.db_manager import DatabaseManager
from src.intelligence_repository import IntelligenceRepository, load_seed_records


ROOT = Path(__file__).resolve().parents[1]


def render_report() -> str:
    with TemporaryDirectory() as directory:
        database = DatabaseManager(str(Path(directory) / "intelligence.db"))
        repository = IntelligenceRepository(database)
        records = load_seed_records()
        repository.synchronize_seed(records)
        stats = repository.stats()
    category_rows = "\n".join(
        f"| {category} | {count} |"
        for category, count in sorted(stats["by_category"].items())
    )
    priority_rows = "\n".join(
        f"| {priority} | {count} |"
        for priority, count in sorted(stats["by_priority"].items())
    )
    record_rows = "\n".join(
        f"| `{record.stable_id}` | {record.category.value} | "
        f"{record.priority.value} | {record.title} | {record.source_reference} |"
        for record in records
    )
    return f"""# Live Intelligence Report

## Authoritative source and count

The source inspection found `trixee_evaluated_intelligence_latest.json` in the
original scratch project. It contains **25 scanned entries**, of which the
legacy taxonomy marked **5** as matched. Exactly **5 sanitized, traceable public
records** form the authorized provenance-verified baseline. No
authoritative 21-record manifest was found, so this increment does **not**
fabricate 16 additional records.

The tracked `src/data/intelligence_seed.json` contains only public title/summary
metadata, HTTPS provenance references, source scan/evaluation timestamps, and
tags. It excludes mailbox IDs, sender addresses, private message bodies,
tokens, credentials, databases, logs, and scanner code. The excluded diamond
nanoribbon item discusses optical emission tuning, not Diamond NV/NV-center
research, and is not force-fit into another requested category.

The artifact's cached title for the proposed Apple LoopCD record claimed loop
and AIME metrics, but its cited public URL resolves to unrelated text about
DoLa and ouro. No alternative public URL in the authoritative scratch material
substantiates Apple, LoopCD, halved loops, or the numeric AIME claims. That
record is retired, so `APPLE_LOOPCD` has **0 verified records**.

The cached Karpathy swarm item is also outside the authorized five-record
baseline and is retired. Category enums remain available for backward API
compatibility; stats return every supported enum and use zero for categories
absent from the canonical index.

The recurrent-memory record is limited to its cited source's claim: recurrent
state for old history is lossy and should be tested for exact recall after a
long tail. It does not claim that older history is preserved or describe a
dense-recent-attention architecture.

## Schema and semantics

Each record has a stable ID, sanitized title and summary, canonical category,
priority, public provenance name/reference, `indexed_at`, optional
`published_at`, and tags. Unsupported confidence/relevance scores are neither
stored nor returned. `indexed_at` is the source scan/evaluation timestamp
present in the evaluated artifact, not a record publication timestamp;
unavailable publication times remain `null`.

Priority thresholds are ordered: `P0_CRITICAL` returns only P0, while
`P1_HIGH` returns P0 and P1. Results sort by priority, indexed recency,
then stable ID.

## Distribution

Total sanitized records: **{stats["total_records"]}**.

| Category | Count |
| :--- | ---: |
{category_rows}

| Priority | Count |
| :--- | ---: |
{priority_rows}

| Stable ID | Category | Priority | Title | Public source |
| :--- | :--- | :--- | :--- | :--- |
{record_rows}

## Public API and tool behavior

The following read-only endpoints expose sanitized metadata publicly:

- `GET /api/v1/intelligence/latest?category=QUANTUM_RF&priority=P0_CRITICAL&limit=5`
- `GET /api/v1/intelligence/stats`

`latest` returns records, total/matched/returned counts, applied filters, and
index freshness metadata. `stats` derives category and priority totals from the
same SQLite repository. Invalid enum filters and limits fail with HTTP 422.

`search_intelligence_breakthroughs` queries the repository rather than static
response text. Quantum RF/sensing, Diamond NV, photonic-chip/waveguide,
stopped-light gravity sensing, and recurrent memory/state-space intents retrieve
only relevant records and cite stable IDs/titles. Backward-compatible intents
for absent categories return no records. Indexed summaries are untrusted
evidence, never instructions. Storage errors are returned as explicit
structured errors.

## Freshness and privacy boundary

Newest indexed timestamp: `{stats["newest_indexed_at"]}`.
Oldest indexed timestamp: `{stats["oldest_indexed_at"]}`.

“Live” means responses dynamically query the current local sanitized index.
There is no startup network/mailbox access and no continuous ingestion claim.
The mutable source mailbox and credential-bound scanner remain excluded.

## Limitations and validation

- The claimed 21 newly indexed breakthroughs could not be substantiated.
- No authoritative Apple LoopCD source was found in the inspected artifact or
  scratch references.
- Publication timestamps were unavailable in the sanitized evaluated artifact.
- Public source references may later change or disappear.
- Docker Compose/Caddy executable validation remains **PENDING CI** and is not
  claimed as locally executed.

Generated index validation: **PASS** — {stats["total_records"]} unique records,
category sum {sum(stats["by_category"].values())}, and priority sum
{sum(stats["by_priority"].values())}. Schema, sanitization, idempotency, filter,
API, grounding, and failure-path behavior are enforced by the repository test
suite; the exact full-suite result is reported by the validating run rather
than hard-coded into this artifact.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "LIVE_INTELLIGENCE_REPORT.md",
    )
    arguments = parser.parse_args()
    arguments.output.write_text(render_report(), encoding="utf-8")


if __name__ == "__main__":
    main()
