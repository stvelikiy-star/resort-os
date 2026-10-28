"""Actual FastAPI RBAC and GreenAPI transport with synthetic provider responses."""
import base64
import logging
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.auth import current_user
from app import whatsapp_connection as wa

TOKEN = "synthetic_provider_token_never_real"
ENV = {"ENABLE_GREEN_API_CONNECTION": "true", "GREEN_API_PROPERTY_CODE": "HOTEL_A",
       "PROPERTY_CODE": "HOTEL_A", "MARINA_TENANT_CONTEXT_ENABLED": "false",
       "GREEN_API_URL": "https://7103.api.greenapi.com", "GREEN_API_ID_INSTANCE": "7103000000",
       "GREEN_API_TOKEN_INSTANCE": TOKEN}
PNG = base64.b64encode(b"\x89PNG\r\n\x1a\nsynthetic-only").decode()


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        wa._windows.clear()
        self.user = {"id": str(uuid.uuid4()), "role": "OWNER", "property_code": "HOTEL_A"}
        self.app = FastAPI(); self.app.include_router(wa.router)
        self.app.dependency_overrides[current_user] = lambda: self.user

    def call(self, body, path="", env=None, status=200):
        seen = []
        def handler(request):
            seen.append(request)
            return httpx.Response(status, json=body)
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with patch.dict(os.environ, {**ENV, **(env or {})}), \
             patch.object(wa.httpx, "AsyncClient", return_value=client), TestClient(self.app) as api:
            result = (api.post if path else api.get)("/api/v1/admin/whatsapp/connection" + path)
        return result, seen

    def test_disabled_never_calls_provider(self):
        result, seen = self.call({}, env={"ENABLE_GREEN_API_CONNECTION": "false"})
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json()["configured"]); self.assertEqual(seen, [])
        self.assertIn("no-store", result.headers["cache-control"])

    def test_only_owner_can_access_even_with_custom_module_grant(self):
        for role in ("MANAGER", "RECEPTION", "AGENT", "MAID", "TECHNICIAN", "COOK", "WAITER"):
            self.user.update(role=role, module_permissions=["WHATSAPP"], module_permissions_custom=True)
            for path in ("", "/qr"):
                result, seen = self.call({}, path)
                self.assertEqual(result.status_code, 403); self.assertEqual(seen, [])

    def test_missing_credentials_or_wrong_binding_never_calls_provider(self):
        for env in ({"GREEN_API_PROPERTY_CODE": "HOTEL_B"}, {"PROPERTY_CODE": "HOTEL_B"},
                    {"MARINA_TENANT_CONTEXT_ENABLED": "true"}, {"GREEN_API_TOKEN_INSTANCE": ""},
                    {"GREEN_API_URL": "https://api.greenapi.com.evil.test"},
                    {"GREEN_API_URL": "http://api.green-api.com"},
                    {"GREEN_API_URL": "https://api.green-api.com/private"},
                    {"GREEN_API_URL": "https://user@api.green-api.com"},
                    {"GREEN_API_URL": "https://[invalid"}):
            result, seen = self.call({}, env=env)
            self.assertEqual(result.status_code, 503, env); self.assertEqual(seen, [])

    def test_state_does_not_claim_delivery_or_ai(self):
        for state in wa.STATES:
            result, seen = self.call({"stateInstance": state, "secret": TOKEN})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["account_authorized"], state == "authorized")
            self.assertFalse(result.json()["messaging_verified"])
            self.assertFalse(result.json()["ai_auto_send"])
            self.assertNotIn(TOKEN, result.text)
            self.assertIn("/getStateInstance/", seen[0].url.path)

    def test_qr_png_only_and_already_authorized(self):
        result, seen = self.call({"type": "qrCode", "message": PNG}, "/qr")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["qr_data_url"], "data:image/png;base64," + PNG)
        self.assertIn("no-store", result.headers["cache-control"])
        self.assertNotIn(TOKEN, result.text)
        self.assertIn("/qr/", seen[0].url.path)
        result, _ = self.call({"type": "alreadyLogged"}, "/qr")
        self.assertEqual(result.status_code, 200); self.assertIsNone(result.json()["qr_data_url"])
        for body in ({"type": "timeout"}, {"type": "error", "message": TOKEN},
                     {"type": "qrCode", "message": "invalid"},
                     {"type": "qrCode", "message": base64.b64encode(b"<svg/>").decode()}):
            result, _ = self.call(body, "/qr")
            self.assertEqual(result.status_code, 502); self.assertNotIn(TOKEN, result.text)

    def test_invalid_provider_responses_are_safe(self):
        for body in ({"stateInstance": "unknown"}, {"stateInstance": []}, [], None):
            result, _ = self.call(body)
            self.assertEqual(result.status_code, 502)
        for code in (302, 401, 429, 500):
            result, seen = self.call({"detail": TOKEN}, status=code)
            self.assertEqual(result.status_code, 502)
            self.assertNotIn(TOKEN, result.text); self.assertEqual(len(seen), 1)

    def test_rate_limit_prevents_provider_calls(self):
        wa._windows[self.user["id"]].extend([wa.time.monotonic()] * 30)
        result, seen = self.call({})
        self.assertEqual(result.status_code, 429); self.assertEqual(seen, [])

    def test_provider_transport_logs_redact_token(self):
        with self.assertLogs("httpx", level=logging.INFO) as captured:
            result, _ = self.call({"stateInstance": "authorized"})
        self.assertEqual(result.status_code, 200)
        self.assertNotIn(TOKEN, " ".join(captured.output))


if __name__ == "__main__":
    unittest.main()
