# DAE-TT-002: Token Terminal Fact Sheet validation (offline scaffold)

This is a **read-only, offline evidence-classification prototype**. It does not connect to Token Terminal, scrape websites, sign transactions, or change the FastAPI gateway.

Run: `python -m unittest -v test_dae_tt002`.

The five pilot assets are Robinhood tokenized NVIDIA, BUIDL, USDC, USDT and a tokenized Treasury product to be selected after source verification.

Input is a JSON list of objects with `asset_id`, `field`, `value`, `vendor_source`, optional `primary_source`, `primary_value`, `checked_at`. Output statuses: VERIFIED, CLAIMED, CONFLICTED, UNKNOWN. VERIFIED currently means **literal string equality with a supplied primary value**, not independent verification that the document is authentic or legally authoritative. Do not use this prototype for legal or investment decisions.

Next steps: provenance capture with document digests and source locators, independent primary-source retrieval, issuer/legal-rights field mapping, adversarial fixtures, and measured baseline benchmark. No real asset validation or latency measurement has been performed.

Safety: no credentials, paid API, wallet connection, trading, deployment, or main-branch modification.
