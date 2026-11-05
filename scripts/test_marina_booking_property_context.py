"""Tenant-bound reservation property regression checks.

The real PostgreSQL / HTTP acceptance remains in marina_two_property_restore_e2e.py.
This test catches accidental reintroduction of property-code-based booking lookups.
"""
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app import pms_reservation_create as booking  # noqa: E402


class FakeConn:
    def __init__(self, row):
        self.row = row
        self.requests = []

    async def fetchrow(self, statement, *params):
        self.requests.append((statement, params))
        return self.row


class BookingPropertyContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_property_context_uses_only_trusted_session_id(self):
        property_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        user = {
            "property_id": str(property_id), "tenant_id": str(tenant_id),
            "property_code": "FORGED_OTHER_HOTEL", "role": "OWNER"
        }
        conn = FakeConn({"id": property_id, "timezone": "Asia/Bishkek", "currency": "KGS"})

        async def verified_property(context_conn, context_user):
            self.assertIs(context_conn, conn)
            self.assertIs(context_user, user)
            return property_id

        with patch.object(booking, "trusted_property_id", side_effect=verified_property) as bound:
            result = await booking.property_context(conn, user)
        self.assertEqual(result["id"], property_id)
        bound.assert_awaited_once()
        self.assertEqual(len(conn.requests), 1)
        statement, params = conn.requests[0]
        self.assertIn("WHERE id=$1", statement)
        self.assertEqual(params, (property_id,))
        self.assertNotIn("FORGED_OTHER_HOTEL", str(conn.requests))

    async def test_missing_trusted_property_fails_closed(self):
        pid = uuid.uuid4()
        conn = FakeConn(None)
        with patch.object(booking, "trusted_property_id", return_value=pid):
            with self.assertRaises(HTTPException) as err:
                await booking.property_context(conn, {"property_id": str(pid)})
        self.assertEqual(err.exception.status_code, 503)

    def test_all_booking_callers_use_authenticated_user(self):
        for path, count in (
            ("services/api/app/pms_reservation_create.py", 3),
            ("services/api/app/group_bookings.py", 3),
        ):
            source = (ROOT / path).read_text(encoding="utf-8")
            self.assertEqual(source.count("await property_context(conn, user)"), count, path)
            self.assertNotIn('property_context(conn, user["property_code"])', source)


if __name__ == "__main__":
    unittest.main()
