#!/usr/bin/env python3
import asyncio
import os
import uuid
from datetime import date, timedelta

import asyncpg
import httpx
from argon2 import PasswordHasher

BASE_URL = os.environ.get("RESORT_CORE_TEST_URL", "http://127.0.0.1:8000")
DATABASE_URL = os.environ["DATABASE_URL"].split("?")[0]
OWNER_USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "reception-rbac-ci-owner")
OWNER_PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "Reception-RBAC-CI-Owner-Password-2026")
RECEPTION_USERNAME = "reception-rbac-ci"
RECEPTION_PASSWORD = "Reception-RBAC-CI-Password-2026"
PH = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


async def local_today() -> date:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval("SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE code='THREE_CROWNS'")
    finally:
        await conn.close()


async def ensure_reception_user():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        pid = await conn.fetchval("SELECT id FROM properties WHERE code='THREE_CROWNS'")
        assert pid
        user_id = await conn.fetchval('SELECT id FROM staff_users WHERE "propertyId"=$1 AND username=$2', pid, RECEPTION_USERNAME)
        password_hash = PH.hash(RECEPTION_PASSWORD)
        if user_id:
            await conn.execute(
                '''UPDATE staff_users SET "displayName"='CI Reception',"passwordHash"=$1,role='RECEPTION',"isActive"=true,"updatedAt"=now() WHERE id=$2''',
                password_hash,
                user_id,
            )
        else:
            user_id = uuid.uuid4()
            await conn.execute(
                '''INSERT INTO staff_users (id,"propertyId",username,"displayName","passwordHash",role,"isActive","createdAt","updatedAt")
                   VALUES ($1,$2,$3,'CI Reception',$4,'RECEPTION',true,now(),now())''',
                user_id,
                pid,
                RECEPTION_USERNAME,
                password_hash,
            )
        return str(user_id)
    finally:
        await conn.close()


async def set_room_clean(room_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('UPDATE rooms SET "operationalState"=\'CLEAN\',"updatedAt"=now() WHERE id=$1', uuid.UUID(room_id))
    finally:
        await conn.close()


async def room_state(room_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval('SELECT "operationalState"::text FROM rooms WHERE id=$1', uuid.UUID(room_id))
    finally:
        await conn.close()


def login(username: str, password: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE_URL, timeout=30.0, headers={"user-agent": "reception-rbac-ci"})
    response = client.post('/api/v1/auth/login', json={"username": username, "password": password})
    response.raise_for_status()
    return client


def main():
    today = asyncio.run(local_today())
    booking_start = today - timedelta(days=1)
    checkout_day = today + timedelta(days=2)
    asyncio.run(ensure_reception_user())

    owner = login(OWNER_USERNAME, OWNER_PASSWORD)
    grid = owner.get('/api/v1/pms/grid', params={"start": booking_start.isoformat(), "end": checkout_day.isoformat()})
    grid.raise_for_status()
    chosen = None
    quote = None
    for room in grid.json()["rooms"]:
        preview = owner.post('/api/v1/admin/pms/reservations/new/preview', json={
            "room_id": room["id"],
            "check_in": booking_start.isoformat(),
            "check_out": checkout_day.isoformat(),
            "adults": 2,
            "children": 0,
        })
        if preview.status_code == 200 and preview.json().get("can_commit"):
            chosen = room
            quote = preview.json()
            break
    assert chosen and quote, "No sellable room for reception acceptance"
    asyncio.run(set_room_clean(chosen["id"]))

    suffix = uuid.uuid4().hex[:8]
    committed = owner.post('/api/v1/admin/pms/reservations/new/commit', json={
        "room_id": chosen["id"],
        "check_in": booking_start.isoformat(),
        "check_out": checkout_day.isoformat(),
        "adults": 2,
        "children": 0,
        "guest_name": "Reception RBAC CI",
        "phone": "+996557" + suffix[:6],
        "email": f"reception-rbac-{suffix}@example.com",
        "expected_total_kgs": quote["pricing"]["total_kgs"],
        "expected_pricing_source": quote["pricing"]["source"],
        "notes": "Reception RBAC acceptance",
    })
    committed.raise_for_status()
    reservation_id = committed.json()["reservation_id"]
    total_kgs = quote["pricing"]["total_kgs"]
    paid_amount = max(1, total_kgs // 3)

    payment = owner.post(f'/api/v1/admin/booking/reservations/{reservation_id}/payments', json={
        "amount_kgs": paid_amount,
        "method": "CASH",
        "external_ref": f"RECEPTION-CI-{suffix}",
        "note": "Manager-recorded fact for Reception read acceptance",
        "idempotency_key": f"reception-rbac-payment-{suffix}",
    })
    payment.raise_for_status()
    assert payment.json()["finance"]["paid_kgs"] == paid_amount

    reception = login(RECEPTION_USERNAME, RECEPTION_PASSWORD)
    me = reception.get('/api/v1/auth/me')
    me.raise_for_status()
    assert me.json()["role"] == "RECEPTION"

    desk = reception.get('/api/v1/admin/reception/reservations', params={"limit": 500})
    desk.raise_for_status()
    item = next(row for row in desk.json()["items"] if row["id"] == reservation_id)
    assert item["paidKgs"] == paid_amount
    assert item["remainingKgs"] == total_kgs - paid_amount
    assert item["room_code"] == chosen["code"]
    assert item["room_state"] == "CLEAN"

    detail = reception.get(f'/api/v1/admin/booking/reservations/{reservation_id}')
    detail.raise_for_status()
    card = detail.json()
    assert card["finance"]["paid_kgs"] == paid_amount
    assert card["finance"]["remaining_kgs"] == total_kgs - paid_amount
    assert card["finance"]["payments"][0]["status"] == "RECEIVED"

    # Commercial / financial authority stays manager-owned.
    denied_payment = reception.post(f'/api/v1/admin/booking/reservations/{reservation_id}/payments', json={
        "amount_kgs": 100,
        "method": "CASH",
        "idempotency_key": f"reception-denied-{suffix}",
    })
    assert denied_payment.status_code == 403, denied_payment.text

    denied_new = reception.post('/api/v1/admin/pms/reservations/new/preview', json={
        "room_id": chosen["id"],
        "check_in": today.isoformat(),
        "check_out": checkout_day.isoformat(),
        "adults": 1,
        "children": 0,
    })
    assert denied_new.status_code == 403, denied_new.text

    denied_schedule = reception.get(f'/api/v1/admin/pms/reservations/{reservation_id}/schedule')
    assert denied_schedule.status_code == 403, denied_schedule.text

    # Operational desk authority is real: Reception performs check-in and check-out.
    checkin = reception.post(f'/api/v1/admin/stays/reservations/{reservation_id}/check-in')
    checkin.raise_for_status()
    assert checkin.json()["status"] == "CHECKED_IN"
    assert checkin.json()["stay_id"]
    assert checkin.json()["guest_access_pin_display_once"] is True

    after_checkin = reception.get('/api/v1/admin/reception/reservations', params={"limit": 500})
    after_checkin.raise_for_status()
    live = next(row for row in after_checkin.json()["items"] if row["id"] == reservation_id)
    assert live["status"] == "CHECKED_IN"
    assert live["room_code"] == chosen["code"]

    # Room QR administration is also an explicit Reception capability.
    qr = reception.post(f'/api/v1/admin/guest-os/room-qrs/{chosen["id"]}/issue')
    qr.raise_for_status()
    assert qr.json()["room_id"] == chosen["id"]

    # The booking began on the prior hotel night, so an early checkout today is a real non-zero-night stay.
    checkout = reception.post(f'/api/v1/admin/stays/reservations/{reservation_id}/check-out')
    checkout.raise_for_status()
    assert checkout.json()["status"] == "CHECKED_OUT"
    assert asyncio.run(room_state(chosen["id"])) == "DIRTY"

    final_card = reception.get(f'/api/v1/admin/booking/reservations/{reservation_id}')
    final_card.raise_for_status()
    assert final_card.json()["reservation"]["status"] == "CHECKED_OUT"
    assert final_card.json()["finance"]["paid_kgs"] == paid_amount

    owner.close()
    reception.close()
    print("RECEPTION_RBAC_E2E_OK")


if __name__ == '__main__':
    main()
