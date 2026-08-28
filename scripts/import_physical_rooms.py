#!/usr/bin/env python3
"""Fail-closed physical-room importer for Three Crowns.

Expected input is a CSV export of the Google Sheet tab `ROOMS_IMPORT`.
Dry-run is the default. Writes require `--apply`.

This importer only updates physical rooms. Room-type definitions, rates,
reservations, payments and inventory truth are never created from Google data.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

import asyncpg

PROPERTY_CODE = "THREE_CROWNS"
EXPECTED_ROOM_COUNT = 84
EXPECTED_ROOM_TYPE_COUNT = 12

ALLOWED_ROOM_TYPE_CODES = {
    "SINGLE_BASEMENT",
    "DOUBLE_STANDARD_BASEMENT",
    "SINGLE_IMPROVED",
    "DOUBLE_IMPROVED",
    "DOUBLE_COTTAGE",
    "JUNIOR_SUITE_NO_BALCONY",
    "SUITE_DOUBLE",
    "SUITE_TRIPLE",
    "TWO_ROOM_JUNIOR_SUITE",
    "TWO_ROOM_STANDARD",
    "APARTMENT",
    "APARTMENT_KITCHEN",
}

ALLOWED_OPERATIONAL_STATES = {"CLEAN", "DIRTY", "IN_INSPECTION", "TECH_BLOCK"}

REQUIRED_COLUMNS = {
    "room_code",
    "room_name",
    "building_or_zone",
    "floor_label",
    "room_type_code",
    "operational_state",
    "area_m2",
    "beds",
    "capacity_adults",
    "capacity_children",
    "notes",
    "owner_confirmed",
    "import_status",
}


@dataclass(frozen=True)
class RoomInput:
    code: str
    name: str
    building_or_zone: str
    floor_label: str
    room_type_code: str
    operational_state: str
    area_m2: str | None
    beds: str | None
    capacity_adults: int | None
    capacity_children: int | None
    notes: str | None


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "postgresql://resort:resort@localhost:5432/resort_os")
    return value.replace("?schema=public", "")


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def required_text(row: dict[str, str], field: str, row_number: int) -> str:
    value = clean(row.get(field))
    if not value or value.upper() == "UNKNOWN":
        raise ValueError(f"row {row_number}: {field} must be explicitly confirmed; got {value!r}")
    return value


def optional_int(value: str | None, field: str, row_number: int) -> int | None:
    normalized = clean(value)
    if not normalized:
        return None
    try:
        result = int(normalized)
    except ValueError as exc:
        raise ValueError(f"row {row_number}: {field} must be an integer, got {normalized!r}") from exc
    if result < 0:
        raise ValueError(f"row {row_number}: {field} cannot be negative")
    return result


def load_csv(path: Path) -> list[RoomInput]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - headers)
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(missing)}")
        source_rows = list(reader)

    # Ignore completely empty spreadsheet tail rows, but never silently ignore a partially filled row.
    rows = [row for row in source_rows if any(clean(value) for key, value in row.items() if key != "row_no")]
    if len(rows) != EXPECTED_ROOM_COUNT:
        raise ValueError(f"Expected exactly {EXPECTED_ROOM_COUNT} populated room rows, got {len(rows)}")

    parsed: list[RoomInput] = []
    seen_codes: set[str] = set()
    for index, row in enumerate(rows, start=2):
        owner_confirmed = (clean(row.get("owner_confirmed")) or "").upper()
        if owner_confirmed != "YES":
            raise ValueError(f"row {index}: owner_confirmed must be YES before production import")

        import_status = (clean(row.get("import_status")) or "").upper()
        if import_status and import_status != "READY":
            raise ValueError(f"row {index}: import_status must be READY, got {import_status!r}")

        code = required_text(row, "room_code", index)
        if code in seen_codes:
            raise ValueError(f"row {index}: duplicate room_code {code!r}")
        seen_codes.add(code)

        room_type_code = required_text(row, "room_type_code", index).upper()
        if room_type_code not in ALLOWED_ROOM_TYPE_CODES:
            raise ValueError(f"row {index}: unsupported room_type_code {room_type_code!r}")

        operational_state = required_text(row, "operational_state", index).upper()
        if operational_state not in ALLOWED_OPERATIONAL_STATES:
            raise ValueError(f"row {index}: unsupported operational_state {operational_state!r}")

        parsed.append(
            RoomInput(
                code=code,
                name=required_text(row, "room_name", index),
                building_or_zone=required_text(row, "building_or_zone", index),
                floor_label=required_text(row, "floor_label", index),
                room_type_code=room_type_code,
                operational_state=operational_state,
                area_m2=clean(row.get("area_m2")),
                beds=clean(row.get("beds")),
                capacity_adults=optional_int(row.get("capacity_adults"), "capacity_adults", index),
                capacity_children=optional_int(row.get("capacity_children"), "capacity_children", index),
                notes=clean(row.get("notes")),
            )
        )
    return parsed


async def load_context(conn: asyncpg.Connection):
    prop = await conn.fetchrow("SELECT id,code,name FROM properties WHERE code=$1", PROPERTY_CODE)
    if not prop:
        raise RuntimeError(f"Property {PROPERTY_CODE} is not loaded")

    room_types = await conn.fetch(
        '''
        SELECT id,code,name,"capacityAdults","capacityChildren"
        FROM room_types
        WHERE "propertyId"=$1
        ORDER BY code
        ''',
        prop["id"],
    )
    type_map = {row["code"]: row for row in room_types}
    if len(type_map) != EXPECTED_ROOM_TYPE_COUNT:
        raise RuntimeError(f"Database must contain exactly {EXPECTED_ROOM_TYPE_COUNT} room types; got {len(type_map)}")
    missing_types = sorted(ALLOWED_ROOM_TYPE_CODES - set(type_map))
    extra_types = sorted(set(type_map) - ALLOWED_ROOM_TYPE_CODES)
    if missing_types or extra_types:
        raise RuntimeError(f"Room-type code mismatch. missing={missing_types}, extra={extra_types}")

    current_rooms = await conn.fetch(
        '''
        SELECT r.id,r.code,r.name,r."buildingOrZone",r."floorLabel",r."bedConfiguration",r."areaLabel",
               r."operationalState"::text AS operational_state,rt.code AS room_type_code
        FROM rooms r
        JOIN room_types rt ON rt.id=r."roomTypeId"
        WHERE r."propertyId"=$1
        ORDER BY r.code
        ''',
        prop["id"],
    )
    return prop, type_map, {row["code"]: row for row in current_rooms}


def validate_capacity(rows: list[RoomInput], type_map) -> None:
    errors: list[str] = []
    for row in rows:
        room_type = type_map[row.room_type_code]
        if row.capacity_adults is not None and row.capacity_adults != room_type["capacityAdults"]:
            errors.append(
                f"{row.code}: capacity_adults={row.capacity_adults}, Core category {row.room_type_code}={room_type['capacityAdults']}"
            )
        core_children = room_type["capacityChildren"]
        if row.capacity_children is not None and core_children is not None and row.capacity_children != core_children:
            errors.append(
                f"{row.code}: capacity_children={row.capacity_children}, Core category {row.room_type_code}={core_children}"
            )
    if errors:
        raise RuntimeError("Capacity/category mismatches:\n- " + "\n- ".join(errors))


async def reference_counts(conn: asyncpg.Connection, property_id: uuid.UUID) -> dict[str, int]:
    return {
        "active_reservations": int(
            await conn.fetchval(
                '''SELECT count(*) FROM reservations WHERE "propertyId"=$1 AND status IN ('GUARANTEED','CHECKED_IN')''',
                property_id,
            )
            or 0
        ),
        "inventory_blocks": int(
            await conn.fetchval(
                '''
                SELECT count(*)
                FROM inventory_blocks ib
                JOIN rooms r ON r.id=ib."roomId"
                WHERE r."propertyId"=$1
                ''',
                property_id,
            )
            or 0
        ),
        "room_tasks": int(
            await conn.fetchval(
                '''
                SELECT count(*)
                FROM operational_tasks t
                JOIN rooms r ON r.id=t."roomId"
                WHERE r."propertyId"=$1
                ''',
                property_id,
            )
            or 0
        ),
    }


def diff_summary(rows: list[RoomInput], current_rooms) -> tuple[set[str], set[str], list[str]]:
    desired_codes = {row.code for row in rows}
    current_codes = set(current_rooms)
    added = desired_codes - current_codes
    missing = current_codes - desired_codes
    changed: list[str] = []
    desired_by_code = {row.code: row for row in rows}
    for code in sorted(desired_codes & current_codes):
        old = current_rooms[code]
        new = desired_by_code[code]
        if any(
            [
                old["name"] != new.name,
                (old["buildingOrZone"] or "") != new.building_or_zone,
                (old["floorLabel"] or "") != new.floor_label,
                old["room_type_code"] != new.room_type_code,
                old["operational_state"] != new.operational_state,
                (old["areaLabel"] or "") != (new.area_m2 or ""),
                (old["bedConfiguration"] or "") != (new.beds or ""),
            ]
        ):
            changed.append(code)
    return added, missing, changed


async def apply_rooms(
    conn: asyncpg.Connection,
    property_id: uuid.UUID,
    rows: list[RoomInput],
    type_map,
    current_rooms,
    allow_reconcile_codes: bool,
) -> None:
    added, missing, _ = diff_summary(rows, current_rooms)
    if (added or missing) and not allow_reconcile_codes:
        raise RuntimeError(
            "room_code set differs from database. Re-run dry-run, verify owner-approved mapping, then use --allow-reconcile-codes only on a safe pre-launch/staging database."
        )

    if added or missing:
        refs = await reference_counts(conn, property_id)
        if any(refs.values()):
            raise RuntimeError(f"Refusing room-code reconciliation because room history exists: {refs}")
        if missing:
            await conn.execute(
                'DELETE FROM rooms WHERE "propertyId"=$1 AND code=ANY($2::text[])',
                property_id,
                sorted(missing),
            )

    for row in rows:
        await conn.execute(
            '''
            INSERT INTO rooms (
              id,"propertyId","roomTypeId",code,name,"buildingOrZone","floorLabel",
              "bedConfiguration","areaLabel","operationalState",notes,"createdAt","updatedAt"
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::"RoomOperationalState",$11,now(),now())
            ON CONFLICT ("propertyId",code) DO UPDATE SET
              "roomTypeId"=EXCLUDED."roomTypeId",
              name=EXCLUDED.name,
              "buildingOrZone"=EXCLUDED."buildingOrZone",
              "floorLabel"=EXCLUDED."floorLabel",
              "bedConfiguration"=EXCLUDED."bedConfiguration",
              "areaLabel"=EXCLUDED."areaLabel",
              "operationalState"=EXCLUDED."operationalState",
              notes=EXCLUDED.notes,
              "updatedAt"=now()
            ''',
            uuid.uuid4(),
            property_id,
            type_map[row.room_type_code]["id"],
            row.code,
            row.name,
            row.building_or_zone,
            row.floor_label,
            row.beds,
            row.area_m2,
            row.operational_state,
            row.notes,
        )

    final_count = await conn.fetchval('SELECT count(*) FROM rooms WHERE "propertyId"=$1', property_id)
    if final_count != EXPECTED_ROOM_COUNT:
        raise RuntimeError(f"Post-import verification failed: expected 84 rooms, got {final_count}")


async def run(args) -> int:
    rows = load_csv(Path(args.csv))
    conn = await asyncpg.connect(database_url())
    try:
        prop, type_map, current_rooms = await load_context(conn)
        validate_capacity(rows, type_map)
        added, missing, changed = diff_summary(rows, current_rooms)
        refs = await reference_counts(conn, prop["id"])

        print(f"property={prop['code']} desired_rooms={len(rows)} current_rooms={len(current_rooms)}")
        print(f"added_codes={len(added)} missing_codes={len(missing)} metadata_or_state_changes={len(changed)}")
        if added:
            print("added:", ", ".join(sorted(added)))
        if missing:
            print("missing:", ", ".join(sorted(missing)))
        print("references:", refs)

        if not args.apply:
            print("DRY RUN OK: no database changes were made.")
            return 0

        if refs["active_reservations"] > 0:
            raise RuntimeError(
                "Refusing production room import while GUARANTEED/CHECKED_IN reservations exist. Use a staging/pre-launch database or schedule a controlled maintenance window."
            )

        async with conn.transaction():
            await apply_rooms(
                conn,
                prop["id"],
                rows,
                type_map,
                current_rooms,
                allow_reconcile_codes=args.allow_reconcile_codes,
            )

        print("APPLY OK: 84 physical rooms verified and committed transactionally.")
        return 0
    finally:
        await conn.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Three Crowns physical 84-room importer")
    parser.add_argument("csv", help="CSV export of Google Sheet tab ROOMS_IMPORT")
    parser.add_argument("--apply", action="store_true", help="Commit changes. Default is dry-run only.")
    parser.add_argument(
        "--allow-reconcile-codes",
        action="store_true",
        help="Allow add/remove room codes only when there is zero room history. Requires --apply.",
    )
    args = parser.parse_args()
    if args.allow_reconcile_codes and not args.apply:
        parser.error("--allow-reconcile-codes requires --apply")
    return args


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(run(parse_args())))
    except Exception as exc:
        print(f"IMPORT FAILED: {exc}", file=sys.stderr)
        raise
