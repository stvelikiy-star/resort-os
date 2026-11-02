"""Contract checks for owner-managed MARINA section permissions."""
from pathlib import Path
import sys
import asyncio
import re
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from app.section_permissions import (  # noqa: E402
    SECTION_MODULES,
    effective_section_permissions,
    has_section_permission,
    normalized_configured_permissions,
    role_or_section_allowed,
    section_for_path,
)
from app.auth import require_roles  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from app.operations import allowed_types_for_user  # noqa: E402
from app.staff_control import StaffPatch  # noqa: E402
from app.staff_guest_requests import guest_request_access, guest_request_codes  # noqa: E402
from app.app_entry import app  # noqa: E402


assert len(SECTION_MODULES) == 26
staff_board = (Path(__file__).resolve().parents[1] / "apps/admin/components/StaffBoard.tsx").read_text(encoding="utf-8")
module_group_source = staff_board.split("const MODULE_GROUPS = [", 1)[1].split("] as const;", 1)[0]
checkbox_modules = set(re.findall(r'\["([A-Z_]+)",\s*"', module_group_source))
assert checkbox_modules == SECTION_MODULES, f"permission checkbox list mismatch: {checkbox_modules ^ SECTION_MODULES}"
assert "STAFF" in effective_section_permissions("MANAGER", None)
assert "WHATSAPP" in effective_section_permissions("OWNER", None)
assert effective_section_permissions("COOK", None) == ["DINING"]
assert effective_section_permissions("RECEPTION", ["FINANCE", "BOGUS"]) == ["FINANCE"]
assert normalized_configured_permissions('["FINANCE"]') == ["FINANCE"]

manager = {"role": "MAID", "module_permissions": ["FINANCE"]}
assert has_section_permission(manager, "/api/v1/admin/finance/summary")
assert not has_section_permission(manager, "/api/v1/admin/finance-unknown/summary")
assert not has_section_permission(manager, "/api/v1/admin/staff/overview")
assert section_for_path("/api/v1/admin/pms/groups/overview") == ("GROUPS",)
assert section_for_path("/api/v1/admin/booking/requests/abc/quote") == ("REQUESTS",)
assert section_for_path("/api/v1/admin/booking/reservations/abc") == ("RESERVATIONS", "PMS")
assert "CONTENT" in section_for_path("/api/v1/admin/site/content/en/draft")
assert "CONTENT" in section_for_path("/api/v1/admin/site/media/slots")
assert "AGENTS" in section_for_path("/api/v1/admin/owner-corrections/agents")
assert "PMS" in section_for_path("/api/v1/admin/owner-corrections/room-blocks")
assert not section_for_path("/api/v1/unmapped/private")
for route in app.routes:
    path = getattr(route, "path", "")
    if path.startswith(("/api/v1/admin/", "/api/v1/ops/", "/api/v1/dining/", "/api/v1/kitchen/")) or path == "/api/v1/pms/grid":
        assert section_for_path(path), f"protected route has no section mapping: {path}"
assert role_or_section_allowed({"role": "MAID", "module_permissions": ["FINANCE"], "module_permissions_custom": True}, "/api/v1/admin/finance/summary", ("OWNER", "MANAGER"))
assert not role_or_section_allowed({"role": "MANAGER", "module_permissions": [], "module_permissions_custom": True}, "/api/v1/admin/finance/summary", ("OWNER", "MANAGER"))
assert not role_or_section_allowed({"role": "COOK", "module_permissions": ["DINING"], "module_permissions_custom": False}, "/api/v1/kitchen/menu", ("OWNER", "MANAGER"))
assert role_or_section_allowed({"role": "MANAGER", "module_permissions": [], "module_permissions_custom": True}, "/api/v1/unmapped/private", ("OWNER", "MANAGER"))
assert not role_or_section_allowed({"role": "MAID", "module_permissions": ["STAFF"], "module_permissions_custom": True}, "/api/v1/admin/staff/9", ("OWNER",), module_grant=False)
assert allowed_types_for_user({"role": "RECEPTION", "module_permissions": ["OPS"], "module_permissions_custom": True}) == {"HOUSEKEEPING", "MAINTENANCE", "GUEST_REQUEST"}
assert allowed_types_for_user({"role": "MANAGER", "module_permissions": [], "module_permissions_custom": True}) == set()
custom_service_staff = {"role": "WAITER", "module_permissions": ["SERVICES"], "module_permissions_custom": True}
assert guest_request_access(custom_service_staff, "/api/v1/ops/guest-requests")
assert guest_request_codes(custom_service_staff) == {"*"}
assert not guest_request_access({"role": "RECEPTION", "module_permissions": [], "module_permissions_custom": True}, "/api/v1/ops/guest-requests")
assert StaffPatch(module_permissions=["FINANCE", "FINANCE"]).module_permissions == ["FINANCE"]
try:
    StaffPatch(module_permissions=["SUPERUSER"])
except ValidationError:
    pass
else:
    raise AssertionError("Unknown module grants must be rejected")


async def verify_role_dependency():
    path = SimpleNamespace(url=SimpleNamespace(path="/api/v1/admin/finance/summary"))
    manager = {"role": "MANAGER", "module_permissions": [], "module_permissions_custom": True}
    try:
        await require_roles("OWNER", "MANAGER")(path, manager)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("A checked-off finance section must be denied by the API")

    maid = {"role": "MAID", "module_permissions": ["FINANCE"], "module_permissions_custom": True}
    assert await require_roles("OWNER", "MANAGER")(path, maid) is maid

    staff_path = SimpleNamespace(url=SimpleNamespace(path="/api/v1/admin/staff/1"))
    try:
        await require_roles("OWNER", module_grant=False)(staff_path, maid)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("A module checkbox must never grant staff account administration")


asyncio.run(verify_role_dependency())

print("MARINA section permission contract: PASS")
