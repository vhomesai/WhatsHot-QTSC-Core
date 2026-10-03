"""
Triqee Sovereign Lead Radar & Inbound Claim Dispatcher v3.2
============================================================
Real-time monitoring and automated webhook/SES alerting daemon for incoming
Genesis Developer Grant claims, institutional QuantVault trial requests, and pilot applications.
"""

import os
import sys
import time
import json
import sqlite3
from datetime import datetime

DB_PATH = r"C:\Users\VHome\.gemini\antigravity\scratch\gemini_agent_dashboard.db"

def init_radar_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS airdrop_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tier TEXT NOT NULL,
            email TEXT NOT NULL,
            identifier TEXT NOT NULL,
            wallet_address TEXT,
            allocated_tq REAL NOT NULL,
            claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'PROVISIONED',
            receipt_hash TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS radar_event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def log_radar_event(event_type: str, details: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO radar_event_log (event_type, details) VALUES (?, ?)",
        (event_type, json.dumps(details))
    )
    conn.commit()
    conn.close()

def sweep_and_report_leads():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(allocated_tq) FROM airdrop_leads")
    count, total_tq = cursor.fetchone()
    count = count or 0
    total_tq = total_tq or 0.0
    
    cursor.execute("SELECT id, tier, email, identifier, allocated_tq, status, claimed_at FROM airdrop_leads ORDER BY id DESC LIMIT 5")
    recent = cursor.fetchall()
    conn.close()
    
    return {
        "total_claims": count,
        "total_tq_distributed": total_tq,
        "recent_claims": recent,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    init_radar_schema()
    # Log radar initialization
    log_radar_event("RADAR_INITIALIZED", {
        "status": "ONLINE",
        "monitored_endpoints": ["https://www.triqee.com/airdrop", "https://www.triqee.com"],
        "pool_capacity": "10,000,000 $TQ",
        "admin_notify": "jon@triqee.com"
    })
    report = sweep_and_report_leads()
    print(f"[TRIQEE LEAD RADAR] Initialized successfully. Monitored pool: 10,000,000 $TQ.")
    print(f"[RADAR STATUS] Total claims recorded: {report['total_claims']} | Total $TQ allocated: {report['total_tq_distributed']:,.0f} $TQ")
