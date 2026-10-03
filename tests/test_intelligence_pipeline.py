"""
Test suite for ArXiv & Research Intelligence Pipeline
=====================================================
Validates XML parsing, keyword categorization, priority assignment,
and database persistence with SQLite context isolation.
"""

import os
import pytest
from src.db_manager import DatabaseManager
from src.arxiv_patent_pipeline import ArxivPatentIntelligencePipeline
from src.headline_taxonomy import evaluate_headline_relevance

MOCK_ARXIV_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2610.12345v1</id>
    <title>High-Precision Quantum RF Sensing via Superconducting SQUID Arrays</title>
    <summary>We present a novel quantum rf sensing receiver operating with superconducting sensor technology for ultra-wideband RF detection.</summary>
    <published>2026-10-01T12:00:00Z</published>
    <link href="http://arxiv.org/pdf/2610.12345v1" rel="related" type="application/pdf" title="pdf"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2610.67890v1</id>
    <title>Room Temperature NV Center Qubit Register in Diamond Nanophotonic Chips</title>
    <summary>Coherent optical control of diamond nv center spins at room temperature enables compact quantum edge hardware.</summary>
    <published>2026-10-01T14:30:00Z</published>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2610.99999v1</id>
    <title>Unrelated Classical Economics Paper on Macro Trends</title>
    <summary>A standard economic survey without quantum or edge technology mentions.</summary>
    <published>2026-10-01T15:00:00Z</published>
  </entry>
</feed>
"""


def test_arxiv_atom_parser(tmp_path):
    db_file = str(tmp_path / "test_intel.db")
    db = DatabaseManager(db_file)
    pipeline = ArxivPatentIntelligencePipeline(db_manager=db)

    entries = pipeline.parse_arxiv_atom_feed(MOCK_ARXIV_XML)
    assert len(entries) == 3
    assert "Quantum RF" in entries[0]["title"]
    assert entries[0]["pdf_url"] == "http://arxiv.org/pdf/2610.12345v1"
    assert entries[1]["pdf_url"] == "http://arxiv.org/pdf/2610.67890v1"


def test_evaluate_and_index_entries(tmp_path):
    db_file = str(tmp_path / "test_intel.db")
    db = DatabaseManager(db_file)
    pipeline = ArxivPatentIntelligencePipeline(db_manager=db)

    entries = pipeline.parse_arxiv_atom_feed(MOCK_ARXIV_XML)
    indexed = pipeline.evaluate_and_index_entries(entries)

    # Only the first two match our taxonomy
    assert len(indexed) == 2
    assert indexed[0]["primary_category"] == "QUANTUM_RF_SENSING"
    assert indexed[0]["priority"] == "P0_CRITICAL"
    assert indexed[1]["primary_category"] == "EDGE_QUANTUM_HARDWARE"
    assert indexed[1]["priority"] == "P0_CRITICAL"

    # Verify SQLite persistence
    articles = db.get_latest_intelligence_articles()
    assert len(articles) == 2

    stats = db.get_intelligence_stats()
    assert stats["total_articles"] == 2
    assert stats["by_priority"].get("P0_CRITICAL") == 2
