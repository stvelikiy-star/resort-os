"""Unit gate for shared Tenant/Property login/RBAC contract; legacy unchanged."""
import asyncio
from types import SimpleNamespace
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app import auth
from app.section_permissions import (
    DEFAULT_ROLE_MODULES, SECTION_MODULES,
    effective_section_permissions, shared_role_module_permissions,
)
from fastapi import HTTPException
from pydantic import ValidationError

SERVER_ROLES = (
    "OWNER", "MANAGER", "RECEPTION", "AGENT", "MAID", "TECHNICIAN",
    "STORE_STAFF", "DINING_STAFF", "COOK", "WAITER",
    "CONTENT_MANAGER", "BEACH_PARTNER",
)


class SharedRoleCeilingTests(unittest.TestCase):
    def test_every_server_role_has_bounded_effective_permissions(self):
        for role in SERVER_ROLES:
            with self.subTest(role=role):
                exposed = shared_role_module_permissions(role, list(SECTION_MODULES))
                ceiling = set(SECTION_MODULES) if role == "OWNER" else set(DEFAULT_ROLE_MODULES.get(role, ()))
                self.assertEqual(set(exposed), ceiling)
                self.assertEqual(exposed, sorted(ceiling))
        self.assertEqual(shared_role_module_permissions("UNKNOWN", ["STAFF"]), [])

    def test_shared_custom_permissions_narrow_grants(self):
        self.assertEqual(shared_role_module_permissions("MAID", ["FINANCE", "STAFF", "OPS"]), ["OPS"])
        self.assertEqual(shared_role_module_permissions("TECHNICIAN", ["OPS", "PMS"]), ["OPS"])
        self.assertEqual(shared_role_module_permissions("MANAGER", ["STAFF", "FINANCE"]), ["FINANCE", "STAFF"])
        self.assertEqual(shared_role_module_permissions("MANAGER", []), [])
        self.assertEqual(shared_role_module_permissions("RECEPTION", ["RESERVATIONS", "DASHBOARD"]),
                         ["RESERVATIONS"])
        self.assertEqual(shared_role_module_permissions("BEACH_PARTNER", ["PMS"]), [])
        self.assertEqual(shared_role_module_permissions("OWNER", []), sorted(SECTION_MODULES))

    def test_legacy_single_property_permissions_remain_unchanged(self):
        self.assertEqual(effective_section_permissions("MAID", ["FINANCE"]), ["FINANCE"])
        with patch.object(auth, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", False):
            self.assertEqual(auth.granted_modules_for_session("MAID", ["FINANCE"]), ["FINANCE"])
        with patch.object(auth, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", True):
            self.assertEqual(auth.granted_modules_for_session("MAID", ["FINANCE"]), [])

    def test_shared_dependency_requires_role_and_module(self):
        request = SimpleNamespace(url=SimpleNamespace(path="/api/v1/admin/dashboard"))
        dishonest = {"role":"MAID","module_permissions_custom":True,"module_permissions":["DASHBOARD"]}
        manager = {"role":"MANAGER","module_permissions_custom":True,"module_permissions":[]}
        owner = {"role":"OWNER","module_permissions_custom":False,"module_permissions":[]}

        async def call(user,shared):
            with patch.object(auth,"MARINA_SHARED_AUTH_PREVIEW_ENABLED",shared):
                return await auth.require_roles("OWNER","MANAGER")(request,user)
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(call(dishonest,True))
        self.assertEqual(ctx.exception.status_code,403)
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(call(manager,True))
        self.assertEqual(ctx.exception.status_code,403)
        self.assertIs(asyncio.run(call(owner,True)),owner)
        # The historical custom delegation is not silently rewritten.
        self.assertIs(asyncio.run(call(dishonest,False)),dishonest)

    def test_login_payload_requires_hotel_fields_only_in_shared_handler(self):
        payload=auth.LoginPayload(username="owner",password="synthetic-password")
        self.assertIsNone(payload.tenant_code)
        self.assertIsNone(payload.property_code)
        chosen=auth.LoginPayload(username="owner",password="synthetic-password",
                                 tenant_code="tenant_a",property_code="HOTEL_A")
        self.assertEqual(chosen.tenant_code,"tenant_a")
        self.assertEqual(chosen.property_code,"HOTEL_A")
        with self.assertRaises(ValidationError):
            auth.LoginPayload(username="owner",password="synthetic-password",
                              tenant_code="../../escape", property_code="HOTEL_A")


if __name__ == "__main__":
    unittest.main()
