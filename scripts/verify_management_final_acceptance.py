#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    target = ROOT / path
    if not target.exists():
        raise AssertionError(f"required file missing: {path}")
    return target.read_text(encoding="utf-8")


CHECKS: list[tuple[str, str, str]] = [
    # Admin shell / RBAC / navigation
    ("apps/admin/components/AdminShell.tsx", 'import DashboardBoard from "./DashboardBoard"', "dashboard mounted"),
    ("apps/admin/components/AdminShell.tsx", 'import PMSGrid from "./PMSGridV9"', "PMS mounted"),
    ("apps/admin/components/AdminShell.tsx", 'import RateManagementBoard from "./RateManagementBoard"', "rates mounted"),
    ("apps/admin/components/AdminShell.tsx", 'import ReceptionWorkspace from "./ReceptionWorkspace"', "reception mounted"),
    ("apps/admin/components/AdminShell.tsx", 'import GuestServicesCenter from "./GuestServicesCenter"', "guest services mounted"),
    ("apps/admin/components/AdminShell.tsx", 'import DiningManagementBoard from "./DiningManagementBoard"', "dining management mounted"),
    ("apps/admin/components/AdminShell.tsx", 'import HotelFinanceBoard from "./HotelFinanceBoard"', "finance mounted"),
    ("apps/admin/components/AdminShell.tsx", 'import ReportsBoard from "./ReportsBoard"', "reports mounted"),
    ("apps/admin/components/AdminShell.tsx", 'import OperationsBoard from "./OperationsBoard"', "operations mounted"),
    ("apps/admin/components/AdminShell.tsx", 'import StaffBoard from "./StaffBoard"', "staff mounted"),
    ("apps/admin/components/AdminShell.tsx", 'import InboxBoard from "./InboxBoard"', "inbox mounted"),
    ("apps/admin/components/AdminShell.tsx", '>Супершахматка</button>', "PMS nav"),
    ("apps/admin/components/AdminShell.tsx", '>Цены / Сезоны</button>', "rates nav"),
    ("apps/admin/components/AdminShell.tsx", '>Ресепшен / Брони</button>', "reception nav"),
    ("apps/admin/components/AdminShell.tsx", '>Сервис гостя</button>', "guest services nav"),
    ("apps/admin/components/AdminShell.tsx", '>Питание / Ресторан</button>', "dining nav"),
    ("apps/admin/components/AdminShell.tsx", '>Финансы</button>', "finance nav"),
    ("apps/admin/components/AdminShell.tsx", '>Отчёты / Аналитика</button>', "reports nav"),
    ("apps/admin/components/AdminShell.tsx", '>Уборка / Ремонт</button>', "operations nav"),
    ("apps/admin/components/AdminShell.tsx", '>Персонал</button>', "staff nav"),
    ("apps/admin/components/AdminShell.tsx", '>Сообщения</button>', "inbox nav"),
    ("apps/admin/components/AdminShell.tsx", 'const isManager = ["OWNER", "MANAGER"].includes(user.role)', "manager RBAC"),
    ("apps/admin/components/AdminShell.tsx", 'const canUseReception = isManager || isReception', "reception RBAC"),
    ("apps/admin/components/AdminShell.tsx", 'const canUseOps = isManager || ["MAID", "TECHNICIAN"].includes(user.role)', "ops RBAC"),

    # Core composition
    ("services/api/app/app_entry.py", "app.include_router(staff_control_router)", "staff control router"),
    ("services/api/app/app_entry.py", "app.include_router(rate_management_router)", "rate management router"),
    ("services/api/app/app_entry.py", "app.include_router(hotel_finance_router)", "finance router"),
    ("services/api/app/app_entry.py", "app.include_router(analytics_reports_router)", "analytics router"),
    ("services/api/app/app_entry.py", "app.include_router(pms_chessboard_router)", "PMS mutation router"),
    ("services/api/app/app_entry.py", "app.include_router(pms_chessboard_read_router)", "PMS read router"),
    ("services/api/app/app_entry.py", "app.include_router(reception_reservations_router)", "reception router"),
    ("services/api/app/app_entry.py", "app.include_router(reception_readiness_router)", "reception readiness router"),
    ("services/api/app/app_entry.py", "app.include_router(guest_services_router)", "guest services router"),
    ("services/api/app/app_entry.py", "app.include_router(operations_router)", "operations router"),
    ("services/api/app/app_entry.py", "app.include_router(operations_assignment_router)", "assignment router"),
    ("services/api/app/app_entry.py", "app.include_router(operations_history_router)", "operations history router"),
    ("services/api/app/app_entry.py", "app.include_router(kitchen_menu_management_router)", "menu management router"),
    ("services/api/app/app_entry.py", "app.include_router(kitchen_admin_router)", "kitchen operations router"),
    ("services/api/app/app_entry.py", "app.include_router(dining_control_router)", "dining control router"),
    ("services/api/app/app_entry.py", "app.include_router(inbox_router)", "inbox router"),
    ("services/api/app/app_entry.py", "app.include_router(channel_outbound_router)", "outbound router"),
    ("services/api/app/app_entry.py", "app.include_router(manager_dashboard_router)", "manager dashboard router"),

    # Rates / staff access
    ("services/api/app/rate_management.py", 'router = APIRouter(prefix="/api/v1/admin/rates"', "rates API prefix"),
    ("services/api/app/rate_management.py", "RATE_PERIOD_OVERLAP", "rate overlap guard"),
    ("services/api/app/staff_control.py", 'router = APIRouter(prefix="/api/v1/admin/staff-control"', "staff control API prefix"),
    ("services/api/app/staff_control.py", 'owner_access = require_roles("OWNER")', "staff owner-only guard"),
    ("services/api/app/staff_control.py", "auth_sessions", "staff session revocation"),

    # Reception / operations / finance
    ("apps/admin/components/ReceptionWorkspace.tsx", "/housekeeping-request", "reception housekeeping handoff"),
    ("apps/admin/components/ReceptionWorkspace.tsx", 'room_state !== "CLEAN"', "reception readiness truth"),
    ("apps/admin/components/OperationsBoard.tsx", "/core/api/v1/ops/tasks", "operations task API"),
    ("apps/admin/components/OperationsBoard.tsx", "/assignee", "operations assignment UI"),
    ("apps/admin/components/HotelFinanceBoard.tsx", "/core/api/v1/admin/finance/summary", "finance summary API"),
    ("apps/admin/components/HotelFinanceBoard.tsx", "не бухгалтерский отчёт", "finance truth boundary"),

    # Kitchen production management
    ("apps/staff/components/KitchenEntry.tsx", 'import KitchenAdminV2 from "./KitchenAdminV2"', "production kitchen manager mounted"),
    ("apps/staff/components/KitchenAdminV2.tsx", 'const canManageMenu = user?.role === "OWNER" || user?.role === "MANAGER"', "menu UI RBAC"),
    ("apps/staff/components/KitchenAdminV2.tsx", "approvedMenu", "orders use approved menu"),
    ("apps/staff/components/KitchenAdminV2.tsx", "Создать черновик", "real menu creation workflow"),
    ("services/api/app/kitchen_menu_management.py", 'manager_access = require_roles("OWNER", "MANAGER")', "menu Core RBAC"),
    ("services/api/app/kitchen_menu_management.py", 'router.post("/menu"', "menu create API"),
    ("services/api/app/kitchen_menu_management.py", 'router.patch("/menu/{item_id}"', "menu update API"),

    # Guest services / offers / inbox
    ("apps/admin/components/GuestServicesCenter.tsx", "/core/api/v1/admin/guest-services", "guest services UI Core-backed"),
    ("services/api/app/guest_services.py", 'center_access = require_roles("OWNER", "MANAGER", "RECEPTION")', "guest services RBAC"),
    ("apps/admin/components/GuestOffersBoard.tsx", "/core/api/v1/admin/guest-offers", "owner-configurable guest offers"),
    ("apps/admin/components/GuestOffersBoard.tsx", "clicks", "guest offer click analytics"),
    ("apps/admin/components/GuestOffersBoard.tsx", "requests", "guest offer request analytics"),
    ("apps/admin/components/InboxBoard.tsx", "/core/api/v1/admin/inbox/conversations", "inbox conversations"),
    ("apps/admin/components/InboxBoard.tsx", "/core/api/v1/admin/inbox/outbound-capabilities", "inbox outbound capability truth"),
    ("apps/admin/components/InboxBoard.tsx", "/core/api/v1/admin/inbox/ai-capabilities", "inbox AI capability truth"),

    # Existing executable acceptance suites
    ("scripts/verify_management_control.py", "MANAGEMENT", "management E2E verifier present"),
    ("scripts/verify_kitchen_menu_management.py", "KITCHEN MENU MANAGEMENT E2E: PASS", "kitchen menu E2E verifier present"),
    ("scripts/verify_guest_services_center.py", "guest-services", "guest services E2E verifier present"),
    ("scripts/verify_kitchen_operations.py", "KITCHEN OPERATIONS E2E: PASS", "kitchen lifecycle E2E verifier present"),
    (".github/workflows/core-ci.yml", "Verify check-in checkout housekeeping lifecycle", "core stay lifecycle gate"),
    (".github/workflows/release-gate-ci.yml", "Root control-center verification", "release control-center gate"),
    (".github/workflows/full-staging-gate.yml", "Run full synthetic staging acceptance", "full staging gate"),
    (".github/workflows/inbox-ci.yml", "Verify command center communication metrics and resolve conversation", "inbox E2E gate"),
    (".github/workflows/guest-services-ci.yml", "Run unified Guest Services Center E2E", "guest services gate"),
    (".github/workflows/kitchen-operations-ci.yml", "Run Kitchen Menu Management E2E", "kitchen management gate"),
]

FORBIDDEN_RUNTIME: list[tuple[str, str, str]] = [
    ("apps/staff/components/KitchenAdminV2.tsx", "Загрузить тестовое меню", "production kitchen must not expose demo menu bootstrap"),
    ("apps/staff/components/KitchenEntry.tsx", 'import KitchenAdmin from "./KitchenAdmin"', "legacy KitchenAdmin must not be active"),
]


def main() -> int:
    passed = 0
    for path, needle, label in CHECKS:
        if needle not in text(path):
            raise AssertionError(f"FAIL [{label}]: {path} missing {needle!r}")
        passed += 1
    for path, needle, label in FORBIDDEN_RUNTIME:
        if needle in text(path):
            raise AssertionError(f"FAIL [{label}]: forbidden marker {needle!r} in {path}")
        passed += 1
    if passed < 70:
        raise AssertionError(f"final acceptance suite unexpectedly small: {passed}")
    print(f"MANAGEMENT_FINAL_ACCEPTANCE_PASS checks={passed}")
    print("BOUNDARY: public website is frozen; acceptance scope is management/admin/staff/Core only")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"MANAGEMENT_FINAL_ACCEPTANCE_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(1)
