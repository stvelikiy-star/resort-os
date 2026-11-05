import sys
import uuid
import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from argon2 import PasswordHasher
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/api'))
from app import auth
from app.shared_auth_preview import SharedAuthPreviewBoundary
from app.health import router as health_router


class Store:
    def __init__(self, hasher):
        self.properties = {k: uuid.uuid4() for k in ('HOTEL_A', 'HOTEL_B')}
        self.tenants = {k: uuid.uuid4() for k in self.properties}
        self.active = {k: True for k in self.properties}
        self.users = {k: dict(id=uuid.uuid4(), username='owner', displayName=k,
            role='OWNER', isActive=True, propertyId=p,
            passwordHash=hasher.hash('Password-'+k), module_permissions=None,
            module_permissions_custom=False) for k, p in self.properties.items()}
        self.sessions = {}
        self.queries = []

    @asynccontextmanager
    async def acquire(self):
        yield self

    def user_row(self, code):
        return {**self.users[code], 'property_code': code, 'property_id': self.properties[code],
                'tenant_id': self.tenants[code]}

    async def fetchval(self, sql, *args):
        self.queries.append((sql, args))
        if 'JOIN tenants' in sql:
            tenant, code = args
            return self.properties.get(code) if tenant == 'tenant_'+code[-1].lower() and self.active.get(code) else None
        if 'FROM properties WHERE code' in sql:
            return self.properties.get(args[0])
        return None if 'max(' in sql else 0

    async def fetchrow(self, sql, *args):
        self.queries.append((sql, args))
        if 'to_regclass' in sql:
            return {k:k for k in ('tenants','properties','staff','sessions','audit')}
        if 'FROM auth_sessions' in sql:
            session = self.sessions.get(args[0])
            if not session:
                return None
            code = next(k for k, u in self.users.items() if u['id'] == session['userId'])
            if "t.status='ACTIVE'" in sql and not self.active[code]:
                return None
            return {**self.user_row(code), **session, 'user_id': self.users[code]['id']}
        key, username = args
        for code, pid in self.properties.items():
            if key in (pid, code) and username == 'owner' and self.active[code]:
                return self.user_row(code)
        return None

    async def execute(self, sql, *args):
        self.queries.append((sql, args))
        if 'INSERT INTO auth_sessions' in sql:
            sid, uid, token_hash, expiry = args
            self.sessions[token_hash] = dict(session_id=sid, userId=uid, expiresAt=expiry, revokedAt=None)
        if 'UPDATE auth_sessions SET "revokedAt"' in sql and args[0] in self.sessions:
            self.sessions[args[0]]['revokedAt'] = datetime.utcnow()

    async def executemany(self, sql, args):
        self.queries.extend((sql, a) for a in args)


def make_app(db):
    app = FastAPI()
    app.state.db = db
    app.add_middleware(SharedAuthPreviewBoundary)
    app.include_router(auth.router)
    app.include_router(health_router)
    @app.get('/api/v1/private-probe')
    async def private_probe(user=Depends(auth.current_user)):
        return user
    # Minimal test-only version of an already admitted read route. This does
    # NOT create or change an endpoint in the production ASGI application.
    @app.get('/api/v1/admin/dashboard')
    async def protected_dashboard(user=Depends(auth.current_user)):
        return {'property_code': user['property_code']}
    return app


class SharedAuthTests(unittest.TestCase):
    def setUp(self):
        self.hasher = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
        self.store = Store(self.hasher)
        self.patches = [patch.object(auth, 'MARINA_SHARED_AUTH_PREVIEW_ENABLED', True),
            patch.object(auth, 'MARINA_TENANT_CONTEXT_ENABLED', True),
            patch.object(auth, 'PROPERTY_CODE', 'UNUSED_GLOBAL'),
            patch.object(auth, 'COOKIE_SECURE', True),
            patch.object(auth, 'password_hasher', self.hasher),
            patch.dict('os.environ', APP_ENV='staging')]
        for p in self.patches: p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patches)])
        auth._preview_attempts.clear()
        self.app = make_app(self.store)
        self.client = TestClient(self.app, base_url='https://testserver')
        self.addCleanup(self.client.close)

    def login(self, code='HOTEL_A', password=None, **extra):
        return self.client.post('/api/v1/auth/login', json=dict(username='owner',
            password=password or 'Password-'+code, tenant_code='tenant_'+code[-1].lower(),
            property_code=code, **extra))

    def test_same_username_is_bound_to_each_hotel(self):
        for code in ('HOTEL_A', 'HOTEL_B'):
            response = self.login(code)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['property_id'], str(self.store.properties[code]))
            me = self.client.get('/api/v1/auth/me', headers={'X-Property-Id': str(uuid.uuid4()), 'X-Tenant-Id': str(uuid.uuid4())})
            self.assertEqual(me.status_code, 200)
            self.assertEqual(me.json()['property_code'], code)

    def test_readiness_does_not_require_or_disclose_a_global_hotel(self):
        response = self.client.get('/health/ready')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['mode'], 'shared_auth_preview')
        self.assertNotIn('property', response.json())

    def test_allowed_snapshot_401_and_unreviewed_503_are_distinct(self):
        # Shared boundary admission is NOT equivalent to authorization.
        # An expired/revoked session gets 401 on admitted management reads.
        # Unreviewed shared inbox, kitchen, dining and assistant routes must
        # remain hard 503 even when the owner has a valid session.
        route = '/api/v1/admin/dashboard'
        self.assertEqual(self.client.get(route).status_code, 401)
        self.assertEqual(self.login('HOTEL_A').status_code, 200)
        self.assertEqual(self.client.get(route).json(), {'property_code': 'HOTEL_A'})
        forbidden_shared = (
            ('GET', '/api/v1/admin/inbox/conversations'),
            ('GET', '/api/v1/kitchen/orders'),
            ('GET', '/api/v1/dining/floor'),
            ('GET', '/api/v1/assistant/capabilities'),
            ('PATCH', '/api/v1/ops/rooms/11111111-1111-4111-8111-111111111111/state'),
        )
        before = len(self.store.queries)
        for method, path in forbidden_shared:
            with self.subTest(path=path):
                response = self.client.request(method, path)
                self.assertEqual(response.status_code, 503)
        self.assertEqual(len(self.store.queries), before,
                         '503 middleware must reject requests before DB access')
        self.assertEqual(self.client.post('/api/v1/auth/logout').status_code, 204)
        self.assertEqual(self.client.get(route).status_code, 401)

    def test_shared_dashboard_never_falls_back_to_previous_hotel(self):
        route = '/api/v1/admin/dashboard'
        self.assertEqual(self.login('HOTEL_A').status_code, 200)
        self.assertEqual(self.client.get(route).json()['property_code'], 'HOTEL_A')
        self.assertEqual(self.client.post('/api/v1/auth/logout').status_code, 204)
        self.assertEqual(self.login('HOTEL_B').status_code, 200)
        self.assertEqual(self.client.get(route).json()['property_code'], 'HOTEL_B')
        self.store.active['HOTEL_B'] = False
        self.assertEqual(self.client.get(route).status_code, 401)
        self.assertNotEqual(self.client.get(route).status_code, 200)

    def test_other_hotel_password_cannot_authenticate(self):
        response = self.login('HOTEL_B', password='Password-HOTEL_A')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {'detail':'Invalid username or password'})
        self.assertFalse(self.store.sessions)

    def test_guessed_selector_and_missing_selector_have_generic_denial(self):
        for payload in ({'username':'owner','password':'Password-HOTEL_A'},
                        {'username':'owner','password':'Password-HOTEL_A','tenant_code':'missing','property_code':'HOTEL_A'}):
            r = self.client.post('/api/v1/auth/login', json=payload)
            self.assertEqual(r.status_code, 401)
            self.assertEqual(r.json()['detail'], 'Invalid username or password')

    def test_disabled_tenant_invalidates_existing_session(self):
        self.assertEqual(self.login().status_code, 200)
        self.store.active['HOTEL_A'] = False
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 401)
        self.assertEqual(self.login().status_code, 401)

    def test_staff_disabled_or_session_revoked_is_rejected(self):
        self.login()
        self.store.users['HOTEL_A']['isActive'] = False
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 401)
        self.store.users['HOTEL_A']['isActive'] = True
        self.client.post('/api/v1/auth/logout')
        self.assertTrue(all(s['revokedAt'] is not None for s in self.store.sessions.values()))

    def test_session_cannot_follow_changed_property_or_tenant(self):
        self.login()
        self.store.tenants['HOTEL_A'] = uuid.uuid4()
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 401)

    def test_tampered_cookie_is_rejected(self):
        self.login()
        token = self.client.cookies.get(auth.SESSION_COOKIE)
        self.client.cookies.clear()
        parts = token.split('.')
        parts[2] = str(self.store.properties['HOTEL_B'])
        self.client.cookies.set(auth.SESSION_COOKIE, '.'.join(parts))
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 401)

    def test_expired_and_legacy_sessions_cannot_enter_preview(self):
        self.login()
        next(iter(self.store.sessions.values()))['expiresAt'] = datetime.utcnow()-timedelta(seconds=1)
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 401)
        self.client.cookies.clear()
        self.client.cookies.set(auth.SESSION_COOKIE, 'legacy-random-token')
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 401)

    def test_other_http_routes_are_closed_before_handler_runs(self):
        self.login()
        before = len(self.store.queries)
        self.assertEqual(self.client.get('/api/v1/private-probe').status_code, 503)
        self.assertEqual(self.client.post('/api/v1/reservations', json={}).status_code, 503)
        self.assertEqual(len(self.store.queries), before)
        with self.assertRaises(Exception) as result:
            with self.client.websocket_connect('/ws/private'): pass
        self.assertEqual(result.exception.code, 1008)

    def test_flag_requires_staging_tenant_context_and_separate_runtime(self):
        for change in ('production', 'tenant_off', 'demo', 'hotel01'):
            with self.subTest(change=change):
                with patch.dict('os.environ', APP_ENV='production' if change=='production' else 'staging'), \
                     patch.object(auth, 'MARINA_TENANT_CONTEXT_ENABLED', change!='tenant_off'), \
                     patch.object(auth, 'PROPERTY_CODE', {'demo':'MARINA_DEMO','hotel01':'MARINA_HOTEL01'}.get(change,'UNUSED_GLOBAL')):
                    self.assertEqual(self.login().status_code, 503)

    def test_shared_auth_fails_closed_when_secure_cookie_is_disabled(self):
        # A staging operator must not accidentally deploy a shared tenant
        # session in a cookie that could be transmitted over plain HTTP.
        with patch.object(auth, 'COOKIE_SECURE', False):
            before = len(self.store.queries)
            for action in (
                lambda: self.login(),
                lambda: self.client.get('/health/ready'),
                lambda: self.client.get('/api/v1/auth/mode'),
            ):
                response = action()
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()['detail'], 'Shared authentication requires Secure session cookies')
            self.assertEqual(len(self.store.queries), before, 'Insecure shared auth must fail before database access')
            self.assertFalse(self.store.sessions)

        # Preserve single-property legacy behavior; the shared preview
        # security prerequisite must not change historical login policy.
        with patch.object(auth, 'COOKIE_SECURE', False), \
             patch.object(auth, 'MARINA_SHARED_AUTH_PREVIEW_ENABLED', False), \
             patch.object(auth, 'PROPERTY_CODE', 'HOTEL_A'):
            response = self.client.post('/api/v1/auth/login', json={
                'username': 'owner', 'password': 'Password-HOTEL_A'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['property_code'], 'HOTEL_A')

    def test_unknown_workspace_attempts_are_limited_before_database(self):
        payload={'username':'owner','password':'long-password','tenant_code':'missing','property_code':'HOTEL_A'}
        for _ in range(30): self.client.post('/api/v1/auth/login', json=payload)
        before=len(self.store.queries)
        self.assertEqual(self.client.post('/api/v1/auth/login', json=payload).status_code,401)
        self.assertEqual(len(self.store.queries),before)

    def test_legacy_mode_ignores_no_scope_and_preserves_original_boundary(self):
        with patch.object(auth,'MARINA_SHARED_AUTH_PREVIEW_ENABLED',False), patch.object(auth,'PROPERTY_CODE','HOTEL_A'):
            r=self.client.post('/api/v1/auth/login',json={'username':'owner','password':'Password-HOTEL_A'})
            self.assertEqual(r.status_code,200)
            self.assertEqual(self.client.get('/api/v1/auth/me').json()['property_code'],'HOTEL_A')
            self.assertEqual(self.login().status_code,422)


if __name__ == '__main__': unittest.main()
