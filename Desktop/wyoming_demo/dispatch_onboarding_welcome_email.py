#!/usr/bin/env python3
"""
Dispatch Genesis Onboarding Welcome Email to jon@triqee.com via verified AWS SES.
"""

import sys
import os
import boto3
import secrets
from botocore.exceptions import ClientError

# Ensure UTF-8 stdout
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

AWS_REGION = "us-east-1"
SENDER = "jon@triqee.com"
RECIPIENTS = ["jon@triqee.com"]

def dispatch_genesis_welcome():
    print(f"Connecting to AWS SES ({AWS_REGION})...")
    ses = boto3.client('ses', region_name=AWS_REGION)
    
    api_key = f"tq_live_{secrets.token_hex(16)}"
    
    subject = "🎉 Welcome to Triqee // Your Quantum Genesis 5,000 $TQ Grant & API Key"
    
    body_text = f"""Welcome to Triqee, Jon!

Your Genesis Developer Grant claim has been verified and provisioned.

YOUR PRODUCTION CREDENTIALS:
- Recipient: jon@triqee.com
- Granted Tier: Tier 2 (Quants & Researchers)
- Allocated Gas Balance: 5,000 $TQ (~$500 Compute Credit)
- Production API Key: {api_key}
- Base L2 Token Contract: 0xTQ00000099200000000000000000000000000001
- CERN Zenodo DOI: https://doi.org/10.5281/zenodo.23045297

GETTING STARTED IN PYTHON:
pip install triqee

import triqee
client = triqee.Client(api_key="{api_key}")
print("Sovereign Node Health:", client.health())

LIVE INTERACTIVE PORTALS:
- QuantVault 60 FPS Terminal: http://localhost:3000/TRIQEE_QUANTVAULT_LIVE_EXECUTION_TERMINAL.html
- Pilot Ingestion Engine: http://localhost:3000/TRIQEE_INSTANT_PILOT_PORTAL.html
- Genesis Airdrop Portal: http://localhost:3000/TRIQEE_GENESIS_AIRDROP_PORTAL.html

If you have any questions or require custom SLA scaling, reach out directly to contact@triqee.com.

Best regards,

Triqee Autonomous Intelligence Desk
WhatsHot, Inc. // Triqee Omniverse DAO LLC (Wyoming Entity: DA-000000992)
"""

    body_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #030712; color: #f8fafc; margin: 0; padding: 24px; }}
  .card {{ background-color: #0f172a; border: 1px solid #38bdf833; border-radius: 12px; padding: 28px; max-width: 600px; margin: 0 auto; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
  .badge {{ background-color: #06b6d41a; border: 1px solid #06b6d4; color: #06b6d4; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; font-family: monospace; display: inline-block; }}
  .title {{ font-size: 24px; font-weight: 800; color: #ffffff; margin-top: 12px; margin-bottom: 8px; }}
  .highlight {{ color: #06b6d4; font-weight: bold; }}
  .code-box {{ background-color: #020617; border: 1px solid #38bdf833; border-radius: 8px; padding: 16px; font-family: monospace; font-size: 13px; color: #38bdf8; margin: 18px 0; word-break: break-all; }}
  .btn {{ background-color: #06b6d4; color: #020617; padding: 12px 24px; border-radius: 8px; font-weight: bold; text-decoration: none; display: inline-block; margin-top: 12px; font-size: 13px; letter-spacing: 0.5px; }}
  .footer {{ margin-top: 24px; border-top: 1px solid #334155; padding-top: 16px; font-size: 11px; color: #64748b; font-family: monospace; }}
</style>
</head>
<body>
  <div class="card">
    <div class="badge">✦ QUANTUM GENESIS GRANT PROVISIONED ✦</div>
    <h1 class="title">Welcome to Triqee, Jon!</h1>
    <p style="color: #94a3b8; font-size: 14px; line-height: 1.6;">
      Your Genesis Developer Grant claim on <strong style="color:#fff;">triqee.com/airdrop</strong> has been verified. You have been provisioned <strong style="color:#10b981;">5,000 $TQ Compute Gas tokens</strong> (~$500 value) for immediate execution across our multi-vendor QPU gateway.
    </p>

    <div class="code-box">
      <div style="color: #64748b; font-size: 11px; margin-bottom: 6px;">// YOUR DEDICATED PRODUCTION API CREDENTIALS</div>
      <div><strong>API Key:</strong> <span style="color: #facc15;">{api_key}</span></div>
      <div><strong>Granted Balance:</strong> <span style="color: #4ade80;">5,000 $TQ Tokens</span> (Base L2)</div>
      <div><strong>Contract:</strong> 0xTQ00000099200000000000000000000000000001</div>
      <div><strong>CERN DOI:</strong> <a href="https://doi.org/10.5281/zenodo.23045297" style="color: #06b6d4;">10.5281/zenodo.23045297</a></div>
    </div>

    <h3 style="color: #ffffff; font-size: 15px; margin-bottom: 8px;">🚀 Quickstart via Python SDK:</h3>
    <div style="background-color: #020617; border: 1px solid #1e293b; border-radius: 6px; padding: 12px; font-family: monospace; font-size: 12px; color: #a855f7;">
      pip install triqee<br/>
      import triqee<br/>
      client = triqee.Client(api_key="{api_key}")<br/>
      print("Status:", client.health())
    </div>

    <div style="text-align: center; margin-top: 20px;">
      <a href="https://www.triqee.com/portal" class="btn">LAUNCH DEVELOPER PORTAL →</a>
    </div>

    <div class="footer">
      WhatsHot, Inc. // Triqee Omniverse DAO LLC (Wyoming Entity: DA-000000992)<br/>
      Statutory Consumptive Utility Token under Wyoming W.S. 34-29-106.
    </div>
  </div>
</body>
</html>
"""

    try:
        response = ses.send_email(
            Source=f"Triqee Quantum Gateway <{SENDER}>",
            Destination={'ToAddresses': RECIPIENTS},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Text': {'Data': body_text, 'Charset': 'UTF-8'},
                    'Html': {'Data': body_html, 'Charset': 'UTF-8'}
                }
            }
        )
        msg_id = response.get('MessageId')
        print(f"🎉 [SES EMAIL SENT SUCCESSFULLY]: MessageId = {msg_id}")
        return True, msg_id
    except ClientError as e:
        print(f"❌ [SES ERROR]: {e.response['Error']['Message']}")
        return False, str(e)

if __name__ == "__main__":
    dispatch_genesis_welcome()
