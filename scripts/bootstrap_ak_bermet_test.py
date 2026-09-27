import asyncio
import json
import os
import uuid
from datetime import time
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data-marina" / "ak-bermet-rooms-20260927.json"
PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "AK_BERMET_TEST")
RATE_PLAN_CODE = os.environ.get("RATE_PLAN_CODE", "AKB_DIRECT_2026")
FULL_MODULES = ["GROUPS","AGENTS","MARKETING","DINING","OFFERS","GROWTH","CONTENT","ROOM_QR","POINT_QR","INBOX"]


def database_url() -> str:
    return os.environ["DATABASE_URL"].replace("?schema=public", "")


def room_type_code(room: dict) -> str:
    key = room.get("price_key")
    if key:
        return key.upper()
    category = room["source_category"]
    if category == "станд. 1 кровать":
        return "C3_STANDARD_ONE_UNPRICED"
    if category == "станд. 2 кровати":
        return "C3_STANDARD_TWO_UNPRICED"
    if category == "4-х семейный-3":
        return "C3_FAMILY_RAW301_UNRESOLVED"
    raise RuntimeError(f"Unmapped unpriced room category: {room['external_id']} {category}")


def room_type_name(room: dict, snapshot: dict) -> str:
    key = room.get("price_key")
    if key:
        price = snapshot["prices"][key]
        return f"{price['object']} · {price['label']}"
    return f"{room['building']} · {room['source_category']}"


def room_type_capacity(room: dict, snapshot: dict) -> int:
    key = room.get("price_key")
    if key:
        return int(snapshot["prices"][key]["official_places"])
    return int(room["official_capacity"])


async def main() -> None:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    rooms = snapshot["rooms"]
    totals = snapshot["totals"]
    if len(rooms) != 169:
        raise RuntimeError(f"AK BERMET snapshot must contain 169 rooms, got {len(rooms)}")
    if sum(int(r["official_capacity"]) for r in rooms) != 407:
        raise RuntimeError("AK BERMET official capacity must equal 407")
    if sum(int(r["max_capacity"]) for r in rooms) != 484:
        raise RuntimeError("AK BERMET max capacity must equal 484")
    if sum(1 for r in rooms if r["operational_state"] == "TECH_BLOCK") != 32:
        raise RuntimeError("AK BERMET blocked inventory must equal verified 32 rooms")
    if sum(1 for r in rooms if r["price_status"] == "PRICED") != 154:
        raise RuntimeError("AK BERMET priced coverage must equal verified 154 rooms")

    conn = await asyncpg.connect(database_url())
    try:
        async with conn.transaction():
            prop = snapshot["property"]
            property_id = await conn.fetchval(
                """
                INSERT INTO properties (id,code,name,timezone,currency,"createdAt","updatedAt")
                VALUES ($1,$2,$3,$4,$5,now(),now())
                ON CONFLICT (code) DO UPDATE SET
                  name=EXCLUDED.name,timezone=EXCLUDED.timezone,currency=EXCLUDED.currency,"updatedAt"=now()
                RETURNING id
                """,
                uuid.uuid4(), PROPERTY_CODE, prop["name"], prop["timezone"], prop["currency"],
            )

            await conn.execute(
                """
                INSERT INTO property_product_settings (
                  id,"propertyId","checkInTime","checkOutTime","enabledModules","createdAt","updatedAt"
                ) VALUES ($1,$2,$3::time,$4::time,$5::jsonb,now(),now())
                ON CONFLICT ("propertyId") DO UPDATE SET
                  "checkInTime"=EXCLUDED."checkInTime",
                  "checkOutTime"=EXCLUDED."checkOutTime",
                  "enabledModules"=EXCLUDED."enabledModules",
                  "updatedAt"=now()
                """,
                uuid.uuid4(), property_id, time.fromisoformat(prop["check_in_time"]), time.fromisoformat(prop["check_out_time"]), json.dumps(FULL_MODULES),
            )

            plan_id = await conn.fetchval(
                """
                INSERT INTO rate_plans (id,"propertyId",code,name,currency,"createdAt","updatedAt")
                VALUES ($1,$2,$3,'AK BERMET Direct 2026','KGS',now(),now())
                ON CONFLICT ("propertyId",code) DO UPDATE SET name=EXCLUDED.name,"updatedAt"=now()
                RETURNING id
                """,
                uuid.uuid4(), property_id, RATE_PLAN_CODE,
            )

            type_ids: dict[str, uuid.UUID] = {}
            type_samples: dict[str, dict] = {}
            for room in rooms:
                type_samples.setdefault(room_type_code(room), room)

            for code, sample in sorted(type_samples.items()):
                type_id = await conn.fetchval(
                    """
                    INSERT INTO room_types (
                      id,"propertyId",code,name,"capacityAdults","capacityChildren","areaLabel","createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,$4,$5,NULL,NULL,now(),now())
                    ON CONFLICT ("propertyId",code) DO UPDATE SET
                      name=EXCLUDED.name,
                      "capacityAdults"=EXCLUDED."capacityAdults",
                      "capacityChildren"=NULL,
                      "updatedAt"=now()
                    RETURNING id
                    """,
                    uuid.uuid4(), property_id, code, room_type_name(sample, snapshot), room_type_capacity(sample, snapshot),
                )
                type_ids[code] = type_id

            for code, sample in type_samples.items():
                key = sample.get("price_key")
                if not key:
                    continue
                price = snapshot["prices"][key]
                for period in snapshot["rate_periods"]:
                    field = period["price_field"]
                    await conn.execute(
                        """
                        INSERT INTO rate_periods (
                          id,"ratePlanId","roomTypeId",label,"validFrom","validTo","priceKgs",
                          "mealIncluded","saleStatus",notes,"createdAt","updatedAt"
                        ) VALUES ($1,$2,$3,$4,$5,$6,$7,'FULL_BOARD','OPEN',$8,now(),now())
                        ON CONFLICT ("ratePlanId","roomTypeId","validFrom","validTo") DO UPDATE SET
                          label=EXCLUDED.label,
                          "priceKgs"=EXCLUDED."priceKgs",
                          "mealIncluded"=EXCLUDED."mealIncluded",
                          "saleStatus"=EXCLUDED."saleStatus",
                          notes=EXCLUDED.notes,
                          "updatedAt"=now()
                        """,
                        uuid.uuid4(), plan_id, type_ids[code], period["label"],
                        period["valid_from"], period["valid_to"], int(price[field]),
                        "AK BERMET owner-confirmed 2026 tariff snapshot",
                    )

            for room in rooms:
                code = room["external_id"].removeprefix("AKB-")
                notes = json.dumps({
                    "source_external_id": room["external_id"],
                    "source_category": room["source_category"],
                    "official_capacity": room["official_capacity"],
                    "max_capacity": room["max_capacity"],
                    "explicit_extra_places": room["explicit_extra_places"],
                    "pdi_marker": room["pdi_marker"],
                    "price_status": room["price_status"],
                    "price_key": room["price_key"],
                }, ensure_ascii=False)
                await conn.execute(
                    """
                    INSERT INTO rooms (
                      id,"propertyId","roomTypeId",code,name,"buildingOrZone","floorLabel",
                      "bedConfiguration","areaLabel","operationalState",notes,"createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,$4,$5,$6,NULL,$7,NULL,$8,$9,now(),now())
                    ON CONFLICT ("propertyId",code) DO UPDATE SET
                      "roomTypeId"=EXCLUDED."roomTypeId",
                      name=EXCLUDED.name,
                      "buildingOrZone"=EXCLUDED."buildingOrZone",
                      "bedConfiguration"=EXCLUDED."bedConfiguration",
                      "operationalState"=EXCLUDED."operationalState",
                      notes=EXCLUDED.notes,
                      "updatedAt"=now()
                    """,
                    uuid.uuid4(), property_id, type_ids[room_type_code(room)], code,
                    f"Номер {room['room_number']}", room["building"], room["source_category"], room["operational_state"], notes,
                )

            db_counts = await conn.fetchrow(
                """
                SELECT count(*)::int AS rooms,
                       count(*) FILTER (WHERE "operationalState"='CLEAN')::int AS clean,
                       count(*) FILTER (WHERE "operationalState"='TECH_BLOCK')::int AS blocked
                FROM rooms WHERE "propertyId"=$1
                """,
                property_id,
            )
            if dict(db_counts) != {"rooms": 169, "clean": 137, "blocked": 32}:
                raise RuntimeError(f"AK BERMET database verification failed: {dict(db_counts)}")

            stale_types = await conn.fetchval(
                'SELECT count(*) FROM room_types WHERE "propertyId"=$1 AND code <> ALL($2::text[])',
                property_id, list(type_ids),
            )
            if stale_types:
                raise RuntimeError(f"Unexpected stale AK BERMET room types exist: {stale_types}")

        print(
            "AK BERMET bootstrap OK: "
            f"property={PROPERTY_CODE}, rooms={totals['units']}, clean={totals['ready_sellable']}, "
            f"blocked={totals['blocked_or_inactive']}, official={totals['official_capacity']}, "
            f"max={totals['max_capacity']}, priced=154, fail_closed_unpriced=15"
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
