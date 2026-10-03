"""
Triqee Social Comment & Inbound Lead Sentinel v3.2
===================================================
Real-time triage engine for inbound LinkedIn/X comments, DMs, and GoDaddy Airo leads.
Generates instant, authoritative, scientifically rigorous responses tailored to:
1. Technical Devs (GitHub / SDK / Transpilation)
2. Institutional Quants (QuantVault / Sharpe Alpha / Paper Trading)
3. Web3 / Token Inquiries (Wyoming W.S. 34-29-106 Consumptive Utility)
4. Enterprise / Sovereign Defense (Air-gapped Appliance / DOE Alignment)
"""

import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = os.getenv("TRIQEE_DB_PATH", str(PROJECT_ROOT / "gemini_agent_dashboard.db"))

COMMENT_TRIAGE_TEMPLATES = {
    "DEV_INQUIRY": {
        "pattern_keywords": ["github", "sdk", "qiskit", "cirq", "transpiler", "swap", "python", "install"],
        "tier": "Tier 1 (500 $TQ)",
        "suggested_response": (
            "Thanks for reaching out! You can claim your 500 $TQ developer grant directly at "
            "https://www.triqee.com/airdrop by submitting your GitHub handle. "
            "To get started immediately with our Python SDK: `pip install triqee` and check our "
            "CERN-indexed paper (DOI: 10.5281/zenodo.23045297) for zero-SWAP routing benchmarks!"
        )
    },
    "QUANT_INQUIRY": {
        "pattern_keywords": ["hedge fund", "sharpe", "alpha", "factor", "portfolio", "backtest", "bloomberg", "trading"],
        "tier": "Tier 2 (5,000 $TQ)",
        "suggested_response": (
            "Great to connect. Institutional researchers and quants can claim 5,000 $TQ (~$500 alpha quota) "
            "at https://www.triqee.com/airdrop with their work email (.edu or fund domain). "
            "QuantVault™ factor models run dynamic IonQ Forte QAOA portfolio optimization with +381.9% Sharpe alpha over SPY. "
            "You can also schedule an air-gapped pilot session directly with our engineering team."
        )
    },
    "TOKEN_UTILITY_INQUIRY": {
        "pattern_keywords": ["token", "utility", "sec", "security", "airdrop", "wyoming", "legal", "exchange"],
        "tier": "Statutory Safe Harbor",
        "suggested_response": (
            "$TQ is a 100% consumptive compute utility token issued under the Wyoming Utility Token Act "
            "(W.S. 34-29-106; Wyoming Entity DA-000000992). It is solely redeemable for QPU compute and "
            "transpilation gas on the Triqee gateway. It confers zero equity or profit share and is not an investment security. "
            "Details: https://www.triqee.com/airdrop"
        )
    },
    "ENTERPRISE_DEFENSE_INQUIRY": {
        "pattern_keywords": ["defense", "doe", "darpa", "air-gapped", "sovereign", "on-prem", "fips"],
        "tier": "Sovereign Briefing",
        "suggested_response": (
            "For federal, defense, and air-gapped institutional deployments, Triqee Sovereign Appliance™ v3.1 "
            "operates zero-egress hardware enclaves equipped with GLI-19 True Quantum Entropy RNG and FIPS 140-3 compliance. "
            "Request a sovereign briefing at https://www.triqee.com/portal or contact jon@triqee.com directly."
        )
    }
}

def triage_inbound_message(user_handle: str, message_text: str, platform: str = "LinkedIn"):
    msg_lower = message_text.lower()
    matched_category = "DEV_INQUIRY" # default

    for cat, data in COMMENT_TRIAGE_TEMPLATES.items():
        if any(kw in msg_lower for kw in data["pattern_keywords"]):
            matched_category = cat
            break

    triage_result = {
        "user_handle": user_handle,
        "platform": platform,
        "category": matched_category,
        "tier_matched": COMMENT_TRIAGE_TEMPLATES[matched_category]["tier"],
        "suggested_response": COMMENT_TRIAGE_TEMPLATES[matched_category]["suggested_response"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS social_triage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_handle TEXT,
            platform TEXT,
            category TEXT,
            message_text TEXT,
            suggested_response TEXT,
            status TEXT DEFAULT 'PENDING_REVIEW',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        INSERT INTO social_triage_log (user_handle, platform, category, message_text, suggested_response)
        VALUES (?, ?, ?, ?, ?)
    """, (user_handle, platform, matched_category, message_text, triage_result["suggested_response"]))
    conn.commit()
    conn.close()

    return triage_result

if __name__ == "__main__":
    # Test triage sample
    sample = triage_inbound_message(
        user_handle="@QuantResearcher_NYC",
        message_text="How does QuantVault calculate Sharpe alpha against SPY using IonQ QAOA?",
        platform="X"
    )
    print("[SENTINEL INITIALIZED] Social Comment & Inbound Lead Sentinel is active.")
    print(f"Sample Triage Result:\n- Category: {sample['category']}\n- Response: {sample['suggested_response']}")
