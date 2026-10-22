"""Role defaults and exact, owner-managed section permissions."""
import json
from typing import Any

SECTION_MODULES = frozenset({
    "PMS", "RATES", "GROUPS", "REQUESTS", "AGENTS", "RESERVATIONS",
    "SERVICES", "DINING", "SERVICE_SETTINGS", "GUESTS", "OFFERS",
    "MARKETING", "GROWTH", "FINANCE", "REPORTS", "CONTENT", "ROOM_QR",
    "POINT_QR", "INBOX", "WHATSAPP", "OPS", "DASHBOARD", "STAFF",
    "SETTINGS", "HOTEL_RULES", "CHANNELS",
})
DEFAULT_ROLE_MODULES: dict[str, tuple[str, ...]] = {
    "OWNER": tuple(sorted(SECTION_MODULES)),
    "MANAGER": tuple(sorted(SECTION_MODULES)),
    "RECEPTION": ("PMS", "RESERVATIONS", "SERVICES", "DINING", "ROOM_QR", "GROUPS", "WHATSAPP"),
    "AGENT": ("PMS",),
    "MAID": ("OPS",),
    "TECHNICIAN": ("OPS",),
    "COOK": ("DINING",),
    "WAITER": ("DINING",),
}


def normalized_configured_permissions(configured: Any) -> list[str] | None:
    if isinstance(configured, str):
        try:
            configured = json.loads(configured)
        except (TypeError, ValueError):
            return None
    if isinstance(configured, (list, tuple, set)):
        return sorted(set(configured).intersection(SECTION_MODULES))
    return None


def effective_section_permissions(role: str, configured: Any) -> list[str]:
    normalized = normalized_configured_permissions(configured)
    if normalized is not None:
        return normalized
    return list(DEFAULT_ROLE_MODULES.get(role, ()))


# Longest path prefix wins. Where two screens intentionally share an API, either
# section grant is accepted; all other unmapped paths remain role-protected.
SECTION_PATHS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("/api/v1/admin/pms/groups", ("GROUPS",)),
    ("/api/v1/admin/pms", ("PMS",)),
    ("/api/v1/pms/grid", ("PMS",)),
    ("/api/v1/admin/rates", ("RATES",)),
    ("/api/v1/admin/reception", ("RESERVATIONS",)),
    ("/api/v1/admin/booking", ("RESERVATIONS", "REQUESTS", "PMS")),
    ("/api/v1/admin/stays", ("RESERVATIONS",)),
    ("/api/v1/admin/folio", ("RESERVATIONS",)),
    ("/api/v1/admin/guest-access", ("ROOM_QR", "RESERVATIONS")),
    ("/api/v1/admin/agents-context", ("AGENTS",)),
    ("/api/v1/admin/agents", ("AGENTS",)),
    ("/api/v1/admin/guest-service-settings", ("SERVICE_SETTINGS",)),
    ("/api/v1/admin/guest-services", ("SERVICES",)),
    ("/api/v1/dining", ("DINING",)),
    ("/api/v1/kitchen", ("DINING",)),
    ("/api/v1/ops/kitchen", ("DINING",)),
    ("/api/v1/admin/guest-crm", ("GUESTS",)),
    ("/api/v1/admin/guest-offers", ("OFFERS",)),
    ("/api/v1/admin/marketing", ("MARKETING",)),
    ("/api/v1/integrations/marketing", ("MARKETING",)),
    ("/api/v1/admin/growth", ("GROWTH",)),
    ("/api/v1/admin/intelligence", ("GROWTH", "REPORTS", "DASHBOARD", "GUESTS")),
    ("/api/v1/admin/finance", ("FINANCE",)),
    ("/api/v1/admin/reports", ("REPORTS",)),
    ("/api/v1/admin/site/content", ("CONTENT",)),
    ("/api/v1/admin/site/media", ("CONTENT",)),
    ("/api/v1/admin/guest-os", ("ROOM_QR", "SERVICES")),
    ("/api/v1/admin/service-points", ("POINT_QR",)),
    ("/api/v1/admin/service-point-payments", ("POINT_QR",)),
    ("/api/v1/admin/inbox", ("INBOX", "WHATSAPP")),
    ("/api/v1/admin/channels", ("CHANNELS", "WHATSAPP")),
    ("/api/v1/ops/housekeeping", ("OPS",)),
    ("/api/v1/ops/guest-requests", ("OPS", "SERVICES")),
    ("/api/v1/ops", ("OPS",)),
    ("/api/v1/admin/staff", ("STAFF",)),
    ("/api/v1/admin/hotel-setup", ("SETTINGS",)),
    ("/api/v1/admin/hotel-rules", ("HOTEL_RULES",)),
    ("/api/v1/admin/dashboard", ("DASHBOARD",)),
    ("/api/v1/admin/owner-corrections", ("DASHBOARD", "FINANCE", "OPS")),
    ("/api/v1/admin/rooms", ("PMS", "ROOM_QR")),
)


def section_for_path(path: str) -> tuple[str, ...]:
    if path.startswith("/api/v1/admin/booking/"):
        if "/requests" in path:
            return ("REQUESTS",)
        if "/reservations" in path:
            return ("RESERVATIONS", "PMS")
    if path.startswith("/api/v1/admin/owner-corrections/"):
        if "/agents" in path:
            return ("AGENTS", "DASHBOARD")
        if "/room-blocks" in path:
            return ("PMS", "ROOM_QR", "DASHBOARD")
        return ("DASHBOARD", "FINANCE", "OPS")
    for prefix, modules in SECTION_PATHS:
        if path == prefix or path.startswith(prefix + "/"):
            return modules
    return ()


def has_section_permission(user: dict[str, Any], path: str) -> bool:
    permissions = user.get("module_permissions")
    if not isinstance(permissions, (list, tuple, set)):
        return False
    return bool(set(permissions).intersection(section_for_path(path)))


def user_has_section(user: dict[str, Any], module: str) -> bool:
    permissions = user.get("module_permissions")
    return isinstance(permissions, (list, tuple, set)) and module in permissions


def role_or_section_allowed(
    user: dict[str, Any], path: str, allowed_roles: tuple[str, ...], *, module_grant: bool = True
) -> bool:
    role = user.get("role")
    if role == "OWNER" and "OWNER" in allowed_roles:
        return True
    modules = section_for_path(path)
    if not module_grant or not modules:
        return role in allowed_roles
    if user.get("module_permissions_custom"):
        return has_section_permission(user, path)
    return role in allowed_roles or has_section_permission(user, path)
