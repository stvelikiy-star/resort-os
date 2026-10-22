"""Contract checks for the assignable MARINA staff roles and their portal surface."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import get_args

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from app.staff_control import MANAGED_ROLES, ManagedRole, StaffCreate, StaffPatch
from pydantic import ValidationError

expected = {
    "MANAGER",
    "RECEPTION",
    "MAID",
    "TECHNICIAN",
    "STORE_STAFF",
    "COOK",
    "WAITER",
}
assert set(MANAGED_ROLES) == expected, MANAGED_ROLES
assert set(get_args(ManagedRole)) == expected, get_args(ManagedRole)

for role in ("COOK", "WAITER"):
    StaffCreate(
        username=f"test-{role.lower()}",
        display_name=f"Test {role}",
        password="Synthetic-Only-Password-2026",
        role=role,
    )
    StaffPatch(role=role)

for role in ("OWNER", "AGENT", "DINING_STAFF", "CONTENT_MANAGER", "BEACH_PARTNER"):
    try:
        StaffCreate(
            username="test-legacy",
            display_name="Test Legacy",
            password="Synthetic-Only-Password-2026",
            role=role,
        )
    except ValidationError:
        pass
    else:
        raise AssertionError(f"{role} must not be assignable through staff management")

print("PASS: owner staff-management roles match active role portals; COOK/WAITER are assignable; legacy roles are rejected")
