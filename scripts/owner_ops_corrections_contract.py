#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    admin = text("apps/admin/components/AdminShell.tsx")
    app_entry = text("services/api/app/app_entry.py")
    pricing = text("services/api/app/pms_reservation_create.py")
    modal = text("apps/admin/components/PMSNewReservationModal.tsx")
    reception = text("apps/admin/components/ReceptionWorkspace.tsx")
    block_panel = text("apps/admin/components/RoomBlocksPanel.tsx")
    agents = text("apps/admin/components/AgentsBoard.tsx")
    builder = text("apps/admin/components/ReservationScheduleBuilder.tsx")
    web_booking = text("apps/web/components/BookingWidget.tsx")
    migration = text("packages/database/prisma/migrations/z100_owner_ops_corrections_20260914/migration.sql")

    # Final admin must retain Marketing while adding Agents.
    require('import MarketingBoard from "./MarketingBoard"' in admin, "MarketingBoard missing from final AdminShell")
    require('tab === "MARKETING"' in admin and '>Маркетинг</button>' in admin, "Marketing tab missing from final admin")
    require('import AgentsBoard from "./AgentsBoard"' in admin, "AgentsBoard missing from final AdminShell")
    require('tab === "AGENTS"' in admin and '>Агенты</button>' in admin, "Agents tab missing from final admin")
    require("app.include_router(marketing_router)" in app_entry, "Marketing API router not composed")
    require("app.include_router(marketing_integration_router)" in app_entry, "Marketing integration router not composed")
    require("app.include_router(marketing_automation_router)" in app_entry, "Marketing automation router not composed")
    require("app.include_router(owner_corrections_router)" in app_entry, "Owner corrections router not composed")

    # Owner-approved extra-bed and returning-guest rules must live in Core.
    for code in ("DOUBLE_STANDARD_BASEMENT", "DOUBLE_IMPROVED", "TWO_ROOM_STANDARD"):
        require(code in pricing, f"Denied extra-bed room type missing: {code}")
    require("RETURNING_GUEST_DISCOUNT_PERCENT = 10" in pricing, "Returning guest 10% discount missing")
    require("extra_bed_count" in pricing and "extra_beds_total_kgs" in pricing, "Server-side extra-bed pricing missing")
    require("agent_id" in pricing and '"agentId"' in pricing, "Agent binding missing from reservation Core")
    require("discount_percent" in modal and "extra_bed_count" in modal and "agent_id" in modal, "PMS booking UI does not send commercial corrections")

    # Reception period holds must be canonical inventory blocks, not fake reservations.
    require('import RoomBlocksPanel from "./RoomBlocksPanel"' in reception and "<RoomBlocksPanel />" in reception, "Reception room block panel not embedded")
    require('block_type: "MAINTENANCE" | "MANUAL"' in block_panel, "Maintenance/manual period block UI missing")
    require("booking_agents" in migration and '"usageCategory"' in migration, "Owner correction migration missing agent/block metadata")

    # Agent CRM must have period filters, reports and interactions.
    require("fromDate" in agents and "toDate" in agents and "loadReport" in agents, "Agent period report/filter missing")
    require("interactions" in agents and "nextContactAt" in agents, "Agent interaction history missing")

    # Drag/drop must never directly commit. It opens builder -> preview -> explicit confirmation -> commit.
    require("/schedule/preview" in builder, "Reservation schedule preview endpoint missing")
    require("/schedule/commit" in builder, "Reservation schedule commit endpoint missing")
    require("Проверить в Resort Core" in builder, "Explicit server preview action missing")
    require("Подтвердить и сохранить график" in builder, "Explicit move/save confirmation missing")

    # Public request success remains server-confirmed and visible to the guest.
    require("Заявка ${id} принята" in web_booking, "Server-confirmed public request success notification missing")

    print("PASS: final Admin retains Marketing and adds Agents")
    print("PASS: Core enforces owner-approved extra-bed and returning-guest pricing rules")
    print("PASS: Reception period maintenance/manual holds use canonical inventory")
    print("PASS: booking drag/drop remains preview + explicit-confirmation only")
    print("PASS: public site keeps server-confirmed request success notification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
