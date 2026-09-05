from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / "services/api/app/guest_marketplace.py").read_text(encoding="utf-8")
DINING_CORE = (ROOT / "services/api/app/dining_control.py").read_text(encoding="utf-8")
OFFERS_CORE = (ROOT / "services/api/app/guest_offers.py").read_text(encoding="utf-8")
APP_ENTRY = (ROOT / "services/api/app/app_entry.py").read_text(encoding="utf-8")
RECEPTION_CORE = (ROOT / "services/api/app/reception_readiness.py").read_text(encoding="utf-8")
DINING_MIGRATION = (ROOT / "packages/database/prisma/migrations/8_dining_service_control/migration.sql").read_text(encoding="utf-8")
OFFERS_MIGRATION = (ROOT / "packages/database/prisma/migrations/9_guest_offer_campaigns/migration.sql").read_text(encoding="utf-8")
PAGE = (ROOT / "apps/web/app/g/[token]/page.tsx").read_text(encoding="utf-8")
GUEST = (ROOT / "apps/web/components/GuestMarketplace.tsx").read_text(encoding="utf-8")
KITCHEN = (ROOT / "apps/staff/components/KitchenEntry.tsx").read_text(encoding="utf-8")
DAY_PLANNER = (ROOT / "apps/staff/components/DiningDayPlanner.tsx").read_text(encoding="utf-8")
WAITER = (ROOT / "apps/staff/components/WaiterEntry.tsx").read_text(encoding="utf-8")
WAITER_PAGE = (ROOT / "apps/staff/app/waiter/page.tsx").read_text(encoding="utf-8")
ADMIN_SHELL = (ROOT / "apps/admin/components/AdminShell.tsx").read_text(encoding="utf-8")
OFFERS_ADMIN = (ROOT / "apps/admin/components/GuestOffersBoard.tsx").read_text(encoding="utf-8")
RECEPTION_UI = (ROOT / "apps/admin/components/ReceptionWorkspace.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "apps/admin/app/admin-experience.css").read_text(encoding="utf-8")


def test_guest_marketplace_core_is_fail_closed_for_daily_approved_menu():
    assert 'm."isActive"=true AND m."isDraft"=false' in CORE
    assert 'a."serviceDate"=$2 AND a."isAvailable"=true AND a."soldOut"=false' in CORE
    assert "GUEST_MARKETPLACE_MENU_NOT_PUBLISHED_TODAY" in CORE
    assert "GUEST_MARKETPLACE_ITEM_NOT_AVAILABLE_TODAY" in CORE
    assert 'financial_posting": "NONE_AUTOMATIC"' in CORE
    assert '@router.get("/rooms/{token}/kitchen/menu")' in CORE
    assert '@router.post("/rooms/{token}/kitchen/orders"' in CORE
    assert "app.include_router(guest_marketplace_router)" in APP_ENTRY
    assert "kitchen_guest_router" not in APP_ENTRY


def test_guest_marketplace_is_composed_in_guest_os():
    assert 'import GuestMarketplace from "../../../components/GuestMarketplace"' in PAGE
    assert '<GuestMarketplace token={token} />' in PAGE
    assert 'concierge-page ~ .ai-admin-root{display:none!important}' in PAGE


def test_guest_marketplace_offers_are_server_managed_not_hardcoded_partner_copy():
    assert '"/offers"' in GUEST
    assert "OfferCampaign" in GUEST
    assert "NEXT_PUBLIC_KOL_MARKETPLACE_URL" not in GUEST
    assert "KOL_MARKETPLACE_URL" not in GUEST
    assert "offerCopy" not in GUEST
    assert 'offer.action_type === "GUEST_REQUEST"' in GUEST
    assert 'offer.action_type === "EXTERNAL_URL"' in GUEST
    assert "offer.ai_prompt" in GUEST
    assert 'offer.external_url.startsWith("https://")' in GUEST


def test_kitchen_has_direct_role_bounded_entry_and_explicit_handoffs():
    assert 'new Set(["OWNER", "MANAGER", "DINING_STAFF"])' in KITCHEN
    assert '"/core/api/v1/auth/login"' in KITCHEN
    assert "Отдельный вход «Официант / зал»" in KITCHEN
    assert 'href="/kitchen/today"' in KITCHEN
    assert 'href="/waiter"' in KITCHEN


def test_dining_schema_separates_daily_menu_tables_and_waiter_assignment():
    assert "CREATE TABLE kitchen_menu_availability" in DINING_MIGRATION
    assert '"serviceDate" date NOT NULL' in DINING_MIGRATION
    assert '"soldOut" boolean NOT NULL DEFAULT false' in DINING_MIGRATION
    assert "CREATE TABLE kitchen_table_reservations" in DINING_MIGRATION
    assert "DINING_TABLE" not in DINING_MIGRATION
    assert 'ALTER TABLE kitchen_orders ADD COLUMN "waiterId" uuid' in DINING_MIGRATION


def test_dining_core_has_day_publish_stoplist_floor_and_table_booking():
    assert '@router.post("/menu-day/publish"' in DINING_CORE
    assert '@router.patch("/menu-day/{availability_id}")' in DINING_CORE
    assert '@router.get("/table-reservations")' in DINING_CORE
    assert '@router.post("/table-reservations"' in DINING_CORE
    assert "DINING_TABLE_TIME_CONFLICT" in DINING_CORE
    assert '@router.patch("/orders/{order_id}/waiter")' in DINING_CORE
    assert 'user["role"] == "DINING_STAFF"' in DINING_CORE
    assert '@router.get("/floor")' in DINING_CORE
    assert "app.include_router(dining_control_router)" in APP_ENTRY


def test_staff_has_separate_daily_menu_and_waiter_surfaces():
    assert "Опубликовать:" in DAY_PLANNER
    assert "Стоп-лист" in DAY_PLANNER
    assert '"/core/api/v1/dining/menu-day/publish"' in DAY_PLANNER
    assert 'new Set(["OWNER", "MANAGER", "DINING_STAFF"])' in WAITER
    assert '"/core/api/v1/dining/floor"' in WAITER
    assert "Взять заказ" in WAITER
    assert "Выдано гостю" in WAITER
    assert "Забронировать стол" in WAITER
    assert 'import WaiterEntry from "../../components/WaiterEntry"' in WAITER_PAGE


def test_guest_offer_schema_is_manager_controlled_and_event_audited():
    assert "CREATE TABLE guest_offer_campaigns" in OFFERS_MIGRATION
    assert "CREATE TABLE guest_offer_events" in OFFERS_MIGRATION
    assert "GUEST_REQUEST','EXTERNAL_URL','AI_PROMPT" in OFFERS_MIGRATION
    assert "CLICK','REQUEST','EXTERNAL_OPEN','AI_PROMPT" in OFFERS_MIGRATION
    assert '"externalUrl" ~ \'^https://\'' in OFFERS_MIGRATION
    assert "minStayNights" in OFFERS_MIGRATION and "maxStayNights" in OFFERS_MIGRATION


def test_guest_offer_core_is_role_bounded_targeted_and_non_commercial_authority():
    assert 'manager_access = require_roles("OWNER", "MANAGER")' in OFFERS_CORE
    assert 'admin_router = APIRouter(prefix="/api/v1/admin/guest-offers"' in OFFERS_CORE
    assert '@guest_router.get("/rooms/{token}/offers")' in OFFERS_CORE
    assert '@guest_router.post("/rooms/{token}/offers/{campaign_id}/events"' in OFFERS_CORE
    assert '"REQUEST_OR_HANDOFF_ONLY"' in OFFERS_CORE
    assert '"isActive"=true' in OFFERS_CORE
    assert '"minStayNights"' in OFFERS_CORE
    assert "GUEST_OFFER_EVENT_ACTION_MISMATCH" in OFFERS_CORE
    assert "app.include_router(guest_offers_guest_router)" in APP_ENTRY
    assert "app.include_router(guest_offers_admin_router)" in APP_ENTRY


def test_owner_manager_admin_can_manage_guest_offer_campaigns():
    assert 'import GuestOffersBoard from "./GuestOffersBoard"' in ADMIN_SHELL
    assert '"OFFERS"' in ADMIN_SHELL
    assert "Офферы гостю" in ADMIN_SHELL
    assert '<GuestOffersBoard />' in ADMIN_SHELL
    assert '"/core/api/v1/admin/guest-offers"' in OFFERS_ADMIN
    assert "Русский" in OFFERS_ADMIN and "Кыргызча" in OFFERS_ADMIN and "English" in OFFERS_ADMIN
    assert "Внешний HTTPS-каталог" in OFFERS_ADMIN
    assert "AI-сценарий" in OFFERS_ADMIN
    assert "Заявка сотрудникам" in OFFERS_ADMIN


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
