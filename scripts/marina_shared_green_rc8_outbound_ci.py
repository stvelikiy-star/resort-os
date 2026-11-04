#!/usr/bin/env python3
"""P0 manual WhatsApp outbox: two real hotel sessions and PostgreSQL, MOCK provider.

Never actually send customer messages or use production credentials.
"""
import asyncio
import json
import os
import secrets
import uuid
from unittest.mock import patch

import asyncpg
from fastapi import HTTPException
from fastapi.testclient import TestClient

from marina_shared_live_browser_db import dsn
from marina_shared_green_rc7_webhook_ci import (
    BASE, ENDPOINT, CHAT, callback, provider_status, db_accounts, expect,
)


async def database_evidence(fixtures):
    conn = await asyncpg.connect(dsn())
    try:
        for hotel in "AB":
            pid = uuid.UUID(fixtures[hotel]["property_id"])
            cid = uuid.UUID(fixtures[hotel]["cid"])
            assert await conn.fetchval(
                'SELECT COUNT(*) FROM conversations WHERE id=$1 AND "propertyId"=$2',
                cid, pid,
            ) == 1
            assert await conn.fetchval(
                '''SELECT COUNT(*) FROM conversation_messages
                   WHERE "conversationId"=$1 AND direction='OUTBOUND'
                     AND "deliveryStatus"='SENT' ''',
                cid,
            ) == 1
            assert await conn.fetchval(
                '''SELECT COUNT(*) FROM automation_inbound_events
                   WHERE "propertyId"=$1 AND source='OUTBOX_WA_MAIN'
                     AND "idempotencyKey"=$2''',
                pid, "rc8-ci-manual-key-001",
            ) == 1
    finally:
        await conn.close()


def run():
    assert os.environ.get("MARINA_SHARED_GREEN_RC8_CI_CONFIRM") == (
        "ISOLATED_TWO_HOTEL_HUMAN_OUTBOUND_CI_ONLY"
    )
    dsn()
    accounts = asyncio.run(db_accounts())
    adapters = []
    webhooks = []
    for hotel in "AB":
        inbox_key = secrets.token_urlsafe(48)
        callback_key = secrets.token_urlsafe(48)
        adapters.append({
            "tenant_code": "tenant_" + hotel.lower(),
            "property_code": "HOTEL_" + hotel,
            "channel_code": "WA_MAIN",
            "external_account_id": accounts[hotel]["instance"],
            "service_key": inbox_key,
        })
        webhooks.append({
            "tenant_code": "tenant_" + hotel.lower(),
            "property_code": "HOTEL_" + hotel,
            "channel_code": "WA_MAIN",
            "instance": accounts[hotel]["instance"],
            "webhook_token": callback_key,
        })
        accounts[hotel]["service_key"] = inbox_key
        accounts[hotel]["webhook_key"] = callback_key

    os.environ["MARINA_SHARED_INBOX_RC5_ADAPTERS_JSON"] = json.dumps(adapters)
    os.environ["MARINA_SHARED_GREEN_RC7_WEBHOOKS_JSON"] = json.dumps(webhooks)
    os.environ["MARINA_SHARED_GREEN_RC6_CONFIG_JSON"] = json.dumps([
        {k: v for k, v in accounts[hotel].items()
         if k in {"tenant_id", "property_id", "property_code", "instance",
                  "provider_origin", "token"}}
        for hotel in "AB"
    ])

    from app import auth, green_outbound
    from app.app_entry import app
    from app.shared_green_rc8 import green_rc8_allowed
    assert green_rc8_allowed(
        "POST", "/api/v1/admin/inbox/conversations/11111111-1111-4111-8111-111111111111/send-text",
    )
    assert not green_rc8_allowed(
        "GET", "/api/v1/admin/inbox/conversations/11111111-1111-4111-8111-111111111111/send-text",
    )
    assert not green_rc8_allowed("POST", "/api/v1/admin/whatsapp/send-text")

    calls = []
    async def synthetic_provider(config, chat_id, text):
        calls.append({"config": config, "chat_id": chat_id, "text": text})
        if text == "Synthetic ambiguous provider outage":
            raise HTTPException(502, detail="provider response unconfirmed")
        return "3EB0RC8SHARED000001"

    with patch.object(green_outbound, "_provider_send", side_effect=synthetic_provider):
        with TestClient(app, base_url=BASE) as client:
            sessions = {}
            password = os.environ["MARINA_SHARED_BROWSER_CI_PASSWORD"]
            for hotel in "AB":
                for role in ("owner", "manager", "reception"):
                    response = expect(client.post("/api/v1/auth/login", json={
                        "tenant_code": "tenant_" + hotel.lower(),
                        "property_code": "HOTEL_" + hotel,
                        "username": role,
                        "password": password,
                    }), 200, hotel + "/" + role + " login")
                    token = client.cookies.get(auth.SESSION_COOKIE)
                    assert response["property_code"] == "HOTEL_" + hotel and token
                    sessions[(hotel, role)] = token
            client.cookies.clear()

            class Staff:
                def __init__(self, hotel, role):
                    self.hotel = hotel
                    self.cookie = sessions[(hotel, role)]

                def get(self, path):
                    return client.get(path, cookies={
                        auth.SESSION_COOKIE: self.cookie,
                    })

                def post(self, path, data=None, *, key=None):
                    h = {"Idempotency-Key": key} if key else {}
                    return client.post(path, json=data, headers=h, cookies={
                        auth.SESSION_COOKIE: self.cookie,
                    })

            owners = {h: Staff(h, "owner") for h in "AB"}
            reception_b = Staff("B", "reception")
            manager_b = Staff("B", "manager")

            def deliver(hotel, data):
                return client.post(
                    ENDPOINT,
                    json=data,
                    headers={"Authorization": "Bearer " + accounts[hotel]["webhook_key"]},
                )

            fixtures = {h: {"property_id": accounts[h]["property_id"]} for h in "AB"}
            for hotel in "AB":
                event = callback(
                    hotel, "rc8-incoming-msg-001",
                    "Synthetic inbound for hotel " + hotel,
                )
                first = expect(deliver(hotel, event), 202, hotel + " incoming")
                assert first["accepted"]
                fixtures[hotel]["cid"] = first["conversation_id"]
            assert fixtures["A"]["cid"] != fixtures["B"]["cid"]

            paths = {
                h: "/api/v1/admin/inbox/conversations/" + fixtures[h]["cid"] + "/send-text"
                for h in "AB"
            }
            # Reception cannot send before intentionally claiming their hotel's
            # conversation. Nor can A's OWNER act on B's conversation.
            expect(reception_b.post(
                paths["B"], {"text": "Synthetic B reply"}, key="rc8-ci-manual-key-001",
            ), 403, "unclaimed reception cannot send")
            expect(owners["A"].post(
                paths["B"], {"text": "Foreign attempt"}, key="rc8-ci-manual-key-001",
            ), 404, "cross-property outbound denied")
            expect(manager_b.get(paths["B"]), 503, "GET must remain blocked")
            assert calls == []

            claim_path = "/api/v1/admin/inbox/conversations/" + fixtures["B"]["cid"] + "/claim"
            expect(reception_b.post(claim_path), 200, "reception human handoff claim")

            for h, staff in (("A", owners["A"]), ("B", reception_b)):
                response = expect(staff.post(
                    paths[h],
                    {"text": "Human-reviewed reply for hotel " + h},
                    key="rc8-ci-manual-key-001",
                ), 200, h + " manual WhatsApp queue")
                assert response["delivery_status"] == "QUEUED"
                assert response["counts_as_response"] is False
                assert response["auto_sent"] is False
                assert response["idempotent_replay"] is False
                replay = expect(staff.post(
                    paths[h],
                    {"text": "Human-reviewed reply for hotel " + h},
                    key="rc8-ci-manual-key-001",
                ), 200, h + " safe idempotency")
                assert replay["idempotent_replay"] is True
                assert replay["message_id"] == response["message_id"]
                expect(staff.post(
                    paths[h],
                    {"text": "Modified duplicate would be unsafe"},
                    key="rc8-ci-manual-key-001",
                ), 409, h + " mismatching idempotency")
            assert len(calls) == 2
            assert calls[0]["config"][1] == accounts["A"]["instance"]
            assert calls[1]["config"][1] == accounts["B"]["instance"]
            assert calls[0]["chat_id"] == CHAT and calls[1]["chat_id"] == CHAT
            assert all("token" not in str(call["text"]).lower() for call in calls)

            # A successful GreenAPI SendMessage is QUEUE acceptance ONLY.
            for h in "AB":
                detail = expect(owners[h].get(
                    "/api/v1/admin/inbox/conversations/" + fixtures[h]["cid"],
                ), 200, h + " queued read")
                assert detail["conversation"]["needs_reply"] is True
                outgoing = [m for m in detail["messages"] if m["direction"] == "OUTBOUND"]
                assert len(outgoing) == 1
                assert outgoing[0]["delivery_status"] == "QUEUED"

            # Only authenticated RC7 callback may subsequently mark SENT.
            delivered_b = expect(deliver("B", provider_status(
                "B", "3EB0RC8SHARED000001", "sent",
            )), 202, "B provider confirmed sent")
            assert delivered_b["accepted"] is True
            assert expect(owners["B"].get(
                "/api/v1/admin/inbox/conversations/" + fixtures["B"]["cid"],
            ), 200, "B needs reply cleared")["conversation"]["needs_reply"] is False
            assert expect(owners["A"].get(
                "/api/v1/admin/inbox/conversations/" + fixtures["A"]["cid"],
            ), 200, "A remains waiting")["conversation"]["needs_reply"] is True
            expect(deliver("A", provider_status(
                "A", "3EB0RC8SHARED000001", "sent",
            )), 202, "A provider confirmation is property-scoped")

            # An ambiguous provider error must NEVER trigger a second send.
            key = "rc8-ci-ambiguous-key-002"
            expect(owners["A"].post(
                paths["A"], {"text": "Synthetic ambiguous provider outage"}, key=key,
            ), 502, "ambiguous provider response")
            first_failure_calls = len(calls)
            retry = expect(owners["A"].post(
                paths["A"], {"text": "Synthetic ambiguous provider outage"}, key=key,
            ), 409, "outbox requires manual reconciliation")
            assert retry["detail"]["automatic_retry_safe"] is False
            assert len(calls) == first_failure_calls

            with patch.dict(os.environ, {"MARINA_SHARED_GREEN_RC8_ENABLED": "false"}):
                expect(owners["A"].post(
                    paths["A"], {"text": "No operation"}, key="rc8-ci-disabled-key-001",
                ), 503, "RC8 disabled must close send")
            assert len(calls) == first_failure_calls

            asyncio.run(database_evidence(fixtures))
    print(
        "PASS: full shared Core manual WhatsApp human-only send, OWNER/RECEPTION "
        "hotel scope, claimant check, idempotency, queued-not-delivered honesty, "
        "tracked RC7 status, no retry after provider ambiguity, ZERO live calls"
    )


if __name__ == "__main__":
    run()
