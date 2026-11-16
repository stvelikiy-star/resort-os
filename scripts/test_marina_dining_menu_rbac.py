"""Role regression: the waiter can read published menu, never mutate the manager's day menu."""
import asyncio
import inspect
import sys
import unittest
import uuid
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from fastapi import HTTPException  # noqa: E402
from starlette.requests import Request  # noqa: E402
from app import dining_control, auth  # noqa: E402


class DiningMenuManagementPermissions(unittest.TestCase):
    def test_waiter_cannot_publish_even_with_custom_dining_grant(self):
        user = {"role": "WAITER", "module_permissions": ["DINING"], "module_permissions_custom": True}
        payload = dining_control.MenuDayPublish(service_date=date(2026, 11, 15),
                                                meal_type="DINNER", menu_item_ids=[])
        # Explicit manager-only guard executes before acquiring a DB connection.
        with self.assertRaises(HTTPException) as failure:
            asyncio.run(dining_control.publish_menu_day(payload, request=None, user=user))
        self.assertEqual(failure.exception.status_code, 403)

    def test_waiter_cannot_change_availability_even_with_custom_dining_grant(self):
        user = {"role": "WAITER", "module_permissions": ["DINING"], "module_permissions_custom": True}
        payload = dining_control.MenuAvailabilityPatch(is_available=True)
        with self.assertRaises(HTTPException) as failure:
            asyncio.run(dining_control.patch_menu_availability(
                uuid.uuid4(), payload, request=None, user=user))
        self.assertEqual(failure.exception.status_code, 403)

    def test_cook_and_reception_cannot_publish(self):
        payload = dining_control.MenuDayPublish(service_date=date(2026, 11, 15),
                                                meal_type="BREAKFAST", menu_item_ids=[])
        for role in ("COOK", "RECEPTION", "STORE_STAFF"):
            with self.subTest(role=role), self.assertRaises(HTTPException) as failure:
                asyncio.run(dining_control.publish_menu_day(
                    payload, request=None, user={"role": role}))
            self.assertEqual(failure.exception.status_code, 403)

    def test_waiter_can_read_menu_with_existing_server_role(self):
        scope = {"type": "http", "method": "GET", "path": "/api/v1/dining/menu-day",
                 "headers": [], "query_string": b"", "server": ("test", 80), "scheme": "http"}
        read_dependency = inspect.signature(dining_control.get_menu_day).parameters["user"].default.dependency
        waiter = {"role": "WAITER", "module_permissions_custom": False}
        with patch.object(auth, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", False):
            result = asyncio.run(read_dependency(request=Request(scope), user=waiter))
        self.assertIs(result, waiter)


if __name__ == "__main__":
    unittest.main()
