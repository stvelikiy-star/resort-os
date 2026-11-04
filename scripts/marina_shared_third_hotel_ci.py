#!/usr/bin/env python3
"""P0: one shared FastAPI/PostgreSQL with 2 occupied hotels + third empty hotel.

Checks strict before/after snapshots, forced rollback and duplicate rejection
before using new/old sessions for hotel-local PMS, payments, roles and audit.
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
import json
from pathlib import Path
import sys

import asyncpg
from fastapi.testclient import TestClient

from marina_shared_add_hotel import (
    NewHotel, EXISTING_CODES, existing_hotel_pairs, provision_additive,
    staged_configuration,
)
from marina_shared_live_browser_db import RECEIPTS, PASSWORD, SERVER_ROLES
from marina_two_property_restore_e2e import snapshot
from prisma_migration_ledger import verify_committed_ledger

ROOT = Path(__file__).resolve().parents[1]
ADDED_TABLES = {
    "tenants": "tenant",
    "properties": "property",
    "rate_plans": "rate",
    "property_product_settings": "settings",
    "staff_users": "owner",
    "audit_logs": "audit",
}


async def existing_rows(dsn: str) -> dict:
    conn = await asyncpg.connect(dsn)
    try:
        answer = {}
        for table in ADDED_TABLES:
            # Names are constants controlled by this source file, not caller input.
            rows = await conn.fetch(
                'SELECT id::text AS id,to_jsonb(t)::text AS value FROM public."' +
                table + '" t ORDER BY id'
            )
            answer[table] = {row["id"]: row["value"] for row in rows}
        return answer
    finally:
        await conn.close()


def compare_additive(before: dict, after: dict, before_rows: dict,
                     after_rows: dict, ids: dict) -> None:
    assert before["constraints"] == after["constraints"], "Schema constraints changed!"
    assert set(before["tables"]) == set(after["tables"]), "Table layout changed!"
    for table in before["tables"]:
        old = before["tables"][table]
        new = after["tables"][table]
        if table not in ADDED_TABLES:
            assert old == new, f"Unrelated preexisting table modified: {table}"
            continue
        assert new["count"] == old["count"] + 1, (
            f"Expected exactly one additive record in {table}"
        )
        new_id = str(ids[ADDED_TABLES[table]])
        assert new_id not in before_rows[table], "New row UUID was already in old hotel data"
        assert new_id in after_rows[table], "Expected new hotel record missing"
        assert before_rows[table] == {
            key: value for key, value in after_rows[table].items() if key != new_id
        }, f"Preexisting {table} records changed or disappeared"


async def create_and_compare(dsn: str, hotel: NewHotel) -> dict:
    conn = await asyncpg.connect(dsn)
    try:
        assert await existing_hotel_pairs(conn) == list(EXISTING_CODES)
        assert len(await verify_committed_ledger(conn, ROOT)) == 39
        assert await conn.fetchval("SELECT count(*) FROM staff_users") == 24
        assert await conn.fetchval("SELECT count(*) FROM reservations") == 6
        assert await conn.fetchval("SELECT count(*) FROM payments") == 2
    finally:
        await conn.close()

    before = await snapshot(dsn)
    old_rows = await existing_rows(dsn)
    conn = await asyncpg.connect(dsn)
    try:
        try:
            await provision_additive(conn, hotel, fail_after_property=True)
        except RuntimeError as exc:
            assert "Injected pre-owner" in str(exc), "Wrong rollback failure"
        else:
            raise AssertionError("Forced rollback did not fail")
    finally:
        await conn.close()
    assert await snapshot(dsn) == before, "Injected failure changed original shared DB"
    assert await existing_rows(dsn) == old_rows, "Injected failure changed previous owner rows"

    conn = await asyncpg.connect(dsn)
    try:
        ids = await provision_additive(conn, hotel)
    finally:
        await conn.close()
    after = await snapshot(dsn)
    new_rows = await existing_rows(dsn)
    compare_additive(before, after, old_rows, new_rows, ids)
    conn = await asyncpg.connect(dsn)
    try:
        assert await existing_hotel_pairs(conn) == [
            ("tenant_a", "HOTEL_A"), ("tenant_b", "HOTEL_B"), ("tenant_c", "HOTEL_C")
        ]
        assert await conn.fetchval("SELECT count(*) FROM staff_users") == 25
        assert await conn.fetchval('SELECT count(*) FROM rooms WHERE "propertyId"=$1',
                                   ids["property"]) == 0
        assert await conn.fetchval('SELECT count(*) FROM reservations WHERE "propertyId"=$1',
                                   ids["property"]) == 0
        # payments has no propertyId column. Derive tenant ownership through
        # reservation/request FKs; require zero new hotel-linked payments.
        assert await conn.fetchval('''
            SELECT count(*) FROM payments pay
            LEFT JOIN reservations res ON res.id=pay."reservationId"
            LEFT JOIN reservation_requests req ON req.id=pay."requestId"
            WHERE res."propertyId"=$1 OR req."propertyId"=$1
        ''', ids["property"]) == 0
        assert len(await verify_committed_ledger(conn, ROOT)) == 39
        try:
            await provision_additive(conn, hotel)
        except RuntimeError as exc:
            assert "inventory not exactly two" in str(exc), str(exc)
        else:
            raise AssertionError("Duplicate hotel attempt should be rejected")
    finally:
        await conn.close()
    assert await snapshot(dsn) == after, "Duplicate attempt modified original shared DB"

    print("MARINA_SHARED_THIRD_HOTEL_ADDITIVE_DATA_PASS: "
          "2 existing properties byte-for-byte preserved; exactly 6 additive "
          "new-hotel rows; 39 migrations/constraints preserved; forced rollback "
          "and duplicate attempt left database unchanged", flush=True)
    return {key: str(value) for key, value in ids.items()}


def login(client: TestClient, hotel: str, tenant: str, *, username: str="owner") -> dict:
    result = client.post("/api/v1/auth/login", json={
        "tenant_code": tenant, "property_code": hotel,
        "username": username, "password": PASSWORD,
    })
    assert result.status_code == 200, f"Hotel login {hotel}: {result.status_code} {result.text[:120]}"
    identity = result.json()
    assert identity["property_code"] == hotel and identity["role"] == "OWNER"
    assert identity["tenant_id"] and identity["property_id"]
    return identity


def scope_check(client: TestClient, hotel: str, own: dict, others: list[dict],
                *, old_reservations: dict) -> None:
    me = client.get("/api/v1/auth/me", headers={
        "X-Role": "OWNER", "X-Property-Id": others[0]["property_id"],
        "X-Tenant-Id": others[0]["tenant_id"],
    })
    assert me.status_code == 200 and me.json()["property_code"] == hotel
    grid = client.get("/api/v1/pms/grid", params={
        "start": (date.today()-timedelta(days=4)).isoformat(),
        "end": (date.today()+timedelta(days=7)).isoformat(),
    })
    assert grid.status_code == 200, f"{hotel} grid={grid.status_code} {grid.text[:160]}"
    assert grid.json()["property"] == hotel
    codes = {room["code"] for room in grid.json()["rooms"]}
    assert codes == ({"A101"} if hotel == "HOTEL_A" else
                     {"B202"} if hotel == "HOTEL_B" else set())
    finance = client.get("/api/v1/admin/finance/summary", params={
        "from_date": (date.today()-timedelta(days=10)).isoformat(),
        "to_date": (date.today()+timedelta(days=10)).isoformat(),
    })
    assert finance.status_code == 200, f"{hotel} finance={finance.status_code} {finance.text[:160]}"
    report = finance.json()
    assert report["scope"]["internal_only"] is True
    assert report["period_payments"]["received_kgs"] == (
        1000 if hotel=="HOTEL_A" else 1500 if hotel=="HOTEL_B" else 0)
    own_reservations = {
        row["reservation_id"] for row in report["reservation_ledger"]
    }
    if hotel in old_reservations:
        assert old_reservations[hotel]["reservation_id"] in own_reservations
    else:
        assert not own_reservations
    for other in old_reservations.values():
        if other["reservation_id"] not in {
            old_reservations.get(hotel, {}).get("reservation_id")
        }:
            assert other["reservation_id"] not in own_reservations
        if hotel == "HOTEL_C":
            foreign = client.get("/api/v1/admin/reception/reservations/" +
                                 other["reservation_id"])
            assert foreign.status_code == 404, "New owner may not read old hotel booking"
            history = client.get("/api/v1/ops/tasks/" +
                                 other["maintenance_task_id"] + "/history")
            assert history.status_code == 404, "New owner may not read old hotel task"
    staff = client.get("/api/v1/admin/staff/overview")
    assert staff.status_code == 200
    accounts = staff.json()["staff"]
    assert len(accounts) == (1 if hotel == "HOTEL_C" else len(SERVER_ROLES))
    assert all(user["username"] in {r.lower() for r in SERVER_ROLES} for user in accounts)
    ops = client.get("/api/v1/ops/tasks")
    assert ops.status_code == 200
    if hotel=="HOTEL_C":
        assert ops.json()["items"] == [], "New hotel must not inherit old operational tasks"
    for other in others:
        assert own["property_id"] != other["property_id"]
        assert own["tenant_id"] != other["tenant_id"]


def main() -> None:
    dsn, hotel = staged_configuration()
    receipts = json.loads(RECEIPTS.read_text())
    assert set(receipts) == {"HOTEL_A", "HOTEL_B"}
    # Both previously authenticated sessions must stay valid throughout
    # the additive transaction; new login is not a substitute for this proof.
    sys.path.insert(0, str(ROOT / "services" / "api"))
    from app.app_entry import app
    with (TestClient(app, base_url="https://localhost:18000") as a,
          TestClient(app, base_url="https://localhost:18000") as b,
          TestClient(app, base_url="https://localhost:18000") as c):
        owner_a=login(a, "HOTEL_A", "tenant_a")
        owner_b=login(b, "HOTEL_B", "tenant_b")
        ids = asyncio.run(create_and_compare(dsn, hotel))
        owner_c=login(c, "HOTEL_C", "tenant_c")
        assert owner_c["property_id"] == ids["property"]
        scope_check(a, "HOTEL_A", owner_a, [owner_b,owner_c],
                    old_reservations=receipts)
        scope_check(b, "HOTEL_B", owner_b, [owner_a,owner_c],
                    old_reservations=receipts)
        scope_check(c, "HOTEL_C", owner_c, [owner_a,owner_b],
                    old_reservations=receipts)
        # Wrong organization/hotel pair cannot log in as an existing owner.
        with TestClient(app, base_url="https://localhost:18000") as wrong:
            for tenant, property_code in (
                ("tenant_a", "HOTEL_C"), ("tenant_c", "HOTEL_A"),
                ("tenant_b", "HOTEL_C"), ("tenant_c", "HOTEL_B"),
            ):
                response = wrong.post("/api/v1/auth/login", json={
                    "tenant_code": tenant, "property_code": property_code,
                    "username": "owner", "password": PASSWORD,
                })
                assert response.status_code == 401, (tenant, property_code, response.status_code)
        # First two existing sessions survived; both remain independent.
        assert a.get("/api/v1/auth/me").json()["property_code"] == "HOTEL_A"
        assert b.get("/api/v1/auth/me").json()["property_code"] == "HOTEL_B"
        assert c.get("/api/v1/auth/me").json()["property_code"] == "HOTEL_C"
        logout = c.post("/api/v1/auth/logout")
        assert logout.status_code == 204
        assert c.get("/api/v1/auth/me").status_code == 401
        assert a.get("/api/v1/auth/me").status_code == 200
        assert b.get("/api/v1/auth/me").status_code == 200
    print("MARINA_SHARED_THREE_HOTEL_API_PASS: existing sessions remain valid; "
          "3 independent owners/grids/finance/staff/ops; 404 foreign data; "
          "selector mismatch 401 and independent logout", flush=True)


if __name__=="__main__":
    main()
