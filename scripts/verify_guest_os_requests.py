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
OWNER_USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "guest-requests-ci-owner")
OWNER_PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "Guest-Requests-CI-Owner-Password-2026")
STAFF_PASSWORD = "Guest-Requests-Staff-Password-2026"
password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


async def local_today() -> date:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval("SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE code='THREE_CROWNS'")
    finally:
        await conn.close()


async def set_room_clean(room_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('UPDATE rooms SET "operationalState"=\'CLEAN\',"updatedAt"=now() WHERE id=$1', uuid.UUID(room_id))
    finally:
        await conn.close()


async def room_state(room_id: str) -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval('SELECT "operationalState"::text FROM rooms WHERE id=$1', uuid.UUID(room_id))
    finally:
        await conn.close()


async def payment_count() -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval('SELECT count(*)::int FROM payments')
    finally:
        await conn.close()


async def ensure_staff(username: str, role: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        pid = await conn.fetchval("SELECT id FROM properties WHERE code='THREE_CROWNS'")
        assert pid
        existing = await conn.fetchval('SELECT id FROM staff_users WHERE "propertyId"=$1 AND username=$2', pid, username)
        password_hash = password_hasher.hash(STAFF_PASSWORD)
        if existing:
            await conn.execute(
                '''UPDATE staff_users SET "displayName"=$1,"passwordHash"=$2,role=$3::"StaffRole","isActive"=true,"updatedAt"=now() WHERE id=$4''',
                f"CI {role}", password_hash, role, existing,
            )
            return str(existing)
        staff_id = uuid.uuid4()
        await conn.execute(
            '''INSERT INTO staff_users (id,"propertyId",username,"displayName","passwordHash",role,"isActive","createdAt","updatedAt")
               VALUES ($1,$2,$3,$4,$5,$6::"StaffRole",true,now(),now())''',
            staff_id, pid, username, f"CI {role}", password_hash, role,
        )
        return str(staff_id)
    finally:
        await conn.close()


async def prove_task(task_id: str, *, code: str, stay_id: str, room_id: str, expected_status: str = "OPEN"):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            '''SELECT type::text AS type,status::text AS status,"serviceCode",source,"stayId","roomId","reservationId","createdByType"
               FROM operational_tasks WHERE id=$1''',
            uuid.UUID(task_id),
        )
        assert row
        assert row["type"] == "GUEST_REQUEST", row
        assert row["status"] == expected_status, row
        assert row["serviceCode"] == code, row
        assert row["source"] == f"GUEST_OS_{code}", row
        assert str(row["stayId"]) == stay_id
        assert str(row["roomId"]) == room_id
        assert row["reservationId"] is not None
        assert row["createdByType"] == "GUEST"
    finally:
        await conn.close()


async def prove_audit_and_history(stay_id: str, created_ids: list[str], completed_ids: list[str]):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        for task_id in created_ids:
            created = await conn.fetchval(
                '''SELECT count(*)::int FROM audit_logs WHERE action='CREATE_GUEST_REQUEST' AND resource='OperationalTask' AND "resourceId"=$1 AND source='GUEST_OS' AND result='SUCCESS' ''',
                task_id,
            )
            assert created == 1, (task_id, created)
        for task_id in completed_ids:
            completed = await conn.fetchval(
                '''SELECT count(*)::int FROM audit_logs WHERE action='COMPLETE_GUEST_REQUEST' AND resource='OperationalTask' AND "resourceId"=$1 AND result='SUCCESS' ''',
                task_id,
            )
            assert completed == 1, (task_id, completed)
        history_created = await conn.fetchval(
            '''SELECT count(*)::int FROM guest_history_events WHERE "stayId"=$1 AND "eventType"='GUEST_REQUEST_CREATED' ''',
            uuid.UUID(stay_id),
        )
        history_done = await conn.fetchval(
            '''SELECT count(*)::int FROM guest_history_events WHERE "stayId"=$1 AND "eventType"='GUEST_REQUEST_COMPLETED' ''',
            uuid.UUID(stay_id),
        )
        assert history_created >= len(created_ids)
        assert history_done >= len(completed_ids)
    finally:
        await conn.close()


def login_staff(username: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    response = client.post('/api/v1/auth/login', json={"username": username, "password": STAFF_PASSWORD})
    response.raise_for_status()
    return client


def main():
    today = asyncio.run(local_today())
    end = today + timedelta(days=3)
    owner = httpx.Client(base_url=BASE_URL, timeout=30.0, headers={"user-agent": "guest-requests-ci"})
    login = owner.post('/api/v1/auth/login', json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD})
    login.raise_for_status()

    grid = owner.get('/api/v1/pms/grid', params={"start": today.isoformat(), "end": end.isoformat()})
    grid.raise_for_status()
    chosen = None
    preview_body = None
    for room in grid.json()["rooms"]:
        preview = owner.post('/api/v1/admin/pms/reservations/new/preview', json={
            "room_id": room["id"], "check_in": today.isoformat(), "check_out": end.isoformat(), "adults": 1, "children": 0,
        })
        if preview.status_code == 200 and preview.json().get('can_commit'):
            chosen = room
            preview_body = preview.json()
            break
    assert chosen and preview_body, 'No sellable room for guest-request E2E'
    asyncio.run(set_room_clean(chosen['id']))

    issue = owner.post(f'/api/v1/admin/guest-os/room-qrs/{chosen["id"]}/issue')
    issue.raise_for_status()
    token = issue.json()['token']

    suffix = uuid.uuid4().hex[:8]
    commit = owner.post('/api/v1/admin/pms/reservations/new/commit', json={
        "room_id": chosen["id"],
        "check_in": today.isoformat(),
        "check_out": end.isoformat(),
        "adults": 1,
        "children": 0,
        "guest_name": "Guest Requests CI",
        "phone": "+996555" + suffix[:6],
        "email": f"guest-requests-{suffix}@example.com",
        "expected_total_kgs": preview_body['pricing']['total_kgs'],
        "expected_pricing_source": preview_body['pricing']['source'],
        "notes": "Guest request routing E2E",
    })
    commit.raise_for_status()
    reservation_id = commit.json()['reservation_id']
    assert commit.json()['payment_created'] is False

    check_in = owner.post(f'/api/v1/admin/stays/reservations/{reservation_id}/check-in')
    check_in.raise_for_status()
    stay_id = check_in.json()['stay_id']
    pin = check_in.json()['guest_access_pin']

    # Guest session is required. A photographed QR alone cannot create requests.
    unauth = httpx.Client(base_url=BASE_URL, timeout=30.0)
    denied = unauth.post(f'/api/v1/guest-os/rooms/{token}/requests', json={"request_code": "TOWELS"})
    assert denied.status_code == 401, denied.text
    unauth.close()

    verified = owner.post(f'/api/v1/guest-os/rooms/{token}/verify', json={"pin": pin})
    verified.raise_for_status()

    payments_before = asyncio.run(payment_count())
    initial_room_state = asyncio.run(room_state(chosen['id']))
    assert initial_room_state == 'CLEAN'

    towels = owner.post(f'/api/v1/guest-os/rooms/{token}/requests', json={
        "request_code": "TOWELS", "description": "2 больших полотенца",
    })
    towels.raise_for_status()
    towels_id = towels.json()['id']
    asyncio.run(prove_task(towels_id, code='TOWELS', stay_id=stay_id, room_id=chosen['id']))

    duplicate = owner.post(f'/api/v1/guest-os/rooms/{token}/requests', json={"request_code": "TOWELS", "description": "ещё раз"})
    assert duplicate.status_code == 409 and duplicate.json()['detail']['code'] == 'GUEST_REQUEST_DUPLICATE_ACTIVE'

    maintenance = owner.post(f'/api/v1/guest-os/rooms/{token}/requests', json={
        "request_code": "MAINTENANCE", "description": "Не работает лампа",
    })
    maintenance.raise_for_status()
    maintenance_id = maintenance.json()['id']
    asyncio.run(prove_task(maintenance_id, code='MAINTENANCE', stay_id=stay_id, room_id=chosen['id']))

    transfer = owner.post(f'/api/v1/guest-os/rooms/{token}/requests', json={
        "request_code": "TRANSFER", "description": "Нужен трансфер", "service_date": (today + timedelta(days=1)).isoformat(), "service_time": "12:30",
    })
    transfer.raise_for_status()
    transfer_id = transfer.json()['id']
    asyncio.run(prove_task(transfer_id, code='TRANSFER', stay_id=stay_id, room_id=chosen['id']))

    admin = owner.post(f'/api/v1/guest-os/rooms/{token}/requests', json={"request_code": "ADMIN", "description": "Перезвоните, пожалуйста"})
    admin.raise_for_status()
    admin_id = admin.json()['id']
    cancel = owner.post(f'/api/v1/guest-os/rooms/{token}/requests/{admin_id}/cancel')
    cancel.raise_for_status()
    assert cancel.json()['status'] == 'CANCELLED'

    # In-stay requests never mutate room readiness or accommodation payments automatically.
    assert asyncio.run(room_state(chosen['id'])) == initial_room_state
    assert asyncio.run(payment_count()) == payments_before

    maid_username = f"guest-requests-maid-{suffix}"
    tech_username = f"guest-requests-tech-{suffix}"
    asyncio.run(ensure_staff(maid_username, 'MAID'))
    asyncio.run(ensure_staff(tech_username, 'TECHNICIAN'))
    maid = login_staff(maid_username)
    tech = login_staff(tech_username)

    maid_queue = maid.get('/api/v1/ops/guest-requests')
    maid_queue.raise_for_status()
    maid_codes = {item['request_code'] for item in maid_queue.json()['items']}
    assert 'TOWELS' in maid_codes and 'MAINTENANCE' not in maid_codes and 'TRANSFER' not in maid_codes

    tech_queue = tech.get('/api/v1/ops/guest-requests')
    tech_queue.raise_for_status()
    tech_codes = {item['request_code'] for item in tech_queue.json()['items']}
    assert 'MAINTENANCE' in tech_codes and 'TOWELS' not in tech_codes

    wrong_role = maid.post(f'/api/v1/ops/guest-requests/{maintenance_id}/claim')
    assert wrong_role.status_code == 403

    maid_claim = maid.post(f'/api/v1/ops/guest-requests/{towels_id}/claim')
    maid_claim.raise_for_status()
    assert maid_claim.json()['status'] == 'IN_PROGRESS'
    maid_done = maid.post(f'/api/v1/ops/guest-requests/{towels_id}/complete')
    maid_done.raise_for_status()
    assert maid_done.json()['status'] == 'DONE'

    tech_claim = tech.post(f'/api/v1/ops/guest-requests/{maintenance_id}/claim')
    tech_claim.raise_for_status()
    tech_done = tech.post(f'/api/v1/ops/guest-requests/{maintenance_id}/complete')
    tech_done.raise_for_status()
    assert tech_done.json()['status'] == 'DONE'

    assert asyncio.run(room_state(chosen['id'])) == initial_room_state
    assert asyncio.run(payment_count()) == payments_before

    mine = owner.get(f'/api/v1/guest-os/rooms/{token}/requests')
    mine.raise_for_status()
    mine_items = {item['id']: item for item in mine.json()['items']}
    assert mine_items[towels_id]['status'] == 'DONE'
    assert mine_items[maintenance_id]['status'] == 'DONE'
    assert mine_items[transfer_id]['status'] == 'OPEN'
    assert mine_items[admin_id]['status'] == 'CANCELLED'
    raw = str(mine.json()).lower()
    assert 'phone' not in raw and 'email' not in raw and 'passport' not in raw

    manager_queue = owner.get('/api/v1/admin/guest-services', params={"status": "ACTIVE"})
    manager_queue.raise_for_status()
    active_ids = {item['id'] for item in manager_queue.json()['items']}
    assert transfer_id in active_ids

    asyncio.run(prove_audit_and_history(stay_id, [towels_id, maintenance_id, transfer_id, admin_id], [towels_id, maintenance_id]))

    maid.close()
    tech.close()
    owner.close()
    print('GUEST_OS_REQUESTS_E2E_OK')


if __name__ == '__main__':
    main()
