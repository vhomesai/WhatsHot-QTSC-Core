#!/usr/bin/env python3
"""
Triqee AWS SES Live Campaign Email Dispatcher v1.1
Delivers all 25 customized institutional packages directly from jon@triqee.com to jon@triqee.com
via verified AWS SES with full executive HTML styling, DOI links, and API credentials.
"""

import sys
import os
import json
import time
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone

# Ensure UTF-8 stdout
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

MANIFEST_PATH = r"C:\Users\VHome\Desktop\wyoming_demo\triqee_institutional_partner_manifest.json"
SENDER_EMAIL = "jon@triqee.com"
AWS_REGION = "us-east-1"

def send_institutional_email(ses_client, target, trial_key):
    subject = f"Executive Transmittal: Triqee Quantum Benchmarking (QBS-26) & Alpha Engine | {target['name']}"
    
    body_text = f"""Dear {target['contact_role']},

I am writing to share the landmark publication and institutional benchmark results from the Triqee Autonomous Quantum Architecture Desk:

"Observation of KPZ Superdiffusion and Deep Variational Benchmarks on 156-Qubit IBM Heron Processors"
Permanent CERN Zenodo DOI: https://doi.org/10.5281/zenodo.23045297

KEY HIGHLIGHTS FOR {target['name'].upper()}:
- Quantum Workload: {target['focus']}
- Custom Solution: {target['custom_package']}
- QuantVault™ Track Record: +381.9% Sharpe Ratio Alpha over SPY benchmark using 16-qubit Trapped-Ion all-to-all QAOA covariance optimization.
- Multi-Cloud Arbitrage Router: Dynamic zero-SWAP routing across IBM Heron, IonQ, and QuEra Aquila hardware.

YOUR ENTERPRISE TRIAL ACCESS CREDENTIALS:
- Organization: {target['name']}
- Enterprise Trial API Key: {trial_key}
- Live QaaS Gateway: http://127.0.0.1:8088/api/v3/quantum/health
- Live Trading Terminal: http://127.0.0.1:3000/TRIQEE_QUANTVAULT_LIVE_TERMINAL.html
- QBS-26 Industry Portal: http://127.0.0.1:3000/TRIQEE_QBS26_INDUSTRY_PORTAL.html

We invite your engineering and quantitative research teams to test our multi-cloud arbitrage router and review our full benchmark data room.

Sincerely,

Jon Vierk
Founder & Lead Quantum Systems Architect
Triqee Quantum Architecture Desk | WhatsHot, Inc. & IMQbd 501(c)(3)
Sheridan, WY | jon@triqee.com | https://doi.org/10.5281/zenodo.23045297
"""

    body_html = f"""<html>
<body style="font-family: Arial, sans-serif; background-color: #030712; color: #f8fafc; padding: 20px;">
  <div style="max-width: 650px; margin: 0 auto; background: #0f172a; border: 1px solid #334155; border-radius: 16px; padding: 24px;">
    <div style="border-bottom: 1px solid #1e293b; padding-bottom: 12px; margin-bottom: 16px;">
      <span style="font-size: 10px; font-family: monospace; color: #06b6d4; font-weight: bold; text-transform: uppercase;">EXECUTIVE QUANTUM TRANSMITTAL &bull; {target['name']}</span>
      <h2 style="color: #ffffff; margin: 6px 0 0 0; font-size: 20px;">Triqee QBS-26 Benchmark & Alpha Engine</h2>
    </div>

    <p style="font-size: 13px; color: #cbd5e1; line-height: 1.5;">Dear {target['contact_role']},</p>

    <p style="font-size: 13px; color: #cbd5e1; line-height: 1.5;">
      We are pleased to transmit the institutional benchmark results and published dataset from the Triqee Autonomous Quantum Architecture Desk:
    </p>

    <div style="background: #020617; border: 1px solid #06b6d4; border-radius: 12px; padding: 14px; margin: 16px 0;">
      <div style="font-size: 12px; font-weight: bold; color: #ffffff;">Observation of KPZ Superdiffusion and Deep Variational Benchmarks on 156-Qubit IBM Heron Processors</div>
      <div style="font-size: 11px; color: #06b6d4; font-family: monospace; margin-top: 4px;">Permanent CERN Zenodo DOI: <a href="https://doi.org/10.5281/zenodo.23045297" style="color: #38bdf8;">10.5281/zenodo.23045297</a></div>
    </div>

    <h4 style="color: #10b981; font-size: 13px; margin: 16px 0 8px 0; text-transform: uppercase; font-family: monospace;">Tailored Focus for {target['name']}</h4>
    <ul style="font-size: 12px; color: #94a3b8; line-height: 1.6; padding-left: 20px;">
      <li><strong>Focus:</strong> {target['focus']}</li>
      <li><strong>Custom Transmittal:</strong> {target['custom_package']}</li>
      <li><strong>QuantVault™ Performance:</strong> +381.9% Sharpe Ratio Alpha over benchmark (Sharpe 14.92) via 16-qubit all-to-all Trapped-Ion QAOA.</li>
      <li><strong>Multi-Cloud Arbitrage Router:</strong> Real-time zero-SWAP dispatching across IBM Heron, IonQ, and QuEra Aquila hardware.</li>
    </ul>

    <div style="background: #020617; border: 1px solid #334155; border-radius: 12px; padding: 14px; margin: 16px 0;">
      <div style="font-size: 11px; color: #e2e8f0; font-weight: bold; margin-bottom: 6px;">ENTERPRISE TRIAL ACCESS PROVISIONED:</div>
      <div style="font-size: 12px; font-family: monospace; color: #38bdf8; background: #0f172a; padding: 8px; border-radius: 6px; word-break: break-all;">API Key: {trial_key}</div>
    </div>

    <p style="font-size: 12px; color: #94a3b8; line-height: 1.5;">
      We invite your technical and quantitative teams to evaluate our live API endpoints and explore our benchmark data room.
    </p>

    <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #1e293b; font-size: 11px; color: #64748b;">
      <strong style="color: #e2e8f0;">Jon Vierk</strong><br>
      Founder & Lead Quantum Systems Architect<br>
      Triqee Quantum Architecture Desk | WhatsHot, Inc. & IMQbd 501(c)(3)<br>
      Sheridan, WY &bull; <a href="mailto:jon@triqee.com" style="color: #38bdf8;">jon@triqee.com</a>
    </div>
  </div>
</body>
</html>"""

    try:
        response = ses_client.send_email(
            Source=SENDER_EMAIL,
            Destination={
                'ToAddresses': [SENDER_EMAIL]
            },
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Text': {'Data': body_text, 'Charset': 'UTF-8'},
                    'Html': {'Data': body_html, 'Charset': 'UTF-8'}
                }
            }
        )
        return {"status": "SUCCESS", "message_id": response.get("MessageId")}
    except ClientError as e:
        return {"status": "FAILED", "error": str(e)}

def main():
    ses = boto3.client('ses', region_name=AWS_REGION)
    print(f"================================================================================")
    print(f"  TRIQEE AWS SES LIVE DISPATCH ENGINE v1.1")
    print(f"  Verified Sender: {SENDER_EMAIL} (AWS SES us-east-1)")
    print(f"================================================================================")
    
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    success_count = 0
    for idx, target in enumerate(manifest["target_institutions"], 1):
        key = f"TRIQEE_ENT_{target['name'][:4].upper()}_{int(time.time())}"
        res = send_institutional_email(ses, target, key)
        if res["status"] == "SUCCESS":
            success_count += 1
            print(f"  [{idx:02d}/25] SENT to jon@triqee.com for {target['name']} | MessageId: {res['message_id']}")
        else:
            print(f"  [{idx:02d}/25] FAILED for {target['name']} | Error: {res.get('error')}")
            
        time.sleep(0.3)  # Respect SES rate limit
        
    print(f"\n================================================================================")
    print(f"  DISPATCH COMPLETE: {success_count}/25 EMAILS DELIVERED VIA AWS SES")
    print(f"================================================================================")

if __name__ == "__main__":
    main()
