from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def add_import(path: str, statement: str) -> None:
    text = read(path)
    if statement in text:
        return
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if 'from "react";' in line:
            lines.insert(index + 1, f"\n{statement}\n")
            write(path, "".join(lines))
            return
    raise RuntimeError(f"React import anchor not found in {path}")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one match in {path}, found {count}: {old[:80]!r}")
    write(path, text.replace(old, new, 1))


HELPER = '''export const HOTEL_TIME_ZONE = "Asia/Bishkek";\n\nconst HOTEL_DATE_FORMATTER = new Intl.DateTimeFormat("en-GB", {\n  timeZone: HOTEL_TIME_ZONE,\n  year: "numeric",\n  month: "2-digit",\n  day: "2-digit",\n});\n\nexport function hotelDateIso(value: Date = new Date()): string {\n  const values: Record<string, string> = {};\n  for (const part of HOTEL_DATE_FORMATTER.formatToParts(value)) {\n    if (part.type !== "literal") values[part.type] = part.value;\n  }\n  const year = values.year;\n  const month = values.month;\n  const day = values.day;\n  if (!year || !month || !day) throw new Error("Unable to resolve hotel-local date");\n  return `${year}-${month}-${day}`;\n}\n\nexport function shiftHotelDateIso(days: number, value: Date = new Date()): string {\n  const [year, month, day] = hotelDateIso(value).split("-").map(Number);\n  return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10);\n}\n\nexport function hotelMonthStartIso(value: Date = new Date()): string {\n  return `${hotelDateIso(value).slice(0, 7)}-01`;\n}\n'''

for helper_path in (
    "apps/admin/lib/hotelDate.ts",
    "apps/staff/lib/hotelDate.ts",
    "apps/web/lib/hotelDate.ts",
):
    write(helper_path, HELPER)

# Admin: agent reporting dates.
add_import("apps/admin/components/AgentsBoard.tsx", 'import { hotelDateIso, hotelMonthStartIso } from "../lib/hotelDate";')
replace_once(
    "apps/admin/components/AgentsBoard.tsx",
    'const todayIso = () => new Date().toISOString().slice(0, 10);\nconst monthStartIso = () => `${todayIso().slice(0, 8)}01`;',
    'const todayIso = hotelDateIso;\nconst monthStartIso = hotelMonthStartIso;',
)

# Admin: room blocks default period.
add_import("apps/admin/components/RoomBlocksPanel.tsx", 'import { hotelDateIso } from "../lib/hotelDate";')
replace_once(
    "apps/admin/components/RoomBlocksPanel.tsx",
    'const isoToday = () => new Date().toISOString().slice(0, 10);',
    'const isoToday = hotelDateIso;',
)

# Admin: group booking defaults.
add_import("apps/admin/components/GroupBookingBoard.tsx", 'import { shiftHotelDateIso } from "../lib/hotelDate";')
replace_once(
    "apps/admin/components/GroupBookingBoard.tsx",
    '''function dateOffset(days: number) {\n  const value = new Date();\n  value.setDate(value.getDate() + days);\n  const shifted = new Date(value.getTime() - value.getTimezoneOffset() * 60000);\n  return shifted.toISOString().slice(0, 10);\n}''',
    'const dateOffset = (days: number) => shiftHotelDateIso(days);',
)

# Admin: dining production business day.
add_import("apps/admin/components/DiningManagementBoard.tsx", 'import { hotelDateIso } from "../lib/hotelDate";')
replace_once(
    "apps/admin/components/DiningManagementBoard.tsx",
    '''function todayIso() {\n  const now = new Date();\n  const shifted = new Date(now.getTime() - now.getTimezoneOffset() * 60000);\n  return shifted.toISOString().slice(0, 10);\n}''',
    'const todayIso = hotelDateIso;',
)

# Staff: menu day, seating day, chef production ranges.
add_import("apps/staff/components/DiningDayPlanner.tsx", 'import { hotelDateIso } from "../lib/hotelDate";')
replace_once(
    "apps/staff/components/DiningDayPlanner.tsx",
    '''function todayIso() {\n  const now = new Date();\n  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);\n  return local.toISOString().slice(0, 10);\n}''',
    'const todayIso = hotelDateIso;',
)

add_import("apps/staff/components/DiningGuestSeatingPanel.tsx", 'import { hotelDateIso } from "../lib/hotelDate";')
replace_once(
    "apps/staff/components/DiningGuestSeatingPanel.tsx",
    '''function todayIso() {\n  const now = new Date();\n  const shifted = new Date(now.getTime() - now.getTimezoneOffset() * 60000);\n  return shifted.toISOString().slice(0, 10);\n}''',
    'const todayIso = hotelDateIso;',
)

add_import("apps/staff/components/ChefProduction.tsx", 'import { shiftHotelDateIso } from "../lib/hotelDate";')
replace_once(
    "apps/staff/components/ChefProduction.tsx",
    '''function localIso(offset = 0) {\n  const value = new Date();\n  value.setDate(value.getDate() + offset);\n  const shifted = new Date(value.getTime() - value.getTimezoneOffset() * 60000);\n  return shifted.toISOString().slice(0, 10);\n}''',
    'const localIso = (offset = 0) => shiftHotelDateIso(offset);',
)

# Public AI booking defaults must follow the resort business date, not visitor device timezone.
add_import("apps/web/components/AiAdministratorWidget.tsx", 'import { shiftHotelDateIso } from "../lib/hotelDate";')
replace_once(
    "apps/web/components/AiAdministratorWidget.tsx",
    '''function todayIso(offset = 0) {\n  const now = new Date();\n  const value = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset);\n  const y = value.getFullYear();\n  const m = String(value.getMonth() + 1).padStart(2, "0");\n  const d = String(value.getDate()).padStart(2, "0");\n  return `${y}-${m}-${d}`;\n}''',
    'const todayIso = (offset = 0) => shiftHotelDateIso(offset);',
)

contract = '''from pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\n\nHELPERS = [\n    ROOT / "apps/admin/lib/hotelDate.ts",\n    ROOT / "apps/staff/lib/hotelDate.ts",\n    ROOT / "apps/web/lib/hotelDate.ts",\n]\n\nTARGETS = {\n    "apps/admin/components/AgentsBoard.tsx": "hotelDateIso",\n    "apps/admin/components/RoomBlocksPanel.tsx": "hotelDateIso",\n    "apps/admin/components/GroupBookingBoard.tsx": "shiftHotelDateIso",\n    "apps/admin/components/DiningManagementBoard.tsx": "hotelDateIso",\n    "apps/staff/components/DiningDayPlanner.tsx": "hotelDateIso",\n    "apps/staff/components/DiningGuestSeatingPanel.tsx": "hotelDateIso",\n    "apps/staff/components/ChefProduction.tsx": "shiftHotelDateIso",\n    "apps/web/components/AiAdministratorWidget.tsx": "shiftHotelDateIso",\n}\n\nFORBIDDEN = (\n    "new Date().toISOString().slice(0, 10)",\n    "getTimezoneOffset() * 60000",\n    "now.getFullYear(), now.getMonth(), now.getDate()",\n)\n\nfor helper in HELPERS:\n    text = helper.read_text(encoding="utf-8")\n    assert 'HOTEL_TIME_ZONE = "Asia/Bishkek"' in text, helper\n    assert "formatToParts" in text, helper\n    assert "Date.UTC" in text, helper\n\nfor relative, helper_name in TARGETS.items():\n    text = (ROOT / relative).read_text(encoding="utf-8")\n    assert helper_name in text, relative\n    for bad in FORBIDDEN:\n        assert bad not in text, f"{relative}: device/UTC hotel-date logic remains: {bad}"\n\n# Date-only UTC arithmetic remains intentionally allowed where the input is already YYYY-MM-DD.\nroom_blocks = (ROOT / "apps/admin/components/RoomBlocksPanel.tsx").read_text(encoding="utf-8")\nassert "Date.UTC(y, m - 1, d + amount)" in room_blocks\n\nprint("hotel business date contract: OK")\n'''
write("scripts/hotel_business_date_contract_test.py", contract)

workflow = '''name: Hotel Business Date CI\n\non:\n  pull_request:\n  push:\n    branches: [main]\n\npermissions:\n  contents: read\n\njobs:\n  hotel-date-contract:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: "3.12"\n      - name: Verify Asia/Bishkek business-date contract\n        run: python scripts/hotel_business_date_contract_test.py\n'''
write(".github/workflows/hotel-business-date-ci.yml", workflow)

# Remove one-shot patch machinery from the final feature commit.
for temporary in (
    ROOT / "scripts/apply_hotel_date_fix.py",
    ROOT / ".github/workflows/apply-hotel-date-fix.yml",
):
    if temporary.exists():
        temporary.unlink()

print("hotel date patch applied")
