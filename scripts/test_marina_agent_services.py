"""Request-level security regressions; fake DB, not PostgreSQL E2E evidence."""
import sys
import unittest
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/api'))
from app import guest_services as services

PID, AGENT, OTHER, RID, UID = [uuid.uuid4() for _ in range(5)]


class Conn:
    def __init__(self):
        self.active = True
        self.owner = AGENT
        self.property = PID
        self.duplicate = False
        self.writes = []
        self.reservation_args = None
        self.list_args = None

    async def fetchval(self, query, *args):
        return RID if args == (RID, self.property, self.owner) else None

    async def fetch(self, query, *args):
        self.list_args = args
        assert 'res."agentId"=$13' in query and 'ANY($14::text[])' in query
        return [{'id': uuid.uuid4(), 'reservationId': RID, 'serviceCode': 'TRANSFER', 'status': 'DONE',
                 'serviceDate': date(2027, 1, 1), 'serviceTime': '10:30', 'description': 'Meeting point'}]

    @asynccontextmanager
    async def transaction(self):
        yield

    async def fetchrow(self, query, *args):
        if 'booking_agents' in query:
            return {'agent_id': AGENT, 'status': 'ACTIVE' if self.active else 'INACTIVE'}
        if 'FOR UPDATE OF r' in query:
            self.reservation_args = args
            if args[1] != self.property or (args[2] is not None and args[2] != self.owner):
                return None
            return {'id': RID, 'bookingNumber': 'AGENT-TEST', 'status': 'GUARANTEED',
                    'checkIn': date(2027, 1, 1), 'checkOut': date(2027, 1, 4)}
        if "status IN ('OPEN','IN_PROGRESS')" in query:
            return {'id': uuid.uuid4(), 'status': 'OPEN', 'source': 'PMS_GUEST_SERVICE'} if self.duplicate else None
        return {'id': str(uuid.uuid4()), 'reservation_id': str(RID), 'service_code': 'TRANSFER'}

    async def execute(self, query, *args):
        self.writes.append(query)


class Pool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


class AgentServices(unittest.TestCase):
    def setUp(self):
        self.user = {'id': UID, 'role': 'AGENT', 'module_permissions': ['PMS']}
        self.conn = Conn()
        self.app = FastAPI()
        self.app.include_router(services.router)
        self.app.state.db = Pool(self.conn)
        self.app.dependency_overrides[services.current_user] = lambda: self.user
        self.client = TestClient(self.app)
        self.property_patch = patch.object(services, 'property_id', return_value=PID)
        self.property_patch.start()
        self.addCleanup(self.property_patch.stop)
        # Serialization isn't under test; preserve the actual SQL/authorization flow.
        self.row_patch = patch.object(services, 'row_to_item', side_effect=lambda row: row)
        self.row_patch.start()
        self.addCleanup(self.row_patch.stop)

    def post(self, **overrides):
        return self.client.post('/api/v1/admin/guest-services', json={
            'reservation_id': str(RID), 'service_code': 'TRANSFER', **overrides})

    def test_active_linked_agent_can_create_own_service_without_payment(self):
        result = self.post()
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(self.conn.reservation_args, (RID, PID, AGENT))
        self.assertTrue(any('INSERT INTO operational_tasks' in q for q in self.conn.writes))
        self.assertTrue(any('INSERT INTO audit_logs' in q for q in self.conn.writes))
        self.assertFalse(any('INSERT INTO payments' in q for q in self.conn.writes))

    def test_other_agent_or_other_property_is_not_found_and_not_written(self):
        for attr, value in [('owner', OTHER), ('property', uuid.uuid4())]:
            with self.subTest(attr=attr):
                old = getattr(self.conn, attr)
                setattr(self.conn, attr, value)
                self.assertEqual(self.post().status_code, 404)
                self.assertEqual(self.conn.writes, [])
                setattr(self.conn, attr, old)

    def test_revoked_agent_link_blocks_write(self):
        self.conn.active = False
        self.assertEqual(self.post().status_code, 403)
        self.assertIsNone(self.conn.reservation_args)
        self.assertEqual(self.conn.writes, [])

    def test_pms_revocation_blocks_write_even_with_services_grant(self):
        self.user['module_permissions'] = ['SERVICES']
        self.assertEqual(self.post().status_code, 403)
        self.assertEqual(self.conn.writes, [])

    def test_operational_services_and_priority_escalation_denied(self):
        for payload in [{'service_code': 'MAINTENANCE'}, {'service_code': 'TOWELS'}, {'priority': 'URGENT'}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.post(**payload).status_code, 403)
                self.assertEqual(self.conn.writes, [])

    def test_duplicate_stays_conflict_with_no_second_task(self):
        self.conn.duplicate = True
        self.assertEqual(self.post().status_code, 409)
        self.assertFalse(any('INSERT' in q for q in self.conn.writes))

    def test_agent_cannot_read_hotel_queue_even_with_custom_services_grant(self):
        self.user.update(module_permissions=['PMS', 'SERVICES'], module_permissions_custom=True)
        self.assertEqual(self.client.get('/api/v1/admin/guest-services').status_code, 403)
        self.assertEqual(self.conn.writes, [])

    def test_owner_existing_creation_does_not_require_agent_link(self):
        self.user.update(role='OWNER', module_permissions=['SERVICES'])
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.conn.reservation_args, (RID, PID, None))

    def test_agent_reads_only_scoped_service_facts(self):
        result = self.client.get('/api/v1/admin/guest-services', params={'reservation_id': str(RID), 'status': 'ALL'})
        self.assertEqual(result.status_code, 200, result.text)
        body = result.json()
        self.assertEqual(body['reservation_id'], str(RID))
        self.assertEqual(body['items'][0]['status'], 'DONE')
        self.assertEqual(set(body['items'][0]), {'id', 'reservation_id', 'service_code', 'status', 'service_date', 'service_time', 'description'})
        self.assertEqual(self.conn.list_args[12], AGENT)
        self.assertEqual(set(self.conn.list_args[13]), services.AGENT_SERVICE_CODES)
        self.assertEqual(self.conn.writes, [])

    def test_agent_cannot_read_foreign_reservation_or_with_revoked_link(self):
        for attribute, value, status in [('owner', OTHER, 404), ('property', OTHER, 404), ('active', False, 403)]:
            old = getattr(self.conn, attribute)
            with self.subTest(attribute=attribute):
                setattr(self.conn, attribute, value)
                result = self.client.get('/api/v1/admin/guest-services', params={'reservation_id': str(RID)})
                self.assertEqual(result.status_code, status)
                self.assertIsNone(self.conn.list_args)
            setattr(self.conn, attribute, old)

    def test_agent_read_requires_pms_and_reports_truncation(self):
        self.user['module_permissions'] = []
        self.assertEqual(self.client.get('/api/v1/admin/guest-services', params={'reservation_id': str(RID)}).status_code, 403)
        self.user['module_permissions'] = ['PMS']
        with patch.object(self.conn, 'fetch', return_value=[{
            'id': uuid.uuid4(), 'reservationId': RID, 'serviceCode': 'TRANSFER', 'status': 'OPEN',
            'serviceDate': None, 'serviceTime': None, 'description': None,
        } for _ in range(2)]):
            result = self.client.get('/api/v1/admin/guest-services', params={'reservation_id': str(RID), 'limit': 1})
            self.assertEqual(result.status_code, 200)
            self.assertTrue(result.json()['preview_truncated'])
            self.assertEqual(len(result.json()['items']), 1)


if __name__ == '__main__':
    unittest.main()
