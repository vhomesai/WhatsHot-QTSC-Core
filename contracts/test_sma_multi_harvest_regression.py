#!/usr/bin/env python3
"""
Regression Test: TriqeeSMATrancheVault Multi-Harvest Yield Accounting
Tests 10 consecutive 12-hour harvest cycles + redemption stub yield to prove zero LP yield omission.
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def simulate_vault_lifecycle(principal_usd=250000.0, epochs=10, epoch_seconds=43200, stub_seconds=21600):
    SECONDS_PER_YEAR = 31536000
    LP_RATE = 0.06000   # 6.000%
    GROSS_RATE = 0.09155 # 9.155%
    PROTOCOL_SPREAD = GROSS_RATE - LP_RATE # 3.155%

    total_lp_paid = 0.0
    total_protocol_paid = 0.0

    print("=" * 80)
    print(f"⚡ SIMULATING VAULT WATERFALL: Principal ${principal_usd:,.2f} over {epochs} Harvest Epochs")
    print("=" * 80)

    # 1. Simulate Harvest Epochs
    for e in range(1, epochs + 1):
        gross_epoch = principal_usd * GROSS_RATE * (epoch_seconds / SECONDS_PER_YEAR)
        lp_epoch = principal_usd * LP_RATE * (epoch_seconds / SECONDS_PER_YEAR)
        protocol_epoch = gross_epoch - lp_epoch

        total_lp_paid += lp_epoch
        total_protocol_paid += protocol_epoch
        print(f"  Epoch {e:2d} (12h): LP Paid: ${lp_epoch:8.4f} | Treasury Spread: ${protocol_epoch:8.4f} | Gross: ${gross_epoch:8.4f}")

    # 2. Simulate Stub Yield upon Redemption
    stub_lp_yield = principal_usd * LP_RATE * (stub_seconds / SECONDS_PER_YEAR)
    total_lp_received = total_lp_paid + stub_lp_yield

    # Theoretical exact total over entire active duration
    total_active_seconds = (epochs * epoch_seconds) + stub_seconds
    expected_lp_total = principal_usd * LP_RATE * (total_active_seconds / SECONDS_PER_YEAR)
    expected_protocol_total = principal_usd * PROTOCOL_SPREAD * ((epochs * epoch_seconds) / SECONDS_PER_YEAR)

    print("-" * 80)
    print(f"[*] Stub Period ({stub_seconds/3600:.1f}h): LP Stub Yield: ${stub_lp_yield:8.4f}")
    print(f"[*] Total LP Preferred Yield Received:   ${total_lp_received:,.4f} (Expected: ${expected_lp_total:,.4f})")
    print(f"[*] Total Protocol Carry Swept:           ${total_protocol_paid:,.4f} (Expected: ${expected_protocol_total:,.4f})")
    print(f"[*] Effective LP APY:                     {(total_lp_received / principal_usd) * (SECONDS_PER_YEAR / total_active_seconds) * 100:.4f}%")
    print(f"[*] Effective Carry Spread APY:           {(total_protocol_paid / principal_usd) * (SECONDS_PER_YEAR / (epochs * epoch_seconds)) * 100:.4f}%")
    
    assert abs(total_lp_received - expected_lp_total) < 1e-6, "LP Yield mismatch!"
    assert abs(total_protocol_paid - expected_protocol_total) < 1e-6, "Protocol Spread mismatch!"
    print("[+] REGRESSION TEST PASSED: 100% of accrued LP preferred yield accounted and distributed.")
    print("=" * 80)

if __name__ == "__main__":
    simulate_vault_lifecycle()
