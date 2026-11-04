#!/usr/bin/env python3
"""Real PostgreSQL/full Core CI for two GREEN-API webhook callbacks.

All callbacks synthetic. Provider send APIs and external AI are NEVER called.
"""
import asyncio
import faulthandler
import json
import os
import secrets
import uuid
from unittest.mock import patch
from datetime import datetime, timezone

import asyncpg
from fastapi.testclient import TestClient

from marina_shared_live_browser_db import dsn

BASE = "https://marina-rc7-ci.invalid"
ENDPOINT = "/api/v1/automation/green-api/webhook"
CHAT = "996555123456@c.us"


def expect(response, status, label):
    assert response.status_code == status, (
        label, response.status_code, response.text[:260],
    )
    return response.json() if response.content else {}


async def db_accounts():
    conn = await asyncpg.connect(dsn())
    try:
        rows = {}
        for hotel in "AB":
            row = await conn.fetchrow(
                """SELECT p.id,p."tenantId" FROM properties p
                   JOIN tenants t ON t.id=p."tenantId"
                   WHERE p.code=$1 AND t.status='ACTIVE'""",
                "HOTEL_" + hotel,
            )
            assert row
            rows[hotel] = {
                "tenant_id": str(row["tenantId"]),
                "property_id": str(row["id"]),
                "property_code": "HOTEL_" + hotel,
                "provider_origin": "https://7103.api.greenapi.com",
                "instance": "10000001" if hotel == "A" else "20000002",
                "token": "synthetic_rc7_provider_token_" + hotel * 22,
            }
        return rows
    finally:
        await conn.close()


async def evidence(fixtures):
    conn = await asyncpg.connect(dsn())
    try:
        for hotel, row in fixtures.items():
            pid, cid = uuid.UUID(row["property_id"]), uuid.UUID(row["cid"])
            assert await conn.fetchval(
                'SELECT count(*) FROM conversations WHERE id=$1 AND "propertyId"=$2',
                cid, pid,
            ) == 1
            assert await conn.fetchval(
                '''SELECT count(*) FROM conversation_messages
                   WHERE "conversationId"=$1 AND direction='INBOUND' ''',
                cid,
            ) == 1
            assert await conn.fetchval(
                '''SELECT count(*) FROM automation_inbound_events
                   WHERE "propertyId"=$1 AND source='INBOX_WA_MAIN'
                     AND "idempotencyKey"=$2''',
                pid, "green7:in:inbound-msg-001",
            ) == 1
        assert len({r["cid"] for r in fixtures.values()}) == 2
    finally:
        await conn.close()


def callback(hotel, event_id, text, *, instance=None, chat=CHAT):
    return {
        "typeWebhook": "incomingMessageReceived",
        "instanceData": {
            "idInstance": int(instance or ("10000001" if hotel == "A" else "20000002")),
            "wid": "996700000000@c.us",
            "typeInstance": "whatsapp",
        },
        "timestamp": 1762290000,
        "idMessage": event_id,
        "senderData": {
            "chatId": chat, "chatType": "user", "sender": chat,
            "senderName": "Green Test Guest " + hotel,
        },
        "messageData": {
            "typeMessage": "textMessage",
            "textMessageData": {"textMessage": text},
        },
    }


def provider_status(hotel, message_id, status, *, send_by_api=True, chat=CHAT):
    return {
        "typeWebhook": "outgoingMessageStatus",
        "instanceData": {
            "idInstance": int("10000001" if hotel == "A" else "20000002"),
            "typeInstance": "whatsapp",
        },
        "timestamp": 1762290001,
        "idMessage": message_id,
        "chatId": chat,
        "status": status,
        "sendByApi": send_by_api,
    }


def login(client, h, role, password):
    return expect(client.post("/api/v1/auth/login", json={
        "tenant_code": "tenant_" + h.lower(), "property_code": "HOTEL_" + h,
        "username": role, "password": password,
    }), 200, h + " owner login")


def main():
    faulthandler.dump_traceback_later(90, repeat=True)
    print("RC7 E2E: initializing two hotel bindings", flush=True)
    assert os.environ.get("MARINA_SHARED_GREEN_RC7_CI_CONFIRM") == (
        "ISOLATED_TWO_HOTEL_GREEN_WEBHOOK_CI_ONLY"
    )
    dsn()
    accounts = asyncio.run(db_accounts())
    adapters = []
    webhooks = []
    for h in "AB":
        key = secrets.token_urlsafe(48)
        webhook_key = secrets.token_urlsafe(48)
        assert key != webhook_key
        adapters.append({
            "tenant_code": "tenant_" + h.lower(),
            "property_code": "HOTEL_" + h,
            "channel_code": "WA_MAIN",
            "external_account_id": accounts[h]["instance"],
            "service_key": key,
        })
        webhooks.append({
            "tenant_code": "tenant_" + h.lower(),
            "property_code": "HOTEL_" + h,
            "channel_code": "WA_MAIN",
            "instance": accounts[h]["instance"],
            "webhook_token": webhook_key,
        })
        accounts[h]["service_key"] = key
        accounts[h]["webhook_key"] = webhook_key
    os.environ["MARINA_SHARED_INBOX_RC5_ADAPTERS_JSON"] = json.dumps(adapters)
    os.environ["MARINA_SHARED_GREEN_RC7_WEBHOOKS_JSON"] = json.dumps(webhooks)
    os.environ["MARINA_SHARED_GREEN_RC6_CONFIG_JSON"] = json.dumps([
        {k: v for k, v in accounts[h].items()
         if k in {"tenant_id", "property_id", "property_code",
                  "provider_origin", "instance", "token"}}
        for h in "AB"
    ])
    from app.app_entry import app
    from app import auth
    from app.shared_green_rc7 import green_rc7_allowed
    assert green_rc7_allowed("POST", ENDPOINT)
    assert not green_rc7_allowed("GET", ENDPOINT)
    assert not green_rc7_allowed("POST", ENDPOINT + "/hotel_a")
    assert not green_rc7_allowed("POST", "/api/v1/admin/whatsapp/send-text")
    password = os.environ["MARINA_SHARED_BROWSER_CI_PASSWORD"]
    fixtures = {h: {"property_id": accounts[h]["property_id"]} for h in "AB"}

    print("RC7 E2E: starting full Core TestClient", flush=True)
    # One ASGI lifespan / one asyncpg pool / one event loop. Multiple
    # simultaneous TestClient lifespan contexts share mutable app.state.db
    # and can deadlock on transaction writes.
    with TestClient(app, base_url=BASE) as svc:
        login(svc, "A", "owner", password)
        token_a = svc.cookies.get(auth.SESSION_COOKIE)
        login(svc, "B", "owner", password)
        token_b = svc.cookies.get(auth.SESSION_COOKIE)
        assert token_a and token_b and token_a != token_b
        svc.cookies.clear()

        class HotelOwner:
            def __init__(self, token):
                self.token = token

            def get(self, path):
                return svc.get(path, cookies={auth.SESSION_COOKIE: self.token})

        owner = {"A": HotelOwner(token_a), "B": HotelOwner(token_b)}
        a, b = owner["A"], owner["B"]

        def deliver(h, event, *, token=None):
            secret = token if token is not None else accounts[h]["webhook_key"]
            return svc.post(
                ENDPOINT,
                headers={"Authorization": "Bearer " + secret},
                json=event,
            )

        print("RC7 E2E: authenticating and exercising webhook guards", flush=True)
        # HTTPS staging admission does NOT authorize unknown or missing
        # callback credentials, cross-hotel instance IDs or chat group events.
        expect(svc.post(ENDPOINT, json=callback("A", "inbound-msg-001", "hello")), 401, "anonymous webhook")
        expect(deliver("A", callback("A", "inbound-msg-001", "hello"),
                       token="not-a-valid-webhook-key"), 401, "invalid bearer")
        expect(deliver("A", callback("A", "inbound-msg-001", "hello", instance="20000002")),
               403, "cross-hotel instance spoof")
        expect(deliver("A", callback("A", "inbound-msg-001", "hello", chat="12345678@g.us")),
               422, "group chat blocked")
        unsupported = callback("A", "inbound-msg-001", "hello")
        unsupported["messageData"]["typeMessage"] = "fileMessage"
        expect(deliver("A", unsupported), 422, "media needs separate acceptance")
        expect(svc.get(ENDPOINT), 503, "only webhook POST is admitted")
        expect(svc.post("/api/v1/admin/whatsapp/send-text"), 503, "no provider send")

        # Identical WhatsApp chat ID and Green ID across two independent
        # provider instances MUST produce separate hotel-scoped conversations.
        print("RC7 E2E: guest message callback and idempotency", flush=True)
        for h in "AB":
            marker = h + "-GREEN7-MESSAGE-MARKER"
            event = callback(h, "inbound-msg-001", marker)
            first = expect(deliver(h, event), 202, h + " incoming")
            replay = expect(deliver(h, event), 202, h + " repeat delivery")
            assert first["accepted"] is True and first["idempotent_replay"] is False
            assert replay["idempotent_replay"] is True
            fixtures[h]["cid"] = first["conversation_id"]
            changed = callback(h, "inbound-msg-001", marker + "-MODIFIED")
            expect(deliver(h, changed), 409, h + " altered replay")
        assert fixtures["A"]["cid"] != fixtures["B"]["cid"]

        for h in "AB":
            own, other = fixtures[h]["cid"], fixtures["B" if h == "A" else "A"]["cid"]
            listing = expect(owner[h].get(
                "/api/v1/admin/inbox/conversations",
            ), 200, h + " scoped inbox")
            assert [r["id"] for r in listing["items"]] == [own]
            expect(owner[h].get(
                "/api/v1/admin/inbox/conversations/" + other,
            ), 404, h + " no foreign conversation")
            # Even if a synthetic outbound delivery callback is legitimate,
            # it cannot create an outbound conversation without a stored send.
            expect(deliver(h, provider_status(
                h, "outbound-msg-001", "delivered",
            )), 409, h + " untracked delivery cannot fabricate response")

        print("RC7 E2E: outbound status reconciliation", flush=True)
        # Create one synthetic queued outgoing record through the existing
        # normalized adapter contract. Never call GREEN API sendMessage.
        queue = {
            "idempotency_key": "rc7:queued:outbound-msg-001",
            "channel_code": "WA_MAIN", "channel_kind": "WHATSAPP",
            "channel_display_name": "WhatsApp",
            "external_account_id": accounts["B"]["instance"],
            "external_conversation_id": CHAT, "external_contact_id": CHAT,
            "direction": "OUTBOUND",
            "external_message_id": "outbound-msg-001",
            "sender_type": "STAFF", "sender_external_id": "test-staff",
            "text": "Synthetic staff-approved queued message",
            "delivery_status": "QUEUED",
        }
        queued = expect(svc.post(
            "/api/v1/automation/inbox/messages",
            json=queue, headers={
                "X-Resort-Service-Key": accounts["B"]["service_key"],
            },
        ), 201, "synthetic outbound queued")
        assert queued["counts_as_response"] is False
        before = expect(b.get(
            "/api/v1/admin/inbox/conversations/" + fixtures["B"]["cid"]
        ), 200, "B before sent status")
        assert before["conversation"]["needs_reply"] is True

        expect(deliver("A", provider_status(
            "A", "outbound-msg-001", "sent",
        )), 409, "Hotel A cannot reconcile B outbound")
        expect(deliver("B", provider_status(
            "B", "outbound-msg-001", "sent", send_by_api=False,
        )), 422, "phone-origin status is not API-delivery proof")
        confirmed = expect(deliver("B", provider_status(
            "B", "outbound-msg-001", "sent",
        )), 202, "registered outbound provider status")
        assert confirmed["accepted"] is True and not confirmed["idempotent_replay"]
        repeated = expect(deliver("B", provider_status(
            "B", "outbound-msg-001", "sent",
        )), 202, "duplicate sent")
        assert repeated["idempotent_replay"] is True

        after = expect(b.get(
            "/api/v1/admin/inbox/conversations/" + fixtures["B"]["cid"]
        ), 200, "B after provider status")
        assert after["conversation"]["needs_reply"] is False
        assert expect(a.get(
            "/api/v1/admin/inbox/conversations/" + fixtures["A"]["cid"]
        ), 200, "A unaffected")["conversation"]["needs_reply"] is True

        delivered = expect(deliver("B", provider_status(
            "B", "outbound-msg-001", "delivered",
        )), 202, "delivered callback")
        assert delivered["accepted"] is True
        detail = expect(b.get(
            "/api/v1/admin/inbox/conversations/" + fixtures["B"]["cid"]
        ), 200, "B after delivered")
        outbound = [m for m in detail["messages"] if m["direction"] == "OUTBOUND"]
        assert len(outbound) == 1 and outbound[0]["delivery_status"] == "DELIVERED"

        with patch.dict(os.environ, {
            "MARINA_SHARED_GREEN_RC7_ENABLED": "false",
        }):
            expect(deliver("B", callback(
                "B", "inbound-msg-002", "disabled",
            )), 503, "RC7 disabled fail closed")
        with patch.dict(os.environ, {
            "MARINA_SHARED_GREEN_RC7_CONFIRM": "invalid",
        }):
            expect(deliver("B", callback(
                "B", "inbound-msg-002", "disabled",
            )), 503, "RC7 missing confirmation")
        asyncio.run(evidence(fixtures))
    print(
        "PASS: two hotel GREEN-API webhook bearer/instance isolation, real "
        "PostgreSQL & canonical Inbox, duplicate suppression, fake delivery "
        "denied, tracked sent/delivered reconciliation, RBAC; provider calls ZERO"
    )


if __name__ == "__main__":
    main()
