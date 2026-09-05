from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / "services/api/app/guest_marketplace.py").read_text(encoding="utf-8")
APP_ENTRY = (ROOT / "services/api/app/app_entry.py").read_text(encoding="utf-8")
RECEPTION_CORE = (ROOT / "services/api/app/reception_readiness.py").read_text(encoding="utf-8")
PAGE = (ROOT / "apps/web/app/g/[token]/page.tsx").read_text(encoding="utf-8")
GUEST = (ROOT / "apps/web/components/GuestMarketplace.tsx").read_text(encoding="utf-8")
KITCHEN = (ROOT / "apps/staff/components/KitchenEntry.tsx").read_text(encoding="utf-8")
ADMIN_SHELL = (ROOT / "apps/admin/components/AdminShell.tsx").read_text(encoding="utf-8")
RECEPTION_UI = (ROOT / "apps/admin/components/ReceptionWorkspace.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "apps/admin/app/admin-experience.css").read_text(encoding="utf-8")


def test_guest_marketplace_core_is_fail_closed_for_drafts():
    assert '"isActive"=true AND "isDraft"=false' in CORE
    assert "GUEST_MARKETPLACE_ITEM_NOT_PUBLISHED" in CORE
    assert 'financial_posting": "NONE_AUTOMATIC"' in CORE
    assert '@router.get("/rooms/{token}/kitchen/menu")' in CORE
    assert '@router.post("/rooms/{token}/kitchen/orders"' in CORE
    assert "app.include_router(guest_marketplace_router)" in APP_ENTRY
    assert "kitchen_guest_router" not in APP_ENTRY


def test_guest_marketplace_is_composed_in_guest_os():
    assert 'import GuestMarketplace from "../../../components/GuestMarketplace"' in PAGE
    assert '<GuestMarketplace token={token} />' in PAGE
    assert 'concierge-page ~ .ai-admin-root{display:none!important}' in PAGE


def test_guest_marketplace_does_not_hardcode_kol_destination():
    assert "NEXT_PUBLIC_KOL_MARKETPLACE_URL" in GUEST
    assert "KOL_MARKETPLACE_URL &&" in GUEST
    assert "http://" not in GUEST


def test_kitchen_has_direct_role_bounded_entry():
    assert 'new Set(["OWNER", "MANAGER", "DINING_STAFF"])' in KITCHEN
    assert '"/core/api/v1/auth/login"' in KITCHEN
    assert "Кухня и зал" in KITCHEN


def test_dashboard_contrast_no_longer_blanket_forces_all_descendants_white():
    forbidden = ".dashboard-shell h1,.dashboard-shell h2,.dashboard-shell h3,.dashboard-shell strong"
    assert forbidden not in CSS
    assert ".dashboard-shell .owner-v2{color:#132943!important}" in CSS
    assert ".room-state-grid>div.state-clean" in CSS


def test_reception_readiness_is_narrow_role_bounded_handoff():
    assert 'ALLOWED_ROLES = {"OWNER", "MANAGER", "RECEPTION"}' in RECEPTION_CORE
    assert "request_housekeeping_for_arrival" in RECEPTION_CORE
    assert "ARRIVAL_ROOM_TECH_BLOCK" in RECEPTION_CORE
    assert "type='HOUSEKEEPING'" in RECEPTION_CORE
    assert "'HOUSEKEEPING','OPEN','HIGH'" in RECEPTION_CORE
    assert "REQUEST_ARRIVAL_HOUSEKEEPING" in RECEPTION_CORE
    assert "allowed_types_for_role" not in RECEPTION_CORE
    assert "RoomStatePatch" not in RECEPTION_CORE
    assert "reception_readiness_router" in APP_ENTRY


def test_reception_admin_uses_proactive_readiness_workspace():
    assert 'import ReceptionWorkspace from "./ReceptionWorkspace"' in ADMIN_SHELL
    assert '<ReceptionWorkspace userRole={user.role}' in ADMIN_SHELL
    assert "Передать в уборку" in RECEPTION_UI
    assert "Нужен менеджер: номер в ремонте" in RECEPTION_UI
    assert "Сначала назначьте номер в шахматке" in RECEPTION_UI
