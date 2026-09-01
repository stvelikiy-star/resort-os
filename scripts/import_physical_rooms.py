#!/usr/bin/env python3
"""Fail-closed physical-room reconciliation for Three Crowns.

The canonical source is ``data-intake/rooms.csv`` and production authority is the
checksum-bound ``room-register-owner-approval.json`` verified by
``room_register_review.py``. Dry-run is the default. Writes require ``--apply``.

This command updates physical room metadata only. It never creates or changes rates,
reservations, payments, inventory blocks, or runtime room operational state. Unknown
optional physical metadata stays NULL rather than being guessed.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

import asyncpg

from room_register_review import (
    audit_checklist,
    audit_rooms,
    load_checklist,
    load_rooms,
    validate_owner_approval,
)
from seed_from_intake import ROOM_TYPE_CODES

PROPERTY_CODE = "THREE_CROWNS"
EXPECTED_ROOM_COUNT = 84
EXPECTED_ROOM_TYPE_COUNT = 12
DEFAULT_ROOMS = Path("data-intake/rooms.csv")
DEFAULT_APPROVAL = Path("data-intake/room-register-owner-approval.json")
DEFAULT_CHECKLIST = Path("data-intake/owner-room-checklist.json")


@dataclass(frozen=True)
class RoomInput:
    code: str
    name: str
    building_or_zone: str | None
    floor_label: str | None
    room_type_name: str
    room_type_code: str
    area_m2: str | None
    beds: str | None
    capacity_adults: int
    capacity_children: int | None
    notes: str | None


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "postgresql://resort:resort@localhost:5432/resort_os")
    return value.replace("?schema=public", "")


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized or normalized.upper() == "UNKNOWN":
        return None
    return normalized


def nullable_int(value: str | None, field: str, room_code: str) -> int | None:
    normalized = clean(value)
    if normalized is None:
        return None
    try:
        result = int(normalized)
    except ValueError as exc:
        raise ValueError(f"room {room_code}: {field} must be an integer or UNKNOWN, got {normalized!r}") from exc
    if result < 0:
        raise ValueError(f"room {room_code}: {field} cannot be negative")
    return result


def required_int(value: str | None, field: str, room_code: str) -> int:
    result = nullable_int(value, field, room_code)
    if result is None:
        raise ValueError(f"room {room_code}: {field} is required")
    return result


def validate_approval(rooms_path: Path, approval_path: Path, checklist_path: Path) -> list[dict[str, str]]:
    rooms = load_rooms(rooms_path)
    checklist = load_checklist(checklist_path)
    structural_errors, issues = audit_rooms(rooms)
    structural_errors.extend(audit_checklist(checklist))

    import json

    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    # validate_owner_approval uses room_register_review.checksum() against its canonical
    # default path. Production reconciliation intentionally accepts only that canonical
    # path, so a caller cannot authorize an arbitrary replacement CSV with old evidence.
    if rooms_path.resolve() != DEFAULT_ROOMS.resolve():
        raise ValueError("production room reconciliation only accepts canonical data-intake/rooms.csv")
    errors = validate_owner_approval(approval, rooms, structural_errors, issues, checklist)
    if errors:
        raise ValueError("owner approval verification failed:\n- " + "\n- ".join(errors))
    return rooms


def parse_rooms(raw_rows: list[dict[str, str]]) -> list[RoomInput]:
    if len(raw_rows) != EXPECTED_ROOM_COUNT:
        raise ValueError(f"Expected exactly {EXPECTED_ROOM_COUNT} room rows, got {len(raw_rows)}")

    parsed: list[RoomInput] = []
    seen: set[str] = set()
    for raw in raw_rows:
        code = (raw.get("room_code") or "").strip()
        name = (raw.get("room_name") or "").strip()
        room_type_name = (raw.get("room_type") or "").strip()
        if not code or not name or not room_type_name:
            raise ValueError(f"room row missing room_code/room_name/room_type: {raw}")
        if code in seen:
            raise ValueError(f"duplicate room_code {code!r}")
        seen.add(code)
        if room_type_name not in ROOM_TYPE_CODES:
            raise ValueError(f"room {code}: unmapped room_type {room_type_name!r}")

        parsed.append(
            RoomInput(
                code=code,
                name=name,
                building_or_zone=clean(raw.get("building_or_zone")),
                floor_label=clean(raw.get("floor")),
                room_type_name=room_type_name,
                room_type_code=ROOM_TYPE_CODES[room_type_name],
                area_m2=clean(raw.get("area_m2")),
                beds=clean(raw.get("bed_configuration")),
                capacity_adults=required_int(raw.get("capacity_adults"), "capacity_adults", code),
                capacity_children=nullable_int(raw.get("capacity_children"), "capacity_children", code),
                notes=clean(raw.get("notes")),
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
    expected_codes = set(ROOM_TYPE_CODES.values())
    if len(type_map) != EXPECTED_ROOM_TYPE_COUNT or set(type_map) != expected_codes:
        raise RuntimeError(
            f"Database room-type mismatch: count={len(type_map)} missing={sorted(expected_codes-set(type_map))} "
            f"extra={sorted(set(type_map)-expected_codes)}"
        )

    current_rooms = await conn.fetch(
        '''
        SELECT r.id,r.code,r.name,r."buildingOrZone",r."floorLabel",r."bedConfiguration",r."areaLabel",
               r."operationalState"::text AS operational_state,r.notes,rt.code AS room_type_code
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
        if row.capacity_adults != room_type["capacityAdults"]:
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
                '''SELECT count(*) FROM inventory_blocks ib JOIN rooms r ON r.id=ib."roomId" WHERE r."propertyId"=$1''',
                property_id,
            )
            or 0
        ),
        "room_tasks": int(
            await conn.fetchval(
                '''SELECT count(*) FROM operational_tasks t JOIN rooms r ON r.id=t."roomId" WHERE r."propertyId"=$1''',
                property_id,
            )
            or 0
        ),
    }


def metadata_changes(row: RoomInput, old) -> list[str]:
    fields: list[str] = []
    comparisons = {
        "name": (old["name"], row.name),
        "building_or_zone": (old["buildingOrZone"], row.building_or_zone),
        "floor_label": (old["floorLabel"], row.floor_label),
        "room_type_code": (old["room_type_code"], row.room_type_code),
        "area_m2": (old["areaLabel"], row.area_m2),
        "beds": (old["bedConfiguration"], row.beds),
        "notes": (old["notes"], row.notes),
    }
    for field, (before, after) in comparisons.items():
        if (before or None) != (after or None):
            fields.append(field)
    return fields


def diff_summary(rows: list[RoomInput], current_rooms) -> tuple[set[str], set[str], dict[str, list[str]]]:
    desired_codes = {row.code for row in rows}
    current_codes = set(current_rooms)
    added = desired_codes - current_codes
    missing = current_codes - desired_codes
    changed: dict[str, list[str]] = {}
    for row in rows:
        old = current_rooms.get(row.code)
        if old is None:
            continue
        fields = metadata_changes(row, old)
        if fields:
            changed[row.code] = fields
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
            "room_code set differs from database. Review dry-run evidence first; --allow-reconcile-codes is permitted only on safe pre-launch/staging data."
        )

    if added or missing:
        refs = await reference_counts(conn, property_id)
        if any(refs.values()):
            raise RuntimeError(f"Refusing room-code reconciliation because room history exists: {refs}")
        if missing:
            await conn.execute(
                'DELETE FROM rooms WHERE "propertyId"=$1 AND code=ANY($2::text[])', property_id, sorted(missing)
            )

    for row in rows:
        # operationalState is deliberately absent from both INSERT conflict updates and
        # the metadata diff. Existing runtime PMS truth survives reconciliation; newly
        # inserted rooms start UNKNOWN and require cutover inspection.
        await conn.execute(
            '''
            INSERT INTO rooms (
              id,"propertyId","roomTypeId",code,name,"buildingOrZone","floorLabel",
              "bedConfiguration","areaLabel","operationalState",notes,"createdAt","updatedAt"
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'UNKNOWN',$10,now(),now())
            ON CONFLICT ("propertyId",code) DO UPDATE SET
              "roomTypeId"=EXCLUDED."roomTypeId",
              name=EXCLUDED.name,
              "buildingOrZone"=EXCLUDED."buildingOrZone",
              "floorLabel"=EXCLUDED."floorLabel",
              "bedConfiguration"=EXCLUDED."bedConfiguration",
              "areaLabel"=EXCLUDED."areaLabel",
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
            row.notes,
        )

    final_count = await conn.fetchval('SELECT count(*) FROM rooms WHERE "propertyId"=$1', property_id)
    if final_count != EXPECTED_ROOM_COUNT:
        raise RuntimeError(f"Post-import verification failed: expected {EXPECTED_ROOM_COUNT} rooms, got {final_count}")


async def run(args) -> int:
    raw_rows = validate_approval(Path(args.rooms), Path(args.approval), Path(args.checklist))
    rows = parse_rooms(raw_rows)
    conn = await asyncpg.connect(database_url())
    try:
        prop, type_map, current_rooms = await load_context(conn)
        validate_capacity(rows, type_map)
        added, missing, changed = diff_summary(rows, current_rooms)
        refs = await reference_counts(conn, prop["id"])

        print(f"owner_approval=VERIFIED canonical_rooms={len(rows)}")
        print(f"property={prop['code']} desired_rooms={len(rows)} current_rooms={len(current_rooms)}")
        print(f"added_codes={len(added)} missing_codes={len(missing)} metadata_changes={len(changed)}")
        for code in sorted(changed):
            print(f"change {code}: {','.join(changed[code])}")
        if added:
            print("added:", ", ".join(sorted(added)))
        if missing:
            print("missing:", ", ".join(sorted(missing)))
        print("references:", refs)
        print("operational_state_policy=PRESERVE_EXISTING; NEW_ROOMS_START_UNKNOWN")

        if not args.apply:
            print("DRY RUN OK: approval verified; no database changes were made.")
            return 0

        if refs["active_reservations"] > 0:
            raise RuntimeError(
                "Refusing physical-room apply while GUARANTEED/CHECKED_IN reservations exist. Use staging/pre-launch data or a controlled maintenance window."
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

        print("APPLY OK: 84 owner-approved physical rooms verified; runtime operational state preserved.")
        return 0
    finally:
        await conn.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Three Crowns owner-approved physical 84-room reconciliation")
    parser.add_argument("--rooms", default=str(DEFAULT_ROOMS), help="Canonical rooms.csv; alternate paths are rejected")
    parser.add_argument("--approval", default=str(DEFAULT_APPROVAL), help="Checksum-bound owner approval JSON")
    parser.add_argument("--checklist", default=str(DEFAULT_CHECKLIST), help="Captured owner checklist provenance JSON")
    parser.add_argument("--apply", action="store_true", help="Commit metadata changes. Default is dry-run only.")
    parser.add_argument(
        "--allow-reconcile-codes",
        action="store_true",
        help="Allow room-code add/remove only with zero room history. Requires --apply.",
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
