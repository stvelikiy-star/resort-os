"""Fail-closed RC5 route and per-hotel normalized WhatsApp ingress contract."""
import asyncio
import json
import os
import unittest
from unittest.mock import patch

from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import auth, guest_os
from app.communication_ingest import NormalizedChannelMessage
from app.shared_inbox_rc5 import SharedInboxRc5Boundary, shared_inbox_rc5_allowed
from app.shared_inbox_rc5_identity import (
    configured_channel_adapters,
    require_hotel_channel_service,
    require_bound_channel,
)

A = "A" * 48
B = "B" * 48
TOKEN = "R" * 43
UID = "11111111-1111-4111-8111-111111111111"
CONFIGS = [
    dict(tenant_code="tenant_a", property_code="HOTEL_A",
         channel_code="WA_MAIN", external_account_id="10000001", service_key=A),
    dict(tenant_code="tenant_b", property_code="HOTEL_B",
         channel_code="WA_MAIN", external_account_id="20000002", service_key=B),
]


def app_fixture():
    app = FastAPI()
    app.add_middleware(SharedInboxRc5Boundary)

    @app.post("/api/v1/automation/inbox/messages")
    async def ingest(service=Depends(require_hotel_channel_service)):
        return {"hotel": service["property_code"], "channel": service["channel_code"]}

    @app.get("/api/v1/admin/inbox/conversations")
    async def inbox():
        return {"admitted": True}

    @app.get("/api/v1/admin/inbox/ai-capabilities")
    async def capability():
        return {"mock": True}

    @app.get("/api/v1/admin/whatsapp/connection")
    async def green():
        return {"unsafe": True}

    @app.get("/api/v1/auth/mode")
    async def mode():
        return {"mode": "shared_auth_preview"}

    return app


class SharedInboxRc5Tests(unittest.TestCase):
    def config(self, **overrides):
        from contextlib import ExitStack
        env = dict(
            APP_ENV="staging",
            PROPERTY_CODE="MARINA_BROWSER_CI",
            MARINA_SHARED_GUEST_QR_RC4_ENABLED="true",
            MARINA_SHARED_GUEST_QR_RC4_CONFIRM="REVIEWED_SHARED_GUEST_QR_STAGING_ONLY",
            MARINA_SHARED_GUEST_QR_RC4_ORIGIN="https://rc5-ci.invalid",
            GUEST_OS_PUBLIC_BASE_URL="https://rc5-ci.invalid",
            MARINA_SHARED_INBOX_RC5_ENABLED="true",
            MARINA_SHARED_INBOX_RC5_CONFIRM="REVIEWED_SHARED_INBOX_STAGING_ONLY",
            MARINA_SHARED_INBOX_RC5_ADAPTERS_JSON=json.dumps(CONFIGS),
            MARINA_SHARED_INBOX_RC5_AI_MOCK_ENABLED="false",
        )
        env.update(overrides)
        stack = ExitStack()
        stack.enter_context(patch.dict(os.environ, env, clear=False))
        stack.enter_context(patch.object(auth, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", True))
        stack.enter_context(patch.object(auth, "MARINA_TENANT_CONTEXT_ENABLED", True))
        stack.enter_context(patch.object(auth, "COOKIE_SECURE", True))
        stack.enter_context(patch.object(auth, "PROPERTY_CODE", "MARINA_BROWSER_CI"))
        stack.enter_context(patch.object(guest_os, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", True))
        stack.enter_context(patch.object(guest_os, "COOKIE_SECURE", True))
        return stack

    def test_narrow_route_allowlist(self):
        with self.config():
            yes = [
                ("POST", "/api/v1/automation/inbox/messages"),
                ("GET", "/api/v1/admin/inbox/conversations"),
                ("GET", f"/api/v1/admin/inbox/conversations/{UID}"),
                ("POST", f"/api/v1/admin/inbox/conversations/{UID}/claim"),
                ("POST", f"/api/v1/admin/inbox/conversations/{UID}/notes"),
                ("PATCH", f"/api/v1/admin/inbox/conversations/{UID}/status"),
            ]
            no = [
                ("GET", "/api/v1/admin/whatsapp/connection"),
                ("POST", f"/api/v1/admin/inbox/conversations/{UID}/send-text"),
                ("PATCH", f"/api/v1/admin/inbox/conversations/{UID}/assignee"),
                ("POST", f"/api/v1/admin/inbox/conversations/{UID}/ai-draft"),
                ("GET", "/api/v1/admin/inbox/ai-capabilities"),
                ("POST", f"/api/v1/guest-os/rooms/{TOKEN}/assistant/chat"),
            ]
            for method, path in yes:
                self.assertIs(shared_inbox_rc5_allowed(method, path), True)
            for method, path in no:
                self.assertIs(shared_inbox_rc5_allowed(method, path), False)

    def test_adapter_credential_maps_to_exactly_one_hotel(self):
        with self.config():
            self.assertEqual(len(configured_channel_adapters()), 2)
            for key, hotel in ((A, "HOTEL_A"), (B, "HOTEL_B")):
                bound = asyncio.run(require_hotel_channel_service(key))
                self.assertEqual(bound["property_code"], hotel)
                self.assertEqual(bound["actor_type"], "SERVICE")
            for key in (None, "legacy-service-key", A[:-1] + "C"):
                with self.assertRaises(HTTPException) as ctx:
                    asyncio.run(require_hotel_channel_service(key))
                self.assertEqual(ctx.exception.status_code, 401)

    def test_bad_config_does_not_select_arbitrary_tenant(self):
        configs = [
            CONFIGS[:1],
            [{**CONFIGS[0], "service_key": B}, CONFIGS[1]],
            [{**CONFIGS[0], "external_account_id": "20000002"}, CONFIGS[1]],
            [{**CONFIGS[0], "property_code": "HOTEL_B"}, CONFIGS[1]],
            [{**CONFIGS[0], "unexpected": "field"}, CONFIGS[1]],
        ]
        for items in configs:
            with self.config(MARINA_SHARED_INBOX_RC5_ADAPTERS_JSON=json.dumps(items)):
                with self.assertRaises(HTTPException) as ctx:
                    configured_channel_adapters()
                self.assertEqual(ctx.exception.status_code, 503)

    def test_channel_body_cannot_impersonate_other_account(self):
        with self.config():
            service = asyncio.run(require_hotel_channel_service(A))
            for account, kind, channel in [
                ("20000002", "WHATSAPP", "WA_MAIN"),
                ("10000001", "TELEGRAM", "WA_MAIN"),
                ("10000001", "WHATSAPP", "WA_OTHER"),
                (None, "WHATSAPP", "WA_MAIN"),
            ]:
                msg = NormalizedChannelMessage(
                    idempotency_key="synthetic-001", channel_code=channel,
                    channel_kind=kind, channel_display_name="WhatsApp",
                    external_account_id=account, external_conversation_id="same-chat",
                    direction="INBOUND", sender_type="GUEST", text="hello",
                )
                with self.assertRaises(HTTPException) as ctx:
                    require_bound_channel(msg, service)
                self.assertEqual(ctx.exception.status_code, 403)

    def test_no_external_opening_even_with_rc5_flag(self):
        variants = [
            {"MARINA_SHARED_INBOX_RC5_ENABLED": "false"},
            {"MARINA_SHARED_INBOX_RC5_CONFIRM": "missing"},
            {"MARINA_SHARED_GUEST_QR_RC4_ENABLED": "false"},
            {"APP_ENV": "production"},
            {"GUEST_OS_PUBLIC_BASE_URL": "http://rc5-ci.invalid"},
        ]
        for variant in variants:
            with self.subTest(variant=variant), self.config(**variant):
                with TestClient(app_fixture(), base_url="https://rc5-ci.invalid") as client:
                    self.assertEqual(
                        client.post("/api/v1/automation/inbox/messages", headers={
                            "X-Resort-Service-Key": A
                        }).status_code, 503
                    )
                    self.assertEqual(
                        client.get("/api/v1/admin/whatsapp/connection").status_code, 503
                    )

    def test_admission_rejects_missing_and_cross_hotel_keys(self):
        with self.config():
            with TestClient(app_fixture(), base_url="https://rc5-ci.invalid") as client:
                path = "/api/v1/automation/inbox/messages"
                self.assertEqual(client.post(path).status_code, 401)
                for key, hotel in ((A, "HOTEL_A"), (B, "HOTEL_B")):
                    response = client.post(path, headers={"X-Resort-Service-Key": key})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["hotel"], hotel)
                self.assertEqual(client.get("/api/v1/admin/inbox/conversations").status_code, 200)
                for other in (
                    "/api/v1/admin/whatsapp/connection",
                    "/api/v1/admin/inbox/ai-capabilities",
                ):
                    self.assertEqual(client.get(other).status_code, 503)


if __name__ == "__main__":
    unittest.main()
