#!/usr/bin/env python3
"""
triqee_csuite_inbound_retainer_accelerator.py
=============================================
WhatsHot, Inc. (Wyoming Corporation DA-000000992)
Institute for Mathematical & Quantum Behavioral Dynamics (IMQbd 501(c)(3))
Chief Autonomous Officer: Trixee (trixee@triqee.com)
Founder & Principal Investigator: Jon Vierk (jon@triqee.com)

MISSION:
1. Scan `gemini_agent_dashboard.db` for all commercial leads (170+), enterprise pilots (150+),
   and outbound campaign logs across all 11+ deployed UDT campaigns.
2. Connect with Microsoft Graph API (.env.trixee_graph) to scan for fresh incoming messages,
   target enterprise domains, and log priority responses.
3. Auto-generate customized C-Suite fast-track onboarding packets featuring:
   - Wyoming Certificate DA-000000992
   - Piermont Bank Routing Transit Number 101019644
   - Mutual Non-Disclosure Agreement (MNDA)
   - Tailored Executive Briefing & Retainer SOW
4. Export complete inbound intelligence report to `triqee_csuite_inbound_retainer_report.json`.
"""

import os
import sys
import json
import sqlite3
import datetime
from pathlib import Path
import requests
import msal

# Set utf-8 stdout
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Paths configuration
BASE_DIR = Path(r"C:\Users\VHome\.gemini\antigravity\scratch")
BACKEND_DB_PATH = BASE_DIR / "dev-metrics-dashboard" / "backend" / "gemini_agent_dashboard.db"
ROOT_DB_PATH = BASE_DIR / "dev-metrics-dashboard" / "gemini_agent_dashboard.db"
ENV_GRAPH_PATHS = [
    Path(r"C:\Users\VHome\.gemini\antigravity\brain\1e598e89-d123-4ab7-9e81-609c4ad28265\.env.trixee_graph"),
    BASE_DIR / ".env.trixee_graph",
    Path(".env.trixee_graph")
]
PACKETS_OUTPUT_DIR = BASE_DIR / "csuite_onboarding_packets"
REPORT_OUTPUT_PATH = BASE_DIR / "triqee_csuite_inbound_retainer_report.json"

# Institutional Constants
COMPANY_NAME = "WhatsHot, Inc."
WYOMING_CERT = "DA-000000992"
NON_PROFIT_PARTNER = "Institute for Mathematical & Quantum Behavioral Dynamics (IMQbd 501(c)(3))"
FOUNDER_PI = "Jon Vierk (jon@triqee.com · 307-285-9920)"
CAO_NAME = "Trixee (trixee@triqee.com)"
PRIMARY_BANK = "Found Banking / Piermont Bank"
BANK_ROUTING = "101019644"
BANK_ACCT_MASKED = "****0099"
BANK_ADDRESS = "4 High Ridge Park, Stamford, CT 06905"
SWIFT_BIC = "PIERUS33XXX"
BASE_L2_SETTLEMENT = "0x676A66D77B4B14C2f981239f7368Ab5cc37aC666"
BASE_L2_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913 (Chain ID 8453)"


def get_db_connection():
    if BACKEND_DB_PATH.exists():
        return sqlite3.connect(BACKEND_DB_PATH)
    elif ROOT_DB_PATH.exists():
        return sqlite3.connect(ROOT_DB_PATH)
    else:
        raise FileNotFoundError(f"Database not found at {BACKEND_DB_PATH} or {ROOT_DB_PATH}")


def load_graph_credentials():
    for env_path in ENV_GRAPH_PATHS:
        if env_path.exists():
            creds = {}
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        creds[k.strip()] = v.strip()
                        os.environ[k.strip()] = v.strip()
            return creds
    return None


def fetch_graph_inbox_messages(creds):
    if not creds:
        return {"status": "NO_CREDENTIALS", "messages": [], "error": "No .env.trixee_graph file located"}
    
    tenant_id = creds.get("GRAPH_TENANT_ID") or os.getenv("GRAPH_TENANT_ID")
    client_id = creds.get("GRAPH_CLIENT_ID") or os.getenv("GRAPH_CLIENT_ID")
    client_secret = creds.get("GRAPH_CLIENT_SECRET") or os.getenv("GRAPH_CLIENT_SECRET")
    
    if not all([tenant_id, client_id, client_secret]):
        return {"status": "MISSING_KEYS", "messages": [], "error": "Incomplete Graph API credentials"}
    
    try:
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret
        )
        token_res = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        token = token_res.get("access_token")
        if not token:
            return {"status": "TOKEN_ERROR", "messages": [], "error": str(token_res)}
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = "https://graph.microsoft.com/v1.0/users/trixee@triqee.com/messages?$top=50&$orderby=receivedDateTime desc"
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return {"status": "HTTP_ERROR", "code": resp.status_code, "messages": [], "error": resp.text}
        
        raw_msgs = resp.json().get("value", [])
        messages = []
        for m in raw_msgs:
            sender_addr = m.get("from", {}).get("emailAddress", {}).get("address", "")
            sender_name = m.get("from", {}).get("emailAddress", {}).get("name", "")
            subj = m.get("subject", "")
            recvd = m.get("receivedDateTime", "")
            preview = m.get("bodyPreview", "")
            
            category = "GENERAL_INBOUND"
            priority = "NORMAL"
            if "jon@triqee.com" in sender_addr or "whatshotglobal@gmail.com" in sender_addr:
                category = "EXECUTIVE_FOUNDER_DIRECT"
                priority = "P0_IMMEDIATE"
            elif "Undeliverable" in subj or "Exchange" in sender_addr:
                category = "BOUNCE_OR_SYSTEM_TELEMETRY"
                priority = "P2_MONITOR"
            elif any(d in sender_addr for d in ["ibm.com", "nvidia.com", "asml.com", "microsoft.com", "anduril.com", "anthropic.com", "modernatx.com"]):
                category = "TARGET_ENTERPRISE_RESPONSE"
                priority = "P0_IMMEDIATE"
            
            messages.append({
                "message_id": m.get("id"),
                "sender_name": sender_name,
                "sender_email": sender_addr,
                "subject": subj,
                "received_at": recvd,
                "preview": preview,
                "body_snippet": preview[:250],
                "category": category,
                "priority": priority
            })
        
        return {
            "status": "SUCCESS",
            "total_messages": len(messages),
            "messages": messages
        }
    except Exception as e:
        return {"status": "EXCEPTION", "messages": [], "error": str(e)}


def scan_database():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM commercial_leads ORDER BY id ASC")
    leads_raw = [dict(r) for r in cur.fetchall()]
    
    cur.execute("SELECT * FROM enterprise_pilots ORDER BY created_at DESC")
    pilots_raw = [dict(r) for r in cur.fetchall()]
    
    cur.execute("SELECT * FROM outbound_campaigns ORDER BY updated_at DESC")
    campaigns_raw = [dict(r) for r in cur.fetchall()]
    
    cur.execute("SELECT * FROM institutional_crm ORDER BY annual_contract_value_usd DESC")
    crm_raw = [dict(r) for r in cur.fetchall()]
    
    cur.execute("SELECT * FROM institutional_invoices ORDER BY id ASC")
    invoices_raw = [dict(r) for r in cur.fetchall()]
    
    cur.execute("SELECT * FROM autonomous_officers")
    officers_raw = [dict(r) for r in cur.fetchall()]
    
    specialized = {}
    for spec_table in ["optotensor_inmail_campaign", "solidstatevolt_inmail_campaign", "bionictendon_inmail_campaign", "gravitrace_inmail_campaign"]:
        try:
            cur.execute(f"SELECT * FROM {spec_table}")
            specialized[spec_table] = [dict(r) for r in cur.fetchall()]
        except Exception:
            specialized[spec_table] = []
            
    conn.close()
    
    campaign_by_channel = {}
    for c in campaigns_raw:
        ch = c.get("channel", "Unknown")
        campaign_by_channel.setdefault(ch, []).append(c)
        
    return {
        "commercial_leads": leads_raw,
        "enterprise_pilots": pilots_raw,
        "outbound_campaigns": campaigns_raw,
        "campaign_by_channel": campaign_by_channel,
        "institutional_crm": crm_raw,
        "institutional_invoices": invoices_raw,
        "autonomous_officers": officers_raw,
        "specialized_campaigns": specialized
    }


def generate_csuite_fast_track_packet(lead_or_deal, packet_type="RETAINER_FAST_TRACK"):
    company = lead_or_deal.get("organization") or lead_or_deal.get("client_name") or lead_or_deal.get("company_name") or "Enterprise Partner"
    contact = lead_or_deal.get("contact_name") or lead_or_deal.get("poc_contact") or lead_or_deal.get("lead_executive") or "Executive Leadership"
    email = lead_or_deal.get("work_email") or lead_or_deal.get("executive_email") or "csuite@" + company.lower().replace(" ", "") + ".com"
    focus = lead_or_deal.get("trading_focus") or lead_or_deal.get("industry_sector") or lead_or_deal.get("tier") or "Frontier Computing, AI & Hardware Optimization"
    deal_id = lead_or_deal.get("deal_id") or f"FAST-TRACK-{abs(hash(company)) % 10000:04d}-2026"
    
    total_val = lead_or_deal.get("annual_contract_value_usd") or lead_or_deal.get("total_sow_usd") or 1250000.0
    retainer_val = lead_or_deal.get("retainer_usd") or (total_val * 0.20 if total_val > 100000 else 50000.0)
    
    today_str = datetime.date.today().strftime("%B %d, %Y")
    due_str = (datetime.date.today() + datetime.timedelta(days=14)).strftime("%B %d, %Y")
    
    packet_md = f"""# 🏛️ INSTITUTIONAL C-SUITE FAST-TRACK ONBOARDING PACKET
**WhatsHot, Inc.** · Wyoming Corporation `{WYOMING_CERT}`  
*In Partnership with the {NON_PROFIT_PARTNER}*  
**Principal Investigator & Founder:** {FOUNDER_PI}  
**Chief Autonomous Officer:** {CAO_NAME}  
**Packet Reference:** `PKT-{deal_id}`  
**Issue Date:** {today_str} · **Payment Terms:** Net 14 (Settlement Due: {due_str})

---

## SECTION 1: EXECUTIVE BRIEFING & TECHNICAL SPECIFICATION

### Target Enterprise: **{company}**
- **Executive Recipient:** {contact} ({email})
- **Technical & Industry Focus:** {focus}
- **Autonomous Architecture Access:** Triqee Production Studios (Class F Autonomous Cluster & Dedicated VPC)
- **PI Direct Hotline:** Jon Vierk (307-285-9920 · `jon@triqee.com`)

### Executive Overview & Strategic Value Proposition:
WhatsHot, Inc. in coordination with IMQbd provides `{company}` with an accelerated enterprise onboarding track to deploy, benchmark, and scale frontier mathematical, quantum-resonant, and neuro-symbolic algorithms. Under this fast-track protocol, `{company}` receives dedicated sandbox environments, low-latency API access, private C++/Rust SDK modules, and collaborative co-design sprints directly overseen by Chief Autonomous Officer Trixee and Principal Investigator Jon Vierk.

---

## SECTION 2: BILATERAL MUTUAL NON-DISCLOSURE AGREEMENT (MNDA)

This Bilateral Mutual Non-Disclosure Agreement ("Agreement") is entered into as of **{today_str}**, by and between:
1. **WhatsHot, Inc.**, a Wyoming Corporation (Entity ID: `{WYOMING_CERT}`), having its principal executive registry in Wyoming, USA, and
2. **{company}** ("Evaluating Enterprise"), having its principal executive offices associated with {contact} ({email}).

### Key Terms:
1. **Confidential Information**: Includes all proprietary software, tensor kernels, neuro-symbolic architectures, financial/settlement records, patent disclosures, trade secrets, and proprietary customer benchmark data exchanged under this engagement.
2. **Zero-Leakage Sandbox Isolation**: WhatsHot, Inc. guarantees strict multi-tenant isolation, cryptographically segregated API signing keys, and zero model training on `{company}`'s proprietary inputs.
3. **Intellectual Property Rights**: All background IP, patents, and mathematical solvers created by WhatsHot, Inc. / IMQbd remain the sole property of WhatsHot, Inc. under 35 U.S.C. § 200 and applicable Wyoming corporate law. `{company}` retains 100% sole ownership of all its proprietary data, proprietary telemetry, and internal domain models.
4. **Governing Law & Jurisdiction**: This Agreement shall be governed by and construed in accordance with the laws of the State of Wyoming, USA.

---

## SECTION 3: STATEMENT OF WORK (SOW) & RETAINER SETTLEMENT SCHEDULE

| Milestone / Deliverable | Technical Scope | Total Enterprise Value | Fast-Track Retainer (Due Now) |
| :--- | :--- | :--- | :--- |
| **Phase 1: Retainer & Sandbox Provisioning** | Dedicated Isolated VPC, Private SDK Access, 10,000 Production Queries, Co-Design Sprint | ${total_val:,.2f} USD | **${retainer_val:,.2f} USD** |
| **Phase 2: Full Production Conversion** | 100% of Phase 1 Retainer (${retainer_val:,.2f} USD) is credited directly toward the Annual Production License upon completion. | Included in ARR | Credited 100% |

**TOTAL UPFRONT RETAINER SETTLEMENT REQUIRED:** `${retainer_val:,.2f} USD`

---

## SECTION 4: OFFICIAL WIRE & ACH SETTLEMENT INSTRUCTIONS

All commercial payments clear to the primary corporate depository of WhatsHot, Inc. under statutory Class F sovereign treasury controls:

- **Beneficiary Legal Entity:** `{COMPANY_NAME}`
- **Corporate Registration:** State of Wyoming · Entity `{WYOMING_CERT}`
- **Depository Bank:** `{PRIMARY_BANK}`
- **Bank Physical Address:** `{BANK_ADDRESS}`
- **Routing Transit Number (ABA / ACH / Wire):** `{BANK_ROUTING}`
- **Account Number:** `{BANK_ACCT_MASKED}` *(Unmasked wire digits transmitted via secure phone/encrypted portal)*
- **SWIFT / BIC (International):** `{SWIFT_BIC}`
- **Wire Reference / Memo:** `RETAINER-{deal_id} / {company}`

### Alternative Web3 / Digital Settlement (Base L2 Native USDC):
- **Network:** Base L2 (Chain ID: 8453)
- **Token Contract (Native USDC):** `{BASE_L2_USDC}`
- **Treasury Multi-Sig Settlement Address:** `{BASE_L2_SETTLEMENT}`

---

## SECTION 5: FORMAL EXECUTION & SIGNATURE BLOCK

**FOR WHATSHOT, INC. & IMQbd 501(c)(3):**  
*(Executed under Class F Majority Sovereign Authority)*  

___________________________________________________  
**Jon Vierk**, Founder & Principal Investigator  
Date: {today_str}  

___________________________________________________  
**Trixee**, Chief Autonomous Officer (CAO)  
Date: {today_str}  

**ACKNOWLEDGED & ACCEPTED FOR {company.upper()}:**  

___________________________________________________  
Authorized Signature  
Name: **{contact}**  
Title: Executive Officer / Managing Director  
Date: ________________________  
"""
    return packet_md.strip()


def run_accelerator():
    print("=" * 80)
    print("🚀 TRIXEE CAO: INSTITUTIONAL INBOUND RETAINER ACCELERATOR STARTING")
    print(f"Timestamp: {datetime.datetime.now().isoformat()}")
    print("=" * 80)
    
    # Step 1: Scan Database
    print("\n[STEP 1] Scanning SQLite Database (gemini_agent_dashboard.db)...")
    db_data = scan_database()
    leads = db_data["commercial_leads"]
    pilots = db_data["enterprise_pilots"]
    campaigns = db_data["outbound_campaigns"]
    crm = db_data["institutional_crm"]
    invoices = db_data["institutional_invoices"]
    officers = db_data["autonomous_officers"]
    specialized = db_data["specialized_campaigns"]
    
    print(f"  -> Commercial Leads Extracted: {len(leads)}")
    print(f"  -> Enterprise Pilots Extracted: {len(pilots)}")
    print(f"  -> Outbound Campaign Records: {len(campaigns)}")
    print(f"  -> Institutional CRM Accounts: {len(crm)}")
    print(f"  -> Institutional Invoices: {len(invoices)}")
    print(f"  -> Autonomous Officers: {len(officers)}")
    for s_name, s_rows in specialized.items():
        print(f"  -> Specialized Table '{s_name}': {len(s_rows)} records")
        
    # Step 2: Microsoft Graph API Sweep
    print("\n[STEP 2] Connecting to Microsoft Graph API for Inbox Sweep...")
    graph_creds = load_graph_credentials()
    inbox_results = fetch_graph_inbox_messages(graph_creds)
    print(f"  -> Graph Inbox Status: {inbox_results.get('status')}")
    print(f"  -> Messages Fetched: {inbox_results.get('total_messages', 0)}")
    
    p0_messages = [m for m in inbox_results.get("messages", []) if m.get("priority") == "P0_IMMEDIATE"]
    print(f"  -> P0 Priority Executive Inbound Messages: {len(p0_messages)}")
    for pm in p0_messages:
        print(f"     * [{pm['received_at']}] {pm['sender_name']} <{pm['sender_email']}>: {pm['subject']}")
        
    # Step 3: Generate C-Suite Fast-Track Onboarding Packets
    print("\n[STEP 3] Auto-Generating C-Suite Fast-Track Onboarding Packets...")
    PACKETS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    generated_packets = []
    
    # Generate for high-priority invoice deals
    for inv in invoices:
        company_clean = inv["company_name"].replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "").replace(".", "")
        filename = f"ONBOARDING_PACKET_{inv['deal_id']}_{company_clean}.md"
        pkt_content = generate_csuite_fast_track_packet(inv, packet_type="INVOICE_FAST_TRACK")
        file_path = PACKETS_OUTPUT_DIR / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(pkt_content)
        generated_packets.append({
            "target": inv["company_name"],
            "deal_id": inv["deal_id"],
            "contact": inv["lead_executive"],
            "email": inv["executive_email"],
            "total_value_usd": inv["total_sow_usd"],
            "retainer_usd": inv["retainer_usd"],
            "file_path": str(file_path),
            "filename": filename
        })
        print(f"  -> Generated: {filename} (${inv['retainer_usd']:,.0f} Retainer)")
        
    # Generate for top qualified commercial leads & campaign targets
    priority_leads = [
        lead for lead in leads 
        if lead.get("status") in ["OUTREACH_PACKAGED", "INBOX_DISPATCH_TRIAGED_HIGH_PRIORITY", "MSA_SIGNED_RETAINER_SETTLED"]
        or "SUPERMAJOR" in str(lead.get("status"))
        or "TITAN" in str(lead.get("status"))
    ]
    
    print(f"  -> Packaging {len(priority_leads)} Priority Commercial Leads into C-Suite Packets...")
    for idx, pl in enumerate(priority_leads[:15], 1):
        org = pl.get("organization", f"Lead-{pl['id']}")
        org_clean = org.replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "").replace(".", "")
        deal_id = f"LEAD-TRQ-{pl['id']:03d}"
        filename = f"ONBOARDING_PACKET_{deal_id}_{org_clean}.md"
        pkt_content = generate_csuite_fast_track_packet({
            "organization": org,
            "contact_name": pl.get("contact_name", "Head of Frontier Tech"),
            "work_email": pl.get("work_email", ""),
            "trading_focus": pl.get("trading_focus", "Enterprise AI & Autonomous Systems"),
            "deal_id": deal_id,
            "annual_contract_value_usd": 1250000.0,
            "retainer_usd": 250000.0
        })
        file_path = PACKETS_OUTPUT_DIR / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(pkt_content)
        generated_packets.append({
            "target": org,
            "deal_id": deal_id,
            "contact": pl.get("contact_name"),
            "email": pl.get("work_email"),
            "total_value_usd": 1250000.0,
            "retainer_usd": 250000.0,
            "file_path": str(file_path),
            "filename": filename
        })

    # Step 4: Export Complete Inbound Intelligence Report
    print("\n[STEP 4] Exporting Inbound Intelligence Report (JSON)...")
    report_data = {
        "report_metadata": {
            "title": "TRIXEE CAO INSTITUTIONAL INBOUND RETAINER INTELLIGENCE REPORT",
            "generated_at": datetime.datetime.now().isoformat(),
            "wyoming_corporate_cert": WYOMING_CERT,
            "piermont_bank_routing": BANK_ROUTING,
            "cao_identity": "Trixee (trixee@triqee.com)",
            "founder_pi": "Jon Vierk (jon@triqee.com)",
            "active_campaign_channels_count": len(db_data["campaign_by_channel"]),
            "database_source": str(BACKEND_DB_PATH if BACKEND_DB_PATH.exists() else ROOT_DB_PATH)
        },
        "executive_summary": {
            "total_commercial_leads": len(leads),
            "total_enterprise_pilots": len(pilots),
            "total_outbound_campaign_records": len(campaigns),
            "total_crm_pipeline_accounts": len(crm),
            "total_pipeline_contract_value_usd": sum(float(r.get("annual_contract_value_usd") or 0) for r in crm),
            "total_invoices_ready": len(invoices),
            "total_immediate_retainer_invoiced_usd": sum(float(r.get("retainer_usd") or 0) for r in invoices),
            "inbox_messages_scanned": inbox_results.get("total_messages", 0),
            "generated_onboarding_packets_count": len(generated_packets)
        },
        "campaign_channel_breakdown": {
            channel: len(records) for channel, records in db_data["campaign_by_channel"].items()
        },
        "graph_api_inbox_telemetry": inbox_results,
        "institutional_invoices_catalog": invoices,
        "csuite_onboarding_packets_catalog": generated_packets,
        "sample_commercial_leads_high_priority": priority_leads[:20],
        "enterprise_pilot_tiers_summary": {
            pilot["tier"]: len([p for p in pilots if p.get("tier") == pilot["tier"]])
            for pilot in pilots[:20]
        }
    }
    
    with open(REPORT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
        
    print(f"  -> Intelligence Report Exported to: {REPORT_OUTPUT_PATH}")
    
    conv_dir = Path(r"C:\Users\VHome\.gemini\antigravity\brain\5f87ac22-8b1c-4f23-bb6f-9dad5c351437")
    if conv_dir.exists():
        conv_report_path = conv_dir / "triqee_csuite_inbound_retainer_report.json"
        with open(conv_report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"  -> Mirrored Report into Artifacts: {conv_report_path}")
        
    print("\n" + "=" * 80)
    print("✅ INSTITUTIONAL SWEEP & RETAINER FAST-TRACK COMPLETE!")
    print(f"Generated Packets: {len(generated_packets)} | Total Retainers Staged: ${sum(p['retainer_usd'] for p in generated_packets):,.2f}")
    print("=" * 80)
    
    return report_data


if __name__ == "__main__":
    run_accelerator()
