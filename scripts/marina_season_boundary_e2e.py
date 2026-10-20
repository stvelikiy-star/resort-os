#!/usr/bin/env python3
"""Verify mixed seasonal pricing over API using *disposable local* MARINA CI data."""
import asyncio
import os
import uuid
from datetime import date, timedelta
from urllib.parse import urlsplit
import asyncpg
import httpx

async def main():
    url = os.environ.get("DATABASE_URL", "").replace("?schema=public", "")
    parsed = urlsplit(url)
    api = urlsplit(os.environ.get("MARINA_BOOKING_TEST_API", ""))
    assert parsed.hostname in ("127.0.0.1", "localhost"), "CI database must be local"
    assert parsed.path == "/marina_full_ci", "Refusing to modify any non-disposable database"
    assert api.scheme == "http" and api.hostname in ("127.0.0.1", "localhost"), "CI API must be local"
    assert os.environ.get("PROPERTY_CODE") == "MARINA_FULL_CI"
    boundary = date.today() + timedelta(days=35)
    conn = await asyncpg.connect(url)
    try:
        async with conn.transaction():
            existing = await conn.fetchrow(
                """SELECT rp.*,rt.code AS type_code
                FROM rate_periods rp
                JOIN room_types rt ON rt.id=rp."roomTypeId"
                JOIN properties p ON p.id=rt."propertyId"
                WHERE p.code='MARINA_FULL_CI' AND rt.code='STANDARD'
                ORDER BY rp."validFrom" LIMIT 1"""
            )
            assert existing and existing["validFrom"] < boundary < existing["validTo"], "Expected synthetic base season"
            lower_price = existing["priceKgs"]
            upper_price = lower_price + 1200
            await conn.execute('UPDATE rate_periods SET "validTo"=$2,"updatedAt"=now() WHERE id=$1', existing["id"], boundary - timedelta(days=1))
            await conn.execute(
                """INSERT INTO rate_periods
                (id,"ratePlanId","roomTypeId",label,"validFrom","validTo","priceKgs","mealIncluded","saleStatus","createdAt","updatedAt")
                VALUES ($1,$2,$3,'Synthetic high season',$4,$5,$6,'NONE','OPEN',now(),now())""",
                uuid.uuid4(), existing["ratePlanId"], existing["roomTypeId"], boundary,
                existing["validTo"], upper_price,
            )
            async with httpx.AsyncClient(base_url=os.environ["MARINA_BOOKING_TEST_API"], timeout=12) as client:
                check_in = boundary - timedelta(days=1)
                check_out = boundary + timedelta(days=1)
                response = await client.get("/api/v1/booking/check-availability", params={
                    "check_in": check_in.isoformat(), "check_out": check_out.isoformat(), "adults": 2,
                    "room_type_code": "STANDARD"
                })
                assert response.status_code == 200, (response.status_code, response.text)
                options = response.json()["results"]
                assert len(options) == 1, options
                pricing = options[0]["pricing"]
                assert pricing["sellable"] is True, pricing
                assert pricing["total_kgs"] == lower_price + upper_price, pricing
                nights = pricing["nights"]
                assert len(nights) == 2, nights
                assert [n["price_kgs"] for n in nights] == [lower_price, upper_price], nights
                print("MARINA_SEASON_BOUNDARY_PASS: nights priced independently across tariff-period boundary")
            # Explicit rollback: this test never leaves altered tariff rows behind.
            raise _Rollback()
    except _Rollback:
        pass
    finally:
        await conn.close()

class _Rollback(Exception):
    pass

if __name__ == "__main__":
    asyncio.run(main())
