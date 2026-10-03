"""
Triqee SQLite Database Management Module
=========================================
Encapsulates connection lifecycle, schema initialization,
parameterized queries, and transaction management.
"""

import sqlite3
import os
import json
from typing import List, Dict, Any, Optional, Tuple


def _neutralize_csv_cell(value: Any) -> str:
    """Prevent spreadsheet formula execution while preserving cell text."""
    if value is None:
        return ""
    text = str(value)
    stripped = text.lstrip()
    if stripped.startswith(("=", "+", "-", "@")):
        leading_whitespace = text[: len(text) - len(stripped)]
        return f"{leading_whitespace}'{stripped}"
    return text


class DatabaseManager:
    """Manages SQLite database connections and table operations."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Ensures all necessary operational tables exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS airdrop_leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tier TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    identifier TEXT NOT NULL,
                    firm_name TEXT,
                    deployment_scale TEXT,
                    category_tag TEXT,
                    notes TEXT,
                    wallet_address TEXT,
                    allocated_tq REAL NOT NULL,
                    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'PROVISIONED'
                )
            """)
            # Ensure new columns exist for existing databases
            for col, col_type in [
                ("firm_name", "TEXT"),
                ("deployment_scale", "TEXT"),
                ("category_tag", "TEXT"),
                ("notes", "TEXT")
            ]:
                try:
                    cursor.execute(f"ALTER TABLE airdrop_leads ADD COLUMN {col} {col_type}")
                except sqlite3.OperationalError:
                    pass  # Column already exists

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS radar_event_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS triage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_handle TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    category TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    suggested_response TEXT NOT NULL,
                    created_at DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS intelligence_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    external_id TEXT UNIQUE,
                    title TEXT NOT NULL,
                    url TEXT,
                    summary TEXT,
                    primary_category TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    matched_keywords TEXT,
                    relevance_score REAL DEFAULT 1.0,
                    evaluated_at DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def record_lead(
        self,
        tier: str,
        email: str,
        identifier: str,
        allocated_tq: float,
        wallet_address: Optional[str] = None,
        firm_name: Optional[str] = None,
        deployment_scale: Optional[str] = None,
        category_tag: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Inserts a new lead into the airdrop_leads table.

        Returns:
            Row ID of the newly created lead.
        """
        if not email or "@" not in email:
            raise ValueError("Valid email address is required.")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO airdrop_leads (tier, email, identifier, wallet_address, allocated_tq, firm_name, deployment_scale, category_tag, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tier, email.strip(), identifier.strip(), wallet_address,
                float(allocated_tq), firm_name, deployment_scale, category_tag, notes
            ))
            conn.commit()
            return cursor.lastrowid

    def get_lead_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single lead by email address."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM airdrop_leads WHERE email = ?", (email.strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_leads(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves all CRM leads ordered by claim timestamp."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM airdrop_leads ORDER BY claimed_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def export_leads_csv(self) -> str:
        """Generates standard CSV export string for institutional CRM leads."""
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Tier", "Email", "Identifier", "Firm Name",
            "Deployment Scale", "Category Tag", "Wallet Address",
            "Allocated $TQ", "Claimed At", "Status", "Notes"
        ])
        for lead in self.get_all_leads(limit=1000):
            writer.writerow([
                lead.get("id"),
                _neutralize_csv_cell(lead.get("tier")),
                _neutralize_csv_cell(lead.get("email")),
                _neutralize_csv_cell(lead.get("identifier")),
                _neutralize_csv_cell(lead.get("firm_name")),
                _neutralize_csv_cell(lead.get("deployment_scale")),
                _neutralize_csv_cell(lead.get("category_tag")),
                _neutralize_csv_cell(lead.get("wallet_address")),
                lead.get("allocated_tq"),
                _neutralize_csv_cell(lead.get("claimed_at")),
                _neutralize_csv_cell(lead.get("status")),
                _neutralize_csv_cell(lead.get("notes"))
            ])
        return output.getvalue()

    def export_leads_json(self) -> str:
        """Generates formatted JSON export string for institutional CRM leads."""
        leads = self.get_all_leads(limit=1000)
        return json.dumps({"leads": leads, "total_count": len(leads)}, indent=2)

    def get_leads_summary(self) -> Dict[str, Any]:
        """Calculates count and sum totals across leads."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(allocated_tq), 0.0) FROM airdrop_leads")
            count, total_tq = cursor.fetchone()
            return {
                "total_records": count,
                "total_tq_allocated": total_tq
            }

    def get_crm_pipeline_stats(self) -> Dict[str, Any]:
        """Generates institutional CRM pipeline analytics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(allocated_tq), 0.0) FROM airdrop_leads")
            total_leads, total_tq = cursor.fetchone()

            cursor.execute("SELECT tier, COUNT(*) as cnt FROM airdrop_leads GROUP BY tier")
            by_tier = {row["tier"]: row["cnt"] for row in cursor.fetchall()}

            cursor.execute("SELECT category_tag, COUNT(*) as cnt FROM airdrop_leads WHERE category_tag IS NOT NULL GROUP BY category_tag")
            by_category = {row["category_tag"]: row["cnt"] for row in cursor.fetchall()}

            cursor.execute("SELECT deployment_scale, COUNT(*) as cnt FROM airdrop_leads WHERE deployment_scale IS NOT NULL GROUP BY deployment_scale")
            by_scale = {row["deployment_scale"]: row["cnt"] for row in cursor.fetchall()}

            return {
                "total_leads": total_leads,
                "total_tq_allocated": total_tq,
                "by_tier": by_tier,
                "by_category": by_category,
                "by_deployment_scale": by_scale
            }

    def log_event(self, event_type: str, details: str) -> int:
        """Records an event into radar_event_log."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO radar_event_log (event_type, details) VALUES (?, ?)",
                (event_type, details)
            )
            conn.commit()
            return cursor.lastrowid

    def record_intelligence_article(
        self,
        source: str,
        title: str,
        primary_category: str,
        priority: str,
        external_id: Optional[str] = None,
        url: Optional[str] = None,
        summary: Optional[str] = None,
        matched_keywords: Optional[List[str]] = None,
        relevance_score: float = 1.0
    ) -> int:
        """Records an evaluated intelligence article."""
        kw_str = json.dumps(matched_keywords or []) if isinstance(matched_keywords, list) else str(matched_keywords or "")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO intelligence_articles
                (source, external_id, title, url, summary, primary_category, priority, matched_keywords, relevance_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(external_id) DO UPDATE SET
                    title=excluded.title,
                    url=excluded.url,
                    summary=excluded.summary,
                    primary_category=excluded.primary_category,
                    priority=excluded.priority,
                    matched_keywords=excluded.matched_keywords,
                    relevance_score=excluded.relevance_score,
                    evaluated_at=CURRENT_TIMESTAMP
            """, (
                source, external_id, title.strip(), url, summary,
                primary_category, priority, kw_str, float(relevance_score)
            ))
            conn.commit()
            return cursor.lastrowid

    def get_latest_intelligence_articles(self, limit: int = 20, min_priority: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches latest evaluated intelligence articles."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if min_priority:
                cursor.execute(
                    "SELECT * FROM intelligence_articles WHERE priority = ? ORDER BY evaluated_at DESC LIMIT ?",
                    (min_priority, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM intelligence_articles ORDER BY evaluated_at DESC LIMIT ?",
                    (limit,)
                )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_intelligence_stats(self) -> Dict[str, Any]:
        """Returns summary counts of intelligence items by category and priority."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total, COUNT(DISTINCT primary_category) as categories FROM intelligence_articles")
            total, num_cats = cursor.fetchone()

            cursor.execute("SELECT priority, COUNT(*) as cnt FROM intelligence_articles GROUP BY priority")
            by_priority = {row["priority"]: row["cnt"] for row in cursor.fetchall()}

            cursor.execute("SELECT primary_category, COUNT(*) as cnt FROM intelligence_articles GROUP BY primary_category")
            by_category = {row["primary_category"]: row["cnt"] for row in cursor.fetchall()}

            return {
                "total_articles": total,
                "categories_count": num_cats,
                "by_priority": by_priority,
                "by_category": by_category
            }
