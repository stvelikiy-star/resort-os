import asyncio
import os
import uuid
from datetime import timedelta

import asyncpg
import httpx
from argon2 import PasswordHasher

BASE_URL = os.environ.get("MY_STAY_E2E_BASE_URL", "http://127.0.0.1:8000")
DATABASE_URL = os.environ["DATABASE_URL"].split("?", 1)[0]
PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
PASSWORD = "MY-Stay-CI-Strong-Password-2026"
ph = PasswordHasher(time_cost=2, memory_cost=32768, parallelism=2)


def require(response: httpx.Response, status: int | tuple[int, ...], label: str):
    expected = (status,) if isinstance(status, int) else status
    if response.status_code not in expected:
        raise AssertionError(f"{label}: expected {expected}, got {response.status_code}: {response.text[:1000]}")
    return response


async def upsert_staff(conn, property_id, username: str, role: str):
    user_id = uuid.uuid4()
    return await conn.fetchval(
        '''
        INSERT INTO staff_users(id,"propertyId",username,"displayName","passwordHash",role,"isActive","createdAt","updatedAt")
        VALUES($1,$2,$3,$4,$5,$6::"StaffRole",true,now(),now())
        ON CONFLICT ("propertyId",username) DO UPDATE SET
          "passwordHash"=EXCLUDED."passwordHash",role=EXCLUDED.role,"isActive"=true,"updatedAt"=now()
        RETURNING id
        ''',
        user_id, property_id, username, f"CI {role}", ph.hash(PASSWORD), role,
    )


async def prepare_fixture():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        property_row = await conn.fetchrow('SELECT id,timezone FROM properties WHERE code=$1', PROPERTY_CODE)
        assert property_row, "Property was not seeded"
        pid = property_row["id"]
        local_today = await conn.fetchval("SELECT (now() AT TIME ZONE $1)::date", property_row["timezone"])
        room = await conn.fetchrow('SELECT id,code FROM rooms WHERE "propertyId"=$1 ORDER BY code LIMIT 1', pid)
        assert room, "No room seeded"
        await conn.execute('UPDATE rooms SET "operationalState"=\'CLEAN\',"updatedAt"=now() WHERE id=$1', room["id"])

        guest_id = uuid.uuid4()
        reservation_id = uuid.uuid4()
        booking = f"MY-STAY-CI-{str(reservation_id)[:8]}"
        check_out = local_today + timedelta(days=2)
        await conn.execute(
            'INSERT INTO guests(id,"propertyId","firstName",phone,"createdAt","updatedAt") VALUES($1,$2,$3,$4,now(),now())',
            guest_id, pid, "MY STAY CI", "+996555990001",
        )
        await conn.execute(
            '''INSERT INTO reservations(id,"propertyId","bookingNumber","primaryGuestId",status,"checkIn","checkOut",adults,children,"totalKgs","createdAt","updatedAt")
               VALUES($1,$2,$3,$4,'CHECKED_IN',$5,$6,2,0,10000,now(),now())''',
            reservation_id, pid, booking, guest_id, local_today, check_out,
        )
        await conn.execute(
            '''INSERT INTO inventory_blocks(id,"roomId","reservationId","blockType","startDate","endDate",active,reason,"createdAt","updatedAt")
               VALUES($1,$2,$3,'RESERVATION',$4,$5,true,$6,now(),now())''',
            uuid.uuid4(), room["id"], reservation_id, local_today, check_out, booking,
        )
        users = {}
        for username, role in [
            ("ci_owner_my_stay", "OWNER"),
            ("ci_admin_my_stay", "ADMIN"),
            ("ci_reception_my_stay", "RECEPTION"),
            ("ci_dining_my_stay", "DINING"),
            ("ci_maid_my_stay", "MAID"),
            ("ci_tech_my_stay", "TECHNICIAN"),
        ]:
            users[role] = str(await upsert_staff(conn, pid, username, role))
        return {
            "property_id": str(pid), "today": str(local_today), "room_id": str(room["id"]), "room_code": room["code"],
            "reservation_id": str(reservation_id), "booking": booking, "users": users,
        }
    finally:
        await conn.close()


async def login(role: str) -> httpx.AsyncClient:
    username = {
        "OWNER":"ci_owner_my_stay", "ADMIN":"ci_admin_my_stay", "RECEPTION":"ci_reception_my_stay",
        "DINING":"ci_dining_my_stay", "MAID":"ci_maid_my_stay", "TECHNICIAN":"ci_tech_my_stay",
    }[role]
    client = httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True)
    response = await client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
    require(response, 200, f"login {role}")
    body = response.json()
    assert body["role"] == role
    return client


async def db_value(sql: str, *args):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval(sql, *args)
    finally:
        await conn.close()


async def main():
    fx = await prepare_fixture()
    rid = fx["reservation_id"]
    room_id = fx["room_id"]
    today = fx["today"]

    owner = await login("OWNER")
    admin = await login("ADMIN")
    reception = await login("RECEPTION")
    dining = await login("DINING")
    maid = await login("MAID")
    tech = await login("TECHNICIAN")
    guest = httpx.AsyncClient(base_url=BASE_URL, follow_redirects=True)
    try:
        # Role boundaries: ADMIN has operational management, RECEPTION is narrow, DINING is dining-only.
        require(await admin.get("/api/v1/ops/tasks"), 200, "ADMIN operations")
        require(await reception.get("/api/v1/admin/reception/reservations"), 200, "RECEPTION reservations")
        require(await reception.get("/api/v1/dining/orders"), 403, "RECEPTION denied dining")
        require(await dining.get("/api/v1/admin/reception/reservations"), 403, "DINING denied reception")
        require(await maid.get("/api/v1/admin/reception/reservations"), 403, "MAID denied reception")
        require(await tech.get("/api/v1/admin/reception/reservations"), 403, "TECH denied reception")

        # Issue a one-time QR activation + PIN and prove the QR renderer stays inside authenticated PMS.
        issued = require(await reception.post(f"/api/v1/admin/my-stay/reservations/{rid}/issue"), 200, "issue guest access").json()
        assert len(issued["pin"]) == 6 and "#activate=" in issued["guest_url"]
        qr = require(await reception.get("/api/v1/admin/my-stay/qr.svg", params={"value": issued["guest_url"]}), 200, "render QR")
        assert "svg" in qr.headers.get("content-type", "") and b"<svg" in qr.content

        # Activation is only valid once and only for CHECKED_IN stay.
        activated = await guest.post("/api/v1/guest/activate", json={"activation_token": issued["activation_token"], "pin": issued["pin"]})
        require(activated, 200, "guest activate")
        replay = await httpx.AsyncClient(base_url=BASE_URL).post("/api/v1/guest/activate", json={"activation_token": issued["activation_token"], "pin": issued["pin"]})
        require(replay, 401, "activation replay denied")
        me = require(await guest.get("/api/v1/guest/me"), 200, "guest me").json()
        assert me["booking_number"] == fx["booking"] and me["room_code"] == fx["room_code"]

        # Reception controls meal plan; dining creates the actual daily menu.
        require(await reception.put(f"/api/v1/admin/my-stay/reservations/{rid}/meal-plan", json={"service_date": today, "meal_type": "LUNCH", "included": False}), 200, "meal plan")
        menu_item = require(await dining.post("/api/v1/dining/menu", json={
            "service_date": today, "meal_type": "LUNCH", "name": "CI Плов", "description": "Synthetic MY STAY E2E item",
            "price_kgs": 650, "available_qty": 3, "included_in_meal_plan": False,
        }), 201, "create menu item").json()
        menu = require(await guest.get("/api/v1/guest/menu", params={"service_date": today, "meal_type": "LUNCH"}), 200, "guest menu").json()
        assert any(str(x["id"]) == menu_item["id"] for x in menu["items"])

        accommodation_total_before = int(await db_value('SELECT "totalKgs" FROM reservations WHERE id=$1::uuid', rid))
        order = require(await guest.post("/api/v1/guest/dining/orders", json={
            "service_date": today, "meal_type": "LUNCH", "items": [{"menu_item_id": menu_item["id"], "quantity": 2}],
        }), 201, "guest dining order").json()
        assert order["total_kgs"] == 1300 and order["payment_mode"] == "ROOM_FOLIO"
        accommodation_total_after = int(await db_value('SELECT "totalKgs" FROM reservations WHERE id=$1::uuid', rid))
        assert accommodation_total_after == accommodation_total_before == 10000, "Ancillary dining must not mutate accommodation total"
        qty_left = await db_value('SELECT "availableQty" FROM dining_menu_items WHERE id=$1::uuid', menu_item["id"])
        assert qty_left == 1
        charge_id = str(await db_value('SELECT id FROM reservation_charges WHERE "sourceType"=\'DINING_ORDER\' AND "sourceId"=$1::uuid', order["id"]))

        # A charge is PAID only after a real RECEIVED Payment belonging to the same reservation is recorded.
        payment = require(await reception.post(f"/api/v1/admin/booking/reservations/{rid}/payments", json={
            "amount_kgs": 1300, "method": "CI_RECEPTION", "external_ref": f"my-stay-{rid}", "note": "MY STAY E2E ancillary",
            "idempotency_key": f"my-stay-e2e-{rid}",
        }), 201, "reception payment").json()
        payment_id = payment["payment_id"]
        require(await reception.patch(f"/api/v1/admin/my-stay/charges/{charge_id}/payment", json={"payment_id": payment_id}), 200, "link charge payment")
        charge_status = await db_value('SELECT status FROM reservation_charges WHERE id=$1::uuid', charge_id)
        assert charge_status == "PAID"

        # Dining workflow is explicit and constrained.
        for next_status in ["ACCEPTED", "PREPARING", "READY", "DELIVERED"]:
            require(await dining.patch(f"/api/v1/dining/orders/{order['id']}/status", json={"status": next_status}), 200, f"dining {next_status}")
        invalid_transition = await dining.patch(f"/api/v1/dining/orders/{order['id']}/status", json={"status": "ACCEPTED"})
        require(invalid_transition, 409, "dining terminal state protected")

        # In-stay housekeeping is a fulfilment request and never changes occupied-room turnover readiness.
        room_state_before = await db_value('SELECT "operationalState"::text FROM rooms WHERE id=$1::uuid', room_id)
        task = require(await guest.post("/api/v1/guest/requests", json={"kind":"HOUSEKEEPING","description":"CI in-stay cleaning","priority":"NORMAL"}), 201, "guest housekeeping").json()
        room_state_after_create = await db_value('SELECT "operationalState"::text FROM rooms WHERE id=$1::uuid', room_id)
        assert room_state_after_create == room_state_before
        require(await maid.post(f"/api/v1/ops/tasks/{task['id']}/claim"), 200, "maid claim in-stay")
        report = require(await maid.post(f"/api/v1/ops/tasks/{task['id']}/complete-report", json={
            "summary":"CI cleaned while occupied","checklist":[{"code":"SURFACES","label":"Поверхности","done":True}],"evidence_urls":[],
        }), 200, "maid complete in-stay").json()
        assert report["status"] == "DONE"
        room_state_after_complete = await db_value('SELECT "operationalState"::text FROM rooms WHERE id=$1::uuid', room_id)
        assert room_state_after_complete == room_state_before

        # Smart access discovery is room-bound; physical unlock stays fail-closed without real controller config.
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute(
                '''INSERT INTO smart_access_points(id,"propertyId",code,name,kind,"roomId","priceKgs",active,"controllerRef","createdAt","updatedAt")
                   VALUES($1,$2::uuid,$3,$4,'ROOM',$5::uuid,0,true,'CI_CONTROLLER',now(),now())''',
                uuid.uuid4(), fx["property_id"], "CI_ROOM_ACCESS", "CI Room Door", room_id,
            )
        finally:
            await conn.close()
        quote = require(await guest.get("/api/v1/guest/access/current-room"), 200, "current room access").json()
        assert quote["code"] == "CI_ROOM_ACCESS" and quote["room_code"] == fx["room_code"]
        unlock = await guest.post("/api/v1/guest/access/CI_ROOM_ACCESS/unlock", json={})
        require(unlock, 503, "smart access fail closed")
        used_grants = int(await db_value("SELECT count(*) FROM smart_access_grants WHERE status='USED'"))
        assert used_grants == 0

        # Brute-force guard trips after repeated bad activations. Run last because it is per-client address.
        attacker = httpx.AsyncClient(base_url=BASE_URL)
        try:
            statuses=[]
            for _ in range(9):
                r=await attacker.post("/api/v1/guest/activate", json={"activation_token":"x"*24,"pin":"000000"})
                statuses.append(r.status_code)
            assert 429 in statuses, statuses
        finally:
            await attacker.aclose()

        print("MY_STAY_E2E=PASS")
    finally:
        for client in [owner, admin, reception, dining, maid, tech, guest]:
            await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
