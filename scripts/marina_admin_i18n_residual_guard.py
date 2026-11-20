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
    "BeachTerminal.tsx","ChefProduction.tsx","DiningDayPlanner.tsx","DiningFloorPlan.tsx",
    "DiningFolioActions.tsx","DiningGuestSeatingPanel.tsx","DiningReadyRealtime.tsx",
    "GuestRequestShiftPanel.tsx","KitchenAdmin.tsx","KitchenAdminV2.tsx","KitchenEntry.tsx",
    "StaffRoleGateway.tsx","StaffShiftV2.tsx","WaiterEntry.tsx","WaiterWorkspace.tsx",
]

# Legitimate values intentionally shown as language samples / multilingual content, not untranslated UI.
ALLOW = {
    "Қазақша", "Каалайм", "Сұрау", "Хочу",
    # PMSOwnerGrid filter labels are rendered through its explicit RU/KG/KZ/EN copy() dictionary.
    "Все корпуса", "Бардык корпустар", "Барлық корпустар",
    "Доступность", "Свободны весь период", "Бүт мезгилге бош", "Бүкіл кезеңге бос",
    "Есть занятые ночи", "Бош эмес түндөр бар", "Бос емес түндер бар",
    "На ремонте", "Оңдоодо", "Жөндеуде",
    "Месяц", "Предыдущий месяц", "Мурунку ай", "Алдыңғы ай",
    "Следующий месяц", "Кийинки ай", "Келесі ай",
    "Сбросить фильтры", "Чыпкаларды тазалоо", "Сүзгілерді тазалау",
    "Номер, гость, бронь…", "Бөлмө, конок, бронь…", "Бөлме, қонақ, бронь…",
    "Режим администратора: шахматка доступна для просмотра. Создание и изменение брони выполняется в разделе «Ресепшен / Брони».",
}
STRING = re.compile(r'(["\'\x60])((?:\\.|(?!\1)[\s\S])*?)\1')

def dynamic_templates(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    found: list[str] = []
    for match in re.finditer(r'`([^`]*\$\{[^`]+)`', text, re.S):
        value = re.sub(r"\s+", " ", match.group(1)).strip()
        if not re.search(r"[А-Яа-яЁё]", value):
            continue
        if len(value) > 220:
            continue
        found.append(value)
    return sorted(set(found))


def dynamic_covered(template: str, runtime: str) -> bool:
    template = template.replace("\\n", " ").replace("\\t", " ")
    parts = re.split(r"\$\{[^}]+\}", template)
    significant: list[str] = []
    for part in parts:
        # Nested template strings can leave an unfinished ${... tail in this
        # lightweight scanner. Only the literal UI prefix is relevant here.
        part = re.sub(r"\$\{.*$", "", part)
        normalized = re.sub(r"\s+", " ", part).strip(" .,:;!?()[]{}«»—–-")
        if not re.search(r"[А-Яа-яЁё]", normalized):
            continue
        if len(normalized) <= 3:
            continue
        significant.append(normalized)
    if not significant:
        return True
    runtime_plain = runtime
    for source, target in [
        (r"\\s+", " "), (r"\\s*", " "), (r"\\.", "."), (r"\\?", "?"),
        (r"\\(", "("), (r"\\)", ")"), (r"\\[", "["), (r"\\]", "]"),
    ]:
        runtime_plain = runtime_plain.replace(source, target)
    return all(fragment in runtime_plain for fragment in significant)

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

def kz_coverage_errors() -> list[str]:
    errors: list[str] = []
    # Every Russian phrase in a {ru,kg,en} common entry must have an explicit
    # Kazakh mapping somewhere in the runtime. Otherwise KZ silently falls back to RU.
    common_ru = re.findall(r'\{\s*ru:\s*"((?:\\.|[^"])*)",\s*kg:\s*"((?:\\.|[^"])*)",\s*en:\s*"((?:\\.|[^"])*)"', ADMIN_RUNTIME)
    for ru, kg, en in common_ru:
        key = '"' + ru.replace('\\', '\\\\').replace('"', '\\"') + '":'
        if key not in ADMIN_RUNTIME:
            errors.append(f"ADMIN missing explicit KZ mapping: {ru}")
    return errors

def main() -> int:
    errors: list[str] = []
    errors.extend(kz_coverage_errors())
    for name in ADMIN_FILES:
        path = ROOT / "apps/admin/components" / name
        if not path.exists():
            continue
        for value in residuals(path, ADMIN_RUNTIME):
            errors.append(f"ADMIN {name}: {value}")
        for value in dynamic_templates(path):
            if not dynamic_covered(value, ADMIN_RUNTIME):
                errors.append(f"ADMIN_DYNAMIC {name}: {value}")
    for name in STAFF_FILES:
        path = ROOT / "apps/staff/components" / name
        if not path.exists():
            continue
        for value in residuals(path, STAFF_RUNTIME):
            errors.append(f"STAFF {name}: {value}")
        for value in dynamic_templates(path):
            if not dynamic_covered(value, STAFF_RUNTIME):
                errors.append(f"STAFF_DYNAMIC {name}: {value}")

    print("MARINA SMART static locale residual guard")
    print(f"FACT: admin_files={len(ADMIN_FILES)} staff_files={len(STAFF_FILES)} kz_explicit=required")
    if errors:
        for error in errors:
            print("FAIL:", error)
        print(f"RESULT: {len(errors)} untranslated static strings")
        return 1
    print("PASS: no untranslated static Cyrillic strings on guarded Admin/Staff surfaces")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
