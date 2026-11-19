#!/usr/bin/env python3
"""P0: prove OWNER can convert an existing DINING_STAFF identity in disposable CI.

No production or real hotel access. Never creates a replacement employee account.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from urllib.parse import urlsplit

import asyncpg
import httpx
from argon2 import PasswordHasher


async def main():
    origin = os.environ.get("MARINA_BOOKING_TEST_API", "")
    parsed = urlsplit(origin)
    assert parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    assert os.environ.get("APP_ENV") in {"ci", "staging"}
    assert os.environ.get("PROPERTY_CODE") == "MARINA_FULL_CI"
    assert "marina_full_ci" in os.environ.get("DATABASE_URL", ""), "Disposable CI PostgreSQL only"

    password = "Synthetic-Legacy-Dining-2026!"
    username = "legacy-dining-" + uuid.uuid4().hex[:10]
    user_id = uuid.uuid4()
    conn = await asyncpg.connect(os.environ["DATABASE_URL"].split("?", 1)[0])
    try:
        property_id = await conn.fetchval("SELECT id FROM properties WHERE code='MARINA_FULL_CI'")
        assert property_id, "Synthetic hotel missing"
        password_hash = PasswordHasher().hash(password)
        await conn.execute(
            """INSERT INTO staff_users (
                 id,"propertyId",username,"displayName","passwordHash",role,
                 "isActive","createdAt","updatedAt"
               ) VALUES ($1,$2,$3,$4,$5,'DINING_STAFF',true,now(),now())""",
            user_id, property_id, username, "Legacy Dining CI", password_hash,
        )
        async with httpx.AsyncClient(base_url=origin, timeout=25) as owner:
            login = await owner.post("/api/v1/auth/login", json={
                "username": os.environ["BOOTSTRAP_OWNER_USERNAME"],
                "password": os.environ["BOOTSTRAP_OWNER_PASSWORD"],
            })
            assert login.status_code == 200, (login.status_code, login.text)
            async with httpx.AsyncClient(base_url=origin, timeout=25) as staff:
                login = await staff.post("/api/v1/auth/login", json={"username": username, "password": password})
                assert login.status_code == 200, (login.status_code, login.text)
                me = await staff.get("/api/v1/auth/me")
                assert me.status_code == 200 and me.json()["role"] == "DINING_STAFF"
                assert me.json()["id"] == str(user_id)
                assert (await staff.get("/api/v1/kitchen/orders")).status_code == 403

                cook = await owner.patch(f"/api/v1/admin/staff/{user_id}", json={"role": "COOK"})
                assert cook.status_code == 200, (cook.status_code, cook.text)
                assert cook.json()["id"] == str(user_id) and cook.json()["role"] == "COOK"
                assert (await staff.get("/api/v1/auth/me")).status_code == 401, "Old session survived role change"
                relogin = await staff.post("/api/v1/auth/login", json={"username": username, "password": password})
                assert relogin.status_code == 200
                assert (await staff.get("/api/v1/kitchen/orders")).status_code == 200
                assert (await staff.get("/api/v1/dining/floor")).status_code == 403

                waiter = await owner.patch(f"/api/v1/admin/staff/{user_id}", json={"role": "WAITER"})
                assert waiter.status_code == 200, (waiter.status_code, waiter.text)
                assert waiter.json()["id"] == str(user_id) and waiter.json()["role"] == "WAITER"
                assert (await staff.get("/api/v1/auth/me")).status_code == 401
                relogin = await staff.post("/api/v1/auth/login", json={"username": username, "password": password})
                assert relogin.status_code == 200
                assert (await staff.get("/api/v1/dining/floor")).status_code == 200
                assert (await staff.get("/api/v1/kitchen/orders")).status_code == 403

        row = await conn.fetchrow(
            'SELECT id,"propertyId",username,"passwordHash",role::text AS role,"isActive" FROM staff_users WHERE id=$1',
            user_id,
        )
        assert row and row["id"] == user_id and row["propertyId"] == property_id
        assert row["username"] == username and row["passwordHash"] == password_hash
        assert row["role"] == "WAITER" and row["isActive"] is True
        assert await conn.fetchval('SELECT count(*) FROM staff_users WHERE "propertyId"=$1 AND username=$2', property_id, username) == 1
    finally:
        await conn.close()
    print("PASS: OWNER transitioned existing DINING_STAFF identity to COOK/WAITER without duplicate staff, password change or stale sessions")


if __name__ == "__main__":
    asyncio.run(main())
