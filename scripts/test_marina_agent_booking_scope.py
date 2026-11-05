"""P0 linked agent: strict hotel-local ACTIVE membership and booking ceilings."""
import asyncio
import sys
import unittest
import uuid
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

from fastapi import HTTPException
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from app import pms_reservation_create as booking, staff_control as staff  # noqa: E402


class FakeConn:
    def __init__(self, agent, status="ACTIVE", property_id=None):
        self.agent = agent
        self.status = status
        self.property_id = property_id
        self.last_args = None

    async def fetchval(self, query, *args):
        self.last_args = args
        if args[0] == self.agent and (
            self.property_id is None or args[1] == self.property_id
        ):
            return self.status
        return None

    async def fetchrow(self, query, *args):
        self.last_args = args
        if self.status == "ACTIVE":
            return {"agent_id": self.agent, "status": "ACTIVE"}
        if self.status == "INACTIVE":
            return {"agent_id": self.agent, "status": "INACTIVE"}
        return None


class LinkedAgentP0(unittest.TestCase):
    def setUp(self):
        self.agent = uuid.uuid4()
        self.property_id = uuid.uuid4()
        self.other = uuid.uuid4()

    def preview(self, **overrides):
        args = {
            "room_id": uuid.uuid4(), "check_in": date(2027, 1, 10),
            "check_out": date(2027, 1, 12), "adults": 2,
            "guest_phone": "+996555123123",
        }
        return booking.GridReservationPreviewPayload(**(args | overrides))

    def test_agent_booking_rejects_all_manager_or_hold_overrides(self):
        with self.assertRaises(HTTPException) as e:
            booking.enforce_agent_booking_scope(self.preview(manager_total_kgs=1), self.agent)
        self.assertEqual(e.exception.status_code, 403)
        for kwargs in (
            {"extra_bed_count": 1, "extra_bed_unit_kgs": 500},
            {"extra_bed_unit_kgs": 500},
            {"discount_percent": 10}, {"discount_reason": "STAFF_OVERRIDE"},
            {"hold_id": uuid.uuid4()}, {"agent_id": self.other},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(HTTPException) as caught:
                booking.enforce_agent_booking_scope(self.preview(**kwargs), self.agent)
            self.assertEqual(caught.exception.status_code, 403)
        allowed = booking.enforce_agent_booking_scope(self.preview(), self.agent)
        self.assertEqual(allowed.agent_id, self.agent)
        self.assertEqual(allowed.discount_percent, 0)
        self.assertIsNone(allowed.guest_phone)
        self.assertIsNone(allowed.manager_total_kgs)

    def test_membership_is_fetched_again_at_every_preview_and_commit(self):
        user = {"role": "AGENT", "id": str(uuid.uuid4())}
        for status, expected in (("ACTIVE", self.agent), ("INACTIVE", None),
                                 (None, None)):
            conn = FakeConn(self.agent, status=status)
            if expected is not None:
                found = asyncio.run(booking.linked_agent_id_for_user(
                    conn, self.property_id, user))
                self.assertEqual(found, expected)
            else:
                with self.assertRaises(HTTPException) as denied:
                    asyncio.run(booking.linked_agent_id_for_user(
                        conn, self.property_id, user))
                self.assertEqual(denied.exception.status_code, 403)
            self.assertEqual(conn.last_args[1], self.property_id)

    def test_only_owner_can_bind_active_same_hotel_agent(self):
        conn = FakeConn(self.agent, property_id=self.property_id)
        result = asyncio.run(staff.validate_owner_agent_binding(
            conn, self.property_id, "AGENT", self.agent, active=True))
        self.assertEqual(result, self.agent)
        self.assertEqual(conn.last_args, (self.agent, self.property_id))
        for pid, aid, active in (
            (self.property_id, self.other, True),
            (uuid.uuid4(), self.agent, True),
            (self.property_id, None, True),
        ):
            with self.subTest(pid=pid, aid=aid), self.assertRaises(HTTPException) as denied:
                asyncio.run(staff.validate_owner_agent_binding(
                    conn, pid, "AGENT", aid, active=active))
            self.assertEqual(denied.exception.status_code, 422)
        for role in ("OWNER", "RECEPTION", "COOK"):
            with self.subTest(role=role), self.assertRaises(HTTPException):
                asyncio.run(staff.validate_owner_agent_binding(
                    conn, self.property_id, role, self.agent, active=True))
        inactive = FakeConn(self.agent, status="INACTIVE", property_id=self.property_id)
        with self.assertRaises(HTTPException):
            asyncio.run(staff.validate_owner_agent_binding(
                inactive, self.property_id, "AGENT", self.agent, active=True))
        self.assertEqual(asyncio.run(staff.validate_owner_agent_binding(
            inactive, self.property_id, "AGENT", self.agent, active=False)), self.agent)

    def test_staff_create_requires_valid_binding(self):
        base = {
            "username": "synthetic-agent", "display_name": "Synthetic Agent",
            "password": "synthetic-ci-only-Agent-Password-123",
            "role": "AGENT",
        }
        with self.assertRaises(ValidationError):
            staff.StaffCreate(**base)
        created = staff.StaffCreate(**(base | {"booking_agent_id": self.agent}))
        self.assertEqual(created.booking_agent_id, self.agent)
        with self.assertRaises(ValidationError):
            staff.StaffCreate(**(base | {"role": "MAID",
                                         "booking_agent_id": self.agent}))
        staff.StaffPatch(role="AGENT", booking_agent_id=self.agent)
        self.assertIn("booking_agent_id", staff.StaffPatch(booking_agent_id=None).model_fields_set)

    def test_canonical_routes_are_reused(self):
        src = (Path(__file__).resolve().parents[1] /
               "services/api/app/pms_reservation_create.py").read_text()
        self.assertEqual(src.count('@router.post("/new/preview")'), 1)
        self.assertEqual(src.count('@router.post("/new/commit"'), 1)
        self.assertIn('AGENT_ACCOUNT_NOT_LINKED', src)
        self.assertIn('AGENT_HOLD_CONFIRM_FORBIDDEN', src)


if __name__ == "__main__":
    unittest.main()
