import os
import unittest

from fastapi.testclient import TestClient

os.environ["WHOT_ENTERPRISE_API_KEYS"] = "test-enterprise-key:internal-testing"

import app


class TestTelemetryGateway(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._client_context = TestClient(app.app)
        cls.client = cls._client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._client_context.__exit__(None, None, None)

    def test_health_check(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_audit_requires_valid_api_key(self):
        response = self.client.post(
            "/v1/audit/ternary-check",
            json={"asset_id": "DA-000000992"},
            headers={"X-API-Key": "invalid-key"},
        )
        self.assertEqual(response.status_code, 403)

    def test_audit_accepts_configured_api_key(self):
        response = self.client.post(
            "/v1/audit/ternary-check",
            json={"asset_id": "DA-000000992"},
            headers={"X-API-Key": "test-enterprise-key"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["wyoming_asset_id"], "DA-000000992")
        self.assertEqual(body["kernel_engine"], "Non-Abelian SU(3) Qutrit")
        self.assertEqual(body["client_name"], "internal-testing")
        self.assertIn("request_hash", body)


if __name__ == "__main__":
    unittest.main()
