"""Isolated real-PostgreSQL HTTP E2E: assigned waiter READY -> SERVED, no Payment."""
import asyncio
import os
import uuid

import asyncpg
import httpx

from kitchen_e2e_target_guard import validate_target

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000")
DB = os.environ["DATABASE_URL"].split("?", 1)[0]
PROPERTY = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
validate_target(base=BASE, database_url=DB, property_code=PROPERTY,
                cookie_secure=os.environ.get("COOKIE_SECURE", "false").lower() in ("true", "1", "yes"),
                rc426_confirm=os.environ.get("RC426_KITCHEN_E2E_CONFIRM"))


def check(cond, message):
    if not cond:
        raise AssertionError(message)


async def login(client, username, password, role):
    response = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    check(response.status_code == 200, f"{role} login {response.status_code}: {response.text}")
    me = await client.get("/api/v1/auth/me")
    check(me.status_code == 200 and me.json().get("role") == role, f"invalid {role} identity")
    check(me.json().get("property_code") == PROPERTY, "cross-property session")
    return me.json()


async def main():
    conn = await asyncpg.connect(DB)
    try:
        pid = await conn.fetchval("SELECT id FROM properties WHERE code=$1", PROPERTY)
        check(pid is not None, "test property missing")
        payment_before = await conn.fetchval("SELECT count(*) FROM payments")
        async with httpx.AsyncClient(base_url=BASE, timeout=25) as owner, httpx.AsyncClient(base_url=BASE, timeout=25) as waiter:
            await login(owner, os.environ["BOOTSTRAP_OWNER_USERNAME"], os.environ["BOOTSTRAP_OWNER_PASSWORD"], "OWNER")
            staff = await login(waiter, os.environ["WAITER_SERVE_E2E_USERNAME"], os.environ["WAITER_SERVE_E2E_PASSWORD"], "WAITER")
            # Only data belonging to the isolated, guard-verified test property is mutated.
            menu_seed = await owner.post("/api/v1/kitchen/menu/bootstrap-draft")
            check(menu_seed.status_code == 200, menu_seed.text)
            items_response = await owner.get("/api/v1/kitchen/menu")
            check(items_response.status_code == 200, items_response.text)
            items = items_response.json()["items"]
            check(len(items) > 0, "no test menu")
            table_resp = await owner.post("/api/v1/kitchen/tables", json={
                "code": "WS" + uuid.uuid4().hex[:9].upper(), "name": "Waiter Serve CI", "seats": 2,
            })
            check(table_resp.status_code == 201, table_resp.text)
            order_resp = await owner.post("/api/v1/kitchen/orders", json={
                "source": "TABLE", "table_id": table_resp.json()["id"], "guest_count": 1,
                "items": [{"menu_item_id": items[0]["id"], "quantity": 2}],
            })
            check(order_resp.status_code == 201, order_resp.text)
            order_id = uuid.UUID(order_resp.json()["id"])
            endpoint = f"/api/v1/kitchen/orders/{order_id}/status"
            # Waiter cannot perform kitchen work or serve orders assigned to somebody else.
            wrong_role = await waiter.patch(endpoint, json={"status": "ACCEPTED"})
            check(wrong_role.status_code == 403, f"waiter promoted to cook: {wrong_role.status_code}")
            early = await waiter.patch(endpoint, json={"status": "SERVED"})
            check(early.status_code == 403, f"unassigned waiter served order: {early.status_code}")
            await conn.execute('UPDATE kitchen_orders SET "waiterId"=$2 WHERE id=$1 AND "propertyId"=$3',
                               order_id, uuid.UUID(staff["id"]), pid)
            still_early = await waiter.patch(endpoint, json={"status": "SERVED"})
            check(still_early.status_code == 409, f"non-READY order served: {still_early.status_code}")
            for status in ("ACCEPTED", "COOKING", "READY"):
                resp = await owner.patch(endpoint, json={"status": status})
                check(resp.status_code == 200, f"owner {status}: {resp.status_code} {resp.text}")
            served = await waiter.patch(endpoint, json={"status": "SERVED"})
            check(served.status_code == 200 and served.json()["status"] == "SERVED",
                  f"assigned waiter could not serve: {served.status_code} {served.text}")
            duplicate = await waiter.patch(endpoint, json={"status": "SERVED"})
            check(duplicate.status_code == 409, f"duplicate terminal serve accepted: {duplicate.status_code}")
            persisted = await conn.fetchrow('SELECT status,"waiterId","completedAt","propertyId" FROM kitchen_orders WHERE id=$1', order_id)
            check(persisted is not None and persisted["status"] == "SERVED", "status not persisted")
            check(persisted["waiterId"] == uuid.UUID(staff["id"]) and persisted["propertyId"] == pid,
                  "assignment/property mismatch")
            check(persisted["completedAt"] is not None, "completion time not persisted")
        payment_after = await conn.fetchval("SELECT count(*) FROM payments")
        check(payment_before == payment_after, "serve operation created a Payment")
        print("WAITER SERVE ISOLATED POSTGRES E2E: PASS")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
