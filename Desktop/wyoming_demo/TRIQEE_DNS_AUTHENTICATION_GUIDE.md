# Triqee Domain DNS Authentication Guide
## 100% Inbound/Outbound Deliverability Setup for `triqee.com`

To ensure emails sent from **`jon@triqee.com`** bypass enterprise spam filters and deliver directly to inboxes at Citadel, NVIDIA, Lockheed Martin, and Two Sigma without bouncing, add the following 6 DNS records in your domain registrar / DNS provider (Cloudflare, Route53, GoDaddy, or Namecheap):

---

### DNS Records Table

| # | Record Type | Host / Name | Value / Target | TTL | Purpose |
| :- | :--- | :--- | :--- | :--- | :--- |
| **1** | **CNAME** | `x4tcloiasvwdlmct6whapmlgwnxzdmxp._domainkey.triqee.com` | `x4tcloiasvwdlmct6whapmlgwnxzdmxp.dkim.amazonses.com` | Auto / 300 | AWS SES DKIM Key 1 |
| **2** | **CNAME** | `e3ywvoddvnyveppsucpietgjjpyoi3sd._domainkey.triqee.com` | `e3ywvoddvnyveppsucpietgjjpyoi3sd.dkim.amazonses.com` | Auto / 300 | AWS SES DKIM Key 2 |
| **3** | **CNAME** | `32obpdqt6j2cyspjynoavdvnri4hsxpv._domainkey.triqee.com` | `32obpdqt6j2cyspjynoavdvnri4hsxpv.dkim.amazonses.com` | Auto / 300 | AWS SES DKIM Key 3 |
| **4** | **TXT** | `_amazonses.triqee.com` | `39xluSqjnGx6u4Z1yrGuXZg9C8DKQGtHdBvz+Hfk/oA=` | Auto / 300 | AWS SES Domain Verification |
| **5** | **TXT** | `@` (or `triqee.com`) | `v=spf1 include:amazonses.com ~all` | Auto / 300 | SPF Anti-Spoofing Record |
| **6** | **TXT** | `_dmarc.triqee.com` | `v=DMARC1; p=none; rua=mailto:jon@triqee.com` | Auto / 300 | DMARC Compliance Policy |

---

### Step-by-Step Instructions

1. **Log in to your Domain Registrar / DNS Manager** (e.g., Cloudflare, GoDaddy, Namecheap, Google Domains / Squarespace, or AWS Route53).
2. Navigate to **DNS Management** for `triqee.com`.
3. Add the **3 CNAME records** above for DKIM cryptographic signing.
4. Add the **3 TXT records** above for Domain Verification, SPF, and DMARC.
5. Save changes. DNS propagation typically completes in **5 to 15 minutes**.
6. Once propagated, AWS SES will automatically transition `triqee.com` to **Domain-Verified status**, granting full production cryptographic deliverability.
