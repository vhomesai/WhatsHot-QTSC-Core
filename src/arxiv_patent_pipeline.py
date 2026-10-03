"""
Triqee Autonomous ArXiv & Research Intelligence Pipeline
========================================================
Queries research repositories (arXiv, Patent abstracts, inbox dispatches),
evaluates entries using the Triqee Intelligence Taxonomy, indexes findings
into SQLite, and generates formatted executive briefings.
"""

import os
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.headline_taxonomy import evaluate_headline_relevance, TAXONOMY_CATEGORIES
from src.db_manager import DatabaseManager

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = os.getenv("TRIQEE_DB_PATH", str(PROJECT_ROOT / "triqee_system.db"))
ARXIV_API_BASE = "http://export.arxiv.org/api/query"


class ArxivPatentIntelligencePipeline:
    """Automates ingestion, categorization, database indexing, and briefing generation."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager(DEFAULT_DB_PATH)

    def fetch_arxiv_papers(
        self,
        query: str = "cat:quant-ph OR cat:physics.app-ph OR cat:cs.AI",
        max_results: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Fetches papers from the official arXiv API via standard REST XML endpoint.
        """
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }
        url = f"{ARXIV_API_BASE}?{urllib.parse.urlencode(params)}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Triqee-Autonomous-Intelligence-Engine/1.0 (research@triqee.com)"}
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                xml_data = response.read()
                return self.parse_arxiv_atom_feed(xml_data)
        except Exception as e:
            print(f"[!] Warning: ArXiv API fetch encountered: {e}")
            return []

    def parse_arxiv_atom_feed(self, xml_bytes: bytes) -> List[Dict[str, Any]]:
        """Parses standard Atom 1.0 XML response from arXiv."""
        root = ET.fromstring(xml_bytes)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        entries = []
        for entry in root.findall("atom:entry", ns):
            arxiv_id_elem = entry.find("atom:id", ns)
            arxiv_id = arxiv_id_elem.text.strip() if arxiv_id_elem is not None else ""

            title_elem = entry.find("atom:title", ns)
            title = " ".join(title_elem.text.strip().split()) if title_elem is not None else "Untitled"

            summary_elem = entry.find("atom:summary", ns)
            summary = " ".join(summary_elem.text.strip().split()) if summary_elem is not None else ""

            published_elem = entry.find("atom:published", ns)
            published = published_elem.text.strip() if published_elem is not None else ""

            pdf_link = ""
            for link in entry.findall("atom:link", ns):
                if link.attrib.get("title") == "pdf":
                    pdf_link = link.attrib.get("href", "")
                    break
            if not pdf_link and arxiv_id:
                pdf_link = arxiv_id.replace("abs", "pdf")

            entries.append({
                "external_id": arxiv_id,
                "title": title,
                "summary": summary,
                "published": published,
                "url": arxiv_id,
                "pdf_url": pdf_link,
                "source": "arXiv"
            })
        return entries

    def evaluate_and_index_entries(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluates a batch of research entries, indexes matched high-priority items into SQLite.
        """
        indexed = []
        for item in items:
            combined_text = f"{item.get('title', '')} {item.get('summary', '')}"
            eval_res = evaluate_headline_relevance(combined_text)

            if eval_res.get("matched"):
                cats = eval_res.get("categories", [])
                primary_cat = cats[0]["category_key"] if cats else "GENERAL_QUANTUM"
                priority = cats[0]["priority"] if cats else "P2_MEDIUM"
                matched_kws = [kw for c in cats for kw in c.get("matched_keywords", [])]

                row_id = self.db.record_intelligence_article(
                    source=item.get("source", "Unknown"),
                    external_id=item.get("external_id"),
                    title=item.get("title", "Untitled"),
                    url=item.get("url"),
                    summary=item.get("summary"),
                    primary_category=primary_cat,
                    priority=priority,
                    matched_keywords=matched_kws,
                    relevance_score=len(matched_kws) * 1.5
                )

                item["db_row_id"] = row_id
                item["primary_category"] = primary_cat
                item["priority"] = priority
                item["matched_keywords"] = matched_kws
                indexed.append(item)

        return indexed

    def ingest_inbox_scan_file(self, json_path: str) -> List[Dict[str, Any]]:
        """Ingests and persists items from a previously executed inbox scan."""
        if not os.path.exists(json_path):
            return []

        with open(json_path, "r", encoding="utf-8") as f:
            raw_items = json.load(f)

        transformed = []
        for item in raw_items:
            eval_info = item.get("evaluation", {})
            if eval_info.get("matched"):
                title = item.get("resolved_title") or item.get("subject") or "Inbox Research Notification"
                transformed.append({
                    "source": "Inbox (trixee@triqee.com)",
                    "external_id": f"inbox_{item.get('index')}_{item.get('date')}",
                    "title": title,
                    "url": item.get("final_url"),
                    "summary": item.get("subject", ""),
                    "evaluation": eval_info
                })

        return self.evaluate_and_index_entries(transformed)

    def run_full_pipeline(self) -> Dict[str, Any]:
        """Runs inbox ingestion + arXiv queries + generates summary stats."""
        # 1. Ingest from inbox scan JSON if available
        inbox_json = os.getenv(
            "TRIQEE_INTELLIGENCE_JSON",
            str(PROJECT_ROOT / "trixee_evaluated_intelligence_latest.json"),
        )
        inbox_indexed = self.ingest_inbox_scan_file(inbox_json)

        # 2. Ingest from arXiv
        arxiv_items = self.fetch_arxiv_papers(max_results=20)
        arxiv_indexed = self.evaluate_and_index_entries(arxiv_items)

        stats = self.db.get_intelligence_stats()
        latest = self.db.get_latest_intelligence_articles(limit=10)

        return {
            "inbox_items_indexed": len(inbox_indexed),
            "arxiv_items_indexed": len(arxiv_indexed),
            "total_indexed_session": len(inbox_indexed) + len(arxiv_indexed),
            "db_stats": stats,
            "latest_articles": latest
        }


if __name__ == "__main__":
    pipeline = ArxivPatentIntelligencePipeline()
    result = pipeline.run_full_pipeline()
    print("\n[+] Full Intelligence Pipeline Ingestion Complete:")
    print(json.dumps(result, indent=2))
