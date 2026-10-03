"""Typed deterministic storage and retrieval for sanitized intelligence records."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse

from src.db_manager import DatabaseManager


DEFAULT_SEED_PATH = Path(__file__).resolve().parent / "data" / "intelligence_seed.json"
MAX_QUERY_LIMIT = 100
_UNSAFE_CONTENT = re.compile(r"<\s*/?\s*(?:script|iframe|object|embed)\b|javascript:", re.I)
_SECRET_CONTENT = re.compile(
    r"(?:-----BEGIN [A-Z ]+PRIVATE KEY-----|ghp_[A-Za-z0-9]{20,}|"
    r"AKIA[0-9A-Z]{16}|(?:password|access[_ -]?token|api[_ -]?key)\s*[:=])",
    re.I,
)


class IntelligencePriority(str, Enum):
    P0_CRITICAL = "P0_CRITICAL"
    P1_HIGH = "P1_HIGH"

    @property
    def rank(self) -> int:
        return {self.P0_CRITICAL: 0, self.P1_HIGH: 1}[self]


class IntelligenceCategory(str, Enum):
    QUANTUM_RF = "QUANTUM_RF"
    DIAMOND_NV = "DIAMOND_NV"
    PHOTONIC_CHIPS = "PHOTONIC_CHIPS"
    GRAVITY_SENSING = "GRAVITY_SENSING"
    RECURRENT_MEMORY = "RECURRENT_MEMORY"
    KARPATHY_AGENT_SWARMS = "KARPATHY_AGENT_SWARMS"
    APPLE_LOOPCD = "APPLE_LOOPCD"

    @property
    def label(self) -> str:
        return {
            self.QUANTUM_RF: "Quantum RF",
            self.DIAMOND_NV: "Diamond NV",
            self.PHOTONIC_CHIPS: "Photonic Chips",
            self.GRAVITY_SENSING: "Stopped-Light Gravity Sensing",
            self.RECURRENT_MEMORY: "Recurrent Memory",
            self.KARPATHY_AGENT_SWARMS: "Karpathy Agent Swarms",
            self.APPLE_LOOPCD: "Apple LoopCD",
        }[self]


CATEGORY_PRIORITY = {
    IntelligenceCategory.QUANTUM_RF: IntelligencePriority.P0_CRITICAL,
    IntelligenceCategory.DIAMOND_NV: IntelligencePriority.P0_CRITICAL,
    IntelligenceCategory.PHOTONIC_CHIPS: IntelligencePriority.P1_HIGH,
    IntelligenceCategory.GRAVITY_SENSING: IntelligencePriority.P0_CRITICAL,
    IntelligenceCategory.RECURRENT_MEMORY: IntelligencePriority.P1_HIGH,
    IntelligenceCategory.KARPATHY_AGENT_SWARMS: IntelligencePriority.P1_HIGH,
    IntelligenceCategory.APPLE_LOOPCD: IntelligencePriority.P1_HIGH,
}

RETIRED_SEED_IDS = (
    "INTEL-20261001-QUANTUM-RF",
    "INTEL-20261001-DIAMOND-PARALLEL-GATE",
    "INTEL-20261002-PHOTONIC-CHIPS",
    "INTEL-20261002-DIAMOND-NANORIBBONS",
    "INTEL-20261003-APPLE-LOOPCD",
    "INTEL-20261003-KARPATHY-SWARMS",
)


@dataclass(frozen=True)
class IntelligenceRecord:
    stable_id: str
    title: str
    summary: str
    category: IntelligenceCategory
    priority: IntelligencePriority
    source_name: str
    source_reference: str
    indexed_at: str
    published_at: str | None
    tags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["category"] = self.category.value
        result["category_label"] = self.category.label
        result["priority"] = self.priority.value
        result["tags"] = list(self.tags)
        return result


def _canonical_timestamp(value: str | None, *, required: bool) -> str | None:
    if value is None:
        if required:
            raise ValueError("indexed_at is required")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid ISO-8601 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise ValueError("Intelligence timestamps must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validated_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    normalized = " ".join(value.split())
    if _UNSAFE_CONTENT.search(normalized) or _SECRET_CONTENT.search(normalized):
        raise ValueError(f"{name} contains unsafe or sensitive content")
    return normalized


def validate_record(raw: dict[str, Any]) -> IntelligenceRecord:
    if any(raw.get(name) is not None for name in ("confidence", "relevance")):
        raise ValueError(
            "confidence and relevance require an authoritative methodology and must be null"
        )
    stable_id = _validated_text("stable_id", raw.get("stable_id"))
    if not re.fullmatch(r"INTEL-[A-Z0-9-]{8,}", stable_id):
        raise ValueError("stable_id must use the INTEL- uppercase identifier format")
    source_reference = _validated_text("source_reference", raw.get("source_reference"))
    parsed_reference = urlparse(source_reference)
    if parsed_reference.scheme != "https" or not parsed_reference.netloc:
        raise ValueError("source_reference must be an absolute HTTPS URL")
    tags_raw = raw.get("tags")
    if not isinstance(tags_raw, list) or not tags_raw:
        raise ValueError("tags must be a non-empty list")
    tags = tuple(_validated_text("tag", tag).lower() for tag in tags_raw)
    if len(tags) != len(set(tags)):
        raise ValueError("tags must be unique")

    category = IntelligenceCategory(raw.get("category"))
    priority = IntelligencePriority(raw.get("priority"))
    if CATEGORY_PRIORITY[category] != priority:
        raise ValueError(
            f"{category.value} requires priority {CATEGORY_PRIORITY[category].value}"
        )
    return IntelligenceRecord(
        stable_id=stable_id,
        title=_validated_text("title", raw.get("title")),
        summary=_validated_text("summary", raw.get("summary")),
        category=category,
        priority=priority,
        source_name=_validated_text("source_name", raw.get("source_name")),
        source_reference=source_reference,
        indexed_at=_canonical_timestamp(raw.get("indexed_at"), required=True),
        published_at=_canonical_timestamp(raw.get("published_at"), required=False),
        tags=tags,
    )


def load_seed_records(path: Path = DEFAULT_SEED_PATH) -> tuple[IntelligenceRecord, ...]:
    raw_records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_records, list):
        raise ValueError("Intelligence seed must be a JSON array")
    records = tuple(validate_record(raw) for raw in raw_records)
    identifiers = [record.stable_id for record in records]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Intelligence seed stable IDs must be unique")
    return records


class IntelligenceRepository:
    """SQLite repository for sanitized public intelligence metadata."""

    def __init__(self, database: DatabaseManager):
        self.database = database

    def upsert(self, records: Iterable[IntelligenceRecord]) -> int:
        validated = tuple(records)
        identifiers = [record.stable_id for record in validated]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Upsert batch contains duplicate stable IDs")
        connection = self.database._get_connection()
        try:
            connection.executemany(
                """
                INSERT INTO intelligence_records (
                    stable_id, title, summary, category, priority, source_name,
                    source_reference, indexed_at, published_at, tags_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stable_id) DO UPDATE SET
                    title=excluded.title, summary=excluded.summary,
                    category=excluded.category, priority=excluded.priority,
                    source_name=excluded.source_name,
                    source_reference=excluded.source_reference,
                    indexed_at=excluded.indexed_at,
                    published_at=excluded.published_at,
                    tags_json=excluded.tags_json
                """,
                [
                    (
                        record.stable_id,
                        record.title,
                        record.summary,
                        record.category.value,
                        record.priority.value,
                        record.source_name,
                        record.source_reference,
                        record.indexed_at,
                        record.published_at,
                        json.dumps(record.tags),
                    )
                    for record in validated
                ],
            )
            connection.commit()
        finally:
            connection.close()
        return len(validated)

    def synchronize_seed(
        self,
        records: Iterable[IntelligenceRecord],
        *,
        retired_ids: Sequence[str] = RETIRED_SEED_IDS,
    ) -> int:
        validated = tuple(records)
        identifiers = [record.stable_id for record in validated]
        count = self.upsert(validated)
        connection = self.database._get_connection()
        try:
            managed_rows = connection.execute(
                "SELECT stable_id FROM intelligence_seed_records"
            ).fetchall()
            obsolete = {
                row["stable_id"] for row in managed_rows
            }.union(retired_ids).difference(identifiers)
            if obsolete:
                connection.executemany(
                    "DELETE FROM intelligence_records WHERE stable_id = ?",
                    [(stable_id,) for stable_id in sorted(obsolete)],
                )
            connection.execute("DELETE FROM intelligence_seed_records")
            connection.executemany(
                "INSERT INTO intelligence_seed_records (stable_id) VALUES (?)",
                [(stable_id,) for stable_id in identifiers],
            )
            connection.commit()
        finally:
            connection.close()
        return count

    def query(
        self,
        *,
        categories: Sequence[IntelligenceCategory] | None = None,
        priority_threshold: IntelligencePriority = IntelligencePriority.P1_HIGH,
        limit: int = 20,
    ) -> dict[str, Any]:
        if isinstance(limit, bool) or not 1 <= limit <= MAX_QUERY_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_QUERY_LIMIT}")
        selected_categories = tuple(categories or ())
        if len(selected_categories) != len(set(selected_categories)):
            raise ValueError("category filters must be unique")
        allowed_priorities = [
            priority.value
            for priority in IntelligencePriority
            if priority.rank <= priority_threshold.rank
        ]
        where = [f"priority IN ({','.join('?' for _ in allowed_priorities)})"]
        parameters: list[Any] = list(allowed_priorities)
        if selected_categories:
            where.append(f"category IN ({','.join('?' for _ in selected_categories)})")
            parameters.extend(category.value for category in selected_categories)
        where_sql = " AND ".join(where)
        connection = self.database._get_connection()
        try:
            total = connection.execute("SELECT COUNT(*) FROM intelligence_records").fetchone()[0]
            matched = connection.execute(
                f"SELECT COUNT(*) FROM intelligence_records WHERE {where_sql}",
                parameters,
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT * FROM intelligence_records WHERE {where_sql}
                ORDER BY CASE priority WHEN 'P0_CRITICAL' THEN 0 ELSE 1 END,
                         indexed_at DESC, stable_id ASC
                LIMIT ?
                """,
                [*parameters, limit],
            ).fetchall()
        finally:
            connection.close()
        return {
            "records": [self._row_to_dict(row) for row in rows],
            "total_count": total,
            "matched_count": matched,
            "returned_count": len(rows),
            "applied_filters": {
                "categories": [category.value for category in selected_categories],
                "priority_threshold": priority_threshold.value,
                "limit": limit,
            },
            "index": self.index_metadata(),
        }

    def index_metadata(self) -> dict[str, Any]:
        connection = self.database._get_connection()
        try:
            row = connection.execute(
                "SELECT MIN(indexed_at), MAX(indexed_at), COUNT(*) FROM intelligence_records"
            ).fetchone()
        finally:
            connection.close()
        newest = row[1]
        age_hours = None
        if newest:
            latest = datetime.fromisoformat(newest.replace("Z", "+00:00"))
            age_hours = max(
                0.0,
                (datetime.now(timezone.utc) - latest).total_seconds() / 3600.0,
            )
        return {
            "record_count": row[2],
            "oldest_indexed_at": row[0],
            "newest_indexed_at": newest,
            "freshness_age_hours": round(age_hours, 3) if age_hours is not None else None,
            "freshness_semantics": "Elapsed hours since the newest indexed_at timestamp; no continuous mailbox ingestion is implied.",
            "indexed_at_semantics": "Source scan/evaluation timestamp from the authoritative evaluated artifact, not a publication timestamp.",
        }

    def stats(self) -> dict[str, Any]:
        connection = self.database._get_connection()
        try:
            total = connection.execute("SELECT COUNT(*) FROM intelligence_records").fetchone()[0]
            by_priority = {
                row[0]: row[1]
                for row in connection.execute(
                    "SELECT priority, COUNT(*) FROM intelligence_records GROUP BY priority ORDER BY priority"
                )
            }
            stored_categories = {
                row[0]: row[1]
                for row in connection.execute(
                    "SELECT category, COUNT(*) FROM intelligence_records GROUP BY category ORDER BY category"
                )
            }
            by_category = {
                category.value: stored_categories.get(category.value, 0)
                for category in IntelligenceCategory
            }
        finally:
            connection.close()
        metadata = self.index_metadata()
        return {
            "total_records": total,
            "by_priority": by_priority,
            "by_category": by_category,
            "category_count_semantics": "All supported category enum values are returned; categories absent from the index have count zero.",
            **metadata,
        }

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any]:
        category = IntelligenceCategory(row["category"])
        return {
            "stable_id": row["stable_id"],
            "title": row["title"],
            "summary": row["summary"],
            "category": category.value,
            "category_label": category.label,
            "priority": row["priority"],
            "source_name": row["source_name"],
            "source_reference": row["source_reference"],
            "indexed_at": row["indexed_at"],
            "published_at": row["published_at"],
            "tags": json.loads(row["tags_json"]),
        }
