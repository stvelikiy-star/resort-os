#!/usr/bin/env python3
"""P0 shared HOLD TTL: real FastAPI/PostgreSQL in TWO disposable hotels.

A hold is a DB-backed 60-minute room block. Expiry must unlock A without
touching B, even if the two hotels hold identical local dates/room codes.
No real data, no clocks/sleeps, no migrations, no mocked DB handlers.
"""
import asyncio
from datetime import date, timedelta
import uuid

import asyncpg
from fastapi.testclient import TestClient

from app import auth
from app.app_entry import app
from marina_shared_live_browser_db import PASSWORD, dsn


def must(result, code, label):
    assert result.status_code == code, (
        label, result.status_code, result.text[:300],
    )
    return result.json() if result.content else {}


async def rooms():
    conn = await asyncpg.connect(dsn())
    try:
        values = {}
        for letter in "AB":
            row = await conn.fetchrow(
                '''SELECT r.id AS room_id,p.id AS property_id
                   FROM rooms r JOIN properties p ON p.id=r."propertyId"
                   JOIN tenants t ON t.id=p."tenantId"
                   WHERE p.code=$1 AND t.code=$2 AND t.status='ACTIVE' ''',
                "HOTEL_" + letter, "tenant_" + letter.lower(),
            )
            assert row, letter
            values[letter] = {
                "room_id": str(row["room_id"]),
                "property_id": str(row["property_id"]),
            }
        assert values["A"]["room_id"] != values["B"]["room_id"]
        assert values["A"]["property_id"] != values["B"]["property_id"]
        return values
    finally:
        await conn.close()


async def force_expire(hold_id):
    """Advance only this test HOLD's stored expiry, never system time."""
    conn = await asyncpg.connect(dsn())
    try:
        updated = await conn.execute(
            '''UPDATE marina_reservation_holds
               SET "expiresAt"=now()-interval '1 minute'
               WHERE id=$1 AND "releasedAt" IS NULL
                     AND "confirmedReservationId" IS NULL''',
            uuid.UUID(hold_id),
        )
        assert updated == "UPDATE 1", (hold_id, updated)
    finally:
        await conn.close()


async def verify_holds(hold_a, hold_b, data, *, expired_b=False):
    conn = await asyncpg.connect(dsn())
    try:
        for hotel, hold_id in (("A", hold_a), ("B", hold_b)):
            row = await conn.fetchrow(
                '''SELECT h."propertyId",h."roomId",h."expiresAt",
                          h."releasedAt",h."confirmedReservationId",
                          b.active,b."reservationId" AS reservation_id
                   FROM marina_reservation_holds h
                   JOIN inventory_blocks b ON b.id=h."inventoryBlockId"
                   WHERE h.id=$1''', uuid.UUID(hold_id),
            )
            assert row
            assert str(row["propertyId"]) == data[hotel]["property_id"]
            assert str(row["roomId"]) == data[hotel]["room_id"]
            should_expire = hotel == "A" or expired_b
            assert (row["releasedAt"] is not None) == should_expire
            assert row["active"] is (not should_expire)
            assert row["confirmedReservationId"] is None
            assert row["reservation_id"] is None
            if should_expire:
                assert row["expiresAt"] < row["releasedAt"]
        assert await conn.fetchval(
            "SELECT count(*)::int FROM reservations"
        ) == 0, "HOLD expiry unexpectedly created a reservation"
        assert await conn.fetchval(
            "SELECT count(*)::int FROM payments"
        ) == 0, "HOLD expiry unexpectedly created a payment"
    finally:
        await conn.close()


async def verify_idempotent_second_sweep():
    from app.db import expire_shared_holds_once
    pool = await asyncpg.create_pool(dsn(), min_size=1, max_size=2)
    try:
        first = await expire_shared_holds_once(pool)
        second = await expire_shared_holds_once(pool)
        assert first == 0 and second == 0, (
            "Repeated shared worker must not retire already-released holds",
            first, second,
        )
    finally:
        await pool.close()


def main():
    dsn()  # Hard guard for localhost + empty disposable synthetic CI DB.
    assert auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED
    assert auth.MARINA_TENANT_CONTEXT_ENABLED and auth.COOKIE_SECURE
    data = asyncio.run(rooms())
    start = date.today() + timedelta(days=21)
    end = start + timedelta(days=2)
    payload = lambda letter: {
        "room_id": data[letter]["room_id"],
        "check_in": start.isoformat(),
        "check_out": end.isoformat(),
        "guest_name": "Synthetic Hold " + letter,
        "guest_phone": "+99670000000" + ("1" if letter == "A" else "2"),
    }
    base = "/api/v1/admin/pms/holds"
    preview = "/api/v1/admin/pms/reservations/new/preview"
    with TestClient(app, base_url="https://localhost:18000") as client:
        def call(token, method, path, **kwargs):
            client.cookies.clear()
            if token:
                client.cookies.set(auth.SESSION_COOKIE, token)
            return client.request(method, path, **kwargs)

        def login(hotel, role):
            client.cookies.clear()
            info = must(client.post("/api/v1/auth/login", json={
                "tenant_code": "tenant_" + hotel.lower(),
                "property_code": "HOTEL_" + hotel,
                "username": role.lower(), "password": PASSWORD,
            }), 200, hotel + " " + role + " login")
            assert info["property_code"] == "HOTEL_" + hotel
            token = client.cookies.get(auth.SESSION_COOKIE)
            assert token and token.startswith("ms1.")
            return token

        owner = {h: login(h, "OWNER") for h in "AB"}
        reception_a = login("A", "RECEPTION")
        maid_b = login("B", "MAID")

        must(call(None, "GET", base), 401, "anonymous may not enumerate holds")
        must(call(reception_a, "POST", base, json=payload("A")),
             403, "reception cannot mint inventory HOLD")
        must(call(maid_b, "GET", base),
             403, "maid cannot enumerate HOLD")

        created = {}
        for h in "AB":
            created[h] = must(call(owner[h], "POST", base, json=payload(h)),
                              201, "hotel " + h + " creates hold")
            assert created[h]["status"] == "HELD"
            assert created[h]["duration_minutes"] == 60
            assert uuid.UUID(created[h]["id"])
            assert (created[h]["expires_at"] is not None)
            # Overlap blocked and cross-hotel room IDs concealed.
            must(call(owner[h], "POST", base, json=payload(h)),
                 409, "same hotel double HOLD rejected")
            other = "B" if h == "A" else "A"
            must(call(owner[h], "POST", base, json=payload(other)),
                 404, "foreign room id cannot be held")
        hold_a, hold_b = created["A"]["id"], created["B"]["id"]
        assert hold_a != hold_b

        for h in "AB":
            own = created[h]["id"]
            foreign = created["B" if h == "A" else "A"]["id"]
            owned = must(call(owner[h], "GET", base), 200, h + " list")
            assert {x["id"] for x in owned["holds"]} == {own}
            must(call(owner[h], "GET", base + "/" + foreign),
                 404, "foreign HOLD id cannot be read")
            must(call(owner[h], "DELETE", base + "/" + foreign),
                 404, "foreign HOLD id cannot be released")

        # Same room/date block; expiration is selected solely by hotel's
        # server-validated property ID. B must remain held in inventory.
        asyncio.run(force_expire(hold_a))
        a_holds = must(call(owner["A"], "GET", base), 200, "expire A by listing")
        assert a_holds["holds"] == []
        must(call(owner["A"], "GET", base + "/" + hold_a),
             404, "expired A detail denied")
        must(call(owner["A"], "POST", preview, json={
            "room_id": data["A"]["room_id"],
            "check_in": start.isoformat(),
            "check_out": end.isoformat(),
            "hold_id": hold_a,
            "adults": 2, "children": 0,
        }), 409, "expired A hold may not be converted")
        b_live = must(call(owner["B"], "GET", base), 200, "B remains held")
        assert [x["id"] for x in b_live["holds"]] == [hold_b]
        no_owner = must(call(owner["A"], "POST", preview, json={
            "room_id": data["A"]["room_id"],
            "check_in": start.isoformat(),
            "check_out": end.isoformat(),
            "adults": 2, "children": 0,
        }), 200, "A after expiry preview")
        assert no_owner["can_commit"] is True
        blocked_b = must(call(owner["B"], "POST", preview, json={
            "room_id": data["B"]["room_id"],
            "check_in": start.isoformat(),
            "check_out": end.isoformat(),
            "adults": 2, "children": 0,
        }), 200, "B while held")
        assert blocked_b["can_commit"] is False
        asyncio.run(verify_holds(hold_a, hold_b, data))

        # B expiry must be independent and remove its own inventory too.
        asyncio.run(force_expire(hold_b))
        assert must(call(owner["B"], "GET", base), 200, "B expire now")["holds"] == []
        assert must(call(owner["A"], "GET", base), 200, "A still empty")["holds"] == []
        asyncio.run(verify_holds(hold_a, hold_b, data, expired_b=True))
    asyncio.run(verify_idempotent_second_sweep())
    print(
        "PASS: 2 hotel OWNER sessions and distinct HOLDs; 60m TTL, 401/403/404, "
        "foreign property cannot read/mutate, overlap 409, A expiry releases only A, "
        "old HOLD cannot convert, B stays blocked until B expiry, "
        "two worker sweeps idempotent, no bookings or payments created."
    )


if __name__ == "__main__":
    main()
