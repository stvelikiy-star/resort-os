"""Disposable Compose demo: edit inventory, then prove restart preserves data."""
import asyncio
import hashlib
import http.cookiejar
import json
import os
import sys
import urllib.request

import asyncpg
from marina_demo_seed import demo_database_url

BASE = "http://127.0.0.1:8000"
TABLES = ("properties", "tenants", "rooms", "room_types", "reservations",
          "reservation_requests", "guests", "staff_users")


def owner_client():
    cookies = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
    response = client.open(urllib.request.Request(
        BASE + "/api/v1/auth/login",
        data=json.dumps({"username": os.environ["BOOTSTRAP_OWNER_USERNAME"],
                         "password": os.environ["BOOTSTRAP_OWNER_PASSWORD"]}).encode(),
        headers={"Content-Type": "application/json"}, method="POST"), timeout=15)
    assert response.status == 200
    response.close()
    return client


def create(client, path, body):
    with client.open(urllib.request.Request(
            BASE + "/api/v1/admin/hotel-setup" + path,
            data=json.dumps(body).encode(), headers={"Content-Type": "application/json"},
            method="POST"), timeout=15) as response:
        assert response.status == 201
        return json.load(response)


async def snapshot():
    conn = await asyncpg.connect(demo_database_url(os.environ["DATABASE_URL"]))
    try:
        result = {}
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            for table in TABLES:
                rows = await conn.fetch(f'SELECT row_to_json(t)::text AS row FROM "{table}" t')
                data = sorted(json.dumps(json.loads(row["row"]), sort_keys=True,
                                         separators=(",", ":")) for row in rows)
                result[table] = {"count": len(data),
                                "sha256": hashlib.sha256("\n".join(data).encode()).hexdigest()}
        return result
    finally:
        await conn.close()


def main():
    if (os.environ.get("APP_ENV") != "staging"
            or os.environ.get("PROPERTY_CODE") != "MARINA_DEMO"
            or os.environ.get("MARINA_DEMO_CONFIRM") != "EMPTY_SYNTHETIC_DB_ONLY"):
        raise RuntimeError("Disposable MARINA demo only")
    demo_database_url(os.environ["DATABASE_URL"])
    if sys.argv[1] == "prepare":
        client = owner_client()
        category = create(client, "/room-types", {
            "code": "RESTART_CI", "name": "Synthetic restart category", "capacity_adults": 2})
        create(client, "/rooms", {
            "room_type_id": category["id"], "code": "RESTART-CI",
            "name": "Synthetic restart room"})
        state = asyncio.run(snapshot())
        assert state["rooms"]["count"] == 13
        assert state["room_types"]["count"] == 4
        assert state["reservations"]["count"] > 0, "Booking test must run first"
        print(json.dumps(state, sort_keys=True))
    elif sys.argv[1] == "verify":
        expected = json.load(sys.stdin)
        actual = asyncio.run(snapshot())
        assert actual == expected, "Restart changed inventory, booking, guest or owner data"
        owner_client()  # same configured credentials still sign in
        print("MARINA_DEMO_RESTART_PASS: edited 13-room/4-category inventory, bookings, guests and owner preserved")
    else:
        raise ValueError("Expected prepare or verify")


if __name__ == "__main__":
    main()
