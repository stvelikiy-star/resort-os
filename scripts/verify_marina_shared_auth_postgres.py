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
        manager_password = 'ManagerA-'+secrets.token_urlsafe(20)
        manager = canonical_client.post('/api/v1/admin/staff', json=dict(
            username='synthetic-manager', display_name='Synthetic Manager A',
            password=manager_password, role='MANAGER'))
        assert manager.status_code == 201, manager.text
        manager_id = manager.json()['id']
        assert canonical_client.patch('/api/v1/admin/staff/'+manager_id,
                                      json={'module_permissions':['STAFF']}).status_code == 200
        manager_login = canonical_client.post('/api/v1/auth/login', json=dict(
            username='synthetic-manager', password=manager_password,
            tenant_code='tenant_a', property_code='HOTEL_A'))
        assert manager_login.status_code == 200, manager_login.text
        manager_token = canonical_client.cookies.get(auth.SESSION_COOKIE)
        manager_overview = canonical_client.get('/api/v1/admin/staff/overview')
        assert manager_overview.status_code == 200, manager_overview.text
        assert manager_overview.json()['can_manage_access'] is False
        assert canonical_client.post('/api/v1/admin/staff', json=dict(
            username='forbidden-manager-create', display_name='Forbidden Manager Create',
            password=manager_password, role='MAID')).status_code == 403
        assert canonical_client.patch('/api/v1/admin/staff/'+worker_a_id,
                                      json={'active':True}).status_code == 403

        owner_login('a')
        assert canonical_client.patch('/api/v1/admin/staff/'+manager_id,
                                      json={'module_permissions':[]}).status_code == 200
        assert canonical_client.get('/api/v1/auth/me', headers={
            'Cookie': auth.SESSION_COOKIE+'='+manager_token}).status_code == 401
        manager_login = canonical_client.post('/api/v1/auth/login', json=dict(
            username='synthetic-manager', password=manager_password,
            tenant_code='tenant_a', property_code='HOTEL_A'))
        assert manager_login.status_code == 200
        assert canonical_client.get('/api/v1/admin/staff/overview').status_code == 403

        owner_login('a')
        receptionist_password = 'ReceptionA-'+secrets.token_urlsafe(20)
        receptionist = canonical_client.post('/api/v1/admin/staff', json=dict(
            username='synthetic-reception', display_name='Synthetic Reception A',
            password=receptionist_password, role='RECEPTION'))
        assert receptionist.status_code == 201, receptionist.text
        receptionist_login = canonical_client.post('/api/v1/auth/login', json=dict(
            username='synthetic-reception', password=receptionist_password,
            tenant_code='tenant_a', property_code='HOTEL_A'))
        assert receptionist_login.status_code == 200
        assert canonical_client.get('/api/v1/admin/staff/overview').status_code == 403
        assert canonical_client.post('/api/v1/admin/staff', json=dict(
            username='reception-forbidden', display_name='Reception Forbidden',
            password=receptionist_password, role='MAID')).status_code == 403

        owner_login('a')
        # Unreviewed operations remain blocked by the canonical boundary.
        assert canonical_client.put('/api/v1/admin/staff').status_code == 503
        assert canonical_client.delete('/api/v1/admin/staff/'+manager_id).status_code == 503
        assert canonical_client.post('/api/v1/reservations', json={}).status_code == 503
        # Shared PMS staging: only reviewed preview/commit/unpaid cancel are opened.
        # Use distinct hotel UUIDs with the same room code and identical stay dates.
        from datetime import date, timedelta
        check_in = (date.today() + timedelta(days=14)).isoformat()
        check_out = (date.today() + timedelta(days=16)).isoformat()
        price = 9000
        path_preview = '/api/v1/admin/pms/reservations/new/preview'
        path_commit = '/api/v1/admin/pms/reservations/new/commit'
        def reservation_data(suffix):
            return {
                'room_id': str(ids['room_'+suffix]), 'check_in': check_in,
                'check_out': check_out, 'adults': 2, 'children': 0,
                'manager_total_kgs': price,
            }
        def commit_data(suffix):
            return {
                **reservation_data(suffix), 'guest_name': 'Shared Booking Synthetic',
                'phone': '+996555771122', 'expected_total_kgs': price,
                'expected_pricing_source': 'MANAGER_OVERRIDE',
            }
        owner_login('a')
        denied_preview = canonical_client.post(path_preview, json=reservation_data('b'))
        assert denied_preview.status_code == 404, denied_preview.text
        denied_commit = canonical_client.post(path_commit, json=commit_data('b'))
        assert denied_commit.status_code == 404, denied_commit.text
        quote_a = canonical_client.post(path_preview, json=reservation_data('a'))
        assert quote_a.status_code == 200 and quote_a.json()['can_commit'], quote_a.text
        assert quote_a.json()['pricing']['total_kgs'] == price
        bad_price = canonical_client.post(path_commit, json={
            **commit_data('a'), 'expected_total_kgs': price + 1,
        })
        assert bad_price.status_code == 409, bad_price.text
        booked_a = canonical_client.post(path_commit, json=commit_data('a'))
        assert booked_a.status_code == 201, booked_a.text
        rid_a = booked_a.json()['reservation_id']
        assert booked_a.json()['room_id'] == str(ids['room_a'])
        assert booked_a.json()['payment_created'] is False
        again_a = canonical_client.post(path_commit, json=commit_data('a'))
        assert again_a.status_code == 409, again_a.text
        grid_a = canonical_client.get(
            '/api/v1/pms/grid', params={'start': check_in, 'end': check_out})
        assert grid_a.status_code == 200
        assert grid_a.json()['property'] == 'HOTEL_A'
        assert any(b['reservation_id'] == rid_a
                   for room in grid_a.json()['rooms'] for b in room['blocks'])
        # Check-in is now staged, but a future-dated reservation is refused.
        assert canonical_client.post(
            '/api/v1/admin/stays/reservations/'+rid_a+'/check-in').status_code == 409
        assert canonical_client.post('/api/v1/admin/pms/holds', json={}).status_code == 422  # now enabled; invalid payload rejected

        owner_login('b')
        foreign_cancel = canonical_client.post(
            '/api/v1/admin/pms/reservations/'+rid_a+'/cancel')
        assert foreign_cancel.status_code == 404, foreign_cancel.text
        quote_b = canonical_client.post(path_preview, json=reservation_data('b'))
        assert quote_b.status_code == 200 and quote_b.json()['can_commit'], quote_b.text
        booked_b = canonical_client.post(path_commit, json=commit_data('b'))
        assert booked_b.status_code == 201, booked_b.text
        rid_b = booked_b.json()['reservation_id']
        assert rid_b != rid_a and booked_b.json()['room_id'] == str(ids['room_b'])
        grid_b = canonical_client.get('/api/v1/pms/grid', params={
            'start': check_in, 'end': check_out})
        assert grid_b.status_code == 200 and grid_b.json()['property'] == 'HOTEL_B'
        assert any(b['reservation_id'] == rid_b
                   for room in grid_b.json()['rooms'] for b in room['blocks'])
        assert all(b.get('reservation_id') != rid_a
                   for room in grid_b.json()['rooms'] for b in room['blocks'])
        cancel_b_from_wrong_hotel = canonical_client.post(
            '/api/v1/admin/pms/reservations/'+rid_a+'/cancel')
        assert cancel_b_from_wrong_hotel.status_code == 404

        owner_login('a')
        assert canonical_client.post(
            '/api/v1/admin/pms/reservations/'+rid_b+'/cancel').status_code == 404
        cancelled = canonical_client.post(
            '/api/v1/admin/pms/reservations/'+rid_a+'/cancel')
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()['status'] == 'CANCELLED'
        assert cancelled.json()['released_blocks'] == 1
        assert canonical_client.post(
            '/api/v1/admin/pms/reservations/'+rid_a+'/cancel').status_code == 409
        available_again = canonical_client.post(path_preview, json=reservation_data('a'))
        assert available_again.status_code == 200 and available_again.json()['can_commit']
        owner_login('b')
        blocked_b = canonical_client.post(path_preview, json=reservation_data('b'))
        assert blocked_b.status_code == 200 and not blocked_b.json()['can_commit']
        assert blocked_b.json()['conflicts']
        # Genuine database-level isolation for the stored reservations/guests.
        async def inspect_pms():
            # TestClient's ASGI pool belongs to a different thread/event loop.
            # Read persisted data through an independent CI-only DB connection.
            conn = await asyncpg.connect(dsn)
            try:
                rows = await conn.fetch(
                    'SELECT id,"propertyId","primaryGuestId",status::text FROM reservations WHERE id=ANY($1::uuid[])',
                    [uuid.UUID(rid_a), uuid.UUID(rid_b)],
                )
                return {str(row['id']): row for row in rows}
            finally:
                await conn.close()
        stored = asyncio.run(inspect_pms())
        assert stored[rid_a]['propertyId'] == ids['property_a']
        assert stored[rid_b]['propertyId'] == ids['property_b']
        assert stored[rid_a]['primaryGuestId'] != stored[rid_b]['primaryGuestId']
        assert stored[rid_a]['status'] == 'CANCELLED'
        assert stored[rid_b]['status'] == 'GUARANTEED'
        # Shared preview intentionally refuses other mutating PMS workflows.
        assert canonical_client.post('/api/v1/admin/booking/reservations/'+rid_b+'/payments', json={}).status_code == 422  # only well-formed internal payments allowed
        auth._preview_attempts.clear()

        # HOLD acceptance on the actual composed MARINA API and real PostgreSQL.
        # Both properties have room code 101. UUID identity—not the code or a
        # client-provided header—decides inventory ownership.
        from app.db import expire_shared_holds_once
        hold_start = (date.today() + timedelta(days=27)).isoformat()
        hold_end = (date.today() + timedelta(days=29)).isoformat()
        hold_path = '/api/v1/admin/pms/holds'
        phones = {'a': '+996701100111', 'b': '+996701100222'}
        hold_names = {'a': 'Synthetic Hold A', 'b': 'Synthetic Hold B'}
        def hold_payload(suffix, start=hold_start, end=hold_end):
            return {
                'room_id': str(ids['room_'+suffix]), 'check_in': start,
                'check_out': end, 'guest_name': hold_names[suffix],
                'guest_phone': phones[suffix],
            }
        def hold_booking(suffix, hold_id=None, start=hold_start, end=hold_end):
            return {
                'room_id': str(ids['room_'+suffix]), 'check_in': start,
                'check_out': end, 'adults': 2, 'children': 0,
                'manager_total_kgs': price, 'hold_id': hold_id,
            }
        def hold_commit(suffix, hold_id=None, start=hold_start, end=hold_end):
            return {
                **hold_booking(suffix, hold_id, start, end),
                'guest_name': hold_names[suffix], 'phone': phones[suffix],
                'expected_total_kgs': price,
                'expected_pricing_source': 'MANAGER_OVERRIDE',
            }

        owner_login('a')
        a_hold = canonical_client.post(hold_path, json=hold_payload('a'))
        assert a_hold.status_code == 201, a_hold.text
        hold_id_a = a_hold.json()['id']
        assert a_hold.json()['duration_minutes'] == 60
        assert canonical_client.post(hold_path, json=hold_payload('b')).status_code == 404
        assert canonical_client.post(hold_path, json=hold_payload('a')).status_code == 409
        listed_a = canonical_client.get(hold_path)
        assert listed_a.status_code == 200
        assert {h['id'] for h in listed_a.json()['holds']} == {hold_id_a}
        assert canonical_client.get(hold_path+'/'+hold_id_a).status_code == 200
        # A regular booking cannot steal an active HOLD; the hold owner can
        # price its own reserved inventory without it counting as a conflict.
        blocked_a = canonical_client.post(path_preview, json=hold_booking('a'))
        assert blocked_a.status_code == 200 and not blocked_a.json()['can_commit']
        quote_held_a = canonical_client.post(path_preview, json=hold_booking('a', hold_id_a))
        assert quote_held_a.status_code == 200 and quote_held_a.json()['can_commit']
        assert canonical_client.post(path_commit, json=hold_commit('a')).status_code == 409

        owner_login('b')
        b_hold = canonical_client.post(hold_path, json=hold_payload('b'))
        assert b_hold.status_code == 201, b_hold.text
        hold_id_b = b_hold.json()['id']
        assert hold_id_a != hold_id_b
        assert {h['id'] for h in canonical_client.get(hold_path).json()['holds']} == {hold_id_b}
        assert canonical_client.get(hold_path+'/'+hold_id_a, headers={
            'X-Property-Id': str(ids['property_a']),
            'X-Tenant-Id': str(ids['tenant_a']), 'X-Role': 'OWNER',
        }).status_code == 404
        assert canonical_client.delete(hold_path+'/'+hold_id_a).status_code == 404
        assert canonical_client.post(path_preview, json=hold_booking('b',hold_id_a)).status_code == 409
        booked_hold_b = canonical_client.post(path_commit, json=hold_commit('b',hold_id_b))
        assert booked_hold_b.status_code == 201, booked_hold_b.text
        rid_hold_b = booked_hold_b.json()['reservation_id']
        assert canonical_client.get(hold_path+'/'+hold_id_b).status_code == 404
        assert canonical_client.delete(hold_path+'/'+hold_id_b).status_code == 409
        assert canonical_client.post(path_commit, json=hold_commit('b',hold_id_b)).status_code == 409

        owner_login('a')
        assert canonical_client.get(hold_path+'/'+hold_id_b).status_code == 404
        assert canonical_client.delete(hold_path+'/'+hold_id_b).status_code == 404
        assert canonical_client.post(path_preview, json=hold_booking('a',hold_id_b)).status_code == 409
        # Expiry must also be applied immediately by ordinary booking preview,
        # not depend on the thirty-second background tick.
        execute("""UPDATE marina_reservation_holds SET
                  "createdAt"=now()-interval '2 hours',
                  "expiresAt"=now()-interval '1 minute'
                  WHERE id=$1""", uuid.UUID(hold_id_a))
        released_quote = canonical_client.post(path_preview, json=hold_booking('a'))
        assert released_quote.status_code == 200 and released_quote.json()['can_commit'], released_quote.text
        assert canonical_client.get(hold_path+'/'+hold_id_a).status_code == 404
        assert canonical_client.post(path_commit, json=hold_commit('a',hold_id_a)).status_code == 409
        booked_after_expiry = canonical_client.post(path_commit, json=hold_commit('a'))
        assert booked_after_expiry.status_code == 201, booked_after_expiry.text
        rid_after_expiry_a = booked_after_expiry.json()['reservation_id']
        assert rid_after_expiry_a != rid_hold_b

        # Directly exercise the production shared-property sweep with DB-backed
        # expiration in A and still-active inventory in B.
        sweep_start = (date.today() + timedelta(days=35)).isoformat()
        sweep_end = (date.today() + timedelta(days=37)).isoformat()
        sweep_a = canonical_client.post(hold_path, json=hold_payload('a',sweep_start,sweep_end))
        assert sweep_a.status_code == 201, sweep_a.text
        sweep_a_id = sweep_a.json()['id']
        owner_login('b')
        sweep_b = canonical_client.post(hold_path, json=hold_payload('b',sweep_start,sweep_end))
        assert sweep_b.status_code == 201, sweep_b.text
        sweep_b_id = sweep_b.json()['id']
        execute("""UPDATE marina_reservation_holds SET
                  "createdAt"=now()-interval '2 hours',
                  "expiresAt"=now()-interval '1 minute'
                  WHERE id=$1""", uuid.UUID(sweep_a_id))
        async def run_shared_sweep():
            pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
            try:
                return await expire_shared_holds_once(pool)
            finally:
                await pool.close()
        asyncio.run(run_shared_sweep())
        async def hold_states():
            conn = await asyncpg.connect(dsn)
            try:
                rows = await conn.fetch("""
                    SELECT h.id,h."propertyId",h."releasedAt",h."confirmedReservationId",
                           i.active AS block_active
                    FROM marina_reservation_holds h
                    JOIN inventory_blocks i ON i.id=h."inventoryBlockId"
                    WHERE h.id=ANY($1::uuid[])
                """, [uuid.UUID(hold_id_a),uuid.UUID(hold_id_b),
                       uuid.UUID(sweep_a_id),uuid.UUID(sweep_b_id)])
                return {str(row['id']): row for row in rows}
            finally:
                await conn.close()
        states = asyncio.run(hold_states())
        assert states[hold_id_a]['releasedAt'] is not None and not states[hold_id_a]['block_active']
        assert states[hold_id_b]['confirmedReservationId'] == uuid.UUID(rid_hold_b)
        assert not states[hold_id_b]['block_active']
        assert states[sweep_a_id]['releasedAt'] is not None and not states[sweep_a_id]['block_active']
        assert states[sweep_b_id]['releasedAt'] is None and states[sweep_b_id]['block_active']
        assert states[sweep_a_id]['propertyId'] == ids['property_a']
        assert states[sweep_b_id]['propertyId'] == ids['property_b']
        assert canonical_client.delete(hold_path+'/'+sweep_a_id).status_code == 404
        released_b = canonical_client.delete(hold_path+'/'+sweep_b_id)
        assert released_b.status_code == 200 and released_b.json()['status'] == 'RELEASED'
        assert canonical_client.delete(hold_path+'/'+sweep_b_id).status_code == 200
        assert canonical_client.get(hold_path).json()['holds'] == []
        assert canonical_client.post(path_preview, json=hold_booking(
            'b',start=sweep_start,end=sweep_end)).json()['can_commit']
        # Competing writes for the same room on the same dates must produce
        # exactly one winning active inventory block, never a double booking.
        from concurrent.futures import ThreadPoolExecutor
        race_start = (date.today() + timedelta(days=41)).isoformat()
        race_end = (date.today() + timedelta(days=43)).isoformat()
        owner_login('a')
        with ThreadPoolExecutor(max_workers=2) as executor:
            hold_future = executor.submit(canonical_client.post, hold_path,
                                          json=hold_payload('a',race_start,race_end))
            book_future = executor.submit(canonical_client.post, path_commit,
                                          json=hold_commit('a',None,race_start,race_end))
            race_hold, race_booking = hold_future.result(), book_future.result()
        assert sorted([race_hold.status_code, race_booking.status_code]) == [201,409], (
            race_hold.status_code, race_hold.text, race_booking.status_code, race_booking.text)
        async def count_race_inventory():
            conn = await asyncpg.connect(dsn)
            try:
                return await conn.fetchval("""
                    SELECT count(*)::int FROM inventory_blocks
                    WHERE "roomId"=$1 AND active=true
                      AND daterange("startDate","endDate",'[)')
                          && daterange($2::date,$3::date,'[)')
                """, ids['room_a'], date.fromisoformat(race_start),
                     date.fromisoformat(race_end))
            finally:
                await conn.close()
        assert asyncio.run(count_race_inventory()) == 1, 'Parallel HOLD and booking created multiple active inventory blocks'

        # Even without UI controls, server RBAC must keep reception and an
        # explicitly staff-only manager outside privileged HOLD operations.
        auth._preview_attempts.clear()
        receptionist_signin = canonical_client.post('/api/v1/auth/login', json=dict(
            username='synthetic-reception', password=receptionist_password,
            tenant_code='tenant_a', property_code='HOTEL_A'))
        assert receptionist_signin.status_code == 200, receptionist_signin.text
        assert canonical_client.get(hold_path).status_code == 403
        assert canonical_client.post(hold_path, json=hold_payload('a')).status_code == 403
        manager_signin = canonical_client.post('/api/v1/auth/login', json=dict(
            username='synthetic-manager', password=manager_password,
            tenant_code='tenant_a', property_code='HOTEL_A'))
        assert manager_signin.status_code == 200, manager_signin.text
        assert canonical_client.get(hold_path).status_code == 403
        assert canonical_client.post(hold_path, json=hold_payload('a')).status_code == 403
        # Hotel-scoped schedule/date changes must use the verified session, not
        # user-supplied hotel codes or forged X-Property-Id headers.
        schedule_a = '/api/v1/admin/pms/reservations/'+rid_after_expiry_a+'/schedule'
        schedule_b = '/api/v1/admin/pms/reservations/'+rid_hold_b+'/schedule'
        def proposed_segments(suffix, start, end):
            return [{'room_id': str(ids['room_'+suffix]), 'start': start, 'end': end}]
        new_checkout = (date.today() + timedelta(days=31)).isoformat()
        collision_start = (date.today() + timedelta(days=32)).isoformat()
        collision_end = (date.today() + timedelta(days=34)).isoformat()
        assert canonical_client.get(schedule_a).status_code == 403
        assert canonical_client.post(schedule_a+'/preview', json={
            'segments':proposed_segments('a',hold_start,new_checkout)}).status_code == 403

        owner_login('b')
        assert canonical_client.get(schedule_a, headers={
            'X-Tenant-Id': str(ids['tenant_a']),
            'X-Property-Id': str(ids['property_a']),
            'X-Role': 'OWNER'}).status_code == 404
        assert canonical_client.post(schedule_a+'/preview', json={
            'segments':proposed_segments('b',hold_start,new_checkout)}).status_code == 404
        foreign_commit = canonical_client.post(schedule_a+'/commit', json={
            'segments':proposed_segments('b',hold_start,new_checkout),
            'expected_version': '2026-11-03T00:00:00.000000'})
        assert foreign_commit.status_code == 404, foreign_commit.text
        b_original = canonical_client.get(schedule_b)
        assert b_original.status_code == 200 and b_original.json()['reservation']['status'] == 'GUARANTEED'

        owner_login('a')
        details_a = canonical_client.get(schedule_a)
        assert details_a.status_code == 200, details_a.text
        version_a = details_a.json()['reservation']['version']
        assert details_a.json()['reservation']['stored_total_kgs'] == price
        target = proposed_segments('a',hold_start,new_checkout)
        wrong_room = canonical_client.post(schedule_a+'/preview', json={
            'segments':proposed_segments('b',hold_start,new_checkout)})
        assert wrong_room.status_code == 422, wrong_room.text
        quote = canonical_client.post(schedule_a+'/preview',json={'segments':target})
        assert quote.status_code == 200 and quote.json()['can_commit'], quote.text
        moved = canonical_client.post(schedule_a+'/commit', json={
            'segments':target,'expected_version':version_a})
        assert moved.status_code == 200 and moved.json()['ok'], moved.text
        assert moved.json()['check_out'] == new_checkout
        assert moved.json()['stored_total_kgs'] == price
        assert canonical_client.post(schedule_a+'/commit', json={
            'segments':target,'expected_version':version_a}).status_code == 409
        updated_a = canonical_client.get(schedule_a)
        assert updated_a.status_code == 200
        assert updated_a.json()['reservation']['check_out'] == new_checkout
        assert updated_a.json()['reservation']['stored_total_kgs'] == price
        # A live HOLD must block an extension into those dates; failed commit
        # must preserve the previously confirmed dates and monetary total.
        hold_a_collision = canonical_client.post(hold_path, json=hold_payload(
            'a',collision_start,collision_end))
        assert hold_a_collision.status_code == 201, hold_a_collision.text
        collision_target = proposed_segments('a',hold_start,collision_end)
        conflict_quote = canonical_client.post(schedule_a+'/preview', json={
            'segments':collision_target})
        assert conflict_quote.status_code == 200 and not conflict_quote.json()['can_commit']
        rejected_change = canonical_client.post(schedule_a+'/commit', json={
            'segments':collision_target,'expected_version':updated_a.json()['reservation']['version']})
        assert rejected_change.status_code == 409, rejected_change.text
        stable_a = canonical_client.get(schedule_a)
        assert stable_a.json()['reservation']['check_out'] == new_checkout
        assert stable_a.json()['reservation']['stored_total_kgs'] == price
        assert canonical_client.delete(hold_path+'/'+hold_a_collision.json()['id']).status_code == 200
        unlocked = canonical_client.post(schedule_a+'/preview', json={
            'segments':collision_target})
        assert unlocked.status_code == 200 and unlocked.json()['can_commit'], unlocked.text
        owner_login('b')
        unchanged_b = canonical_client.get(schedule_b)
        assert unchanged_b.status_code == 200
        assert unchanged_b.json()['reservation']['check_out'] == hold_end
        assert unchanged_b.json()['reservation']['stored_total_kgs'] == price
        # Confirm persisted schedule and financial invariants in PostgreSQL.
        async def verify_schedule_db():
            conn = await asyncpg.connect(dsn)
            try:
                return await conn.fetch("""
                    SELECT r.id,r."propertyId",r."checkIn",r."checkOut",r."totalKgs",
                           (SELECT count(*) FROM payments p WHERE p."reservationId"=r.id)::int AS payments
                    FROM reservations r WHERE r.id=ANY($1::uuid[])
                """, [uuid.UUID(rid_after_expiry_a),uuid.UUID(rid_hold_b)])
            finally:
                await conn.close()
        dates_stored = {str(row['id']): row for row in asyncio.run(verify_schedule_db())}
        assert dates_stored[rid_after_expiry_a]['propertyId'] == ids['property_a']
        assert dates_stored[rid_after_expiry_a]['checkOut'].isoformat() == new_checkout
        assert dates_stored[rid_hold_b]['propertyId'] == ids['property_b']
        assert dates_stored[rid_hold_b]['checkOut'].isoformat() == hold_end
        for item in dates_stored.values():
            assert item['totalKgs'] == price and item['payments'] == 0

        # Strictly internal manual payment facts, NOT acquiring/bank settlement.
        # The shared staging gate must not open legacy provider/QR callbacks.
        pay_base = '/api/v1/admin/booking/reservations/'
        def payment_payload(label, amount):
            return {
                'amount_kgs':amount,'method':'CASH',
                'idempotency_key':'shared-manual-'+label+'-'+secrets.token_hex(12),
                'external_ref':'synthetic-cash-'+label+'-'+secrets.token_hex(8),
                'note':'Synthetic CI cash recorded, no bank confirmation',
            }
        owner_login('a')
        status_a = canonical_client.get(pay_base+rid_after_expiry_a+'/acquiring-readiness')
        assert status_a.status_code == 200, status_a.text
        assert status_a.json()['paid_kgs'] == 0
        assert status_a.json()['provider_connected'] is False
        assert status_a.json()['acquiring_status'] == 'NOT_CONFIGURED'
        assert canonical_client.get(pay_base+rid_hold_b+'/acquiring-readiness').status_code == 404
        assert canonical_client.get(pay_base+rid_hold_b+'/cancellation-finance-review').status_code == 404
        assert canonical_client.post(pay_base+rid_hold_b+'/payments', json=payment_payload(
            'foreign-b',1000)).status_code == 404
        assert canonical_client.post(pay_base+rid_a+'/payments', json=payment_payload(
            'cancelled-a',1000)).status_code == 409
        assert canonical_client.post(pay_base+rid_after_expiry_a+'/payments',json={
            'method':'QR','amount_kgs':100,
            'idempotency_key':'shared-disallowed-method-'+secrets.token_hex(8)}).status_code == 422

        pay_a = payment_payload('hotel-a',4000)
        accepted_a = canonical_client.post(pay_base+rid_after_expiry_a+'/payments',json=pay_a)
        assert accepted_a.status_code == 201, accepted_a.text
        assert accepted_a.json()['idempotent_replay'] is False
        pay_id_a = accepted_a.json()['payment_id']
        assert accepted_a.json()['payment']['provider'] == 'MANAGER_MANUAL'
        assert accepted_a.json()['finance']['paid_kgs'] == 4000
        assert accepted_a.json()['finance']['remaining_kgs'] == price-4000
        replay_a = canonical_client.post(pay_base+rid_after_expiry_a+'/payments',json=pay_a)
        assert replay_a.status_code == 201 and replay_a.json()['idempotent_replay'] is True, replay_a.text
        assert replay_a.json()['payment_id'] == pay_id_a
        changed_key = canonical_client.post(pay_base+rid_after_expiry_a+'/payments',
            json={**pay_a,'amount_kgs':4001})
        assert changed_key.status_code == 409
        overpayment = canonical_client.post(pay_base+rid_after_expiry_a+'/payments',
                                            json=payment_payload('overpayment',price))
        assert overpayment.status_code == 409, overpayment.text
        after_a = canonical_client.get(pay_base+rid_after_expiry_a+'/acquiring-readiness')
        assert after_a.status_code == 200 and after_a.json()['paid_kgs'] == 4000
        assert after_a.json()['provider_connected'] is False
        finance_a = canonical_client.get(pay_base+rid_after_expiry_a+'/cancellation-finance-review')
        assert finance_a.status_code == 200 and finance_a.json()['requires_manual_review'] is True
        assert canonical_client.post(
            '/api/v1/admin/pms/reservations/'+rid_after_expiry_a+'/cancel').status_code == 409

        owner_login('b')
        assert canonical_client.get(pay_base+rid_after_expiry_a+'/acquiring-readiness').status_code == 404
        assert canonical_client.post(pay_base+rid_after_expiry_a+'/payments',
                                    json=payment_payload('foreign-a',500)).status_code == 404
        status_b = canonical_client.get(pay_base+rid_hold_b+'/acquiring-readiness')
        assert status_b.status_code == 200 and status_b.json()['paid_kgs'] == 0
        pay_b = payment_payload('hotel-b',2000)
        accepted_b = canonical_client.post(pay_base+rid_hold_b+'/payments',json=pay_b)
        assert accepted_b.status_code == 201 and accepted_b.json()['finance']['paid_kgs'] == 2000
        pay_id_b = accepted_b.json()['payment_id']
        assert pay_id_b != pay_id_a
        assert canonical_client.get(pay_base+rid_hold_b+'/cancellation-finance-review').json()['requires_manual_review']

        # Unauthorized RECEPTION cannot read or manufacture a manual payment.
        auth._preview_attempts.clear()
        reception_auth = canonical_client.post('/api/v1/auth/login', json=dict(
            username='synthetic-reception', password=receptionist_password,
            tenant_code='tenant_a', property_code='HOTEL_A'))
        assert reception_auth.status_code == 200, reception_auth.text
        assert canonical_client.get(pay_base+rid_after_expiry_a+'/acquiring-readiness').status_code == 403
        assert canonical_client.post(pay_base+rid_after_expiry_a+'/payments',
                                    json=payment_payload('unauthorized',100)).status_code == 403

        async def persisted_payment_scope():
            conn = await asyncpg.connect(dsn)
            try:
                rows = await conn.fetch("""
                    SELECT p.id,p."reservationId",r."propertyId",p."amountKgs",
                           p.provider,p.status::text AS status
                    FROM payments p JOIN reservations r ON r.id=p."reservationId"
                    WHERE r.id=ANY($1::uuid[]) ORDER BY r."propertyId"
                """, [uuid.UUID(rid_after_expiry_a),uuid.UUID(rid_hold_b)])
                return rows
            finally:
                await conn.close()
        paid_rows = asyncio.run(persisted_payment_scope())
        assert len(paid_rows) == 2, paid_rows
        scope_by_payment = {str(row['id']):row for row in paid_rows}
        assert scope_by_payment[pay_id_a]['propertyId'] == ids['property_a']
        assert scope_by_payment[pay_id_b]['propertyId'] == ids['property_b']
        assert {row['status'] for row in paid_rows} == {'RECEIVED'}
        assert {row['provider'] for row in paid_rows} == {'MANAGER_MANUAL'}
        assert sum(int(row['amountKgs']) for row in paid_rows) == 6000
        assert canonical_client.post(
            '/api/v1/admin/booking/requests/'+rid_after_expiry_a+'/confirm-payment',json={}).status_code == 503
        auth._preview_attempts.clear()
        # Canonical two-property stay lifecycle: no bank settlement, only
        # verified reservation and hotel-scoped operations, staff role grants.
        from datetime import datetime
        from zoneinfo import ZoneInfo
        local_today = datetime.now(ZoneInfo('Asia/Bishkek')).date()
        stay_start = (local_today-timedelta(days=1)).isoformat()
        stay_end = (local_today+timedelta(days=2)).isoformat()
        stay_route = '/api/v1/admin/stays/reservations/'
        owner_login('a')
        created_stay_a = canonical_client.post(path_commit,
            json=hold_commit('a',None,stay_start,stay_end))
        assert created_stay_a.status_code == 201, created_stay_a.text
        rid_stay_a = created_stay_a.json()['reservation_id']
        assert canonical_client.post(
            stay_route+rid_hold_b+'/check-in').status_code == 404
        assert canonical_client.post(
            stay_route+rid_stay_a+'/check-out').status_code == 409
        # Actual CHECK_IN enforces both room readiness and current hotel-local date.
        assert canonical_client.post(
            stay_route+rid_after_expiry_a+'/check-in').status_code == 409

        owner_login('b')
        created_stay_b = canonical_client.post(path_commit,
            json=hold_commit('b',None,stay_start,stay_end))
        assert created_stay_b.status_code == 201, created_stay_b.text
        rid_stay_b = created_stay_b.json()['reservation_id']
        assert rid_stay_a != rid_stay_b
        assert canonical_client.post(stay_route+rid_stay_a+'/check-in',headers={
            'X-Property-Id':str(ids['property_a']),
            'X-Tenant-Id':str(ids['tenant_a']), 'X-Role':'OWNER'}).status_code == 404
        assert canonical_client.post(stay_route+rid_stay_a+'/check-out').status_code == 404
        assert canonical_client.post(stay_route+rid_stay_b+'/check-out').status_code == 409
        execute('UPDATE rooms SET "operationalState"=\'CLEAN\' WHERE id=$1',
                ids['room_a'])
        execute('UPDATE rooms SET "operationalState"=\'CLEAN\' WHERE id=$1',
                ids['room_b'])
        b_check_in = canonical_client.post(stay_route+rid_stay_b+'/check-in')
        assert b_check_in.status_code == 200, b_check_in.text
        assert b_check_in.json()['status'] == 'CHECKED_IN'
        assert len(b_check_in.json()['guest_access_pin']) == 6
        assert canonical_client.post(stay_route+rid_stay_b+'/check-in').status_code == 409
        assert canonical_client.post(stay_route+rid_stay_a+'/check-out').status_code == 404

        owner_login('a')
        assert canonical_client.post(stay_route+rid_stay_b+'/check-out').status_code == 404
        # Owner removes and restores reception permission before real check-in.
        receptionist_id = receptionist.json()['id']
        assert canonical_client.patch('/api/v1/admin/staff/'+receptionist_id,
                                      json={'module_permissions':[]}).status_code == 200
        auth._preview_attempts.clear()
        denied_reception = canonical_client.post('/api/v1/auth/login',json=dict(
            username='synthetic-reception',password=receptionist_password,
            tenant_code='tenant_a',property_code='HOTEL_A'))
        assert denied_reception.status_code == 200
        assert canonical_client.post(stay_route+rid_stay_a+'/check-in').status_code == 403
        owner_login('a')
        assert canonical_client.patch('/api/v1/admin/staff/'+receptionist_id,
                                      json={'module_permissions':['RESERVATIONS']}).status_code == 200
        auth._preview_attempts.clear()
        allowed_reception = canonical_client.post('/api/v1/auth/login',json=dict(
            username='synthetic-reception',password=receptionist_password,
            tenant_code='tenant_a',property_code='HOTEL_A'))
        assert allowed_reception.status_code == 200
        assert canonical_client.post(stay_route+rid_stay_b+'/check-in').status_code == 404
        a_check_in = canonical_client.post(stay_route+rid_stay_a+'/check-in')
        assert a_check_in.status_code == 200, a_check_in.text
        assert a_check_in.json()['status'] == 'CHECKED_IN'
        assert len(a_check_in.json()['guest_access_pin']) == 6
        assert a_check_in.json()['guest_access_pin_display_once'] is True
        assert canonical_client.post(stay_route+rid_stay_a+'/check-in').status_code == 409

        owner_login('a')
        a_check_out = canonical_client.post(stay_route+rid_stay_a+'/check-out')
        assert a_check_out.status_code == 200, a_check_out.text
        assert a_check_out.json()['status'] == 'CHECKED_OUT'
        assert a_check_out.json()['room_state'] == 'DIRTY'
        assert a_check_out.json()['housekeeping_task_id']
        assert a_check_out.json()['early_checkout_released_inventory'] is True
        assert a_check_out.json()['stored_total_kgs_changed'] is False
        assert canonical_client.post(stay_route+rid_stay_a+'/check-out').status_code == 409
        assert canonical_client.post(stay_route+rid_stay_b+'/check-out').status_code == 404
        owner_login('b')
        # Other hotel is still checked in and its room remains CLEAN.
        async def inspect_before_b_checkout():
            conn = await asyncpg.connect(dsn)
            try:
                return await conn.fetchrow("""
                    SELECT r.status::text AS booking_status,
                           s.status::text AS stay_status,room."operationalState"::text AS room_state
                    FROM reservations r JOIN stays s ON s."reservationId"=r.id
                    JOIN room_assignments ra ON ra."stayId"=s.id AND ra."endedAt" IS NULL
                    JOIN rooms room ON room.id=ra."roomId"
                    WHERE r.id=$1 AND r."propertyId"=$2
                """,uuid.UUID(rid_stay_b),ids['property_b'])
            finally:
                await conn.close()
        b_live = asyncio.run(inspect_before_b_checkout())
        assert b_live and b_live['booking_status'] == 'CHECKED_IN'
        assert b_live['stay_status'] == 'ACTIVE' and b_live['room_state'] == 'CLEAN'
        b_check_out = canonical_client.post(stay_route+rid_stay_b+'/check-out')
        assert b_check_out.status_code == 200, b_check_out.text
        assert b_check_out.json()['housekeeping_task_id']
        assert b_check_out.json()['early_checkout_released_inventory'] is True
        assert canonical_client.post(stay_route+rid_stay_b+'/check-out').status_code == 409

        async def inspect_closed_stays():
            conn = await asyncpg.connect(dsn)
            try:
                return await conn.fetch("""
                    SELECT r.id,r."propertyId",r.status::text AS reservation_status,
                           r."totalKgs",s.id AS stay_id,
                           s.status::text AS stay_status,s."guestAccessPinHash" AS pin_hash,
                           room."operationalState"::text AS room_state,
                           (SELECT count(*) FROM operational_tasks task
                            WHERE task."propertyId"=r."propertyId"
                              AND task."reservationId"=r.id AND task.source='CHECK_OUT')::int AS cleaning_tasks,
                           (SELECT count(*) FROM operational_tasks task
                            WHERE task."propertyId"=r."propertyId"
                              AND task."reservationId"=r.id AND task.source='CHECK_IN_ARRIVAL_SYNC')::int AS arrival_tasks
                    FROM reservations r
                    JOIN stays s ON s."reservationId"=r.id
                    JOIN room_assignments ra ON ra."stayId"=s.id
                    JOIN rooms room ON room.id=ra."roomId"
                    WHERE r.id=ANY($1::uuid[])
                """,[uuid.UUID(rid_stay_a),uuid.UUID(rid_stay_b)])
            finally:
                await conn.close()
        checked = {str(row['id']):row for row in asyncio.run(inspect_closed_stays())}
        assert set(checked) == {rid_stay_a,rid_stay_b},checked
        assert checked[rid_stay_a]['propertyId'] == ids['property_a']
        assert checked[rid_stay_b]['propertyId'] == ids['property_b']
        for item in checked.values():
            assert item['reservation_status'] == 'CHECKED_OUT'
            assert item['stay_status'] == 'CHECKED_OUT'
            assert item['pin_hash'] is None
            assert item['room_state'] == 'DIRTY'
            assert item['totalKgs'] == price
            assert item['cleaning_tasks'] == 1
            assert item['arrival_tasks'] == 1
        # Staging remains fail closed for unreviewed guest/provider operations.
        assert canonical_client.post('/api/v1/ops/kitchen/sync-arrivals').status_code == 503
        auth._preview_attempts.clear()

    print('PASS: canonical shared HOLD expiry/create/convert/release: independent hotels, owned inventory, no cross-hotel access, stale HOLD cannot be confirmed')
    print('PASS: canonical shared staff lifecycle: same usernames isolated, owner-only writes, cross-hotel 404, old session revocation, disabled login denial')

    # Separate synthetic test clients intentionally share a process and default IP.
    # Reset only the in-memory CI attempt counter between independent test phases;
    # the real runtime throttle and its security tests remain unchanged.
    auth._preview_attempts.clear()

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

    # Separate synthetic test clients intentionally share a process and default IP.
    # Reset only the in-memory CI attempt counter between independent test phases;
    # the real runtime throttle and its security tests remain unchanged.
    auth._preview_attempts.clear()

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
