"""
Triqee Autonomous Intelligence Scanner & Evaluation Engine
==========================================================
Scans trixee@triqee.com inbox, resolves article URLs, and categorizes
breakthroughs across Quantum RF, Room-Temp Diamond NV, Edge AI Kernels,
and Fault-Tolerant qLDPC Computing.
"""

import os
import sys
import json
import re
import requests
import msal
import urllib3
from typing import Dict, Any, List

urllib3.disable_warnings()

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure src is importable
SCRATCH_DIR = r"C:\Users\VHome\.gemini\antigravity\scratch"
if SCRATCH_DIR not in sys.path:
    sys.path.insert(0, SCRATCH_DIR)

from src.headline_taxonomy import evaluate_headline_relevance, TAXONOMY_CATEGORIES

ENV_FILE = r"C:\Users\VHome\.gemini\antigravity\brain\1e598e89-d123-4ab7-9e81-609c4ad28265\.env.trixee_graph"

def fetch_inbox_messages(top_count: int = 30) -> List[Dict[str, Any]]:
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip().strip("\"'")

    app = msal.ConfidentialClientApplication(
        os.getenv("GRAPH_CLIENT_ID"),
        authority=f"https://login.microsoftonline.com/{os.getenv('GRAPH_TENANT_ID')}",
        client_credential=os.getenv("GRAPH_CLIENT_SECRET")
    )
    token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"]).get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    url = f"https://graph.microsoft.com/v1.0/users/trixee@triqee.com/messages?$top={top_count}&$select=id,subject,from,receivedDateTime,bodyPreview,body"
    r = requests.get(url, headers=headers)
    return r.json().get("value", [])

def scan_and_evaluate_inbox(top_count: int = 30):
    msgs = fetch_inbox_messages(top_count)
    http_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    results = []
    print(f"[*] Fetched {len(msgs)} messages. Evaluating against Expanded Quantum & Edge AI Taxonomy...\n")

    for i, m in enumerate(msgs):
        dt = m.get("receivedDateTime", "")
        sender = m.get("from", {}).get("emailAddress", {}).get("address", "")
        subject = m.get("subject", "")
        preview = m.get("bodyPreview", "")
        body = m.get("body", {}).get("content", "")

        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', body)
        resolved_title = ""
        final_url = ""

        # Attempt to resolve the first meaningful URL
        for u in urls[:2]:
            u_clean = u.replace("&amp;", "&")
            try:
                res = requests.get(u_clean, headers=http_headers, allow_redirects=True, timeout=5)
                title_m = re.search(r'<title>(.*?)</title>', res.text, re.IGNORECASE | re.DOTALL)
                if title_m:
                    resolved_title = re.sub(r'\s+', ' ', title_m.group(1)).strip()
                final_url = res.url
                break
            except Exception:
                continue

        text_to_eval = f"{subject} {preview} {resolved_title}"
        eval_res = evaluate_headline_relevance(text_to_eval)

        item = {
            "index": i + 1,
            "date": dt,
            "sender": sender,
            "subject": subject,
            "resolved_title": resolved_title,
            "final_url": final_url,
            "evaluation": eval_res
        }
        results.append(item)

        # Print matched highlights
        if eval_res["matched"]:
            print(f"[{i+1}] MATCHED: {resolved_title or subject or preview[:60]}")
            for cat in eval_res["categories"]:
                print(f"    -> [{cat['priority']}] {cat['label']}")
                print(f"       Matched Keywords: {cat['matched_keywords']}")
            print("-" * 65)

    out_file = os.path.join(SCRATCH_DIR, "trixee_evaluated_intelligence_latest.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[+] Scan Complete. Evaluated report saved to: {out_file}")
    return results

if __name__ == "__main__":
    scan_and_evaluate_inbox(25)
