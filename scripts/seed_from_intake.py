import asyncio
import csv
import os
import re
import uuid
from datetime import date
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
ROOMS_CSV = ROOT / "data-intake" / "rooms.csv"
RATES_CSV = ROOT / "data-intake" / "rates.csv"

PROPERTY_CODE = "THREE_CROWNS"
PROPERTY_NAME = "Три Короны"
RATE_PLAN_CODE = "DIRECT_2026_27"
RATE_PLAN_NAME = "Direct official tariff 2026/27"

ROOM_TYPE_CODES = {
    "Одноместный, цоколь": "SINGLE_BASEMENT",
    "Двухместный стандарт, цоколь": "DOUBLE_STANDARD_BASEMENT",
    "Одноместный, улучшенный": "SINGLE_IMPROVED",
    "Двухместный стандарт в коттеджном доме": "DOUBLE_COTTAGE",
    "Двухместный улучшенный": "DOUBLE_IMPROVED",
    "Полулюкс без балкона": "JUNIOR_SUITE_NO_BALCONY",
    "Люкс двухместный": "SUITE_DOUBLE",
    "Люкс трехместный": "SUITE_TRIPLE",
    "Двухкомнатный стандарт": "TWO_ROOM_STANDARD",
    "Двухкомнатный полулюкс": "TWO_ROOM_JUNIOR_SUITE",
    "Апартаменты": "APARTMENT",
    "Квартиры / апартаменты с кухней": "APARTMENT_KITCHEN",
}

# Owner correction supersedes the older intake reconstruction for these exact rooms.
# Keep untouched raw bed/area fields because the owner correction only changes location,
# operational existence/capacity and category.
OWNER_ROOM_CORRECTIONS = {
    "501": {
        "floor": "BASEMENT",
        "room_type": "Двухместный стандарт, цоколь",
        "capacity_adults": "2",
        "note": "OWNER_APPROVED_2026-09-05: basement above laundry; operational; two-person room",
    },
    "502": {
        "floor": "BASEMENT",
        "room_type": "Двухместный стандарт, цоколь",
        "capacity_adults": "2",
        "note": "OWNER_APPROVED_2026-09-05: basement above laundry; operational; two-person room",
    },
}


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "postgresql://resort:resort@localhost:5432/resort_os")
    return value.replace("?schema=public", "")


def nullable_int(value: str | None) -> int | None:
    if value is None:
        return None
    value = value.strip()
    if not value or value.upper() == "UNKNOWN":
        return None
    return int(value)


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value or value.upper() == "UNKNOWN":
        return None
    return value


def rate_capacity_adults(row: dict) -> int:
    """Derive capacity only from the explicit tariff occupancy rule.

    Some owner-approved room corrections can legitimately leave a sellable tariff
    category with zero currently assigned rooms. In that case the category must not
    disappear from room_types, because rates remain authoritative evidence that the
    category exists. We never invent a room; only the type metadata is retained.
    """
    rule = clean(row.get("occupancy_rule"))
    if not rule:
        raise RuntimeError(f"Rate row for {row.get('room_type')} has no occupancy_rule")
    match = re.search(r"\b(\d+)\b", rule)
    if not match:
        raise RuntimeError(f"Cannot derive capacity from occupancy_rule={rule!r}")
    capacity = int(match.group(1))
    if capacity <= 0 or capacity > 20:
        raise RuntimeError(f"Invalid tariff capacity {capacity} in occupancy_rule={rule!r}")
    return capacity


def load_rooms() -> list[dict]:
    with ROOMS_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        code = row["room_code"].strip()
        correction = OWNER_ROOM_CORRECTIONS.get(code)
        if not correction:
            continue
        row["floor"] = correction["floor"]
        row["room_type"] = correction["room_type"]
        row["capacity_adults"] = correction["capacity_adults"]
        existing = clean(row.get("notes"))
        row["notes"] = f"{existing}; {correction['note']}" if existing else correction["note"]

    codes = [r["room_code"].strip() for r in rows]
    if len(rows) != 84:
        raise RuntimeError(f"Expected 84 room rows, got {len(rows)}")
    if len(codes) != len(set(codes)):
        raise RuntimeError("Duplicate room_code detected")
    unknown_types = sorted({r["room_type"].strip() for r in rows} - set(ROOM_TYPE_CODES))
    if unknown_types:
        raise RuntimeError(f"Unmapped room types: {unknown_types}")
    return rows


def load_rates() -> list[dict]:
    with RATES_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    unknown_types = sorted({r["room_type"].strip() for r in rows} - set(ROOM_TYPE_CODES))
    if unknown_types:
        raise RuntimeError(f"Unmapped rate room types: {unknown_types}")
    return rows


async def upsert_property(conn) -> uuid.UUID:
    return await conn.fetchval(
        '''
        INSERT INTO properties (id, code, name, timezone, currency, "createdAt", "updatedAt")
        VALUES ($1, $2, $3, 'Asia/Bishkek', 'KGS', now(), now())
        ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, "updatedAt" = now()
        RETURNING id
        ''',
        uuid.uuid4(), PROPERTY_CODE, PROPERTY_NAME,
    )


async def upsert_room_types(
    conn,
    property_id: uuid.UUID,
    room_rows: list[dict],
    rate_rows: list[dict],
) -> dict[str, uuid.UUID]:
    """Seed all canonical categories backed by either inventory or tariff evidence.

    Inventory determines the facts for categories that currently have rooms. Tariff
    rows are a safe fallback for a category with no room after an owner correction.
    This keeps the canonical 12-category catalogue without synthesizing inventory.
    """
    room_samples: dict[str, dict] = {}
    rate_samples: dict[str, dict] = {}
    for row in room_rows:
        room_samples.setdefault(row["room_type"].strip(), row)
    for row in rate_rows:
        rate_samples.setdefault(row["room_type"].strip(), row)

    ids: dict[str, uuid.UUID] = {}
    for name, code in ROOM_TYPE_CODES.items():
        room_sample = room_samples.get(name)
        rate_sample = rate_samples.get(name)
        if room_sample is None and rate_sample is None:
            raise RuntimeError(f"Room type {name!r} has neither room nor tariff evidence")

        if room_sample is not None:
            capacity_adults = int(room_sample["capacity_adults"])
            capacity_children = nullable_int(room_sample.get("capacity_children"))
            area_label = clean(room_sample.get("area_m2"))
        else:
            capacity_adults = rate_capacity_adults(rate_sample)
            capacity_children = None
            area_label = None

        room_type_id = await conn.fetchval(
            '''
            INSERT INTO room_types (
                id, "propertyId", code, name, "capacityAdults", "capacityChildren", "areaLabel", "createdAt", "updatedAt"
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, now(), now())
            ON CONFLICT ("propertyId", code) DO UPDATE SET
                name = EXCLUDED.name,
                "capacityAdults" = EXCLUDED."capacityAdults",
                "capacityChildren" = EXCLUDED."capacityChildren",
                "areaLabel" = EXCLUDED."areaLabel",
                "updatedAt" = now()
            RETURNING id
            ''',
            uuid.uuid4(), property_id, code, name,
            capacity_adults, capacity_children, area_label,
        )
        ids[name] = room_type_id
    return ids


async def upsert_rooms(conn, property_id: uuid.UUID, type_ids: dict[str, uuid.UUID], rows: list[dict]) -> None:
    for row in rows:
        room_type = row["room_type"].strip()
        await conn.execute(
            '''
            INSERT INTO rooms (
                id, "propertyId", "roomTypeId", code, name, "buildingOrZone", "floorLabel",
                "bedConfiguration", "areaLabel", "operationalState", notes, "createdAt", "updatedAt"
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'UNKNOWN', $10, now(), now())
            ON CONFLICT ("propertyId", code) DO UPDATE SET
                "roomTypeId" = EXCLUDED."roomTypeId",
                name = EXCLUDED.name,
                "buildingOrZone" = EXCLUDED."buildingOrZone",
                "floorLabel" = EXCLUDED."floorLabel",
                "bedConfiguration" = EXCLUDED."bedConfiguration",
                "areaLabel" = EXCLUDED."areaLabel",
                notes = EXCLUDED.notes,
                "updatedAt" = now()
            ''',
            uuid.uuid4(), property_id, type_ids[room_type], row["room_code"].strip(),
            row["room_name"].strip(), clean(row.get("building_or_zone")), clean(row.get("floor")),
            clean(row.get("bed_configuration")), clean(row.get("area_m2")), clean(row.get("notes")),
        )


async def upsert_rates(conn, property_id: uuid.UUID, type_ids: dict[str, uuid.UUID], rows: list[dict]) -> None:
    plan_id = await conn.fetchval(
        '''
        INSERT INTO rate_plans (id, "propertyId", code, name, currency, "createdAt", "updatedAt")
        VALUES ($1, $2, $3, $4, 'KGS', now(), now())
        ON CONFLICT ("propertyId", code) DO UPDATE SET name = EXCLUDED.name, "updatedAt" = now()
        RETURNING id
        ''',
        uuid.uuid4(), property_id, RATE_PLAN_CODE, RATE_PLAN_NAME,
    )

    for row in rows:
        room_type_name = row["room_type"].strip()
        price = int(row["price_kgs"])
        notes = clean(row.get("notes"))
        # A zero in the legacy/off-season source is never treated as a free sale price.
        sale_status = "CONFIRM_REQUIRED" if price <= 0 else "OPEN"
        valid_from = date.fromisoformat(row["valid_from"])
        valid_to = date.fromisoformat(row["valid_to"])
        await conn.execute(
            '''
            INSERT INTO rate_periods (
                id, "ratePlanId", "roomTypeId", label, "validFrom", "validTo", "priceKgs",
                "mealIncluded", "saleStatus", notes, "createdAt", "updatedAt"
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, now(), now())
            ON CONFLICT ("ratePlanId", "roomTypeId", "validFrom", "validTo") DO UPDATE SET
                label = EXCLUDED.label,
                "priceKgs" = EXCLUDED."priceKgs",
                "mealIncluded" = EXCLUDED."mealIncluded",
                "saleStatus" = EXCLUDED."saleStatus",
                notes = EXCLUDED.notes,
                "updatedAt" = now()
            ''',
            uuid.uuid4(), plan_id, type_ids[room_type_name], row["rate_name"].strip(),
            valid_from, valid_to, price, row["meal_included"].strip(), sale_status, notes,
        )


async def main() -> None:
    room_rows = load_rooms()
    rate_rows = load_rates()
    conn = await asyncpg.connect(database_url())
    try:
        async with conn.transaction():
            property_id = await upsert_property(conn)
            type_ids = await upsert_room_types(conn, property_id, room_rows, rate_rows)
            await upsert_rooms(conn, property_id, type_ids, room_rows)
            await upsert_rates(conn, property_id, type_ids, rate_rows)

            room_count = await conn.fetchval('SELECT count(*) FROM rooms WHERE "propertyId" = $1', property_id)
            type_count = await conn.fetchval('SELECT count(*) FROM room_types WHERE "propertyId" = $1', property_id)
            if room_count != 84:
                raise RuntimeError(f"Seed verification failed: database has {room_count} rooms")
            if type_count != 12:
                raise RuntimeError(f"Seed verification failed: database has {type_count} room types")

        print(f"Seed OK: property={PROPERTY_CODE}, rooms={room_count}, room_types={type_count}, rates={len(rate_rows)}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
