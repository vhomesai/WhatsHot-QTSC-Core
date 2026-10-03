import csv
import io
import json

import pytest

from src.db_manager import DatabaseManager, _neutralize_csv_cell


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("=SUM(A1:A2)", "'=SUM(A1:A2)"),
        ("+cmd|' /C calc'!A0", "'+cmd|' /C calc'!A0"),
        ("-1+2", "'-1+2"),
        ("@SUM(1,2)", "'@SUM(1,2)"),
        ("  =HYPERLINK(\"https://example.test\")", "  '=HYPERLINK(\"https://example.test\")"),
        ("\t+SUM(1,2)", "\t'+SUM(1,2)"),
        ("\r\n@payload", "\r\n'@payload"),
        ("ordinary text", "ordinary text"),
        ("comma, quote \" and\nnewline", "comma, quote \" and\nnewline"),
        ("", ""),
        (None, ""),
    ],
)
def test_neutralize_csv_cell(value, expected):
    assert _neutralize_csv_cell(value) == expected


def test_csv_export_neutralizes_every_text_field_and_preserves_csv_quoting(tmp_path, monkeypatch):
    db = DatabaseManager(str(tmp_path / "crm.db"))
    lead = {
        "id": 7,
        "tier": "=tier",
        "email": "+user@example.com",
        "identifier": "-identifier",
        "firm_name": "@firm",
        "deployment_scale": "  =scale",
        "category_tag": "\t+category",
        "wallet_address": None,
        "allocated_tq": 25000.0,
        "claimed_at": "2026-10-03T09:00:00Z",
        "status": "PROVISIONED",
        "notes": "comma, quote \" and\nnewline",
    }
    monkeypatch.setattr(db, "get_all_leads", lambda limit: [lead])

    csv_text = db.export_leads_csv()
    rows = list(csv.reader(io.StringIO(csv_text)))

    assert rows[0][0:4] == ["ID", "Tier", "Email", "Identifier"]
    assert rows[1] == [
        "7",
        "'=tier",
        "'+user@example.com",
        "'-identifier",
        "'@firm",
        "  '=scale",
        "\t'+category",
        "",
        "25000.0",
        "2026-10-03T09:00:00Z",
        "PROVISIONED",
        "comma, quote \" and\nnewline",
    ]
    assert '"comma, quote "" and\nnewline"' in csv_text


def test_json_export_remains_semantically_unchanged(tmp_path, monkeypatch):
    db = DatabaseManager(str(tmp_path / "crm.db"))
    leads = [
        {
            "id": 1,
            "tier": "=tier",
            "email": "+user@example.com",
            "identifier": "@identifier",
            "firm_name": "Firm, \"Quoted\"",
            "deployment_scale": None,
            "category_tag": "ENTERPRISE_INQUIRY",
            "wallet_address": "-wallet",
            "allocated_tq": 500.0,
            "claimed_at": "2026-10-03",
            "status": "PROVISIONED",
            "notes": "line one\nline two",
        }
    ]
    monkeypatch.setattr(db, "get_all_leads", lambda limit: leads)

    exported = json.loads(db.export_leads_json())

    assert exported == {"leads": leads, "total_count": 1}
