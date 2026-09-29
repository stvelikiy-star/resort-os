#!/usr/bin/env python3
"""Fail if production Admin/Staff screens add static Cyrillic UI text outside locale dictionaries."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN_RUNTIME = (ROOT / "apps/admin/components/AdminExperienceRuntime.tsx").read_text(encoding="utf-8")
STAFF_RUNTIME = (ROOT / "apps/staff/components/StaffLocaleRuntime.tsx").read_text(encoding="utf-8")

ADMIN_FILES = [
    "AdminShell.tsx","AgentsBoard.tsx","ChessboardReservationModal.tsx","DashboardBoard.tsx",
    "DiningManagementBoard.tsx","GroupBookingBoard.tsx","GrowthControlBoard.tsx",
    "GuestCrmEnrichmentPanel.tsx","GuestHistoryBoard.tsx","GuestOffersBoard.tsx",
    "GuestServiceSettingsBoard.tsx","GuestServicesCenter.tsx","HotelFinanceBoard.tsx",
    "HotelSetupBoard.tsx","InboxBoard.tsx","MarketingBoard.tsx","NfcFinanceBoard.tsx",
    "OperationsBoard.tsx","OwnerControlV2.tsx","OwnerExecutivePack.tsx","OwnerOccupancyMatrix.tsx",
    "OwnerOperationsPerformance.tsx","PMSBulkGuardV9.tsx","PMSControlSnapshotV9.tsx",
    "PMSGrid.tsx","PMSGridV2.tsx","PMSGridV9.tsx","PMSIntegrationRailV10.tsx",
    "PMSNewReservationModal.tsx","PMSOperationsCockpitV9.tsx","PMSOwnerGrid.tsx",
    "PMSUniversalBoard.tsx","RateManagementBoard.tsx","ReceptionBoard.tsx","ReceptionWorkspace.tsx",
    "ReportsBoard.tsx","RequestsBoard.tsx","ReservationFolioPanel.tsx","ReservationQuickFacts.tsx",
    "ReservationScheduleBuilder.tsx","ReservationsBoard.tsx","RoomBlocksPanel.tsx",
    "RoomDetailModal.tsx","RoomQrBoard.tsx","ServicePointsBoard.tsx","SiteContentBoard.tsx",
    "SiteMediaBoard.tsx","StaffBoard.tsx",
]
STAFF_FILES = [
    "StaffRoleGateway.tsx","StaffShiftV2.tsx","KitchenAdminV2.tsx","ChefProduction.tsx",
    "DiningDayPlanner.tsx","DiningFloorPlan.tsx","WaiterEntry.tsx","WaiterWorkspace.tsx","BeachTerminal.tsx",
]

# Legitimate values intentionally shown as language samples / multilingual content, not untranslated UI.
ALLOW = {
    "Қазақша", "Каалайм", "Сұрау", "Хочу",
}
STRING = re.compile(r'(["\'\x60])((?:\\.|(?!\1)[\s\S])*?)\1')

def residuals(path: Path, runtime: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    found: list[str] = []
    for match in STRING.finditer(text):
        value = match.group(2).replace("\\n", " ").strip()
        if not value or value in ALLOW or len(value) < 2 or len(value) > 180:
            continue
        if not re.search(r"[А-Яа-яЁё]", value):
            continue
        if any(token in value for token in ("{", "}", "$", "<", ">")):
            continue
        if value in runtime:
            continue
        found.append(value)
    return sorted(set(found))

def main() -> int:
    errors: list[str] = []
    for name in ADMIN_FILES:
        path = ROOT / "apps/admin/components" / name
        if not path.exists():
            continue
        for value in residuals(path, ADMIN_RUNTIME):
            errors.append(f"ADMIN {name}: {value}")
    for name in STAFF_FILES:
        path = ROOT / "apps/staff/components" / name
        if not path.exists():
            continue
        for value in residuals(path, STAFF_RUNTIME):
            errors.append(f"STAFF {name}: {value}")

    print("MARINA SMART static locale residual guard")
    print(f"FACT: admin_files={len(ADMIN_FILES)} staff_files={len(STAFF_FILES)}")
    if errors:
        for error in errors:
            print("FAIL:", error)
        print(f"RESULT: {len(errors)} untranslated static strings")
        return 1
    print("PASS: no untranslated static Cyrillic strings on guarded Admin/Staff surfaces")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
