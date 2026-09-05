from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / "services/api/app/guest_marketplace.py").read_text(encoding="utf-8")
PAGE = (ROOT / "apps/web/app/g/[token]/page.tsx").read_text(encoding="utf-8")
GUEST = (ROOT / "apps/web/components/GuestMarketplace.tsx").read_text(encoding="utf-8")
KITCHEN = (ROOT / "apps/staff/components/KitchenEntry.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "apps/admin/app/admin-experience.css").read_text(encoding="utf-8")


def test_guest_marketplace_core_is_fail_closed_for_drafts():
    assert '"isActive"=true AND "isDraft"=false' in CORE
    assert "GUEST_MARKETPLACE_ITEM_NOT_PUBLISHED" in CORE
    assert 'financial_posting": "NONE_AUTOMATIC"' in CORE


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
