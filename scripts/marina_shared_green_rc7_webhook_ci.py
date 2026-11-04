#!/usr/bin/env python3
"""RC7: actual FastAPI -> canonical Inbox -> PostgreSQL, no external calls."""
import asyncio
import json
import os
import secrets
import time
from unittest.mock import patch

import asyncpg
from fastapi.testclient import TestClient

from marina_shared_live_browser_db import dsn
from marina_shared_green_rc6_db_ci import prepare_accounts

PATH = "/api/v1/automation/green-api/webhook"
CHAT = "996700000001@c.us"
MSG_ID = "SYNTHETICGREENWEBHOOKMESSAGE2026"


def expect(response, status, action):
    assert response.status_code == status, (
        action, response.status_code, response.text[:230]
    )
    return response.json()


def notification(instance, text, *, kind="textMessage", chat=CHAT, msg_id=MSG_ID):
    content = (
        {"typeMessage": kind, "textMessageData": {"textMessage": text}}
        if kind == "textMessage" else
        {"typeMessage": kind, "extendedTextMessageData": {"text": text}}
    )
    return {
        "typeWebhook": "incomingMessageReceived",
        "instanceData": {"idInstance": int(instance), "typeInstance": "whatsapp"},
        "timestamp": int(time.time()),
        "idMessage": msg_id,
        "senderData": {"chatId": chat, "sender": chat, "senderName": "Synthetic Contact"},
        "messageData": content,
    }


def send(api, token, payload, **kwargs):
    headers = {"Authorization": "Bearer " + token}
    headers.update(kwargs.pop("headers", {}))
    return api.post(PATH, headers=headers, json=payload, **kwargs)


def login(api, tenant, property_code, username):
    result = expect(api.post("/api/v1/auth/login", json={
        "tenant_code": tenant, "property_code": property_code,
        "username": username,
        "password": os.environ["MARINA_SHARED_BROWSER_CI_PASSWORD"],
    }), 200, property_code + " login")
    return result


async def verify_db():
    conn = await asyncpg.connect(dsn())
    try:
        rows = await conn.fetch(
            """SELECT c.id,c."propertyId",ch."externalAccountId" AS instance,
                      c."externalConversationId" AS chat,p.code AS hotel
               FROM conversations c
               JOIN communication_channels ch ON ch.id=c."channelId"
               JOIN properties p ON p.id=c."propertyId"
               WHERE ch.code='WA_MAIN' ORDER BY p.code"""
        )
        assert len(rows) == 2, rows
        assert {r["hotel"] for r in rows} == {"HOTEL_A", "HOTEL_B"}
        assert {r["instance"] for r in rows} == {"7103000001", "7103000002"}
        assert {r["chat"] for r in rows} == {CHAT}
        for r in rows:
            assert await conn.fetchval(
                'SELECT count(*)::int FROM conversation_messages WHERE "conversationId"=$1 AND direction=\'INBOUND\'',
                r["id"],
            ) == 1
            assert await conn.fetchval(
                'SELECT count(*)::int FROM automation_inbound_events WHERE "propertyId"=$1 AND source=\'INBOX_WA_MAIN\' AND "idempotencyKey"=$2',
                r["propertyId"], "green:" + MSG_ID,
            ) == 1
        assert len({r["id"] for r in rows}) == 2
        return {r["hotel"]: str(r["id"]) for r in rows}
    finally:
        await conn.close()


def main():
    assert os.environ.get("MARINA_SHARED_GREEN_WEBHOOK_RC7_CI_CONFIRM") == (
        "ISOLATED_TWO_HOTEL_WEBHOOK_ONLY"
    )
    dsn()
    from app.app_entry import app
    from app.auth import SESSION_COOKIE
    accounts = asyncio.run(prepare_accounts())
    registry = json.loads(os.environ["MARINA_SHARED_INBOX_RC5_ADAPTERS_JSON"])
    assert len(registry) == 2
    token_a, token_b = secrets.token_urlsafe(48), secrets.token_urlsafe(48)
    for token in (token_a, token_b):
        assert len(token) >= 32
    webhook = [
        {"tenant_code": "tenant_" + hotel.lower(),
         "property_code": "HOTEL_" + hotel,
         "instance": "7103000001" if hotel == "A" else "7103000002",
         "webhook_token": token_a if hotel == "A" else token_b}
        for hotel in "AB"
    ]
    os.environ["MARINA_SHARED_GREEN_RC6_CONFIG_JSON"] = json.dumps(accounts)
    os.environ["MARINA_SHARED_GREEN_WEBHOOK_RC7_JSON"] = json.dumps(webhook)

    with TestClient(app, base_url="https://green-webhook-rc7.invalid") as api:
        status = expect(api.get("/api/v1/auth/mode"), 200, "shared auth mode")
        assert status["mode"] == "shared_auth_preview"

        a_msg = notification("7103000001", "SYNTHETIC_HOTEL_A_MESSAGE_MARKER")
        b_msg = notification("7103000002", "SYNTHETIC_HOTEL_B_MESSAGE_MARKER")

        expect(api.post(PATH, json=a_msg), 401, "no Bearer secret")
        expect(api.post(PATH, json=a_msg, headers={"Authorization": "Basic " + token_a}), 401, "reject Basic auth")
        expect(send(api, "wrong-secret", a_msg), 401, "wrong Bearer secret")
        expect(send(api, token_a, b_msg), 403, "A token cannot submit B instance")
        expect(send(api, token_b, a_msg), 403, "B token cannot submit A instance")
        assert not api.post(PATH, headers={
            "Authorization": "Bearer " + token_a,
            "Content-Type": "text/plain",
        }, content=b"not json").status_code == 202
        expect(send(api, token_a, {**a_msg, "instanceData": {
            "idInstance": int(webhook[0]["instance"]), "typeInstance": "v3",
        }}), 403, "reject MAX messenger on WhatsApp route")
        malformed = {
            **a_msg,
            "messageData": {"typeMessage": "textMessage", "textMessageData": {
                "textMessage": "",
            }},
        }
        expect(send(api, token_a, malformed), 422, "empty text")
        expect(send(api, token_a, {**a_msg, "idMessage": "no"}), 422, "invalid message id")

        for hotel, token, payload in (
            ("A", token_a, a_msg),
            ("B", token_b, b_msg),
        ):
            first = expect(send(api, token, payload), 202, hotel + " inbound webhook")
            assert first["accepted"] and first["stored"] and not first["idempotent_replay"]
            replay = expect(send(api, token, payload), 202, hotel + " duplicate")
            assert replay["idempotent_replay"] is True
            mutated = {**payload, "messageData": {
                "typeMessage": "textMessage",
                "textMessageData": {"textMessage": "FORGED-MUTATION"},
            }}
            expect(send(api, token, mutated), 409, "idempotency mutation rejected")
            ignored = expect(send(api, token, {
                **payload, "typeWebhook": "outgoingMessageStatus",
            }), 202, "unsupported outbound status ignored")
            assert ignored == {
                "accepted": True, "stored": False,
                "reason": "UNSUPPORTED_EVENT",
            }
            group = expect(send(api, token, {
                **payload,
                "senderData": {"chatId": "123456789@g.us", "sender": CHAT},
            }), 202, "group messages ignored")
            assert group["stored"] is False

        # Confirm service-scoped PostgreSQL truth after incoming writes.
        ids = asyncio.run(verify_db())

        # Authenticated staff sessions under ONE shared FastAPI lifespan.
        class Session:
            def __init__(self, hotel, role):
                api.cookies.clear()
                login(api, "tenant_" + hotel.lower(), "HOTEL_" + hotel, role)
                self.cookie = api.cookies.get(SESSION_COOKIE)
                assert self.cookie
                self.hotel = hotel

            def call(self, method, path, **kwargs):
                api.cookies.clear()
                api.cookies.set(SESSION_COOKIE, self.cookie)
                return api.request(method, path, **kwargs)

            def get(self, path, **kwargs):
                return self.call("GET", path, **kwargs)

            def post(self, path, **kwargs):
                return self.call("POST", path, **kwargs)

        owner = {hotel: Session(hotel, "owner") for hotel in "AB"}
        manager = {hotel: Session(hotel, "manager") for hotel in "AB"}
        reception = {hotel: Session(hotel, "reception") for hotel in "AB"}
        for hotel in "AB":
            cid = ids["HOTEL_" + hotel]
            other = ids["HOTEL_" + ("B" if hotel == "A" else "A")]
            for client in (owner[hotel], manager[hotel], reception[hotel]):
                listing = expect(client.get(
                    "/api/v1/admin/inbox/conversations?needs_reply=true",
                ), 200, "hotel Inbox list")
                assert {x["id"] for x in listing["items"]} == {cid}
                detail = expect(client.get(
                    "/api/v1/admin/inbox/conversations/" + cid,
                ), 200, "own Inbox detail")
                assert detail["conversation"]["needs_reply"] is True
                assert "SYNTHETIC_HOTEL_" + hotel + "_MESSAGE_MARKER" in (
                    detail["messages"][0]["text"]
                )
                expect(client.get("/api/v1/admin/inbox/conversations/" + other),
                       404, "foreign conversation concealed")

        # No provider outbound, no QR secret endpoint, no automatic AI.
        for path in (
            "/api/v1/admin/inbox/outbound-capabilities",
            "/api/v1/assistant/capabilities",
            "/api/v1/admin/whatsapp/connection/send-text",
        ):
            expect(owner["A"].get(path), 503, "unreviewed route remains closed")
        with patch.dict(os.environ, {"MARINA_SHARED_GREEN_WEBHOOK_RC7_ENABLED": "false"}):
            expect(send(api, token_a, a_msg), 503, "webhook flag disabled")
        with patch.dict(os.environ, {"MARINA_SHARED_GREEN_WEBHOOK_RC7_CONFIRM": "wrong"}):
            expect(send(api, token_a, a_msg), 503, "missing staging approval")
        with patch.dict(os.environ, {"MARINA_SHARED_GREEN_WEBHOOK_RC7_JSON": json.dumps(webhook[:1])}):
            expect(send(api, token_a, a_msg), 503, "misconfigured hotel set")
    print(
        "PASS: RC7 authenticated GreenAPI webhook -> canonical Inbox -> "
        "PostgreSQL two hotel isolation, replay dedupe and mutation 409, "
        "owner/manager/reception isolation, disabled provider send. "
        "All messages synthetic; no live provider calls."
    )


if __name__ == "__main__":
    main()
