"""Existing FLEX API wiring and least-privilege fail-closed guards."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from index import app, qa_dsn, _CHECK_SQL


class NeonProbePolicy(unittest.TestCase):
    def test_deployed_flex_modules_match_single_source_of_truth(self):
        """No independent copy of commercial logic is allowed to drift."""
        root = Path(__file__).resolve().parents[3]
        names = (
            "flex_control_plane.py", "flex_foundation.py",
            "flex_partner_portal.py", "flex_onboarding.py",
            "flex_catalog_admin.py",
        )
        for name in names:
            with self.subTest(name=name):
                original = root / "services" / "api" / "app" / name
                shipped = root / "apps" / "flex-api-qa" / "app" / name
                self.assertEqual(shipped.read_bytes(), original.read_bytes())

    def test_no_pms_package_import_in_deployed_control_plane(self):
        shipped = (Path(__file__).resolve().parents[1] / "app" /
                   "flex_control_plane.py").read_text()
        self.assertNotIn("from .db import", shipped)
        self.assertNotIn("from .pms", shipped)

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
                     "/v1/platform/catalog/skus"]:
            with self.subTest(path=path):
                self.assertEqual(client.post(path).status_code, 404)

    def test_existing_business_read_routes_reused(self):
        methods = {
            (method, route.path)
            for route in app.routes
            for method in getattr(route, "methods", ())
        }
        for path in (
            "/v1/me", "/v1/hotels", "/v1/catalog",
            "/v1/hotels/{hotel_id}/subscription",
            "/v1/hotels/{hotel_id}/invoices",
            "/v1/partner/me/earnings",
            "/v1/platform/partner-earnings-summary",
            "/v1/platform/catalog",
            "/v1/platform/catalog/skus/{sku}/versions",
            "/v1/platform/subscription-drafts",
        ):
            self.assertIn(("GET", path), methods)
        for method, path in methods:
            if path.startswith("/v1/"):
                self.assertEqual(method, "GET")
            self.assertNotIn("payment", path)
            self.assertNotIn("payout", path)
            self.assertNotIn("settlement", path)

    def test_admin_catalog_is_readable_but_never_writable_in_default_qa(self):
        client = TestClient(app)
        for path in ("/v1/platform/catalog", "/v1/platform/subscription-drafts"):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 401)
                self.assertEqual(client.post(path, json={}).status_code, 404)
        for route in app.routes:
            if getattr(route, "path", "").startswith("/v1/platform/"):
                self.assertNotIn("POST", getattr(route, "methods", set()))

    def test_core_identity_without_token_fails_closed(self):
        r = TestClient(app).get("/v1/me")
        self.assertEqual(r.status_code, 401)

    def test_sql_guard_checks_no_direct_privileges(self):
        self.assertIn("rolbypassrls", _CHECK_SQL)
        self.assertIn("direct_payment_write", _CHECK_SQL)
        self.assertIn("payment_simulator_absent", _CHECK_SQL)
        self.assertIn("direct_draft_write", _CHECK_SQL)


if __name__ == "__main__":
    unittest.main()
