"""No live Neon required. The QA diagnostic must always fail closed."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from index import app, qa_dsn, _CHECK_SQL


class NeonProbePolicy(unittest.TestCase):
    def test_missing_configuration_fails_closed(self):
        with patch.dict(os.environ, {"FLEX_ENVIRONMENT": "qa", "FLEX_DATABASE_URL": ""}):
            response = TestClient(app).get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "FLEX_QA_NOT_CONFIGURED")

    def test_wrong_database_role_and_plaintext_fail_closed(self):
        for dsn in [
            "postgresql://flex_qa_owner:fake@db.example.org/flex_qa?sslmode=require",
            "postgresql://flex_qa_owner:fake@branch.neon.tech/flex_qa?sslmode=require",
            "postgresql://flex_qa_read_runtime:fake@branch.neon.tech/pms?sslmode=require",
            "postgresql://flex_qa_read_runtime:fake@branch.neon.tech/flex_qa",
            "postgresql://flex_qa_read_runtime:fake@branch.neon.tech/flex_qa?sslmode=disable",
        ]:
            with self.subTest(dsn=dsn.split('@')[-1]):
                with patch.dict(os.environ, {"FLEX_ENVIRONMENT":"qa", "FLEX_DATABASE_URL":dsn}):
                    with self.assertRaises(ValueError):
                        qa_dsn()

    def test_non_qa_fails_closed(self):
        with patch.dict(os.environ, {"FLEX_ENVIRONMENT":"production",
                                       "FLEX_DATABASE_URL":"postgresql://flex_qa_read_runtime:fake@c.neon.tech/flex_qa?sslmode=require"}):
            with self.assertRaises(ValueError):
                qa_dsn()

    def test_no_pms_or_payment_routes(self):
        client = TestClient(app)
        for path in ["/v1/payments", "/v1/payouts", "/v1/onboarding/hotels",
                     "/v1/platform/catalog/skus", "/v1/me"]:
            with self.subTest(path=path):
                self.assertEqual(client.post(path).status_code, 404)

    def test_sql_guard_checks_no_direct_privileges(self):
        self.assertIn("rolbypassrls", _CHECK_SQL)
        self.assertIn("direct_payment_write", _CHECK_SQL)
        self.assertIn("payment_simulator_absent", _CHECK_SQL)
        self.assertIn("direct_draft_write", _CHECK_SQL)


if __name__ == "__main__":
    unittest.main()
