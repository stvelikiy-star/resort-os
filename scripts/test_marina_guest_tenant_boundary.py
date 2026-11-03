"""Guest QR administration and review links must follow authenticated hotel IDs."""
from contextlib import asynccontextmanager
from pathlib import Path
import sys
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/api'))
from app import auth, guest_os, guest_stay_reviews as reviews


class Store:
    def __init__(self):
        self.tenants = [uuid.uuid4(), uuid.uuid4()]
        self.properties = {uuid.uuid4(): dict(code='HOTEL_'+suffix, name=suffix,
                           timezone='Asia/Bishkek') for suffix in ('A', 'B')}
        self.ids = list(self.properties)
        self.code_lookups = []
        self.room_lookups = []

    @asynccontextmanager
    async def acquire(self):
        yield self

    @asynccontextmanager
    async def transaction(self):
        yield self

    async def fetchval(self, query, *args):
        if 'JOIN tenants' in query:
            return args[0] if args in tuple(zip(self.ids, self.tenants)) else None
        if 'SELECT id FROM properties WHERE code=$1' in query:
            self.code_lookups.append(args[0])
            return next((key for key, row in self.properties.items() if row['code'] == args[0]), None)
        if 'SELECT code FROM properties WHERE id=$1' in query:
            return self.properties.get(args[0], {}).get('code')
        raise AssertionError('Unexpected property query')

    async def fetchrow(self, query, *args):
        if 'FROM properties' in query:
            if 'WHERE code=$1' in query:
                self.code_lookups.append(args[0])
                return next((dict(id=key, **row) for key, row in self.properties.items()
                             if row['code'] == args[0]), None)
            return dict(id=args[0], **self.properties[args[0]]) if args[0] in self.properties else None
        if 'FROM rooms' in query:
            self.room_lookups.append(args)
            return None
        raise AssertionError('Unexpected row query')

    async def fetch(self, query, *args):
        return []

    async def execute(self, query, *args):
        raise AssertionError('Denied cross-hotel operation must not write')


class GuestTenantTests(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.user = dict(id=str(uuid.uuid4()), role='OWNER', property_code='HOTEL_B',
                         property_id=str(self.store.ids[1]), tenant_id=str(self.store.tenants[1]))
        self.app = FastAPI()
        self.app.state.db = self.store
        self.app.include_router(guest_os.admin_router)
        self.app.include_router(reviews.router)
        self.app.dependency_overrides[guest_os.admin_access] = lambda: self.user
        self.flag = patch.object(auth, 'MARINA_TENANT_CONTEXT_ENABLED', True)
        self.flag.start()
        self.addCleanup(self.flag.stop)
        self.runtime = patch.object(guest_os, 'PROPERTY_CODE', 'HOTEL_A')
        self.runtime.start()
        self.addCleanup(self.runtime.stop)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def test_qr_list_uses_authenticated_hotel_despite_runtime_and_headers(self):
        response = self.client.get('/api/v1/admin/guest-os/room-qrs', headers={
            'X-Property-Id': str(self.store.ids[0]), 'X-Tenant-Id': str(self.store.tenants[0])})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['property'], 'HOTEL_B')
        self.assertEqual(self.store.code_lookups, [])

    def test_foreign_room_issue_and_rotation_never_write(self):
        room_id = uuid.uuid4()
        for action in ('issue', 'rotate'):
            with self.subTest(action=action):
                response = self.client.post(f'/api/v1/admin/guest-os/room-qrs/{room_id}/{action}')
                self.assertEqual(response.status_code, 404)
                self.assertEqual(self.store.room_lookups[-1], (room_id, self.store.ids[1]))

    def test_missing_tenant_context_is_denied_before_runtime_fallback(self):
        self.user.pop('tenant_id')
        response = self.client.get('/api/v1/admin/guest-os/room-qrs')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.store.code_lookups, [])

    def test_legacy_runtime_retains_its_existing_hotel_boundary(self):
        self.user.update(property_code='HOTEL_A', property_id=str(self.store.ids[0]),
                         tenant_id=str(self.store.tenants[0]))
        with patch.object(auth, 'MARINA_TENANT_CONTEXT_ENABLED', False), \
                patch.object(auth, 'PROPERTY_CODE', 'HOTEL_A'):
            response = self.client.get('/api/v1/admin/guest-os/room-qrs')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['property'], 'HOTEL_A')

    def test_guest_links_follow_verified_qr_hotel(self):
        verified = AsyncMock(return_value=({'propertyId': self.store.ids[1]}, {}, {}))
        rules = AsyncMock(return_value={'rules': {'review_google_url': 'https://maps.google.com/hotel-b'}})
        with patch.object(reviews, 'authorized_context', verified), patch.object(reviews, 'load_rules', rules):
            response = self.client.get('/api/v1/guest-os/rooms/test-token/review-links')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['google'], 'https://maps.google.com/hotel-b')
        rules.assert_awaited_once_with(self.store, 'HOTEL_B')

    def test_unverified_guest_cannot_read_any_hotel_links(self):
        with patch.object(reviews, 'authorized_context', AsyncMock(side_effect=HTTPException(401))), \
                patch.object(reviews, 'load_rules', AsyncMock()) as rules:
            response = self.client.get('/api/v1/guest-os/rooms/invalid/review-links')
        self.assertEqual(response.status_code, 401)
        rules.assert_not_awaited()

    def test_missing_qr_hotel_fails_closed_without_rules_fallback(self):
        verified = AsyncMock(return_value=({'propertyId': uuid.uuid4()}, {}, {}))
        with patch.object(reviews, 'authorized_context', verified), \
                patch.object(reviews, 'load_rules', AsyncMock()) as rules:
            response = self.client.get('/api/v1/guest-os/rooms/test-token/review-links')
        self.assertEqual(response.status_code, 404)
        rules.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
