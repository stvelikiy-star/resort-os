#!/usr/bin/env python3
"""Disposable two-hotel PostgreSQL fixtures and post-browser evidence.

Never run against a live environment: explicit CI confirmation, database-name
and localhost gates are mandatory. No destructive reset is performed.
"""
import asyncio
from datetime import date
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
import uuid

import asyncpg
from argon2 import PasswordHasher

DB_NAME = "marina_shared_browser_ci"
RECEIPTS = Path("/tmp/marina_shared_browser_receipts.json")
PASSWORD = os.environ.get("MARINA_SHARED_BROWSER_CI_PASSWORD", "")
ROOM_CODES = {"a": "A101", "b": "B202"}
PRICES = {"a": 3000, "b": 4500}


def dsn():
    value = os.environ.get("DATABASE_URL", "").split("?", 1)[0]
    parsed = urlsplit(value)
    assert os.environ.get("MARINA_SHARED_BROWSER_CI_CONFIRM") == "DISPOSABLE_TWO_HOTEL_BROWSER_CI"
    assert parsed.scheme in {"postgresql", "postgres"}
    assert parsed.hostname in {"127.0.0.1", "localhost"}
    assert parsed.path == "/" + DB_NAME
    assert len(PASSWORD) >= 16 and PASSWORD.startswith("synthetic-ci-only-")
    assert os.environ.get("PROPERTY_CODE") == "MARINA_BROWSER_CI"
    assert os.environ.get("APP_ENV") == "staging"
    assert os.environ.get("MARINA_SHARED_AUTH_PREVIEW_ENABLED") == "true"
    assert os.environ.get("MARINA_TENANT_CONTEXT_ENABLED") == "true"
    assert os.environ.get("RATE_PLAN_CODE") == "MARINA_BROWSER_CI"
    return value


async def seed(conn):
    assert await conn.fetchval("SELECT count(*) FROM properties") == 0, "DB is not empty"
    assert await conn.fetchval("SELECT count(*) FROM tenants") == 0, "DB has tenants"
    assert await conn.fetchval("SELECT count(*) FROM reservations") == 0, "DB has reservations"
    hashed_password = PasswordHasher().hash(PASSWORD)
    start = date(date.today().year, 1, 1)
    end = date(date.today().year + 1, 12, 31)
    async with conn.transaction():
        for hotel in ("a", "b"):
            tenant_id, property_id = uuid.uuid4(), uuid.uuid4()
            room_type_id, rate_plan_id = uuid.uuid4(), uuid.uuid4()
            await conn.execute('''
                INSERT INTO tenants(id,code,name,status,"updatedAt")
                VALUES($1,$2,$3,'ACTIVE',now())
            ''', tenant_id, "tenant_" + hotel, "CI Tenant " + hotel.upper())
            await conn.execute('''
                INSERT INTO properties(id,code,name,timezone,currency,"updatedAt","tenantId")
                VALUES($1,$2,$3,'Asia/Bishkek','KGS',now(),$4)
            ''', property_id, "HOTEL_" + hotel.upper(), "CI Hotel " + hotel.upper(), tenant_id)
            await conn.execute('''
                INSERT INTO staff_users
                (id,"propertyId",username,"displayName","passwordHash",role,"isActive","updatedAt")
                VALUES($1,$2,'owner',$3,$4,'OWNER',true,now())
            ''', uuid.uuid4(), property_id, "Synthetic Owner " + hotel.upper(), hashed_password)
            await conn.execute('''
                INSERT INTO room_types(id,"propertyId",code,name,"capacityAdults","updatedAt")
                VALUES($1,$2,'STANDARD','CI Standard',2,now())
            ''', room_type_id, property_id)
            await conn.execute('''
                INSERT INTO rooms(id,"propertyId","roomTypeId",code,name,"operationalState","updatedAt")
                VALUES($1,$2,$3,$4,'CI Room','CLEAN',now())
            ''', uuid.uuid4(), property_id, room_type_id, ROOM_CODES[hotel])
            await conn.execute('''
                INSERT INTO rate_plans(id,"propertyId",code,name,currency,"updatedAt")
                VALUES($1,$2,'MARINA_BROWSER_CI','CI nightly rate','KGS',now())
            ''', rate_plan_id, property_id)
            await conn.execute('''
                INSERT INTO rate_periods(id,"ratePlanId","roomTypeId",label,
                                         "validFrom","validTo","priceKgs",
                                         "mealIncluded","saleStatus","updatedAt")
                VALUES($1,$2,$3,'CI period',$4,$5,$6,'NONE','OPEN',now())
            ''', uuid.uuid4(), rate_plan_id, room_type_id, start, end, PRICES[hotel])
    print("PASS: two independent hotel-owner accounts, rooms, and distinct live Core rates seeded")


async def verify(conn):
    receipts = json.loads(RECEIPTS.read_text())
    assert set(receipts) == {"HOTEL_A", "HOTEL_B"}, receipts
    rows = await conn.fetch('''
        SELECT r.id,r."propertyId",r."bookingNumber",r."totalKgs",r.status::text AS status,
               p.code AS hotel, ib."roomId"
        FROM reservations r
        JOIN properties p ON p.id=r."propertyId"
        JOIN inventory_blocks ib ON ib."reservationId"=r.id AND ib.active=true
                                    AND ib."blockType"='RESERVATION'
        ORDER BY p.code
    ''')
    assert len(rows) == 2, "Exactly one committed reservation per hotel required"
    assert len({row["id"] for row in rows}) == 2
    property_ids = {}
    for row in rows:
        hotel = row["hotel"]
        property_ids[hotel] = row["propertyId"]
        receipt = receipts[hotel]
        assert str(row["id"]) == receipt["reservation_id"], "Browser/API and DB reservation IDs differ"
        assert str(row["roomId"]) == receipt["room_id"], "Browser room differs from persisted room"
        assert row["bookingNumber"] == receipt["booking_number"]
        assert row["totalKgs"] == receipt["total_kgs"] == 2 * PRICES[hotel[-1].lower()]
        assert row["status"] == "GUARANTEED"
        assert await conn.fetchval('''
            SELECT count(*) FROM rooms WHERE id=$1 AND "propertyId"=$2
        ''', row["roomId"], row["propertyId"]) == 1, "Cross-hotel inventory link!"
        assert await conn.fetchval('''
            SELECT count(*) FROM payments WHERE "reservationId"=$1
        ''', row["id"]) == 0, "Booking unexpectedly created payment"
    # The second reservation per hotel was made through real HTTP and cancelled
    # through the real browser; no financial history may be silently refunded.
    assert await conn.fetchval('SELECT count(*) FROM reservations') == 4
    cancelled_rows=await conn.fetch('''
        SELECT r.id,r."propertyId",r.status::text AS status,p.code AS hotel
        FROM reservations r JOIN properties p ON p.id=r."propertyId"
        WHERE r.status='CANCELLED'
    ''')
    assert len(cancelled_rows)==2
    for row in cancelled_rows:
        hotel=row["hotel"]
        fixture=receipts[hotel]["cancel_fixture"]
        assert str(row["id"])==fixture["reservation_id"]
        assert row["propertyId"]==property_ids[hotel]
        assert await conn.fetchval('''
            SELECT count(*) FROM inventory_blocks
            WHERE "reservationId"=$1 AND active=true
        ''',row["id"])==0,"Cancelled booking retained active inventory"
        assert await conn.fetchval('''
            SELECT count(*) FROM payments WHERE "reservationId"=$1
        ''',row["id"])==0,"Cancelled fixture unexpectedly has payments"
    for row in rows:
        hotel=row["hotel"]
        # Dates changed in one server transaction but original total is retained
        # until a separately reviewed financial adjustment is made.
        state=await conn.fetchrow('SELECT "checkOut","totalKgs" FROM reservations WHERE id=$1',row["id"])
        assert state["checkOut"].isoformat()==receipts[hotel]["new_check_out"]
        assert int(state["totalKgs"])==receipts[hotel]["total_kgs"],"Schedule silently repriced stored total"
        assert await conn.fetchval('''
            SELECT count(*) FROM audit_logs WHERE "propertyId"=$1
              AND action='PMS_SCHEDULE_MUTATION' AND "resourceId"=$2
        ''',row["propertyId"],str(row["id"]))==1,"Missing schedule audit"
    assert await conn.fetchval('SELECT count(*) FROM marina_reservation_holds') == 2
    for hotel, receipt in receipts.items():
        hold = await conn.fetchrow('''
            SELECT h."propertyId",h."releasedAt",h."confirmedReservationId",b.active
            FROM marina_reservation_holds h
            JOIN inventory_blocks b ON b.id=h."inventoryBlockId"
            WHERE h.id=$1
        ''', uuid.UUID(receipt["hold_id"]))
        assert hold is not None, "Missing browser-created HOLD"
        assert hold["propertyId"] == property_ids[hotel], "Cross-hotel HOLD ownership"
        assert hold["releasedAt"] is not None, "HOLD not released"
        assert hold["confirmedReservationId"] is None, "Released HOLD unexpectedly confirmed"
        assert hold["active"] is False, "Released HOLD still blocks availability"
    assert await conn.fetchval('SELECT count(*) FROM inventory_blocks WHERE active=true') == 2
    print("MARINA_SHARED_LIVE_BROWSER_DB_PASS: 2 hotels, 2 active schedule-mutated bookings, 2 cancelled unpaid PMS fixtures, 2 released HOLDs, 2 audit mutations, tenant isolation, no payments")


async def main():
    import sys
    assert len(sys.argv) == 2 and sys.argv[1] in {"seed", "verify"}
    if sys.argv[1] == "seed":
        assert not RECEIPTS.exists(), "stale browser test receipt"
    conn = await asyncpg.connect(dsn())
    try:
        if sys.argv[1] == "seed":
            await seed(conn)
        else:
            await verify(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
