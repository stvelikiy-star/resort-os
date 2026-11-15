#!/usr/bin/env python3
"""DB assertions for ephemeral Mobile-transport ⇄ Web PMS CI; never use real hotel data."""
import asyncio
import json
import os
import uuid
from urllib.parse import urlsplit
import asyncpg

async def main():
    dsn=os.environ["DATABASE_URL"].split("?",1)[0]
    url=urlsplit(dsn)
    assert url.hostname in {"localhost","127.0.0.1"}
    assert url.path == "/marina_shared_browser_ci"
    assert os.environ["MARINA_CROSS_CLIENT_CONFIRM"] == "SYNTHETIC_MOBILE_TO_WEB_POSTGRES_ONLY"
    receipt=json.load(open("/tmp/marina-fl2-cross-client-receipts.json",encoding="utf-8"))
    ids=[uuid.UUID(receipt["mobileToWeb"]),uuid.UUID(receipt["webToMobile"])]
    assert len(set(ids)) == 2
    conn=await asyncpg.connect(dsn)
    try:
        records=await conn.fetch("""
            SELECT r.id,r.status::text AS status,r."totalKgs" AS amount,
                   p.code AS property_code, ib."roomId" AS room_id
            FROM reservations r
            JOIN properties p ON p.id=r."propertyId"
            JOIN inventory_blocks ib ON ib."reservationId"=r.id
              AND ib.active=true AND ib."blockType"='RESERVATION'
            WHERE r.id=ANY($1::uuid[])
        """,ids)
        assert len(records)==2,records
        assert all(row["property_code"]=="HOTEL_A" and row["status"]=="GUARANTEED"
                   and row["amount"]>0 and str(row["room_id"])==receipt["roomId"]
                   for row in records),records
        assert await conn.fetchval("SELECT count(*) FROM reservations") == 2
        assert await conn.fetchval("SELECT count(*) FROM payments") == 0
        assert await conn.fetchval("""
            SELECT count(*) FROM reservations r JOIN properties p
            ON p.id=r."propertyId" WHERE p.code='HOTEL_B'
        """) == 0
        print("MARINA_CROSS_CLIENT_POSTGRES_PASS: 2 Web/Mobile transport bookings, same HOTEL_A room, 0 payments, 0 foreign bookings")
    finally:
        await conn.close()

if __name__=="__main__":
    asyncio.run(main())
