import unittest
from dae_tt002 import Claim, evaluate, Status

BASE = dict(asset_id="asset-001", field="redemption", value="restricted",
            vendor_source="https://example.org/vendor")

class TestEvidence(unittest.TestCase):
    def test_vendor_only_not_verified(self):
        self.assertEqual(evaluate(Claim(**BASE))["status"], Status.CLAIMED.value)
    def test_matching_primary(self):
        c = Claim(**BASE, primary_source="https://issuer.example/terms",
                  primary_value="restricted", checked_at="2026-11-12T00:00:00Z")
        self.assertEqual(evaluate(c)["status"], Status.VERIFIED.value)
    def test_conflict(self):
        c = Claim(**BASE, primary_source="https://issuer.example/terms",
                  primary_value="unrestricted", checked_at="2026-11-12T00:00:00Z")
        self.assertEqual(evaluate(c)["status"], Status.CONFLICTED.value)
    def test_missing_value(self):
        self.assertEqual(evaluate(Claim(**{**BASE, "value": ""}))["status"], Status.UNKNOWN.value)
    def test_non_https_primary(self):
        c = Claim(**BASE, primary_source="http://issuer.example/terms",
                  primary_value="restricted", checked_at="2026-11-12")
        self.assertEqual(evaluate(c)["status"], Status.CLAIMED.value)
    def test_missing_timestamp(self):
        c = Claim(**BASE, primary_source="https://issuer.example/terms", primary_value="restricted")
        self.assertEqual(evaluate(c)["status"], Status.CLAIMED.value)

if __name__ == "__main__":
    unittest.main()
