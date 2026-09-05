import asyncio
import os
import uuid

import asyncpg
import httpx

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000")
DB = os.environ["DATABASE_URL"].split("?", 1)[0]
USERNAME = os.environ["BOOTSTRAP_OWNER_USERNAME"]
PASSWORD = os.environ["BOOTSTRAP_OWNER_PASSWORD"]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


async def main() -> None:
    conn = await asyncpg.connect(DB)
    try:
        property_id = await conn.fetchval("SELECT id FROM properties WHERE code='THREE_CROWNS'")
        check(property_id is not None, "property missing")
        payment_before = await conn.fetchval("SELECT count(*) FROM payments")
        reservation_total_before = await conn.fetchval("SELECT COALESCE(sum(\"totalKgs\"),0) FROM reservations")

        async with httpx.AsyncClient(base_url=BASE, timeout=20) as client:
            login = await client.post("/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD})
            check(login.status_code == 200, f"owner login failed: {login.status_code} {login.text}")

            bootstrap = await client.post("/api/v1/kitchen/menu/bootstrap-draft")
            check(bootstrap.status_code == 200, f"menu bootstrap failed: {bootstrap.text}")
            menu_response = await client.get("/api/v1/kitchen/menu")
            check(menu_response.status_code == 200, menu_response.text)
            menu = menu_response.json()["items"]
            check(len(menu) >= 15, f"expected draft menu, got {len(menu)} items")
            check(all(item["is_draft"] for item in menu), "bootstrap menu must be explicitly draft")

            table_code = f"CI{uuid.uuid4().hex[:6].upper()}"
            table_response = await client.post("/api/v1/kitchen/tables", json={"code": table_code, "name": "CI Kitchen Table", "seats": 4})
            check(table_response.status_code == 201, f"table create failed: {table_response.text}")
            table = table_response.json()

            first = menu[0]
            second = menu[1]
            create_order = await client.post(
                "/api/v1/kitchen/orders",
                json={
                    "source": "TABLE",
                    "table_id": table["id"],
                    "guest_count": 2,
                    "notes": "CI order",
                    "items": [
                        {"menu_item_id": first["id"], "quantity": 2},
                        {"menu_item_id": second["id"], "quantity": 1},
                    ],
                },
            )
            check(create_order.status_code == 201, f"order create failed: {create_order.text}")
            order = create_order.json()
            expected_total = first["price_kgs"] * 2 + second["price_kgs"]
            check(order["total_kgs"] == expected_total, "order total must be server-derived from menu prices")
            check(order["financial_posting"] == "NONE_AUTOMATIC", "kitchen must not auto-post hotel finance")

            active = await client.get("/api/v1/kitchen/orders", params={"status": "ACTIVE"})
            check(active.status_code == 200, active.text)
            found = next((item for item in active.json()["items"] if item["id"] == order["id"]), None)
            check(found is not None, "new kitchen order absent from active queue")
            check(found["table_code"] == table_code, "table context lost")
            check(len(found["items"]) == 2, "order item details lost")

            for state in ["ACCEPTED", "COOKING", "READY", "SERVED"]:
                response = await client.patch(f"/api/v1/kitchen/orders/{order['id']}/status", json={"status": state})
                check(response.status_code == 200, f"status {state} failed: {response.text}")
                check(response.json()["status"] == state, f"status {state} not persisted")

            invalid = await client.patch(f"/api/v1/kitchen/orders/{order['id']}/status", json={"status": "READY"})
            check(invalid.status_code == 409, "terminal order must reject invalid backwards transition")

            tables = await client.get("/api/v1/kitchen/tables")
            saved_table = next(item for item in tables.json()["items"] if item["id"] == table["id"])
            check(saved_table["status"] == "AVAILABLE", "table must return AVAILABLE after terminal order")

            # Materialize a factual recent check-in to prove kitchen arrival synchronization and idempotency.
            guest_id = uuid.uuid4()
            reservation_id = uuid.uuid4()
            stay_id = uuid.uuid4()
            assignment_id = uuid.uuid4()
            room = await conn.fetchrow('SELECT id,code FROM rooms WHERE "propertyId"=$1 ORDER BY code LIMIT 1', property_id)
            check(room is not None, "canonical room missing")
            booking = f"KCI-{uuid.uuid4().hex[:8].upper()}"
            await conn.execute(
                '''INSERT INTO guests (id,"propertyId","firstName","createdAt","updatedAt") VALUES ($1,$2,'Kitchen CI',now(),now())''',
                guest_id, property_id,
            )
            await conn.execute(
                '''INSERT INTO reservations (id,"propertyId","bookingNumber","primaryGuestId",status,"checkIn","checkOut",adults,children,"totalKgs","createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,'CHECKED_IN',current_date,current_date + 2,2,1,10000,now(),now())''',
                reservation_id, property_id, booking, guest_id,
            )
            await conn.execute(
                '''INSERT INTO stays (id,"propertyId","reservationId","guestId",status,"actualCheckInAt","createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,'ACTIVE',now(),now(),now())''',
                stay_id, property_id, reservation_id, guest_id,
            )
            await conn.execute(
                '''INSERT INTO room_assignments (id,"propertyId","stayId","roomId","startedAt",source,"createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,now(),'KITCHEN_CI',now(),now())''',
                assignment_id, property_id, stay_id, room["id"],
            )

            sync1 = await client.post("/api/v1/ops/kitchen/sync-arrivals")
            check(sync1.status_code == 200, f"arrival sync failed: {sync1.text}")
            check(sync1.json()["created"] >= 1, "recent check-in did not create kitchen arrival card")
            sync2 = await client.post("/api/v1/ops/kitchen/sync-arrivals")
            check(sync2.status_code == 200, sync2.text)
            check(sync2.json()["created"] == 0, "arrival sync must be idempotent")

            arrivals = await client.get("/api/v1/ops/kitchen/arrivals")
            check(arrivals.status_code == 200, arrivals.text)
            arrival = next((item for item in arrivals.json()["items"] if item["booking_number"] == booking), None)
            check(arrival is not None, "arrival inbox missing new stay")
            check("Kitchen CI" not in (arrival.get("description") or ""), "arrival card leaked guest name")
            ack = await client.post(f"/api/v1/ops/kitchen/arrivals/{arrival['id']}/ack")
            check(ack.status_code == 200 and ack.json()["status"] == "DONE", "arrival acknowledgement failed")

        payment_after = await conn.fetchval("SELECT count(*) FROM payments")
        reservation_total_after = await conn.fetchval("SELECT COALESCE(sum(\"totalKgs\"),0) FROM reservations")
        # Only the synthetic reservation above may change the aggregate reservation total.
        check(payment_after == payment_before, "kitchen flow created/changed Payment rows")
        check(reservation_total_after == reservation_total_before + 10000, "kitchen flow mutated accommodation totals")
        print("KITCHEN OPERATIONS E2E: PASS")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
