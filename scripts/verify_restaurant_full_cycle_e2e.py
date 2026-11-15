"""Single isolated DB-backed restaurant E2E: stay → seat → multi-item order → serve → move → folio → release."""
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
                cookie_secure=os.environ.get("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"},
                rc426_confirm=os.environ.get("RC426_KITCHEN_E2E_CONFIRM"))


def require(response, status, label):
    assert response.status_code == status, f"{label}: {response.status_code} {response.text}"
    return response.json()


async def sign_in(client, username, password, role):
    require(await client.post("/api/v1/auth/login", json={"username": username, "password": password}), 200, role + " login")
    me = require(await client.get("/api/v1/auth/me"), 200, "identity")
    assert me["role"] == role and me["property_code"] == PROPERTY, "wrong role/property"
    return me


async def main():
    db = await asyncpg.connect(DB)
    try:
        pid = await db.fetchval("SELECT id FROM properties WHERE code=$1", PROPERTY)
        assert pid is not None
        room = await db.fetchrow(
            """SELECT r.id FROM rooms r WHERE r."propertyId"=$1
               AND NOT EXISTS (SELECT 1 FROM room_assignments ra
                               WHERE ra."roomId"=r.id AND ra."endedAt" IS NULL)
               ORDER BY r.code LIMIT 1""", pid)
        assert room, "no isolated hotel room"
        business_date = await db.fetchval(
            """SELECT (now() AT TIME ZONE COALESCE(timezone,'Asia/Bishkek'))::date
                 FROM properties WHERE id=$1""", pid)
        payments_before = await db.fetchval("SELECT count(*) FROM payments")
        guest_id, reservation_id, stay_id, assignment_id = (uuid.uuid4() for _ in range(4))
        async with db.transaction():
            await db.execute(
                """INSERT INTO guests (id,"propertyId","firstName","createdAt","updatedAt")
                   VALUES ($1,$2,'Restaurant CI',now(),now())""", guest_id, pid)
            await db.execute(
                """INSERT INTO reservations
                   (id,"propertyId","bookingNumber","primaryGuestId",status,"checkIn","checkOut",
                    adults,children,"totalKgs","createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,'CHECKED_IN',$5::date,$5::date + 2,2,0,8000,now(),now())""",
                reservation_id, pid, "RCE-" + uuid.uuid4().hex[:10].upper(), guest_id, business_date)
            await db.execute(
                """INSERT INTO stays
                   (id,"propertyId","reservationId","guestId",status,"actualCheckInAt","createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,'ACTIVE',now(),now(),now())""",
                stay_id, pid, reservation_id, guest_id)
            await db.execute(
                """INSERT INTO room_assignments
                   (id,"propertyId","stayId","roomId","startedAt",source,"createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,now(),'RESTAURANT_CI',now(),now())""",
                assignment_id, pid, stay_id, room["id"])

        async with httpx.AsyncClient(base_url=BASE, timeout=30) as owner, httpx.AsyncClient(base_url=BASE, timeout=30) as waiter, httpx.AsyncClient(base_url=BASE, timeout=30) as cook, httpx.AsyncClient(base_url=BASE, timeout=30) as other_waiter:
            await sign_in(owner, os.environ["BOOTSTRAP_OWNER_USERNAME"], os.environ["BOOTSTRAP_OWNER_PASSWORD"], "OWNER")
            await sign_in(cook, os.environ["KITCHEN_MENU_DINING_USERNAME"], os.environ["KITCHEN_MENU_DINING_PASSWORD"], "COOK")
            waiter_user = await sign_in(waiter, os.environ["WAITER_SERVE_E2E_USERNAME"], os.environ["WAITER_SERVE_E2E_PASSWORD"], "WAITER")
            wid = waiter_user["id"]
            await sign_in(other_waiter, os.environ["WAITER_OTHER_E2E_USERNAME"], os.environ["WAITER_OTHER_E2E_PASSWORD"], "WAITER")
            require(await owner.post("/api/v1/kitchen/menu/bootstrap-draft"), 200, "test menu")
            menu = require(await owner.get("/api/v1/kitchen/menu"), 200, "menu")["items"]
            assert len(menu) >= 2, "need two different dishes"
            for item in menu[:2]:
                require(await owner.patch(f"/api/v1/kitchen/menu/{item['id']}",
                                          json={"is_active": True, "is_draft": False}), 200, "publish test dish")
            # WAITER can read only approved menu without protected recipe data.
            waiter_menu = require(await waiter.get("/api/v1/kitchen/menu"), 200, "waiter menu")["items"]
            assert all(row["is_active"] and not row["is_draft"] and "recipe" not in row for row in waiter_menu)
            assert {item["id"] for item in menu[:2]}.issubset({item["id"] for item in waiter_menu})
            require(await waiter.patch(f"/api/v1/kitchen/menu/{menu[0]['id']}",
                                       json={"is_active": False}), 403, "waiter cannot edit menu")
            require(await waiter.post("/api/v1/kitchen/menu", json={}), 403, "waiter cannot create menu")
            require(await waiter.get("/api/v1/kitchen/orders"), 403, "waiter cannot read cook queue")
            tables = []
            for suffix in ("A", "B"):
                table = require(await waiter.post("/api/v1/kitchen/tables", json={
                    "code": "RCE" + uuid.uuid4().hex[:7].upper() + suffix,
                    "name": "Restaurant E2E " + suffix, "seats": 4}), 201, "new table")
                tables.append(table)
            source, target = tables
            require(await waiter.patch(f"/api/v1/kitchen/tables/{source['id']}",
                                       json={"status": "OUT_OF_SERVICE"}), 403, "waiter cannot change table status")
            session = require(await waiter.post("/api/v1/dining/sessions", json={
                "stay_id": str(stay_id), "table_id": source["id"],
                "service_date": business_date.isoformat(), "meal_type": "DINNER",
                "status": "SEATED"}), 201, "seat guest")
            assert session["stay_id"] == str(stay_id) and session["waiter_id"] == wid
            approved_ids = {item["id"] for item in menu[:2]}
            draft = next((item for item in menu if item["is_draft"] and item["id"] not in approved_ids), None)
            assert draft is not None, "at least one draft must remain unapproved"
            require(await waiter.post("/api/v1/kitchen/orders", json={
                "source": "TABLE", "table_id": source["id"],
                "items": [{"menu_item_id": draft["id"], "quantity": 1}]}),
                409, "waiter cannot order unapproved draft by UUID")
            require(await waiter.post("/api/v1/kitchen/orders", json={
                "source": "ROOM", "table_id": source["id"],
                "items": [{"menu_item_id": menu[0]["id"], "quantity": 1}]}),
                403, "waiter cannot create room order")
            require(await waiter.post("/api/v1/kitchen/orders", json={
                "source": "TABLE", "table_id": source["id"], "stay_id": str(stay_id),
                "items": [{"menu_item_id": menu[0]["id"], "quantity": 1}]}),
                403, "waiter cannot inject guest/stay")
            order = require(await waiter.post("/api/v1/kitchen/orders", json={
                "source": "TABLE", "table_id": source["id"],
                "guest_count": 2, "items": [
                    {"menu_item_id": menu[0]["id"], "quantity": 2},
                    {"menu_item_id": menu[1]["id"], "quantity": 3}
                ]}), 201, "create multi-item order")
            oid = order["id"]
            # Staff Web uses this exact kitchen orders API via the /core proxy.
            owner_orders = require(await owner.get("/api/v1/kitchen/orders?status=ACTIVE"), 200, "Web-owner order feed")["items"]
            cook_orders = require(await cook.get("/api/v1/kitchen/orders?status=ACTIVE"), 200, "Web-cook order feed")["items"]
            owner_view = next(row for row in owner_orders if row["id"] == oid)
            cook_view = next(row for row in cook_orders if row["id"] == oid)
            for view in (owner_view, cook_view):
                assert view["order_number"] == order["order_number"]
                assert view["status"] == "NEW" and view["total_kgs"] == order["total_kgs"]
                assert view["table_code"] == source["code"]
                assert sorted(x["quantity"] for x in view["items"]) == [2, 3]
                assert sum(x["line_total_kgs"] for x in view["items"]) == order["total_kgs"]
            db_lines = await db.fetch(
                'SELECT quantity,"lineTotalKgs" FROM kitchen_order_items WHERE "orderId"=$1 ORDER BY quantity',
                uuid.UUID(oid))
            assert [line["quantity"] for line in db_lines] == [2, 3]
            assert sum(line["lineTotalKgs"] for line in db_lines) == order["total_kgs"]
            require(await other_waiter.post("/api/v1/kitchen/orders", json={
                "source": "TABLE", "table_id": source["id"],
                "items": [{"menu_item_id": menu[0]["id"], "quantity": 1}]}),
                403, "other waiter cannot create order for assigned table")
            require(await other_waiter.patch(f"/api/v1/kitchen/orders/{oid}/status",
                                             json={"status": "SERVED"}), 403,
                    "other waiter cannot serve another waiter's order")
            assert order["total_kgs"] == menu[0]["price_kgs"] * 2 + menu[1]["price_kgs"] * 3
            assigned = await db.fetchval('SELECT "waiterId" FROM kitchen_orders WHERE id=$1', uuid.UUID(oid))
            assert str(assigned) == wid, "waiter must own order from creation"
            for state in ("ACCEPTED", "COOKING", "READY"):
                result = require(await cook.patch(f"/api/v1/kitchen/orders/{oid}/status",
                                                   json={"status": state}), 200, state)
                assert result["status"] == state
            ready_feed = require(await cook.get("/api/v1/kitchen/orders?status=READY"), 200, "Web READY queue")["items"]
            assert any(x["id"] == oid and x["status"] == "READY" for x in ready_feed)
            served = require(await waiter.patch(f"/api/v1/kitchen/orders/{oid}/status",
                                                json={"status": "SERVED"}), 200, "waiter serves")
            assert served["status"] == "SERVED"
            candidates = require(await waiter.get("/api/v1/dining/folio-orders"), 200, "folio candidate")
            match = next(x for x in candidates["items"] if x["id"] == oid)
            assert match["eligible_to_post"] and match["waiter_id"] == wid
            require(await other_waiter.post(f"/api/v1/dining/orders/{oid}/folio"), 403,
                    "other waiter cannot post another waiter's folio")
            charge = require(await waiter.post(f"/api/v1/dining/orders/{oid}/folio"), 201, "post folio")
            assert charge["payment_created"] is False and charge["idempotent_replay"] is False
            again = require(await waiter.post(f"/api/v1/dining/orders/{oid}/folio"), 201, "folio replay")
            assert again["charge_id"] == charge["charge_id"] and again["idempotent_replay"]
            moved = require(await waiter.post(f"/api/v1/dining/sessions/{session['id']}/move", json={
                "target_table_id": target["id"], "waiter_mode": "KEEP"}), 200, "move guests")
            assert moved["table_id"] == target["id"] and moved["waiter_id"] == wid
            released = require(await waiter.patch(f"/api/v1/dining/sessions/{session['id']}/status",
                                                  json={"status": "RELEASED"}), 200, "release table")
            assert released["status"] == "RELEASED"
            persisted = await db.fetchrow(
                'SELECT status,"waiterId","stayId","reservationId" FROM kitchen_orders WHERE id=$1 AND "propertyId"=$2',
                uuid.UUID(oid), pid)
            assert persisted["status"] == "SERVED" and str(persisted["waiterId"]) == wid
            assert persisted["stayId"] == stay_id and persisted["reservationId"] == reservation_id
            charge_rows = await db.fetch(
                'SELECT id,status,"amountKgs" FROM guest_folio_charges WHERE "sourceType"=\'KITCHEN_ORDER\' AND "sourceId"=$1',
                oid)
            assert len(charge_rows) == 1 and charge_rows[0]["status"] == "OPEN"
            assert int(charge_rows[0]["amountKgs"]) == order["total_kgs"]
            floor = require(await owner.get("/api/v1/dining/floor-layout"), 200, "final floor")
            by_id = {row["id"]: row for row in floor["tables"]}
            assert by_id[source["id"]]["status"] == "CLEANING"
            assert by_id[target["id"]]["status"] == "CLEANING"
            assert await db.fetchval("SELECT count(*) FROM payments") == payments_before
            print("WAITER-LED FULL RESTAURANT POSTGRES E2E: PASS")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
