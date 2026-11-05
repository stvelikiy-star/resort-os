"""Shared dining P0: exact ASGI admission and fail-closed staging opt-in."""
import os
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from app import auth, shared_dining_p0 as dining, kitchen  # noqa: E402


ORDER_A = "11111111-2222-4333-8444-5555555555a1"


class SharedDiningP0Tests(unittest.TestCase):
    def test_only_reviewed_method_path_pairs_are_admitted(self):
        approved = {
            ("GET", "/api/v1/kitchen/orders"),
            ("GET", "/api/v1/dining/floor"),
            ("GET", "/api/v1/dining/table-reservations"),
            ("POST", "/api/v1/dining/table-reservations"),
            ("PATCH", f"/api/v1/kitchen/orders/{ORDER_A}/status"),
            ("PATCH", f"/api/v1/dining/orders/{ORDER_A}/waiter"),
            ("PATCH", f"/api/v1/dining/table-reservations/{ORDER_A}"),
        }
        for method, path in approved:
            with self.subTest(method=method, path=path):
                self.assertTrue(dining.allowed(method, path))
        denied = {
            ("GET", "/api/v1/kitchen/menu"),
            ("POST", "/api/v1/kitchen/menu/bootstrap-draft"),
            ("POST", "/api/v1/kitchen/orders"),
            ("GET", "/api/v1/dining/menu-day"),
            ("POST", "/api/v1/dining/menu-day/publish"),
            ("PATCH", "/api/v1/kitchen/orders/not-a-uuid/status"),
            ("GET", f"/api/v1/kitchen/orders/{ORDER_A}/status"),
            ("POST", f"/api/v1/dining/orders/{ORDER_A}/waiter"),
            ("POST", "/api/v1/admin/finance/summary"),
            ("GET", "/api/v1/assistant/capabilities"),
            ("GET", "/api/v1/admin/inbox/conversations"),
        }
        for method, path in denied:
            with self.subTest(method=method, path=path):
                self.assertFalse(dining.allowed(method, path))
        self.assertTrue(dining.allowed("OPTIONS", "/api/v1/dining/floor"))
        self.assertFalse(dining.allowed("OPTIONS", "/api/v1/kitchen/menu"))

    def test_guard_rejects_default_and_missing_acknowledgment(self):
        with patch.object(auth, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", True), (
            patch.object(auth, "MARINA_TENANT_CONTEXT_ENABLED", True)
        ), patch.object(auth, "COOKIE_SECURE", True), (
            patch.object(auth, "PROPERTY_CODE", "MARINA_BROWSER_CI")
        ), patch.dict(os.environ, {"APP_ENV": "staging",
                                   "MARINA_SHARED_DINING_P0_ENABLED": "false",
                                   "MARINA_SHARED_DINING_P0_CONFIRM": ""}):
            with self.assertRaises(HTTPException) as blocked:
                dining.guard()
            self.assertEqual(blocked.exception.status_code, 503)
            with patch.dict(os.environ, {
                "MARINA_SHARED_DINING_P0_ENABLED": "true",
                "MARINA_SHARED_DINING_P0_CONFIRM": "",
            }):
                with self.assertRaises(HTTPException) as missing:
                    dining.guard()
                self.assertEqual(missing.exception.status_code, 503)
            with patch.dict(os.environ, {
                "MARINA_SHARED_DINING_P0_ENABLED": "true",
                "MARINA_SHARED_DINING_P0_CONFIRM": "REVIEWED_SHARED_DINING_STAGING_ONLY",
            }):
                dining.guard()  # Explicit isolated staging only.

    def test_waiter_can_only_serve_his_own_assigned_ready_order(self):
        waiter_id = uuid.uuid4()
        other_id = uuid.uuid4()
        waiter = {"id": str(waiter_id), "role": "WAITER"}
        cook = {"id": str(other_id), "role": "COOK"}
        with patch.object(kitchen, "shared_dining_staging_guard") as stage:
            kitchen.enforce_waiter_service_request(waiter, "SERVED")
            stage.assert_called_once()
            for status in ("NEW", "ACCEPTED", "COOKING", "READY", "CANCELLED"):
                with self.subTest(status=status), self.assertRaises(HTTPException) as blocked:
                    kitchen.enforce_waiter_service_request(waiter, status)
                self.assertEqual(blocked.exception.status_code, 403)
                self.assertEqual(blocked.exception.detail["code"], "WAITER_ONLY_SERVES")
            kitchen.enforce_waiter_order_assignment(waiter, waiter_id)
            for invalid in (None, other_id):
                with self.subTest(assigned=invalid), self.assertRaises(HTTPException) as blocked:
                    kitchen.enforce_waiter_order_assignment(waiter, invalid)
                self.assertEqual(blocked.exception.status_code, 403)
                self.assertEqual(blocked.exception.detail["code"], "WAITER_ORDER_NOT_ASSIGNED")
            # The existing kitchen role retains its original status and order operations.
            kitchen.enforce_waiter_service_request(cook, "COOKING")
            kitchen.enforce_waiter_order_assignment(cook, None)

    def test_waiter_serving_stays_closed_without_staging_guard(self):
        waiter = {"id": str(uuid.uuid4()), "role": "WAITER"}
        with patch.object(kitchen, "shared_dining_staging_guard",
                          side_effect=HTTPException(status_code=503,
                                                    detail="Shared dining not enabled")):
            with self.assertRaises(HTTPException) as blocked:
                kitchen.enforce_waiter_service_request(waiter, "SERVED")
            self.assertEqual(blocked.exception.status_code, 503)

    def test_cannot_activate_on_demo_production_or_plain_cookie(self):
        with patch.object(auth, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", True), (
            patch.object(auth, "MARINA_TENANT_CONTEXT_ENABLED", True)
        ), patch.dict(os.environ, {
            "APP_ENV": "staging",
            "MARINA_SHARED_DINING_P0_ENABLED": "true",
            "MARINA_SHARED_DINING_P0_CONFIRM": "REVIEWED_SHARED_DINING_STAGING_ONLY",
        }):
            for code, cookie in (("MARINA_DEMO", True), ("MARINA_HOTEL01", True),
                                  ("MARINA_BROWSER_CI", False)):
                with self.subTest(property_code=code, secure=cookie), (
                    patch.object(auth, "PROPERTY_CODE", code)
                ), patch.object(auth, "COOKIE_SECURE", cookie):
                    with self.assertRaises(HTTPException) as blocked:
                        dining.guard()
                    self.assertEqual(blocked.exception.status_code, 503)
            with patch.object(auth, "PROPERTY_CODE", "MARINA_BROWSER_CI"), (
                patch.object(auth, "COOKIE_SECURE", True)
            ), patch.dict(os.environ, {"APP_ENV": "production"}):
                with self.assertRaises(HTTPException) as blocked:
                    dining.guard()
                self.assertEqual(blocked.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
