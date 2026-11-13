# DAE-RWA-001: first public-source intake — BUIDL

Status: **research intake only, NOT asset verified**. No downloaded primary document was independently hashed in this repository; no chain state, legal title, fund NAV, or custodian holdings were reconciled.

## Source register (public URLs; source statements, not verified conclusions)

- Securitize launch release (2024-03-20): https://investors.securitize.io/news/news-details/2024/BlackRock-Launches-Its-First-Tokenized-Fund-BUIDL-on-the-Ethereum-Network-03-20-2024/default.aspx — describes tokenized fund, qualified investors, Securitize distribution.
- Securitize Q3 2026 investor presentation: https://s21.q4cdn.com/825684987/files/content_files/SECZ-3Q26-Earnings-Presentation_vF.pdf — characterizes BUIDL as a private BVI fund; do not conflate with registered money-market funds.
- Securitize press release (2026-11-12): https://www.prnewswire.com/news-releases/securitize-and-ethena-launch-100-million-liquidity-facility-for-blackrocks-buidl-302937776.html — claims a liquidity facility with $50M initial liquidity and up to $100M capacity; **facility capacity is not fund backing, guaranteed redemption, or cash immediately available**.
- FIA DLT report: https://www.fia.org/sites/default/files/2025-08/FULL%20REPORT%20-%20DLT%20REPORT.pdf — secondary overview of transfer agent, custody, investor eligibility and multi-chain supply.

## Required independent evidence before a verification claim

1. Current fund offering memorandum, subscription agreement and tokenholder register/legal terms, with version/date and issuer provenance.
2. Custodian/administrator confirmations for an identical as-of date and independently corroborated holdings.
3. Authoritative contract registry for each chain and pinned-block supply reconciliation across chains and classes.
4. Redemption terms, eligibility, restrictions, liquidity facility contract and current availability.
5. Auditor/attestation reports and evidence of encumbrances and exceptions.

## Engineering boundary

The `dae_rwa001.py` gate accepts caller-provided source URL, SHA-256 digest, locator, timestamp and independent-review flag. It checks metadata **shape only**. It does not download or authenticate the document, validate its contents, check independence, or verify the asset. The strongest output is `LEGAL_AND_CUSTODY_REVIEW_REQUIRED`, never auto-approval. Any conflicting claim forces escalation.

Run `python -m unittest -v test_dae_rwa001`.
