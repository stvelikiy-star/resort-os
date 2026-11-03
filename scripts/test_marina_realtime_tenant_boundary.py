"""WebSocket snapshots must follow current session identity and permissions."""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest
import uuid
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/api'))
from app import auth, realtime, dining_realtime, websocket_security


class Store:
    def __init__(self):
        self.properties = {code: uuid.uuid4() for code in ('HOTEL_A', 'HOTEL_B')}
        self.tenants = {code: uuid.uuid4() for code in self.properties}
        self.active = {code: True for code in self.properties}
        self.rows, self.tokens = {}, {}
        self.reads = []
        self.connections = 0
        for code, pid in self.properties.items():
            token = f'ms1.{self.tenants[code]}.{pid}.' + 'x'*64
            self.tokens[code] = token
            self.rows[auth.hash_session_token(token)] = dict(
                session_id=uuid.uuid4(), user_id=uuid.uuid4(), username='same-user',
                displayName=code, role='MANAGER', isActive=True,
                expiresAt=datetime.utcnow()+timedelta(hours=1), revokedAt=None,
                property_code=code, property_id=pid, tenant_id=self.tenants[code],
                module_permissions=['PMS','DINING'], module_permissions_custom=True)

    @asynccontextmanager
    async def acquire(self):
        self.connections += 1
        try:
            yield self
        finally:
            self.connections -= 1

    async def fetchrow(self, query, *args):
        if 'FROM auth_sessions' in query:
            row = self.rows.get(args[0])
            if row and "t.status='ACTIVE'" in query and not self.active[row['property_code']]:
                return None
            return row
        raise AssertionError('Unexpected row lookup')

    async def fetchval(self, query, *args):
        if 'JOIN tenants' in query:
            return next((pid for code, pid in self.properties.items()
                         if (pid, self.tenants[code]) == args and self.active[code]), None)
        if 'FROM properties WHERE code=$1' in query:
            return self.properties.get(args[0])
        raise AssertionError('Unexpected property lookup')

    async def execute(self, query, *args):
        return 'UPDATE 1'

    async def fetch(self, query, *args):
        self.reads.append(args[0])
        if 'FROM rooms r' in query:
            return [dict(id=args[0], code='101', name='Own room', buildingOrZone=None,
                         floorLabel=None, bedConfiguration=None, operational_state='CLEAN',
                         room_type_code='STANDARD', room_type_name='Standard')]
        if 'FROM inventory_blocks' in query or 'FROM kitchen_orders' in query:
            return []
        raise AssertionError('Unexpected snapshot query')


class RealtimeTenantTests(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.app = FastAPI()
        self.app.state.db = self.store
        self.app.include_router(realtime.router)
        self.app.include_router(dining_realtime.router)
        self.patches = [
            patch.object(auth, 'MARINA_SHARED_AUTH_PREVIEW_ENABLED', True),
            patch.object(auth, 'MARINA_TENANT_CONTEXT_ENABLED', True),
            patch.object(auth, 'PROPERTY_CODE', 'HOTEL_A'),
            patch.object(realtime, 'PROPERTY_CODE', 'HOTEL_A'),
            patch.object(dining_realtime, 'PROPERTY_CODE', 'HOTEL_A'),
            patch.object(realtime, 'POLL_SECONDS', 0.25),
            patch.object(dining_realtime, 'POLL_SECONDS', 0.25),
            patch.object(websocket_security, 'WS_ENFORCE_SAME_ORIGIN', True),
            patch.dict('os.environ', APP_ENV='staging'),
        ]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def headers(self, code='HOTEL_A'):
        return {'Cookie': auth.SESSION_COOKIE+'='+self.store.tokens[code],
                'Origin':'http://testserver', 'X-Property-Id':str(self.store.properties['HOTEL_A'])}

    def row(self, code='HOTEL_A'):
        return self.store.rows[auth.hash_session_token(self.store.tokens[code])]

    def test_shared_pms_snapshots_use_each_sessions_hotel(self):
        for code in ('HOTEL_A','HOTEL_B'):
            with self.subTest(code=code), self.client.websocket_connect('/ws/pms/grid', headers=self.headers(code)) as ws:
                body = ws.receive_json()
                self.assertEqual(body['data']['property'], code)
                self.assertEqual(body['data']['rooms'][0]['id'], str(self.store.properties[code]))

    def test_shared_dining_query_is_scoped_to_session_hotel(self):
        with self.client.websocket_connect('/ws/dining/ready', headers=self.headers('HOTEL_B')) as ws:
            self.assertEqual(ws.receive_json()['type'], 'dining.ready.snapshot')
        self.assertTrue(self.store.reads)
        self.assertEqual(set(self.store.reads), {self.store.properties['HOTEL_B']})

    def test_removed_section_is_denied_even_when_role_still_matches(self):
        self.row()['module_permissions'] = []
        for path in ('/ws/pms/grid','/ws/dining/ready'):
            with self.subTest(path=path):
                with self.assertRaises(WebSocketDisconnect) as error:
                    with self.client.websocket_connect(path, headers=self.headers()):
                        pass
                self.assertEqual(error.exception.code, 4403)

    def test_open_sockets_close_after_revocation_or_permission_removal(self):
        for path in ('/ws/pms/grid','/ws/dining/ready'):
            for field, value, close_code in (('revokedAt', datetime.utcnow(), 4401),
                                              ('module_permissions', [], 4403)):
                with self.subTest(path=path, field=field):
                    self.row().update(revokedAt=None, module_permissions=['PMS','DINING'])
                    with self.client.websocket_connect(path, headers=self.headers()) as ws:
                        ws.receive_json()
                        self.row()[field] = value
                        with self.assertRaises(WebSocketDisconnect) as error:
                            # A heartbeat is also a protected frame. It must not
                            # be delivered after the next permission recheck.
                            ws.receive_json()
                        self.assertEqual(error.exception.code, close_code)

    def test_tampered_shared_token_and_wrong_origin_are_denied(self):
        headers = self.headers()
        parts = self.store.tokens['HOTEL_A'].split('.')
        parts[2] = str(self.store.properties['HOTEL_B'])
        headers['Cookie'] = auth.SESSION_COOKIE+'='+'.'.join(parts)
        with self.assertRaises(WebSocketDisconnect) as error:
            with self.client.websocket_connect('/ws/pms/grid', headers=headers):
                pass
        self.assertEqual(error.exception.code, 4401)
        headers = self.headers()
        headers['Origin'] = 'https://foreign.example'
        with self.assertRaises(WebSocketDisconnect) as error:
            with self.client.websocket_connect('/ws/pms/grid', headers=headers):
                pass
        self.assertEqual(error.exception.code, 4403)

    def test_blocked_shared_tenant_is_denied(self):
        self.store.active['HOTEL_A'] = False
        with self.assertRaises(WebSocketDisconnect) as error:
            with self.client.websocket_connect('/ws/pms/grid', headers=self.headers()):
                pass
        self.assertEqual(error.exception.code, 4401)

    def test_legacy_sessions_keep_their_pinned_hotel_and_validate_active_tenant(self):
        tokens = {code: 'legacy-'+code+'x'*32 for code in self.store.properties}
        for code, token in tokens.items():
            self.store.rows[auth.hash_session_token(token)] = self.row(code)
        with patch.object(auth, 'MARINA_SHARED_AUTH_PREVIEW_ENABLED', False):
            for path in ('/ws/pms/grid','/ws/dining/ready'):
                headers = {**self.headers(), 'Cookie':auth.SESSION_COOKIE+'='+tokens['HOTEL_A']}
                with self.client.websocket_connect(path, headers=headers) as ws:
                    self.assertIn('type', ws.receive_json())
                headers['Cookie'] = auth.SESSION_COOKIE+'='+tokens['HOTEL_B']
                with self.assertRaises(WebSocketDisconnect) as error:
                    with self.client.websocket_connect(path, headers=headers):
                        pass
                self.assertEqual(error.exception.code, 4401)
            self.store.active['HOTEL_A'] = False
            with self.assertRaises(WebSocketDisconnect) as error:
                with self.client.websocket_connect('/ws/pms/grid', headers={
                    **self.headers(), 'Cookie':auth.SESSION_COOKIE+'='+tokens['HOTEL_A']}):
                    pass
            self.assertEqual(error.exception.code, 4401)

    def test_open_streams_release_connections_between_polls(self):
        for path in ('/ws/pms/grid','/ws/dining/ready'):
            with self.subTest(path=path):
                with self.client.websocket_connect(path, headers=self.headers()) as ws:
                    ws.receive_json()
                    self.assertEqual(self.store.connections, 0)


if __name__ == '__main__':
    unittest.main()
