"""Regression: canonical hotel WAITER may only serve their assigned READY order."""
import os
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))
from app.kitchen import (  # noqa: E402
    ORDER_TRANSITIONS,
    enforce_waiter_order_assignment,
    enforce_waiter_service_request,
)
from app.shared_dining_p0 import guard as shared_staging_guard  # noqa: E402


class WaiterServeContract(unittest.TestCase):
    def test_waiter_serves_without_shared_staging_switch(self):
        # Admission to the regular hotel API is still handled by ordinary auth.
        with patch.dict(os.environ, {"APP_ENV": "production", "MARINA_SHARED_DINING_P0_ENABLED": "false"}):
            enforce_waiter_service_request({"role": "WAITER"}, "SERVED")
        self.assertIn("SERVED", ORDER_TRANSITIONS["READY"])
        self.assertNotIn("SERVED", ORDER_TRANSITIONS["NEW"])
        self.assertNotIn("SERVED", ORDER_TRANSITIONS["COOKING"])
        self.assertNotIn("SERVED", ORDER_TRANSITIONS["SERVED"])

    def test_waiter_cannot_perform_other_kitchen_status_changes(self):
        for target in ("ACCEPTED", "COOKING", "READY", "CANCELLED"):
            with self.subTest(target=target), self.assertRaises(HTTPException) as denied:
                enforce_waiter_service_request({"role": "WAITER"}, target)
            self.assertEqual(denied.exception.status_code, 403)

    def test_only_assigned_waiter_is_accepted(self):
        waiter_id = uuid.uuid4()
        user = {"role": "WAITER", "id": str(waiter_id)}
        enforce_waiter_order_assignment(user, waiter_id)
        for assigned_id in (None, uuid.uuid4()):
            with self.subTest(assigned_id=assigned_id), self.assertRaises(HTTPException) as denied:
                enforce_waiter_order_assignment(user, assigned_id)
            self.assertEqual(denied.exception.status_code, 403)

    def test_staging_preview_guard_is_still_closed_in_production(self):
        with patch.dict(os.environ, {"APP_ENV": "production", "MARINA_SHARED_DINING_P0_ENABLED": "true",
                                      "MARINA_SHARED_DINING_P0_CONFIRM": "REVIEWED_SHARED_DINING_STAGING_ONLY"}):
            with self.assertRaises(HTTPException) as denied:
                shared_staging_guard()
            self.assertEqual(denied.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
