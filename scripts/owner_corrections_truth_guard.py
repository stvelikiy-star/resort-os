#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOMS = ROOT / "data-intake" / "rooms.csv"
APPROVAL = ROOT / "data-intake" / "room-register-owner-approval.json"
OWNER_MIGRATION = ROOT / "packages" / "database" / "prisma" / "migrations" / "z11_owner_corrections_20260905" / "migration.sql"
SETTINGS = ROOT / "services" / "api" / "app" / "guest_service_settings.py"
SITE_DEFAULTS = ROOT / "services" / "api" / "data" / "site_content_defaults.json"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    with ROOMS.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 84:
        fail(f"expected 84 rooms, got {len(rows)}")

    by_code = {row["room_code"].strip(): row for row in rows}
    for code in ("501", "502"):
        row = by_code.get(code)
        if not row:
            fail(f"room {code} missing")
        expected = {
            "floor": "BASEMENT",
            "room_type": "Двухместный стандарт, цоколь",
            "capacity_adults": "2",
        }
        for field, value in expected.items():
            if row[field].strip() != value:
                fail(f"room {code} {field}={row[field]!r}, expected {value!r}")
        notes = row["notes"] or ""
        if "OWNER_APPROVED_2026-09-05" not in notes:
            fail(f"room {code} is missing 2026-09-05 owner-correction evidence")

    approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    digest = hashlib.sha256(ROOMS.read_bytes()).hexdigest()
    if approval.get("status") != "OWNER_APPROVED":
        fail("room register approval is not OWNER_APPROVED")
    if approval.get("room_count") != 84:
        fail("room register approval count is not 84")
    if approval.get("rooms_sha256") != digest:
        fail(f"room register checksum drift: approval={approval.get('rooms_sha256')} actual={digest}")
    if "P0_501_502_BASEMENT_CORRECTION" not in approval.get("resolved_question_ids", []):
        fail("owner correction question is not recorded as resolved")

    migration = OWNER_MIGRATION.read_text(encoding="utf-8")
    for token in ("DOUBLE_STANDARD_BASEMENT", "r.code IN ('501', '502')", "'BASEMENT'"):
        if token not in migration:
            fail(f"owner correction migration missing token: {token}")

    settings = SETTINGS.read_text(encoding="utf-8")
    if "VALUES ($1,$2,60,true,200,3,true,now(),now())" not in settings:
        fail("owner guest-service defaults drifted from cutoff=60, delivery=200, housekeeping=3, linen=true")

    defaults = json.loads(SITE_DEFAULTS.read_text(encoding="utf-8"))
    for locale in ("ru", "kg", "en"):
        conference = defaults[locale]["conference"]
        if "20" not in conference["capacity"] or "120" not in conference["capacity"]:
            fail(f"{locale} conference capacity drifted")
        if not conference.get("menu"):
            fail(f"{locale} conference individual-menu rule missing")

    print(
        "PASS: owner corrections are consistent across canonical room intake, checksum evidence, "
        "database migration, guest-service defaults and public conference content"
    )


if __name__ == "__main__":
    main()
