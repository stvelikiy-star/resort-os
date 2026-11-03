"""Real PostgreSQL + HTTP acceptance for the isolated shared-auth CI database."""
import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import secrets
import sys
import time
from urllib.parse import urlsplit
import uuid
from unittest.mock import patch

import asyncpg
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/api'))
from app import auth
from app import guest_os
from app import realtime, dining_realtime, websocket_security
from app.shared_auth_preview import SharedAuthPreviewBoundary
from app.health import router as health_router


def main():
    dsn = os.environ.get('DATABASE_URL', '').split('?', 1)[0]
    target = urlsplit(dsn)
    assert os.environ.get('MARINA_SHARED_AUTH_CI_CONFIRM') == 'ISOLATED_SHARED_AUTH_CI_ONLY'
    assert target.hostname in {'localhost', '127.0.0.1'} and target.path == '/marina_shared_auth_ci'
    assert auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED and auth.MARINA_TENANT_CONTEXT_ENABLED
    auth.shared_auth_preview_guard()
    ids = {name: uuid.uuid4() for name in ('tenant_a','tenant_b','property_a','property_b',
                                         'user_a','user_b','type_a','type_b','room_a','room_b')}
    passwords = {suffix: secrets.token_urlsafe(24) for suffix in ('a','b')}

    async def seed():
        conn = await asyncpg.connect(dsn)
        try:
            assert await conn.fetchval('SELECT count(*) FROM properties') == 0, 'CI database must be empty'
            async with conn.transaction():
                for suffix in ('a','b'):
                    await conn.execute('''INSERT INTO tenants (id,code,name,status,"updatedAt")
                        VALUES ($1,$2,$3,'ACTIVE',now())''', ids['tenant_'+suffix], 'tenant_'+suffix, 'Synthetic '+suffix)
                    await conn.execute('''INSERT INTO properties (id,code,name,timezone,currency,"updatedAt","tenantId")
                        VALUES ($1,$2,$3,'Asia/Bishkek','KGS',now(),$4)''', ids['property_'+suffix], 'HOTEL_'+suffix.upper(), 'Synthetic '+suffix, ids['tenant_'+suffix])
                    await conn.execute('''INSERT INTO staff_users
                        (id,"propertyId",username,"displayName","passwordHash",role,"isActive","updatedAt")
                        VALUES ($1,$2,'owner',$3,$4,'OWNER',true,now())''', ids['user_'+suffix], ids['property_'+suffix], 'Synthetic owner '+suffix, auth.password_hasher.hash(passwords[suffix]))
                    await conn.execute('''INSERT INTO room_types
                        (id,"propertyId",code,name,"capacityAdults","updatedAt")
                        VALUES ($1,$2,'STANDARD','Synthetic standard',2,now())''',
                        ids['type_'+suffix], ids['property_'+suffix])
                    await conn.execute('''INSERT INTO rooms
                        (id,"propertyId","roomTypeId",code,name,"updatedAt")
                        VALUES ($1,$2,$3,'101','Synthetic room',now())''',
                        ids['room_'+suffix], ids['property_'+suffix], ids['type_'+suffix])
        finally:
            await conn.close()
    asyncio.run(seed())

    @asynccontextmanager
    async def lifespan(app):
        app.state.db = await asyncpg.create_pool(dsn, min_size=1, max_size=4)
        try: yield
        finally: await app.state.db.close()
    app = FastAPI(lifespan=lifespan)
    app.add_middleware(SharedAuthPreviewBoundary)
    app.include_router(auth.router)
    app.include_router(health_router)

    def execute(sql, *args):
        async def run():
            conn = await asyncpg.connect(dsn)
            try: return await conn.execute(sql, *args)
            finally: await conn.close()
        return asyncio.run(run())

    with TestClient(app, base_url='https://shared-auth.test') as client:
        readiness = client.get('/health/ready')
        assert readiness.status_code == 200 and readiness.json()['mode'] == 'shared_auth_preview'
        def login(suffix, password=None, tenant=None):
            return client.post('/api/v1/auth/login', json=dict(username='owner',
                password=password or passwords[suffix], tenant_code=tenant or 'tenant_'+suffix,
                property_code='HOTEL_'+suffix.upper()))
        tokens = {}
        for suffix in ('a','b'):
            response = login(suffix)
            assert response.status_code == 200, response.text
            assert response.json()['property_id'] == str(ids['property_'+suffix])
            assert response.json()['tenant_id'] == str(ids['tenant_'+suffix])
            tokens[suffix] = client.cookies.get(auth.SESSION_COOKIE)
        def me(suffix, token=None):
            return client.get('/api/v1/auth/me', headers={
                'Cookie':auth.SESSION_COOKIE+'='+(token or tokens[suffix]),
                'X-Tenant-Id':str(ids['tenant_b']), 'X-Property-Id':str(ids['property_b']),
                'X-Role':'OWNER'})
        assert me('a').json()['property_code'] == 'HOTEL_A'
        assert me('b').json()['property_code'] == 'HOTEL_B'
        assert login('b', password=passwords['a']).status_code == 401
        assert login('a', tenant='missing').status_code == 401
        parts = tokens['a'].split('.'); parts[2] = str(ids['property_b'])
        assert me('a', token='.'.join(parts)).status_code == 401
        execute("UPDATE tenants SET status='BLOCKED' WHERE id=$1", ids['tenant_a'])
        assert me('a').status_code == 401 and me('b').status_code == 200
        execute("UPDATE tenants SET status='ACTIVE' WHERE id=$1", ids['tenant_a'])
        execute('UPDATE staff_users SET "propertyId"=$1,username=\'moved_owner\' WHERE id=$2', ids['property_b'], ids['user_a'])
        assert me('a').status_code == 401, 'A session must not follow a transferred user'
        execute('UPDATE staff_users SET "isActive"=false WHERE id=$1', ids['user_b'])
        assert me('b').status_code == 401
        execute('UPDATE staff_users SET "isActive"=true WHERE id=$1', ids['user_b'])
        assert client.get('/api/v1/admin/staff').status_code == 503
        assert client.post('/api/v1/reservations',json={}).status_code == 503
        assert client.post('/api/v1/auth/logout',headers={'Cookie':auth.SESSION_COOKIE+'='+tokens['b']}).status_code == 204
        assert me('b').status_code == 401
    print('PASS: PostgreSQL shared login, same usernames, tenant/session isolation, tampering, revocation and closed workspace boundary')

    # Canonical boundary: one deliberately reviewed tenant-scoped read-only cabinet.
    # All other operational routes remain closed until separately accepted.
    execute('UPDATE staff_users SET "propertyId"=$1,username=\'owner\' WHERE id=$2',
            ids['property_a'], ids['user_a'])
    from app.manager_dashboard import router as manager_dashboard_router
    dash_app = FastAPI(lifespan=lifespan)
    dash_app.add_middleware(SharedAuthPreviewBoundary)
    dash_app.include_router(auth.router)
    dash_app.include_router(manager_dashboard_router)
    with TestClient(dash_app, base_url='https://shared-auth.test') as dash_client:
        for suffix, foreign in (('a','b'), ('b','a')):
            signed_in = dash_client.post('/api/v1/auth/login', json=dict(
                username='owner', password=passwords[suffix], tenant_code='tenant_'+suffix,
                property_code='HOTEL_'+suffix.upper()))
            assert signed_in.status_code == 200, 'Shared dashboard sign-in failed'
            forged = {'X-Property-Id': str(ids['property_'+foreign]),
                      'X-Tenant-Id': str(ids['tenant_'+foreign]), 'X-Role': 'OWNER'}
            dashboard = dash_client.get('/api/v1/admin/dashboard', headers=forged)
            assert dashboard.status_code == 200, dashboard.text
            data = dashboard.json()
            assert data['property']['code'] == 'HOTEL_'+suffix.upper()
            assert data['rooms']['total'] == 1, 'Dashboard leaked or lost hotel room inventory'
            assert dash_client.get('/api/v1/admin/staff', headers=forged).status_code == 503
        execute("UPDATE staff_users SET role='WAITER' WHERE id=$1", ids['user_b'])
        assert dash_client.get('/api/v1/admin/dashboard').status_code == 403
        execute("UPDATE tenants SET status='BLOCKED' WHERE id=$1", ids['tenant_b'])
        assert dash_client.get('/api/v1/admin/dashboard').status_code == 401
        execute("UPDATE tenants SET status='ACTIVE' WHERE id=$1", ids['tenant_b'])
        execute("UPDATE staff_users SET role='OWNER' WHERE id=$1", ids['user_b'])
    print('PASS: isolated dashboard test harness, not yet canonical app')

    # Acceptance must use the real ASGI application composition, not a test router.
    from app.app_entry import app as canonical_app
    with TestClient(canonical_app, base_url='https://shared-auth.test') as canonical_client:
        for suffix, foreign in (('a', 'b'), ('b', 'a')):
            signin = canonical_client.post('/api/v1/auth/login', json=dict(
                username='owner', password=passwords[suffix],
                tenant_code='tenant_'+suffix, property_code='HOTEL_'+suffix.upper()))
            assert signin.status_code == 200, signin.text
            response = canonical_client.get('/api/v1/admin/dashboard', headers={
                'X-Property-Id': str(ids['property_'+foreign]),
                'X-Tenant-Id': str(ids['tenant_'+foreign]), 'X-Role': 'OWNER'})
            assert response.status_code == 200, response.text
            result = response.json()
            assert result['property']['code'] == 'HOTEL_'+suffix.upper()
            assert result['rooms']['total'] == 1
            assert canonical_client.get('/api/v1/admin/staff').status_code == 503
            grid = canonical_client.get('/api/v1/pms/grid?start=2026-11-04&end=2026-11-05', headers={
                'X-Property-Id': str(ids['property_'+foreign]), 'X-Tenant-Id': str(ids['tenant_'+foreign])})
            assert grid.status_code == 200, grid.text
            assert grid.json()['property'] == 'HOTEL_'+suffix.upper()
            assert [room['id'] for room in grid.json()['rooms']] == [str(ids['room_'+suffix])]
        execute("UPDATE staff_users SET role='WAITER' WHERE id=$1", ids['user_b'])
        assert canonical_client.get('/api/v1/pms/grid?start=2026-11-04&end=2026-11-05').status_code == 403
        execute("UPDATE staff_users SET role='OWNER' WHERE id=$1", ids['user_b'])
        execute("UPDATE tenants SET status='BLOCKED' WHERE id=$1", ids['tenant_b'])
        assert canonical_client.get('/api/v1/pms/grid?start=2026-11-04&end=2026-11-05').status_code == 401
        execute("UPDATE tenants SET status='ACTIVE' WHERE id=$1", ids['tenant_b'])
        # Owner-managed staff lifecycle in the REAL assembled ASGI app and isolated PostgreSQL.
        # Both hotels use the same username; scoped identity is resolved server-side.
        staff_username = 'synthetic-worker'
        staff_password_a = 'WorkerA-'+secrets.token_urlsafe(20)
        staff_password_b = 'WorkerB-'+secrets.token_urlsafe(20)
        def owner_login(suffix):
            res = canonical_client.post('/api/v1/auth/login', json=dict(
                username='owner', password=passwords[suffix],
                tenant_code='tenant_'+suffix, property_code='HOTEL_'+suffix.upper()))
            assert res.status_code == 200, res.text

        owner_login('a')
        a_overview = canonical_client.get('/api/v1/admin/staff/overview')
        assert a_overview.status_code == 200, a_overview.text
        assert {row['id'] for row in a_overview.json()['staff']} == {str(ids['user_a'])}
        worker_a = canonical_client.post('/api/v1/admin/staff', json=dict(
            username=staff_username, display_name='Synthetic Worker A',
            password=staff_password_a, role='MAID'))
        assert worker_a.status_code == 201, worker_a.text
        worker_a_id = worker_a.json()['id']
        assert canonical_client.post('/api/v1/admin/staff', json=dict(
            username=staff_username, display_name='Duplicate A',
            password=staff_password_a, role='MAID')).status_code == 409
        assert worker_a_id in {row['id'] for row in canonical_client.get('/api/v1/admin/staff/overview').json()['staff']}

        owner_login('b')
        b_overview = canonical_client.get('/api/v1/admin/staff/overview')
        assert b_overview.status_code == 200, b_overview.text
        assert {row['id'] for row in b_overview.json()['staff']} == {str(ids['user_b'])}
        worker_b = canonical_client.post('/api/v1/admin/staff', json=dict(
            username=staff_username, display_name='Synthetic Worker B',
            password=staff_password_b, role='MAID'))
        assert worker_b.status_code == 201, worker_b.text
        worker_b_id = worker_b.json()['id']
        assert worker_a_id != worker_b_id
        assert canonical_client.patch('/api/v1/admin/staff/'+worker_a_id,
                                      json={'active': False}).status_code == 404
        assert canonical_client.patch('/api/v1/admin/staff/'+str(ids['user_b']),
                                      json={'active': False}).status_code == 403

        owner_login('a')
        assert canonical_client.patch('/api/v1/admin/staff/'+worker_b_id,
                                      json={'active': False}).status_code == 404
        assert canonical_client.post('/api/v1/auth/login', json=dict(
            username=staff_username, password=staff_password_b,
            tenant_code='tenant_a', property_code='HOTEL_A')).status_code == 401
        maid_login = canonical_client.post('/api/v1/auth/login', json=dict(
            username=staff_username, password=staff_password_a,
            tenant_code='tenant_a', property_code='HOTEL_A'))
        assert maid_login.status_code == 200, maid_login.text
        maid_token = canonical_client.cookies.get(auth.SESSION_COOKIE)
        assert canonical_client.get('/api/v1/admin/staff/overview').status_code == 403
        assert canonical_client.post('/api/v1/admin/staff', json=dict(
            username='forbidden-staff', display_name='Forbidden Staff',
            password=staff_password_a, role='MAID')).status_code == 403
        assert canonical_client.patch('/api/v1/admin/staff/'+worker_a_id,
                                      json={'active': False}).status_code == 403
        owner_login('a')
        changed = canonical_client.patch('/api/v1/admin/staff/'+worker_a_id,
                                         json={'role':'TECHNICIAN','module_permissions':['OPS']})
        assert changed.status_code == 200 and changed.json()['role'] == 'TECHNICIAN', changed.text
        revoked = canonical_client.get('/api/v1/auth/me', headers={
            'Cookie': auth.SESSION_COOKIE+'='+maid_token})
        assert revoked.status_code == 401, 'Old staff session survived a permission change'
        disabled = canonical_client.patch('/api/v1/admin/staff/'+worker_a_id, json={'active':False})
        assert disabled.status_code == 200 and disabled.json()['active'] is False
        assert canonical_client.post('/api/v1/auth/login', json=dict(
            username=staff_username, password=staff_password_a,
            tenant_code='tenant_a', property_code='HOTEL_A')).status_code == 401

        # A has no authority over B's same-username worker, even after A revocation.
        worker_b_login = canonical_client.post('/api/v1/auth/login', json=dict(
            username=staff_username, password=staff_password_b,
            tenant_code='tenant_b', property_code='HOTEL_B'))
        assert worker_b_login.status_code == 200, worker_b_login.text
        assert canonical_client.get('/api/v1/auth/me').json()['property_code'] == 'HOTEL_B'
        owner_login('a')
        manager = canonical_client.post('/api/v1/admin/staff', json=dict(
            username='synthetic-manager', display_name='Synthetic Manager A',
            password='ManagerA-'+secrets.token_urlsafe(20), role='MANAGER'))
        assert manager.status_code == 201, manager.text
        manager_id = manager.json()['id']
        assert canonical_client.patch('/api/v1/admin/staff/'+manager_id,
                                      json={'module_permissions':['STAFF']}).status_code == 200
        # Unreviewed operations remain blocked by the canonical boundary.
        assert canonical_client.put('/api/v1/admin/staff').status_code == 503
        assert canonical_client.delete('/api/v1/admin/staff/'+manager_id).status_code == 503
        assert canonical_client.post('/api/v1/reservations', json={}).status_code == 503
    print('PASS: canonical shared staff lifecycle: same usernames isolated, owner-only writes, cross-hotel 404, old session revocation, disabled login denial')

    # Exercise only the reviewed QR handlers in a test harness with the real
    # shared auth and one pool. The canonical application's preview boundary
    # above remains closed; this is not a general shared-workspace rollout.
    execute('UPDATE staff_users SET "propertyId"=$1,username=\'owner\' WHERE id=$2',
            ids['property_a'], ids['user_a'])
    qr_app = FastAPI(lifespan=lifespan)
    qr_app.include_router(auth.router)
    qr_app.include_router(guest_os.admin_router)
    with TestClient(qr_app, base_url='https://shared-auth.test') as qr_client:
        for suffix, foreign in (('a','b'), ('b','a')):
            result = qr_client.post('/api/v1/auth/login', json=dict(
                username='owner', password=passwords[suffix], tenant_code='tenant_'+suffix,
                property_code='HOTEL_'+suffix.upper()))
            assert result.status_code == 200, 'Shared QR owner sign-in failed'
            forged = {'X-Tenant-Id': str(ids['tenant_'+foreign]),
                      'X-Property-Id': str(ids['property_'+foreign])}
            listed = qr_client.get('/api/v1/admin/guest-os/room-qrs', headers=forged)
            assert listed.status_code == 200
            assert listed.json()['property'] == 'HOTEL_'+suffix.upper()
            assert [r['room_id'] for r in listed.json()['items']] == [str(ids['room_'+suffix])]
            for action in ('issue','rotate'):
                denied = qr_client.post(
                    f"/api/v1/admin/guest-os/room-qrs/{ids['room_'+foreign]}/{action}", headers=forged)
                assert denied.status_code == 404, 'Foreign room QR mutation must be denied'
            own = qr_client.post(f"/api/v1/admin/guest-os/room-qrs/{ids['room_'+suffix]}/issue")
            assert own.status_code == 201, 'Own room QR issue failed'
            rotated = qr_client.post(f"/api/v1/admin/guest-os/room-qrs/{ids['room_'+suffix]}/rotate")
            assert rotated.status_code == 201 and rotated.json()['qr_id'] != own.json()['qr_id']
            batch = qr_client.post('/api/v1/admin/guest-os/room-qrs/issue-missing', json={})
            assert batch.status_code == 201 and batch.json()['issued_count'] == 0
        execute("UPDATE tenants SET status='BLOCKED' WHERE id=$1", ids['tenant_b'])
        assert qr_client.get('/api/v1/admin/guest-os/room-qrs').status_code == 401
    print('PASS: single test runtime + PostgreSQL: two-hotel QR list/issue/rotate/batch, foreign IDs/headers and blocked tenant denial; canonical preview remains closed')

    # Test only the reviewed socket routers with real shared sessions and one
    # PostgreSQL pool. Do not open canonical shared-preview routes here.
    execute("UPDATE tenants SET status='ACTIVE' WHERE id=$1", ids['tenant_b'])
    orders = {key: uuid.uuid4() for key in ('a','b','unassigned_a','unassigned_b')}
    for suffix in ('a','b'):
        for key, waiter in ((suffix, ids['user_'+suffix]), ('unassigned_'+suffix, None)):
            execute('''INSERT INTO kitchen_orders
                (id,"propertyId","orderNumber",status,source,"waiterId","totalKgs","readyAt")
                VALUES ($1,$2,$3,'READY','MANAGER',$4,100,now())''',
                orders[key], ids['property_'+suffix], 'WS-'+key, waiter)
    ws_app = FastAPI(lifespan=lifespan)
    ws_app.include_router(auth.router)
    ws_app.include_router(realtime.router)
    ws_app.include_router(dining_realtime.router)
    with patch.object(realtime, 'POLL_SECONDS', 0.25), \
            patch.object(dining_realtime, 'POLL_SECONDS', 0.25), \
            patch.object(websocket_security, 'WS_ENFORCE_SAME_ORIGIN', True), \
            TestClient(ws_app, base_url='https://shared-auth.test') as ws_client:
        def login_ws(suffix):
            result = ws_client.post('/api/v1/auth/login', json=dict(
                username='owner', password=passwords[suffix], tenant_code='tenant_'+suffix,
                property_code='HOTEL_'+suffix.upper()))
            assert result.status_code == 200, 'Shared realtime sign-in failed'
            return ws_client.cookies.get(auth.SESSION_COOKIE)

        def socket_headers(token):
            return {'Cookie':auth.SESSION_COOKIE+'='+token, 'Origin':'https://shared-auth.test',
                    'X-Property-Id':str(ids['property_b']), 'X-Tenant-Id':str(ids['tenant_b'])}

        def expect_close(ws, code):
            try:
                ws.receive_json()
            except WebSocketDisconnect as error:
                assert error.code == code, 'Wrong realtime denial code'
            else:
                raise AssertionError('Unauthorized frame delivered after permission recheck')

        for suffix in ('a','b'):
            token = login_ws(suffix)
            with ws_client.websocket_connect('wss://shared-auth.test/ws/pms/grid', headers=socket_headers(token)) as ws:
                message = ws.receive_json()
                assert message['data']['property'] == 'HOTEL_'+suffix.upper()
                assert [r['id'] for r in message['data']['rooms']] == [str(ids['room_'+suffix])]
                deadline = time.monotonic() + 2
                while ws_app.state.db.get_idle_size() != ws_app.state.db.get_size() and time.monotonic() < deadline:
                    time.sleep(0.01)
                assert ws_app.state.db.get_idle_size() == ws_app.state.db.get_size(), 'Socket pinned a DB connection'
            with ws_client.websocket_connect('wss://shared-auth.test/ws/dining/ready', headers=socket_headers(token)) as ws:
                message = ws.receive_json()
                assert {o['id'] for o in message['orders']} == {str(orders[suffix]), str(orders['unassigned_'+suffix])}
                assert message['scope'] == 'ALL'

        # Update grants without revoking the session so this proves periodic
        # authorization, independently of the staff API's session revocation.
        execute("UPDATE staff_users SET role='MANAGER' WHERE id=$1", ids['user_a'])
        for path in ('/ws/pms/grid','/ws/dining/ready'):
            for revoke_session in (False, True):
                execute('UPDATE staff_users SET "modulePermissions"=$1::jsonb WHERE id=$2',
                        '["PMS","DINING"]', ids['user_a'])
                token = login_ws('a')
                with ws_client.websocket_connect('wss://shared-auth.test'+path, headers=socket_headers(token)) as ws:
                    ws.receive_json()
                    if revoke_session:
                        execute('UPDATE auth_sessions SET "revokedAt"=now() WHERE "tokenHash"=$1',
                                auth.hash_session_token(token))
                    else:
                        execute('UPDATE staff_users SET "modulePermissions"=$1::jsonb WHERE id=$2', '[]', ids['user_a'])
                    expect_close(ws, 4401 if revoke_session else 4403)

        execute('UPDATE staff_users SET role=\'WAITER\',"modulePermissions"=NULL WHERE id=$1', ids['user_a'])
        token = login_ws('a')
        with ws_client.websocket_connect('wss://shared-auth.test/ws/dining/ready', headers=socket_headers(token)) as ws:
            message = ws.receive_json()
            assert message['scope'] == 'ASSIGNED_TO_ME'
            assert [o['id'] for o in message['orders']] == [str(orders['a'])]
        try:
            with ws_client.websocket_connect('wss://shared-auth.test/ws/pms/grid', headers=socket_headers(token)):
                pass
        except WebSocketDisconnect as error:
            assert error.code == 4403
        else:
            raise AssertionError('Waiter accessed PMS realtime')

        token = login_ws('b')
        with ws_client.websocket_connect('wss://shared-auth.test/ws/pms/grid', headers=socket_headers(token)) as ws:
            ws.receive_json()
            execute("UPDATE tenants SET status='BLOCKED' WHERE id=$1", ids['tenant_b'])
            expect_close(ws, 4401)
    print('PASS: shared PostgreSQL WebSockets: two-hotel room/order isolation, same usernames, forged headers, waiter scope, live session/grant revocation, blocked tenant and released pool connections; canonical preview remains closed')


if __name__ == '__main__': main()
