#!/usr/bin/env python3
"""
Test Suite for Triqee Wyoming Vector 2 Consumptive Compute Burn Bridge
Validates hardware ticket generation, quota provisioning, and statutory compliance.
"""

import sys
import os
import json
import time
import urllib.request
import urllib.error

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8018"
_use_test_client = False
_client = None

try:
    urllib.request.urlopen(f"{BASE_URL}/api/v1/compute/matrix", timeout=1)
except Exception:
    try:
        from fastapi.testclient import TestClient
        from triqee_consumptive_burn_bridge import app
        _client = TestClient(app)
        _use_test_client = True
    except Exception:
        pass

def get_json(url_path):
    if _use_test_client and _client:
        res = _client.get(url_path)
        assert res.status_code == 200
        return res.json()
    req = urllib.request.Request(f"{BASE_URL}{url_path}")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        return json.loads(resp.read().decode())

def post_json(url_path, payload):
    if _use_test_client and _client:
        res = _client.post(url_path, json=payload)
        assert res.status_code == 200
        return res.json()
    req = urllib.request.Request(
        f"{BASE_URL}{url_path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        return json.loads(resp.read().decode())

def test_bridge_matrix():
    print("[TEST 1/4] Verifying Statutory Consumptive Matrix...")
    data = get_json("/api/v1/compute/matrix")
    rates = data.get("rates", {})
    assert "IBM_HERON_156Q" in rates
    assert "GEMINI_ARGON_REASONING" in rates
    print(f"  ✓ Validated Matrix: {len(rates)} Hardware Targets under {data['statutory_authority']}")

def test_burn_ibm_heron():
    print("\n[TEST 2/4] Testing $TQ Burn for IBM Heron 156Q Heavy-Hex QPU...")
    payload = {
        "burner_address": "0xf958A93652aD2540b344dBA75379c3C5ae09C7b0",
        "amount_tq": 500.0,
        "hardware_target": "IBM_HERON_156Q"
    }
    data = post_json("/api/v1/compute/verify_burn", payload)
    assert data["amount_tq_burned"] == 500.0
    assert data["hardware_target"] == "IBM_HERON_156Q"
    assert data["quota_issued"] == 5.0 # 500 / 100
    assert data["quota_unit"] == "QPU_SHOTS"
    assert data["api_key"].startswith("TRIQEE-TQ-BURN-")
    print(f"  ✓ Burned: 500 $TQ -> Issued {data['quota_issued']} {data['quota_unit']}")
    print(f"  ✓ Ticket ID: {data['ticket_id']}")
    print(f"  ✓ API Bearer Key: {data['api_key']}")
    print(f"  ✓ Proof Hash: {data['proof_hash'][:32]}...")

def test_burn_gemini_argon():
    print("\n[TEST 3/4] Testing $TQ Burn for Google Gemini 4 Argon Reasoning...")
    payload = {
        "burner_address": "0xf958A93652aD2540b344dBA75379c3C5ae09C7b0",
        "amount_tq": 1000.0,
        "hardware_target": "GEMINI_ARGON_REASONING"
    }
    data = post_json("/api/v1/compute/verify_burn", payload)
    assert data["amount_tq_burned"] == 1000.0
    assert data["quota_issued"] == 1_000_000.0 # 1000 * 1000
    assert data["quota_unit"] == "ARGON_REASONING_TOKENS"
    print(f"  ✓ Burned: 1,000 $TQ -> Issued {data['quota_issued']:,.0f} {data['quota_unit']}")
    print(f"  ✓ Statutory Status: {data['statutory_safe_harbor']}")

def test_account_quota():
    print("\n[TEST 4/4] Verifying Account Ledger & Safe Harbor Certification...")
    account = "0xf958A93652aD2540b344dBA75379c3C5ae09C7b0"
    data = get_json(f"/api/v1/compute/quota/{account}")
    assert data["safe_harbor_certified"] is True
    assert data["total_tq_burned"] >= 1500.0
    assert data["active_ticket_count"] >= 2
    print(f"  ✓ Verified Account: {account}")
    print(f"  ✓ Total $TQ Burned Recorded: {data['total_tq_burned']:,.0f} $TQ")
    print(f"  ✓ Active Consumptive Tickets: {data['active_ticket_count']}")
    print(f"  ✓ Safe Harbor Certified: {data['safe_harbor_certified']}")

if __name__ == "__main__":
    print("=" * 80)
    print("   TRIQEE WYOMING DA-000000992 // VECTOR 2 CONSUMPTIVE BURN BRIDGE TESTS")
    print("   Wyoming W.S. 34-29-106 Non-Security Safe Harbor Verification")
    print("=" * 80)
    test_bridge_matrix()
    test_burn_ibm_heron()
    test_burn_gemini_argon()
    test_account_quota()
    print("\n================================================================================")
    print("   ALL VECTOR 2 CONSUMPTIVE BURN TESTS PASSED (100% OPERATIONAL)")
    print("================================================================================")
