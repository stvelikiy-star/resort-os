#!/usr/bin/env python3
"""P0 regression: no unreviewed legacy store privileges in shared hotels.

Run: python3 scripts/verify_store_role_fail_closed.py
This is a static role-contract check, not a substitute for a two-hotel E2E.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
permissions_path = ROOT / "services/api/app/section_permissions.py"
spec = importlib.util.spec_from_file_location("marina_section_permissions", permissions_path)
assert spec and spec.loader
permissions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permissions)

for role in ("STORE_STAFF", "DINING_STAFF", "CONTENT_MANAGER", "BEACH_PARTNER"):
    assert permissions.shared_role_module_permissions(role, None) == [], role
    assert permissions.shared_role_module_permissions(role, ["FINANCE", "OPS", "DINING", "STAFF"]) == [], role

for role in ("COOK", "WAITER"):
    assert permissions.shared_role_module_permissions(role, ["DINING", "FINANCE", "STAFF"]) == ["DINING"], role

gateway = (ROOT / "apps/staff/components/StaffRoleGateway.tsx").read_text(encoding="utf-8")
assert "Кабинет магазина пока не введён в эксплуатацию." in gateway
assert "Смена магазина подключена к Hotel OS." not in gateway
assert "user.role === \"STORE_STAFF\"" in gateway
print("PASS: legacy store roles fail closed, dining role ceilings preserved, workspace status truthful")
