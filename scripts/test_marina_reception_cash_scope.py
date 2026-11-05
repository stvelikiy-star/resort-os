"""P0: shared reception can only record actually received CASH for own hotel.

No new payment endpoints. Manager-only cancellation finance review stays unavailable
to RECEPTION, and source locked RC3 admission is unchanged.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from app import auth, reservation_payments as payments  # noqa: E402


class ReceptionCashTests(unittest.TestCase):
    def setUp(self):
        self.reception = {
            "role": "RECEPTION", "module_permissions": ["PMS", "RESERVATIONS"],
        }
        self.scope = [
            patch.object(payments, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", True),
            patch.object(auth, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", True),
            patch.object(auth, "MARINA_TENANT_CONTEXT_ENABLED", True),
            patch.object(auth, "PROPERTY_CODE", "MARINA_BROWSER_CI"),
            patch.object(auth, "COOKIE_SECURE", True),
            patch.dict(os.environ, {
                "APP_ENV": "staging",
                "MARINA_SHARED_RECEPTION_CASH_P0_ENABLED": "true",
                "MARINA_SHARED_RECEPTION_CASH_P0_CONFIRM": "REVIEWED_RECEPTION_CASH_STAGING_ONLY",
            }),
        ]
        for scope in self.scope:
            scope.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(self.scope)])

    def test_cash_only_with_reservations_grant(self):
        payments.enforce_reception_cash_scope(self.reception)
        payments.enforce_reception_cash_scope(self.reception, method="CASH")
        for method, paid_at in (
            ("BANK_TRANSFER", None), ("CARD_POS", None),
            ("OTHER", None), ("CASH", datetime.now(timezone.utc)),
        ):
            with self.subTest(method=method, paid_at=paid_at), self.assertRaises(HTTPException) as result:
                payments.enforce_reception_cash_scope(
                    self.reception, method=method, paid_at=paid_at)
            self.assertEqual(result.exception.status_code, 403)
            self.assertEqual(result.exception.detail["code"], "RECEPTION_CASH_ONLY")
        # Management retains all previously reviewed manual payment methods.
        payments.enforce_reception_cash_scope(
            {"role": "MANAGER", "module_permissions": []},
            method="BANK_TRANSFER",
        )

    def test_owner_revocation_rechecks_effective_session_grants(self):
        reception = {**self.reception, "module_permissions": ["PMS"]}
        with self.assertRaises(HTTPException) as result:
            payments.enforce_reception_cash_scope(reception, method="CASH")
        self.assertEqual(result.exception.status_code, 403)
        self.assertEqual(result.exception.detail["code"], "RECEPTION_RESERVATIONS_GRANT_REQUIRED")

    def test_legacy_demo_production_and_missing_approval_closed(self):
        with patch.object(payments, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", False):
            with self.assertRaises(HTTPException) as result:
                payments.enforce_reception_cash_scope(self.reception, method="CASH")
            self.assertEqual(result.exception.status_code, 403)
        for key, value in (
            ("APP_ENV", "production"),
            ("MARINA_SHARED_RECEPTION_CASH_P0_ENABLED", "false"),
            ("MARINA_SHARED_RECEPTION_CASH_P0_CONFIRM", ""),
        ):
            with self.subTest(key=key), patch.dict(os.environ, {key: value}):
                with self.assertRaises(HTTPException) as result:
                    payments.enforce_reception_cash_scope(self.reception, method="CASH")
                self.assertEqual(result.exception.status_code, 403)
        for global_code in ("MARINA_DEMO", "MARINA_HOTEL01"):
            with self.subTest(global_code=global_code), patch.object(auth, "PROPERTY_CODE", global_code):
                with self.assertRaises(HTTPException) as result:
                    payments.enforce_reception_cash_scope(self.reception, method="CASH")
                self.assertEqual(result.exception.status_code, 503)

    def test_cancellation_review_remains_manager_only(self):
        from app import reservation_payments
        from fastapi.routing import APIRoute
        endpoints = {route.path: route for route in reservation_payments.router.routes if isinstance(route, APIRoute)}
        cancel = endpoints["/api/v1/admin/booking/reservations/{reservation_id}/cancellation-finance-review"]
        paid = endpoints["/api/v1/admin/booking/reservations/{reservation_id}/payments"]
        # Body-visible provenance: management-only dependency is not replaced on the review route.
        self.assertIs(cancel.dependant.dependencies[0].call, payments.payment_access)
        self.assertIs(paid.dependant.dependencies[0].call, payments.reception_cash_access)
        self.assertEqual("POST", next(iter(paid.methods)))


if __name__ == "__main__":
    unittest.main()
