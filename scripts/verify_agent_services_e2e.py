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
            payload = {'reservation_id': str(own_rid), 'service_code': 'TRANSFER',
                       'service_date': today.isoformat(), 'service_time': '10:30', 'description': 'Meet at reception'}
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
            scoped = {'reservation_id': str(own_rid), 'status': 'ALL'}
            first = checked(await client.get(path, params=scoped), 200)
            assert first['items'][0]['id'] == result['id'] and first['items'][0]['status'] == 'OPEN'
            assert first['items'][0]['service_date'] == today.isoformat()
            assert first['items'][0]['service_time'] == '10:30'
            assert first['items'][0]['description'] == 'Meet at reception'
            assert 'guest_phone' not in first['items'][0] and 'assigned_to_id' not in first['items'][0]
            checked(await client.get(path, params={'reservation_id': str(other_rid)}), 404)
            checked(await client.post(path, json={**payload, 'service_date': (today + timedelta(days=3)).isoformat()}), 422)
            # Staff processes the SAME canonical task through existing Web APIs;
            # agent then reads back its actual status, without a local replica.
            async with httpx.AsyncClient(base_url=base, timeout=30) as owner:
                response = await owner.post('/api/v1/auth/login', json={
                    'username': os.environ['BOOTSTRAP_OWNER_USERNAME'], 'password': os.environ['BOOTSTRAP_OWNER_PASSWORD']})
                checked(response, 200)
                owner.headers['Cookie'] = '; '.join(f'{k}={v}' for k, v in response.cookies.items())
                ops = '/api/v1/ops/guest-requests/' + result['id']
                checked(await owner.post(ops + '/claim'), 200)
                middle = checked(await client.get(path, params=scoped), 200)
                assert middle['items'][0]['status'] == 'IN_PROGRESS'
                checked(await owner.post(ops + '/complete'), 200)
                final = checked(await client.get(path, params=scoped), 200)
                assert final['items'][0]['status'] == 'DONE'
                assert await conn.fetchval('SELECT status::text FROM operational_tasks WHERE id=$1', uuid.UUID(result['id'])) == 'DONE'

            await conn.execute('UPDATE booking_agents SET status=\'INACTIVE\' WHERE id=$1', agent)
            checked(await client.post(path, json={**payload, 'service_code': 'MEALS'}), 403)
            checked(await client.get(path, params=scoped), 403)
            assert await conn.fetchval('SELECT count(*) FROM operational_tasks WHERE "reservationId"=$1', other_rid) == 0
            assert await conn.fetchval('SELECT count(*) FROM operational_tasks WHERE "reservationId"=$1', own_rid) == 1
            assert await conn.fetchval('SELECT count(*) FROM payments') == payment_count
        print('AGENT SERVICES POSTGRES PASS: own scheduled task persisted; staff claim/complete -> agent OPEN/IN_PROGRESS/DONE readback; duplicate 409; other agent 404; queue/priority/operational-service/revoked link 403; no Payment')
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
