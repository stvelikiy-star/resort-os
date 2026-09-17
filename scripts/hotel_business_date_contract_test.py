from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HELPERS = [
    ROOT / "apps/admin/lib/hotelDate.ts",
    ROOT / "apps/staff/lib/hotelDate.ts",
    ROOT / "apps/web/lib/hotelDate.ts",
]

TARGETS = {
    "apps/admin/components/AgentsBoard.tsx": "hotelDateIso",
    "apps/admin/components/RoomBlocksPanel.tsx": "hotelDateIso",
    "apps/admin/components/GroupBookingBoard.tsx": "shiftHotelDateIso",
    "apps/admin/components/DiningManagementBoard.tsx": "hotelDateIso",
    "apps/staff/components/DiningDayPlanner.tsx": "hotelDateIso",
    "apps/staff/components/DiningGuestSeatingPanel.tsx": "hotelDateIso",
    "apps/staff/components/ChefProduction.tsx": "shiftHotelDateIso",
    "apps/web/components/AiAdministratorWidget.tsx": "shiftHotelDateIso",
}

FORBIDDEN = (
    "new Date().toISOString().slice(0, 10)",
    "getTimezoneOffset() * 60000",
    "now.getFullYear(), now.getMonth(), now.getDate()",
)

for helper in HELPERS:
    text = helper.read_text(encoding="utf-8")
    assert 'HOTEL_TIME_ZONE = "Asia/Bishkek"' in text, helper
    assert "formatToParts" in text, helper
    assert "Date.UTC" in text, helper

for relative, helper_name in TARGETS.items():
    text = (ROOT / relative).read_text(encoding="utf-8")
    assert helper_name in text, relative
    for bad in FORBIDDEN:
        assert bad not in text, f"{relative}: device/UTC hotel-date logic remains: {bad}"

# Date-only UTC arithmetic remains intentionally allowed where the input is already YYYY-MM-DD.
room_blocks = (ROOT / "apps/admin/components/RoomBlocksPanel.tsx").read_text(encoding="utf-8")
assert "Date.UTC(y, m - 1, d + amount)" in room_blocks

print("hotel business date contract: OK")
