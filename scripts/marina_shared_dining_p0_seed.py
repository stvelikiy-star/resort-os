#!/usr/bin/env python3
"""Add disposable kitchen/restaurant facts to an already seeded TWO-hotel CI DB.

NEVER point this at a customer DB. Reuse the RC3 localhost/name/confirmation
gate; no truncation or reset, and refuse any populated dining ledger.
"""
import asyncio
import os
import uuid

import asyncpg
from marina_shared_live_browser_db import dsn


ORDERS = {
    "A": uuid.UUID("11111111-2222-4333-8444-5555555555a1"),
    "B": uuid.UUID("11111111-2222-4333-8444-5555555555b2"),
}
TABLES = {
    "A": uuid.UUID("11111111-2222-4333-8444-6666666666a1"),
    "B": uuid.UUID("11111111-2222-4333-8444-6666666666b2"),
}


async def main():
    if os.environ.get("MARINA_SHARED_DINING_P0_SEED_CONFIRM") != "ISOLATED_DINING_CI_ONLY":
        raise RuntimeError("Dining CI seed confirmation missing")
    if os.environ.get("MARINA_SHARED_DINING_P0_ENABLED") != "true":
        raise RuntimeError("Dining staging opt-in missing")
    # The immutable RC3 guard validates localhost, synthetic credentials,
    # exact database name, shared staging flags, fixture confirmation and rate.
    database = dsn()
    conn = await asyncpg.connect(database)
    try:
        async with conn.transaction():
            assert await conn.fetchval("SELECT count(*) FROM properties") == 2
            assert await conn.fetchval("SELECT count(*) FROM tenants") == 2
            for table in ("kitchen_tables", "kitchen_orders", "kitchen_order_items"):
                assert await conn.fetchval(f"SELECT count(*) FROM {table}") == 0, (
                    f"Refusing to seed populated {table}"
                )
            for code in ("A", "B"):
                prop = await conn.fetchrow(
                    'SELECT id FROM properties WHERE code=$1', "HOTEL_" + code,
                )
                assert prop, "Missing synthetic hotel " + code
                pid = prop["id"]
                for role in ("OWNER", "COOK", "WAITER"):
                    user_id = await conn.fetchval(
                        'SELECT id FROM staff_users WHERE "propertyId"=$1'
                        " AND role=$2::\"StaffRole\" AND \"isActive\"=true",
                        pid, role,
                    )
                    assert user_id, f"Missing {code} {role} fixture"
                owner = await conn.fetchval(
                    'SELECT id FROM staff_users WHERE "propertyId"=$1 AND role=\'OWNER\'',
                    pid,
                )
                await conn.execute(
                    """INSERT INTO kitchen_tables
                    (id,"propertyId",code,name,seats,status,"isActive",notes,
                     "createdAt","updatedAt")
                    VALUES ($1,$2,$3,$4,4,'OCCUPIED',true,
                            'DISPOSABLE_DINING_P0_ONLY',now(),now())""",
                    TABLES[code], pid, "CI" + code + "01",
                    "Synthetic Dining Table " + code,
                )
                await conn.execute(
                    """INSERT INTO kitchen_orders (
                        id,"propertyId","orderNumber",status,source,"tableId",
                        "guestCount","mealType",notes,"totalKgs","openedById",
                        "openedAt","createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,'NEW','TABLE',$4,2,'BREAKFAST',
                              'DISPOSABLE_DINING_P0_ONLY',0,$5,now(),now(),now())""",
                    ORDERS[code], pid, "CI-DINING-" + code, TABLES[code], owner,
                )
            assert await conn.fetchval("SELECT count(*) FROM kitchen_orders") == 2
            assert await conn.fetchval("SELECT count(*) FROM kitchen_tables") == 2
    finally:
        await conn.close()
    print("PASS: two hotel-local synthetic dining tables and distinct orders seeded")


if __name__ == "__main__":
    asyncio.run(main())
