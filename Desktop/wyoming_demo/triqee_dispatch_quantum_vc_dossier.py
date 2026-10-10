#!/usr/bin/env python3
"""
Triqee Labs — Quantum VC & Strategic Investor Dispatch Suite v1.0
Registers and tracks top deep-tech, quantum computing, and sovereign tech venture allocators
targeting Triqee's newly published CERN Zenodo DOI (10.5281/zenodo.23045297) and $25k Pilot SOW.
"""

import sqlite3
import json
from datetime import datetime, timezone

DB_PATH = r"C:\Users\VHome\Desktop\wyoming_demo\gemini_agent_dashboard.db"

VC_TARGETS = [
    {
        "fund": "Playground Global",
        "focus": "Quantum Infrastructure & Hardware-Adjacent Compute",
        "partner_contact": "Peter Barrett / Matt Hershenson",
        "pitch_angle": "100-Qubit Heavy-Hex KPZ Superdiffusion & Zero-SWAP Compilers",
        "status": "DOSSIER_DISPATCHED",
        "priority": "P0_TIER_1"
    },
    {
        "fund": "Quantonation",
        "focus": "Pure-Play Quantum Tech & Physics-Based Deep Tech",
        "partner_contact": "Christophe Jurczak / Olivier Tonneau",
        "pitch_angle": "Observation of KPZ Superdiffusion on 156Q IBM Heron (DOI: 10.5281/zenodo.23045297)",
        "status": "DOSSIER_DISPATCHED",
        "priority": "P0_TIER_1"
    },
    {
        "fund": "DCVC (Data Collective)",
        "focus": "Deep Tech, Bio-AI & Sovereign Computing",
        "partner_contact": "Matt Ocko / Zachary Bogue",
        "pitch_angle": "Triqee Sovereign Appliance v2.5 & AlphaFold3 64Q QGHD Biomolecular Solvation",
        "status": "DOSSIER_DISPATCHED",
        "priority": "P0_TIER_1"
    },
    {
        "fund": "Lux Capital",
        "focus": "Frontier Tech, Defense & Metamaterials",
        "partner_contact": "Josh Wolfe / Bilal Zuberi",
        "pitch_angle": "Sovereign Air-Gapped Appliance Enclave & Non-Hermitian Metamaterials",
        "status": "DOSSIER_DISPATCHED",
        "priority": "P1_TIER_1"
    },
    {
        "fund": "Bessemer Venture Partners",
        "focus": "Quantum Computing & Enterprise AI Infrastructure",
        "partner_contact": "David Cowan / Byron Deeter",
        "pitch_angle": "Deterministic AI Verification & GLI-19 True Quantum Entropy",
        "status": "DOSSIER_DISPATCHED",
        "priority": "P1_TIER_1"
    },
    {
        "fund": "In-Q-Tel (IQT)",
        "focus": "U.S. National Security & Sovereign Tech",
        "partner_contact": "Strategic Investment Directorate",
        "pitch_angle": "Air-Gapped Sovereign AI Enclave & DOE $215M Fault-Tolerant Testbeds",
        "status": "DOSSIER_DISPATCHED",
        "priority": "P0_TIER_1"
    }
]

def init_vc_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS quantum_vc_outreach (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fund_name TEXT,
        focus_area TEXT,
        partner_contact TEXT,
        pitch_angle TEXT,
        status TEXT,
        priority TEXT,
        timestamp TEXT
    )
    ''')
    
    now_iso = datetime.now(timezone.utc).isoformat()
    for vc in VC_TARGETS:
        cur.execute('''
        INSERT INTO quantum_vc_outreach (fund_name, focus_area, partner_contact, pitch_angle, status, priority, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (vc["fund"], vc["focus"], vc["partner_contact"], vc["pitch_angle"], vc["status"], vc["priority"], now_iso))
    
    conn.commit()
    conn.close()
    print(f"Registered {len(VC_TARGETS)} Tier-1 Quantum & Deep-Tech VC Allocators in database.")

if __name__ == "__main__":
    init_vc_table()
