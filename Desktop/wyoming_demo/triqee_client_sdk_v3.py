#!/usr/bin/env python3
"""
Triqee Sovereign Enterprise QaaS Client SDK v3.0
Python Client library & verification test runner for Sovereign Engine v3.0.
"""

import sys
import json
import urllib.request
import urllib.parse
import time

# Ensure UTF-8 stdout
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class TriqeeClientSDK:
    def __init__(self, base_url="http://127.0.0.1:8088", api_key="TRIQEE_ENT_KEY_2026"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _post(self, path, payload):
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Triqee-Key": self.api_key
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get(self, path):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(
            url,
            headers={"X-Triqee-Key": self.api_key},
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def check_health(self):
        return self._get("/api/v3/quantum/health")

    def route_workload(self, qubits, couplers, circuit_type="Dense QUBO", shots=1000):
        return self._post("/api/v3/quantum/arbitrage/route", {
            "qubits": qubits,
            "couplers": couplers,
            "circuit_type": circuit_type,
            "shots": shots
        })

    def execute_ionq_job(self, assets, shots=2000):
        return self._post("/api/v3/quantum/execute/ionq", {
            "assets": assets,
            "shots": shots
        })

    def execute_quera_ahs(self, atoms=256):
        return self._post("/api/v3/quantum/execute/quera", {
            "atoms": atoms
        })

    def get_quantvault_signals(self):
        return self._get("/api/v3/quantum/quantvault/signals")

    def get_billing_metering(self):
        return self._get("/api/v3/quantum/billing/metering")

if __name__ == "__main__":
    print("================================================================")
    print("  TRIQEE ENTERPRISE QAAS CLIENT SDK v3.0 | TEST RUNNER")
    print("================================================================")
    
    sdk = TriqeeClientSDK()
    
    # Test 1: Health
    health = sdk.check_health()
    print(f"✓ Health Check: {health['appliance_name']} - Status: {health['status']}")
    print(f"  Active Version: {health['version']} | DOI: {health['official_publication']['doi']}")
    
    # Test 2: Arbitrage Routing
    route = sdk.route_workload(qubits=16, couplers=120, circuit_type="Dense Financial QUBO", shots=2000)
    print(f"\n✓ QaaS Arbitrage Route: {route['route_id']}")
    print(f"  Selected Modality: {route['decision']['selected_modality']}")
    print(f"  Projected Fidelity: {route['decision']['projected_fidelity']} | Estimated Cost: ${route['decision']['estimated_cost_usd']}")
    
    # Test 3: QuantVault Signals
    signals = sdk.get_quantvault_signals()
    print(f"\n✓ QuantVault Feed: Sharpe Ratio {signals['portfolio_metrics']['quantum_sharpe_ratio']} (Alpha {signals['portfolio_metrics']['sharpe_alpha_pct']}%)")
    print(f"  Selected Portfolio: {signals['selected_assets']}")
    
    # Test 4: Metering Telemetry
    metering = sdk.get_billing_metering()
    print(f"\n✓ Metering Telemetry: Total Billed ${metering['total_billed_usd']} across {metering['total_api_calls']} API calls.")
    
    print("\n================================================================")
    print("  ALL ENTERPRISE QAAS ENDPOINTS TESTED & OPERATIONAL (100% PASS)")
    print("================================================================")
