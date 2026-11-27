"""Offline single-property outbound binding regression tests."""
import asyncio
import os
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from app import green_outbound as out
from test_marina_single_green_webhook import ENV


class SingleHotelOutboundTests(unittest.TestCase):
    def setUp(self):
        self.env = {**ENV, "ENABLE_GREEN_API_SINGLE_OUTBOUND": "true"}
        self.user = {"id": "staff-1", "role": "OWNER", "property_code": "ASKA_TASH"}
        self.pid = uuid.UUID(ENV["GREEN_API_PROPERTY_ID"])
        self.cid = uuid.uuid4()
        self.row = {"channel_kind": "WHATSAPP", "channel_code": "GREEN_7103000000",
                    "external_account_id": "7103000000", "externalConversationId": "996555000000@c.us",
                    "assignedToId": "staff-1"}
        self.conn = SimpleNamespace(fetchrow=AsyncMock(return_value=self.row))
        self.manager = MagicMock()
        self.manager.__aenter__ = AsyncMock(return_value=self.conn)
        self.manager.__aexit__ = AsyncMock(return_value=False)
        self.request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=SimpleNamespace(acquire=lambda: self.manager))))

    def test_outbound_requires_separate_opt_in(self):
        with patch.dict(os.environ, {**self.env, "ENABLE_GREEN_API_SINGLE_OUTBOUND": "false"}, clear=True):
            with self.assertRaises(HTTPException) as err:
                out.single_outbound_binding(self.user)
            self.assertEqual(err.exception.status_code, 503)

    def test_outbound_requires_callback_binding(self):
        with patch.dict(os.environ, {**self.env, "ENABLE_GREEN_API_SINGLE_WEBHOOK": "false"}, clear=True):
            with self.assertRaises(HTTPException):
                out.single_outbound_binding(self.user)

    def test_valid_binding_and_foreign_staff_denied(self):
        with patch.dict(os.environ, self.env, clear=True):
            self.assertEqual(out.single_outbound_binding(self.user)["bound_property_id"], str(self.pid))
            with self.assertRaises(HTTPException) as err:
                out.single_outbound_binding({**self.user, "property_code": "OTHER"})
            self.assertEqual(err.exception.status_code, 403)

    def assert_send_denied(self, status, user=None, pid=None, row=None):
        self.conn.fetchrow.return_value = row if row is not None else self.row
        with patch.dict(os.environ, self.env, clear=True), patch.object(out, "trusted_property_id", AsyncMock(return_value=pid or self.pid)), patch.object(out, "_provider_send", AsyncMock()) as provider:
            with self.assertRaises(HTTPException) as err:
                asyncio.run(out.send_green_text(self.cid, "synthetic", self.request, user or self.user, "test-key-123"))
            self.assertEqual(err.exception.status_code, status)
            provider.assert_not_awaited()

    def test_wrong_database_uuid(self):
        self.assert_send_denied(409, pid=uuid.uuid4())

    def test_wrong_conversation_channel(self):
        self.assert_send_denied(409, row={**self.row, "channel_code": "OTHER"})

    def test_wrong_provider_account(self):
        self.assert_send_denied(409, row={**self.row, "external_account_id": "7103000001"})

    def test_reception_must_claim(self):
        self.assert_send_denied(403, user={**self.user, "role": "RECEPTION"}, row={**self.row, "assignedToId": "staff-2"})

    def test_unprivileged_staff_cannot_send(self):
        self.assert_send_denied(403, user={**self.user, "role": "COOK"})


if __name__ == "__main__":
    unittest.main()
