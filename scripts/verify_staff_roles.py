#!/usr/bin/env python3
import asyncio
import os
import uuid

import asyncpg
import httpx
from argon2 import PasswordHasher

BASE_URL = os.environ.get("RESORT_CORE_TEST_URL", "http://127.0.0.1:8000")
DATABASE_URL = os.environ["DATABASE_URL"].split("?")[0]
PASSWORD = "Staff-Roles-CI-Password-2026"
password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


async def property_id():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval("SELECT id FROM properties WHERE code='THREE_CROWNS'")
    finally:
        await conn.close()


async def ensure_user(username: str, role: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        pid = await conn.fetchval("SELECT id FROM properties WHERE code='THREE_CROWNS'")
        assert pid
        user_id = await conn.fetchval('SELECT id FROM staff_users WHERE "propertyId"=$1 AND username=$2', pid, username)
        hashed = password_hasher.hash(PASSWORD)
        if user_id:
            await conn.execute(
                '''UPDATE staff_users SET "displayName"=$1,"passwordHash"=$2,role=$3::"StaffRole","isActive"=true,"updatedAt"=now() WHERE id=$4''',
                f"CI {role}", hashed, role, user_id,
            )
            return str(user_id)
        user_id = uuid.uuid4()
        await conn.execute(
            '''INSERT INTO staff_users (id,"propertyId",username,"displayName","passwordHash",role,"isActive","createdAt","updatedAt")
               VALUES ($1,$2,$3,$4,$5,$6::"StaffRole",true,now(),now())''',
            user_id, pid, username, f"CI {role}", hashed, role,
        )
        return str(user_id)
    finally:
        await conn.close()


async def seed_requests():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        pid = await conn.fetchval("SELECT id FROM properties WHERE code='THREE_CROWNS'")
        assert pid
        rows = []
        for code, title in [("TRANSFER", "CI трансфер"), ("MEALS", "CI питание"), ("TOWELS", "CI полотенца")]:
            task_id = uuid.uuid4()
            await conn.execute(
                '''INSERT INTO operational_tasks (
                     id,"propertyId",type,status,priority,title,"serviceCode","createdByType",source,"createdAt","updatedAt"
                   ) VALUES ($1,$2,'GUEST_REQUEST','OPEN','NORMAL',$3,$4,'GUEST',$5,now(),now())''',
                task_id, pid, title, code, f"GUEST_OS_{code}",
            )
            rows.append((code, str(task_id)))
        return dict(rows)
    finally:
        await conn.close()


async def audit_count(action: str, resource_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval(
            '''SELECT count(*)::int FROM audit_logs WHERE action=$1 AND resource='OperationalTask' AND "resourceId"=$2 AND result='SUCCESS' ''',
            action, resource_id,
        )
    finally:
        await conn.close()


def login(username: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    response = client.post('/api/v1/auth/login', json={"username": username, "password": PASSWORD})
    response.raise_for_status()
    assert response.json()['role']
    me = client.get('/api/v1/auth/me')
    me.raise_for_status()
    assert me.json()['username'] == username
    return client


def queue_codes(client: httpx.Client) -> set[str]:
    response = client.get('/api/v1/ops/guest-requests?status=ACTIVE&limit=100')
    response.raise_for_status()
    return {item['request_code'] for item in response.json()['items']}


def main():
    suffix = uuid.uuid4().hex[:8]
    reception_name = f"staff-ci-reception-{suffix}"
    dining_name = f"staff-ci-dining-{suffix}"
    store_name = f"staff-ci-store-{suffix}"
    maid_name = f"staff-ci-maid-{suffix}"
    asyncio.run(ensure_user(reception_name, 'RECEPTION'))
    asyncio.run(ensure_user(dining_name, 'DINING_STAFF'))
    asyncio.run(ensure_user(store_name, 'STORE_STAFF'))
    asyncio.run(ensure_user(maid_name, 'MAID'))
    requests = asyncio.run(seed_requests())

    reception = login(reception_name)
    dining = login(dining_name)
    store = login(store_name)
    maid = login(maid_name)

    reception_codes = queue_codes(reception)
    assert 'TRANSFER' in reception_codes
    assert 'MEALS' not in reception_codes
    assert 'TOWELS' not in reception_codes

    dining_codes = queue_codes(dining)
    assert 'MEALS' in dining_codes
    assert 'TRANSFER' not in dining_codes
    assert 'TOWELS' not in dining_codes

    maid_codes = queue_codes(maid)
    assert 'TOWELS' in maid_codes
    assert 'MEALS' not in maid_codes
    assert 'TRANSFER' not in maid_codes

    store_queue = store.get('/api/v1/ops/guest-requests')
    assert store_queue.status_code == 403, store_queue.text

    wrong = dining.post(f"/api/v1/ops/guest-requests/{requests['TRANSFER']}/claim")
    assert wrong.status_code == 403, wrong.text

    claim = reception.post(f"/api/v1/ops/guest-requests/{requests['TRANSFER']}/claim")
    claim.raise_for_status()
    assert claim.json()['status'] == 'IN_PROGRESS'
    done = reception.post(f"/api/v1/ops/guest-requests/{requests['TRANSFER']}/complete")
    done.raise_for_status()
    assert done.json()['status'] == 'DONE'
    assert asyncio.run(audit_count('CLAIM_GUEST_REQUEST', requests['TRANSFER'])) == 1
    assert asyncio.run(audit_count('COMPLETE_GUEST_REQUEST', requests['TRANSFER'])) == 1

    claim_meal = dining.post(f"/api/v1/ops/guest-requests/{requests['MEALS']}/claim")
    claim_meal.raise_for_status()
    done_meal = dining.post(f"/api/v1/ops/guest-requests/{requests['MEALS']}/complete")
    done_meal.raise_for_status()

    for client in (reception, dining, store, maid):
        logout = client.post('/api/v1/auth/logout')
        assert logout.status_code == 204
        client.close()

    print('STAFF_ROLES_E2E_OK')


if __name__ == '__main__':
    main()
