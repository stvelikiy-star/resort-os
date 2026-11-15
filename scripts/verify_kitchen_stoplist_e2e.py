"""Isolated PostgreSQL E2E: cooked stop-list blocks new orders, not past financial truth."""
import asyncio
import os
import uuid
import asyncpg
import httpx
from kitchen_e2e_target_guard import validate_target

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000")
DB = os.environ["DATABASE_URL"].split("?", 1)[0]
PROPERTY = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
validate_target(
    base=BASE, database_url=DB, property_code=PROPERTY,
    cookie_secure=os.environ.get("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"},
    rc426_confirm=os.environ.get("RC426_KITCHEN_E2E_CONFIRM"),
)


def require(r, code, label):
    assert r.status_code == code, f"{label}: {r.status_code} {r.text}"
    return r.json()


async def login(client, role, username, password):
    require(await client.post("/api/v1/auth/login", json={
        "username": username, "password": password}), 200, role + " login")
    me = require(await client.get("/api/v1/auth/me"), 200, role + " identity")
    assert me["role"] == role and me["property_code"] == PROPERTY
    return me


async def main():
    db = await asyncpg.connect(DB)
    try:
        pid = await db.fetchval("SELECT id FROM properties WHERE code=$1", PROPERTY)
        assert pid is not None
        async with httpx.AsyncClient(base_url=BASE, timeout=25) as owner, \
                httpx.AsyncClient(base_url=BASE, timeout=25) as cook, \
                httpx.AsyncClient(base_url=BASE, timeout=25) as waiter:
            await login(owner, "OWNER", os.environ["BOOTSTRAP_OWNER_USERNAME"],
                        os.environ["BOOTSTRAP_OWNER_PASSWORD"])
            await login(cook, "COOK", os.environ["KITCHEN_MENU_DINING_USERNAME"],
                        os.environ["KITCHEN_MENU_DINING_PASSWORD"])
            await login(waiter, "WAITER", os.environ["WAITER_SERVE_E2E_USERNAME"],
                        os.environ["WAITER_SERVE_E2E_PASSWORD"])
            code = "STOP" + uuid.uuid4().hex[:12].upper()
            item = require(await owner.post("/api/v1/kitchen/menu", json={
                "code": code, "category": "MAIN",
                "name_ru": "Стоп-лист CI", "name_kg": "Стоп CI",
                "name_kz": "Стоп CI", "name_en": "Stoplist CI",
                "price_kgs": 400, "is_active": True, "is_draft": True,
            }), 201, "create draft")
            mid = item["id"]
            endpoint = f"/api/v1/kitchen/menu/{mid}/availability"
            require(await cook.put(endpoint, json={
                "available": False, "reason": "Ingredient unavailable",
            }), 409, "draft cannot be stop-listed")
            require(await owner.patch(f"/api/v1/kitchen/menu/{mid}", json={
                "is_draft": False, "is_active": True,
            }), 200, "publish approved item")
            owner_order = {"source": "MANAGER", "items": [
                {"menu_item_id": mid, "quantity": 2},
            ]}
            previous = require(await owner.post("/api/v1/kitchen/orders", json=owner_order),
                               201, "prior order")
            assert previous["total_kgs"] == 800
            assert any(row["id"] == mid for row in
                       require(await waiter.get("/api/v1/kitchen/menu"), 200, "visible menu")["items"])
            require(await waiter.put(endpoint, json={
                "available": False, "reason": "Not authorized",
            }), 403, "waiter cannot change availability")
            require(await cook.put(endpoint, json={
                "available": True, "reason": "Try unauthorized restore",
            }), 403, "cook cannot restore dish")
            require(await cook.put(endpoint, json={
                "available": False, "reason": "  Ingredient   unavailable  ",
            }), 200, "cook stops dish")
            unavailable = require(await cook.get("/api/v1/kitchen/menu/availability"),
                                  200, "cook availability feed")["items"]
            assert next(row for row in unavailable if row["id"] == mid)["is_available"] is False
            assert all(row["id"] != mid for row in
                       require(await waiter.get("/api/v1/kitchen/menu"), 200, "waiter menu after stop")["items"])
            require(await owner.post("/api/v1/kitchen/orders", json=owner_order),
                    409, "new order must not bypass stoplist")
            order_before = await db.fetchrow(
                'SELECT status,"totalKgs" FROM kitchen_orders WHERE id=$1 AND "propertyId"=$2',
                uuid.UUID(previous["id"]), pid)
            assert order_before["status"] == "NEW" and order_before["totalKgs"] == 800
            duplicate = require(await cook.put(endpoint, json={
                "available": False, "reason": "Still unavailable",
            }), 200, "idempotent stop")
            assert duplicate["already_set"] is True
            require(await cook.put("/api/v1/kitchen/menu/" + str(uuid.uuid4()) + "/availability",
                                   json={"available": False, "reason": "Not owned"}),
                    404, "unknown menu id")
            restored = require(await owner.put(endpoint, json={
                "available": True, "reason": "Ingredient restocked",
            }), 200, "manager restores")
            assert restored["is_available"] is True and restored["already_set"] is False
            assert any(row["id"] == mid for row in
                       require(await waiter.get("/api/v1/kitchen/menu"), 200, "waiter menu restored")["items"])
            next_order = require(await owner.post("/api/v1/kitchen/orders", json=owner_order),
                                 201, "new order after restore")
            assert next_order["total_kgs"] == previous["total_kgs"]
            audit = await db.fetch(
                '''SELECT action,"actorId","afterJson" FROM audit_logs
                   WHERE "propertyId"=$1 AND resource='KitchenMenuItem' AND "resourceId"=$2
                     AND action IN ('STOPLIST_MENU_ITEM','RESTORE_MENU_AVAILABILITY')
                   ORDER BY "createdAt"''',
                pid, mid)
            assert len(audit) == 2 and {x["action"] for x in audit} == {
                "STOPLIST_MENU_ITEM", "RESTORE_MENU_AVAILABILITY"}
            assert all(x["actorId"] for x in audit)
            assert {x["afterJson"]["reason"] for x in audit} == {
                "Ingredient unavailable", "Ingredient restocked"}
            assert await db.fetchval(
                'SELECT count(*) FROM payments WHERE "propertyId"=$1', pid
            ) == 0, "stop-list must never cause payment"
            print("KITCHEN STOP-LIST POSTGRES E2E: PASS")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
