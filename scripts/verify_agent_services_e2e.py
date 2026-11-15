"""Disposable localhost PostgreSQL + API only: own-agent service write boundaries."""
import asyncio
import os
import secrets
import uuid
from datetime import timedelta
from urllib.parse import urlparse

import asyncpg
import httpx
from argon2 import PasswordHasher


def checked(response, expected):
    assert response.status_code == expected, (expected, response.status_code, response.text)
    return response.json()


async def main():
    if os.environ.get('ALLOW_AGENT_SERVICE_TEST_WRITES') != '1':
        raise RuntimeError('Disposable CI database opt-in required')
    url = os.environ['DATABASE_URL'].split('?', 1)[0]
    base = os.environ.get('CORE_API_URL', 'http://127.0.0.1:8000')
    if urlparse(url).hostname not in {'localhost', '127.0.0.1'} or urlparse(base).hostname != '127.0.0.1':
        raise RuntimeError('Only local disposable test targets are supported')
    conn = await asyncpg.connect(url)
    try:
        pid = await conn.fetchval('SELECT id FROM properties WHERE code=$1', os.environ.get('PROPERTY_CODE', 'THREE_CROWNS'))
        assert pid
        today = await conn.fetchval('SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE id=$1', pid)
        suffix = uuid.uuid4().hex
        agent, other, staff, guest = [uuid.uuid4() for _ in range(4)]
        password = secrets.token_urlsafe(24)
        for aid in (agent, other):
            await conn.execute('''INSERT INTO booking_agents (id,"propertyId",name,status,"createdAt","updatedAt")
                VALUES ($1,$2,$3,'ACTIVE',now(),now())''', aid, pid, 'CI-AGENT-' + str(aid))
        await conn.execute('''INSERT INTO staff_users
            (id,"propertyId",username,"displayName","passwordHash",role,"bookingAgentId","isActive","createdAt","updatedAt")
            VALUES ($1,$2,$3,'CI services agent',$4,'AGENT',$5,true,now(),now())''',
            staff, pid, 'ci-agent-' + suffix, PasswordHasher().hash(password), agent)
        await conn.execute('''INSERT INTO guests (id,"propertyId","firstName",phone,"createdAt","updatedAt")
            VALUES ($1,$2,'Synthetic agent guest','+996555000000',now(),now())''', guest, pid)
        own_rid, other_rid = uuid.uuid4(), uuid.uuid4()
        for rid, aid in [(own_rid, agent), (other_rid, other)]:
            await conn.execute('''INSERT INTO reservations
                (id,"propertyId","bookingNumber","primaryGuestId",status,"checkIn","checkOut",adults,children,"totalKgs","agentId","createdAt","updatedAt")
                VALUES ($1,$2,$3,$4,'GUARANTEED',$5,$6,1,0,1000,$7,now(),now())''',
                rid, pid, 'CI-AS-' + str(rid), guest, today, today + timedelta(days=2), aid)
        payment_count = await conn.fetchval('SELECT count(*) FROM payments')
        path = '/api/v1/admin/guest-services'
        async with httpx.AsyncClient(base_url=base, timeout=30) as client:
            login = await client.post('/api/v1/auth/login', json={'username': 'ci-agent-' + suffix, 'password': password})
            checked(login, 200)
            client.headers['Cookie'] = '; '.join(f'{k}={v}' for k, v in login.cookies.items())
            me = checked(await client.get('/api/v1/auth/me'), 200)
            assert me['role'] == 'AGENT' and 'PMS' in me['module_permissions']
            payload = {'reservation_id': str(own_rid), 'service_code': 'TRANSFER'}
            result = checked(await client.post(path, json=payload), 201)
            row = await conn.fetchrow('SELECT "propertyId","reservationId","serviceCode","createdById" FROM operational_tasks WHERE id=$1', uuid.UUID(result['id']))
            assert row['propertyId'] == pid and row['reservationId'] == own_rid
            assert row['serviceCode'] == 'TRANSFER' and row['createdById'] == str(staff)
            checked(await client.post(path, json=payload), 409)
            checked(await client.post(path, json={**payload, 'reservation_id': str(other_rid)}), 404)
            checked(await client.post(path, json={**payload, 'reservation_id': str(uuid.uuid4())}), 404)
            checked(await client.post(path, json={**payload, 'service_code': 'TOWELS'}), 403)
            checked(await client.post(path, json={**payload, 'priority': 'URGENT'}), 403)
            checked(await client.get(path), 403)
            await conn.execute('UPDATE booking_agents SET status=\'INACTIVE\' WHERE id=$1', agent)
            checked(await client.post(path, json={**payload, 'service_code': 'MEALS'}), 403)
            assert await conn.fetchval('SELECT count(*) FROM operational_tasks WHERE "reservationId"=$1', other_rid) == 0
            assert await conn.fetchval('SELECT count(*) FROM operational_tasks WHERE "reservationId"=$1', own_rid) == 1
            assert await conn.fetchval('SELECT count(*) FROM payments') == payment_count
        print('AGENT SERVICES POSTGRES PASS: own task persisted; duplicate 409; other agent 404; queue/priority/operational-service/revoked link 403; no Payment')
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
