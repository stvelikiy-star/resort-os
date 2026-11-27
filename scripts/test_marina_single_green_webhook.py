"""Synthetic single-property callback admission; no live WhatsApp or database."""
import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from app import green_api_webhook as g

SECRET = "synthetic_callback_secret_1234567890"
ENV = {
    "PROPERTY_CODE": "ASKA_TASH",
    "GREEN_API_PROPERTY_CODE": "ASKA_TASH",
    "GREEN_API_PROPERTY_ID": "12345678-1234-4234-8234-123456789abc",
    "ENABLE_GREEN_API_CONNECTION": "true",
    "ENABLE_GREEN_API_SINGLE_WEBHOOK": "true",
    "GREEN_API_ID_INSTANCE": "7103000000",
    "GREEN_API_URL": "https://7103.api.greenapi.com",
    "GREEN_API_TOKEN_INSTANCE": "synthetic_provider_token",
    "GREEN_API_WEBHOOK_TOKEN": SECRET,
    "AUTOMATION_SERVICE_KEY": "synthetic_automation_service_key",
}


class SingleHotelWebhookTests(unittest.TestCase):
    def identity(self, changes=None, secret=SECRET):
        with patch.dict(os.environ, {**ENV, **(changes or {})}, clear=True):
            return g._bearer_identity("Bearer " + secret)

    def test_hotel_bound(self):
        service = self.identity()
        self.assertEqual(service["property_code"], "ASKA_TASH")
        self.assertEqual(service["channel_code"], "GREEN_7103000000")
        self.assertEqual(service["external_account_id"], "7103000000")
        self.assertEqual(service["bound_property_id"], ENV["GREEN_API_PROPERTY_ID"])

    def test_disabled_wrong_hotel_or_shared_mode(self):
        for change in (
            {"ENABLE_GREEN_API_SINGLE_WEBHOOK": "false"},
            {"ENABLE_GREEN_API_CONNECTION": "false"},
            {"GREEN_API_PROPERTY_CODE": "HOTEL_B"},
            {"MARINA_TENANT_CONTEXT_ENABLED": "true"},
            {"MARINA_SHARED_AUTH_PREVIEW_ENABLED": "true"},
            {"MARINA_SHARED_GREEN_RC7_ENABLED": "true"},
            {"MARINA_SHARED_GREEN_RC8_ENABLED": "true"},
            {"PROPERTY_CODE": "MARINA_DEMO", "GREEN_API_PROPERTY_CODE": "MARINA_DEMO"},
            {"GREEN_API_PROPERTY_ID": "invalid"},
            {"GREEN_API_WEBHOOK_TOKEN": ""},
            {"GREEN_API_TOKEN_INSTANCE": SECRET},
            {"AUTOMATION_SERVICE_KEY": SECRET},
        ):
            with self.subTest(change=change), self.assertRaises(HTTPException) as err:
                self.identity(change)
            self.assertEqual(err.exception.status_code, 503)

    def test_wrong_bearer(self):
        with self.assertRaises(HTTPException) as err:
            self.identity(secret="incorrect_callback_secret_123456789")
        self.assertEqual(err.exception.status_code, 401)

    def test_instance_mismatch(self):
        service = self.identity()
        g._valid_instance({"instanceData": {"idInstance": 7103000000, "typeInstance": "whatsapp"}}, service)
        with self.assertRaises(HTTPException) as err:
            g._valid_instance({"instanceData": {"idInstance": 7103000001, "typeInstance": "whatsapp"}}, service)
        self.assertEqual(err.exception.status_code, 403)

    def test_db_property_uuid_must_match(self):
        service = self.identity()
        conn = SimpleNamespace(fetchval=AsyncMock(return_value=ENV["GREEN_API_PROPERTY_ID"]))
        manager = MagicMock()
        manager.__aenter__ = AsyncMock(return_value=conn)
        manager.__aexit__ = AsyncMock(return_value=False)
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=SimpleNamespace(acquire=lambda: manager))))
        asyncio.run(g._verify_active_provider_hotel(request, service))
        conn.fetchval.assert_awaited_once_with("SELECT id FROM properties WHERE code=$1", "ASKA_TASH")
        for pid in (None, "22345678-1234-4234-8234-123456789abc"):
            conn.fetchval.return_value = pid
            with self.assertRaises(HTTPException) as err:
                asyncio.run(g._verify_active_provider_hotel(request, service))
            self.assertEqual(err.exception.status_code, 503)

    def test_inbound_uses_canonical_inbox_model(self):
        service = self.identity()
        payload = g._incoming({
            "idMessage": "synthetic_message_1",
            "timestamp": 1700000000,
            "senderData": {"chatId": "996555000000@c.us", "sender": "996555000000@c.us"},
            "messageData": {"typeMessage": "textMessage", "textMessageData": {"textMessage": "Hello"}},
        }, service)
        self.assertEqual(payload.channel_code, service["channel_code"])
        self.assertEqual(payload.external_account_id, service["external_account_id"])
        self.assertEqual(payload.idempotency_key, "green7:in:synthetic_message_1")
        self.assertEqual(payload.direction, "INBOUND")

if __name__ == "__main__":
    unittest.main()
