import unittest
from dae_rwa001 import Evidence, evaluate, digest, GATES

VALID = dict(status="VERIFIED", source_url="https://issuer.example/terms",
             document_sha256=digest(b"sample primary document"),
             source_locator="section 3", observed_at="2026-11-12T23:00:00Z",
             independent=True)

class TestRWA(unittest.TestCase):
    def test_empty_is_insufficient(self):
        self.assertEqual(evaluate("BUIDL", [])["decision"], "INSUFFICIENT_EVIDENCE")
    def test_vendor_only_is_unverified(self):
        self.assertEqual(evaluate("BUIDL", [Evidence("holder_rights", "VERIFIED")])["gates"]["holder_rights"], "UNVERIFIED")
    def test_provenance_is_review_not_legal_certification(self):
        records = [Evidence(g, **VALID) for g in GATES]
        out = evaluate("BUIDL", records)
        self.assertEqual(out["decision"], "LEGAL_AND_CUSTODY_REVIEW_REQUIRED")
        self.assertFalse(out["independent_legal_verification"])
    def test_conflict_veto(self):
        records = [Evidence(g, **VALID) for g in GATES]
        records.append(Evidence("holder_rights", "CONFLICTED"))
        self.assertEqual(evaluate("BUIDL", records)["decision"], "ESCALATE")
    def test_bad_digest_does_not_pass(self):
        bad = {**VALID, "document_sha256": "x" * 64}
        self.assertEqual(evaluate("BUIDL", [Evidence("asset_existence", **bad)])["gates"]["asset_existence"], "UNVERIFIED")
    def test_invalid_gate_rejected(self):
        with self.assertRaises(ValueError):
            evaluate("BUIDL", [Evidence("not_a_gate", "UNKNOWN")])
    def test_no_timezone_does_not_pass(self):
        bad = {**VALID, "observed_at": "2026-11-12T23:00:00"}
        self.assertEqual(evaluate("BUIDL", [Evidence("custody", **bad)])["gates"]["custody"], "UNVERIFIED")

if __name__ == "__main__":
    unittest.main()
