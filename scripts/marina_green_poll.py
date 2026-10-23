#!/usr/bin/env python3
"""Isolated Green-API WhatsApp inbox adapter for ONE MARINA property.

No n8n, browser token, automatic AI reply or automatic reservation.
Explicit opt-in process: start only after configuring per-hotel secrets.
"""
import argparse
import asyncio
import os
import re
import sys

import httpx


class AdapterError(RuntimeError):
    pass


def configuration(env):
    keys = ("GREEN_API_URL", "GREEN_API_ID_INSTANCE", "GREEN_API_TOKEN_INSTANCE",
            "AUTOMATION_SERVICE_KEY", "PROPERTY_CODE")
    absent = [key for key in keys if not env.get(key)]
    if absent:
        raise AdapterError("Missing required per-hotel settings: " + ", ".join(absent))
    if len(env["AUTOMATION_SERVICE_KEY"]) < 32:
        raise AdapterError("AUTOMATION_SERVICE_KEY must contain at least 32 characters")
    instance = str(env["GREEN_API_ID_INSTANCE"])
    if not re.fullmatch(r"[0-9]{6,14}", instance):
        raise AdapterError("Invalid GREEN_API_ID_INSTANCE")
    base = env["GREEN_API_URL"].rstrip("/")
    if not base.startswith("https://") or "@" in base or "?" in base or "#" in base:
        raise AdapterError("GREEN_API_URL must be a clean HTTPS base URL")
    return {
        "base": base,
        "instance": instance,
        "token": env["GREEN_API_TOKEN_INSTANCE"],
        "key": env["AUTOMATION_SERVICE_KEY"],
        "property": env["PROPERTY_CODE"],
        "core": env.get("RESORT_CORE_URL", "http://127.0.0.1:8000").rstrip("/"),
    }


def normalize(item, expected_instance, property_code):
    if not isinstance(item, dict) or not isinstance(item.get("body"), dict):
        raise AdapterError("Invalid provider envelope; refusing to acknowledge")
    body = item["body"]
    reported = (body.get("instanceData") or {}).get("idInstance")
    if str(reported) != expected_instance:
        raise AdapterError("Provider instance mismatch; refusing to acknowledge")
    receipt = item.get("receiptId")
    if not isinstance(receipt, int) or receipt < 0:
        raise AdapterError("Invalid receipt; refusing to acknowledge")
    if body.get("typeWebhook") != "incomingMessageReceived":
        return receipt, None
    sender = body.get("senderData") or {}
    chat = sender.get("chatId", "")
    if not isinstance(chat, str) or not re.fullmatch(r"[0-9]{5,18}@c\.us", chat):
        # Never silently discard guest traffic from unsupported chat formats.
        raise AdapterError("Unsupported WhatsApp chat type; manual reconciliation required")
    message = body.get("messageData") or {}
    if message.get("typeMessage") != "textMessage":
        # Media must not disappear from Green queue without an inbox record.
        raise AdapterError("Unsupported inbound media; manual reconciliation required")
    content = (message.get("textMessageData") or {}).get("textMessage")
    msg_id = body.get("idMessage")
    if not isinstance(msg_id, str) or not msg_id or not isinstance(content, str) or not content.strip():
        raise AdapterError("Malformed text message; refusing to acknowledge")
    if len(content) > 12000:
        raise AdapterError("Message exceeds inbox contract; refusing to acknowledge")
    return receipt, {
        "idempotency_key": "green:" + expected_instance + ":" + msg_id,
        "channel_code": "GREEN_" + expected_instance,
        "channel_kind": "WHATSAPP",
        "channel_display_name": "WhatsApp " + property_code,
        "external_account_id": expected_instance,
        "external_conversation_id": chat,
        "external_contact_id": chat,
        "contact_name": (sender.get("senderName") or sender.get("senderContactName") or "")[:180] or None,
        "contact_phone": "+" + chat.split("@", 1)[0],
        "direction": "INBOUND",
        "external_message_id": msg_id,
        "sender_type": "GUEST",
        "sender_external_id": chat,
        "text": content,
        "content_type": "TEXT",
        "delivery_status": "RECEIVED",
    }


async def process_one(client, cfg):
    endpoint = f'{cfg["base"]}/waInstance{cfg["instance"]}'
    received = await client.get(f'{endpoint}/receiveNotification/{cfg["token"]}', params={"receiveTimeout": 5})
    received.raise_for_status()
    item = received.json()
    if not item:
        return "EMPTY"
    receipt, payload = normalize(item, cfg["instance"], cfg["property"])
    if payload is not None:
        stored = await client.post(
            cfg["core"] + "/api/v1/automation/inbox/messages",
            json=payload,
            headers={"X-Resort-Service-Key": cfg["key"]},
        )
        if stored.status_code not in (200, 201):
            raise AdapterError(f"Core inbox rejected delivery (HTTP {stored.status_code}); message not acknowledged")
    ack = await client.delete(f'{endpoint}/deleteNotification/{cfg["token"]}/{receipt}')
    ack.raise_for_status()
    return "INGESTED" if payload is not None else "SKIPPED_UNSUPPORTED"


async def run(once):
    cfg = configuration(os.environ)
    # A process is pinned to ONE hotel via its private environment.
    async with httpx.AsyncClient(timeout=20.0) as client:
        while True:
            try:
                result = await process_one(client, cfg)
                print(result, flush=True)
            except (AdapterError, httpx.HTTPError, ValueError) as exc:
                # Do not leak tokens, provider URLs or message content in logs.
                print("GREEN_ADAPTER_ERROR: processing stopped; inspect private service diagnostics", file=sys.stderr)
                raise SystemExit(1) from None
            if once:
                return
            if result == "EMPTY":
                await asyncio.sleep(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Process at most one queue item, then exit")
    args = parser.parse_args()
    asyncio.run(run(args.once))
