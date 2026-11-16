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
    "COOK",
    "WAITER",
    "AGENT",
    "STORE_STAFF",
}
assert set(MANAGED_ROLES) == expected, MANAGED_ROLES
assert set(get_args(ManagedRole)) == expected, get_args(ManagedRole)

for role in ("COOK", "WAITER", "STORE_STAFF"):
    StaffCreate(
        username=f"test-{role.lower()}",
        display_name=f"Test {role}",
        password="Synthetic-Only-Password-2026",
        role=role,
    )
    StaffPatch(role=role)

for role in ("OWNER", "DINING_STAFF", "CONTENT_MANAGER", "BEACH_PARTNER"):
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

import uuid
binding = uuid.uuid4()
StaffCreate(username="test-agent", display_name="Test Agent",
            password="Synthetic-Only-Password-2026", role="AGENT",
            booking_agent_id=binding)
StaffPatch(role="AGENT", booking_agent_id=binding)
for value in ({"role":"AGENT"},
              {"role":"COOK", "booking_agent_id":binding}):
    try:
        StaffCreate(username="invalid-agent", display_name="Invalid Agent",
                    password="Synthetic-Only-Password-2026", **value)
    except ValidationError:
        pass
    else:
        raise AssertionError("Agent binding policy must reject invalid user")

print("PASS: eight managed roles; AGENT requires binding; unreviewed legacy roles rejected")

from app.section_permissions import role_or_section_allowed
custom_store={"role":"STORE_STAFF","module_permissions_custom":True,"module_permissions":["DINING","FINANCE","STAFF"]}
assert role_or_section_allowed(custom_store,"/api/v1/kitchen/stock",("STORE_STAFF","OWNER"))
for path,roles in [
 ("/api/v1/kitchen/production-targets",("COOK","MANAGER")),
 ("/api/v1/kitchen/stock/consume",("COOK","MANAGER")),
 ("/api/v1/admin/finance/summary",("OWNER","MANAGER")),
 ("/api/v1/admin/staff",("OWNER",)),
]:
 assert not role_or_section_allowed(custom_store,path,roles),path
print("PASS: STORE_STAFF custom module grants never elevate role")
