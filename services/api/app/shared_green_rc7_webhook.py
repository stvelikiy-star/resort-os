"""Provider-specific GREEN-API webhook adapter; RC7 staging only.

Documented GREEN-API WebhookURLToken sends Authorization: Bearer <secret>.
That is a shared secret, NOT a signed request or proof of external delivery.
The selected hotel derives exclusively from the verified secret and a
cross-checked RC5 Inbox / RC6 owner-GreenAPI provider configuration.
No network calls and no new storage schema: reuse canonical Inbox ingest.
"""
from datetime import datetime, timezone
import hmac
import json
import os
import re
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from .communication_ingest import NormalizedChannelMessage, ingest_normalized_channel_message
from .shared_green_rc6 import rc6_guard
from .shared_inbox_rc5_identity import configured_channel_adapters, require_bound_channel


router = APIRouter(prefix="/api/v1/automation/green-api", tags=["green-api-webhook"])
AUTH_PATTERN = re.compile(r"^Bearer ([A-Za-z0-9_-]{32,256})$")
DIRECT_CHAT = re.compile(r"^[0-9]{5,20}@c\.us$")
MESSAGE_ID = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


def rc7_webhook_config() -> tuple[dict[str, str], ...]:
    rc6_guard()
    if (os.environ.get("MARINA_SHARED_GREEN_WEBHOOK_RC7_ENABLED") != "true"
            or os.environ.get("MARINA_SHARED_GREEN_WEBHOOK_RC7_CONFIRM") != (
                "REVIEWED_GREEN_WEBHOOK_STAGING_ONLY"
            )):
        raise HTTPException(503, detail="GREEN-API webhook is not enabled")
    try:
        raw = json.loads(os.environ.get("MARINA_SHARED_GREEN_WEBHOOK_RC7_JSON", ""))
        green = json.loads(os.environ.get("MARINA_SHARED_GREEN_RC6_CONFIG_JSON", ""))
        inbox = configured_channel_adapters()
        if not isinstance(raw, list) or len(raw) != len(inbox):
            raise ValueError("Expected one webhook secret per configured hotel")
        if not isinstance(green, list) or len(green) != len(inbox):
            raise ValueError("Expected one GreenAPI instance per hotel")
        bindings = []
        for row in raw:
            if not isinstance(row, dict) or set(row) != {
                "tenant_code", "property_code", "instance", "webhook_token",
            }:
                raise ValueError("Invalid webhook mapping")
            if any(not isinstance(v, str) for v in row.values()):
                raise ValueError("Invalid webhook values")
            if not (re.fullmatch(r"[A-Za-z0-9_-]{32,256}", row["webhook_token"])
                    and re.fullmatch(r"[0-9]{5,24}", row["instance"])):
                raise ValueError("Webhook credential or instance invalid")
            matches = [
                (i, g) for i in inbox for g in green
                if i["tenant_code"] == row["tenant_code"]
                and i["property_code"] == row["property_code"]
                and i["external_account_id"] == row["instance"]
                and g.get("property_code") == i["property_code"]
                and g.get("instance") == row["instance"]
            ]
            if len(matches) != 1:
                raise ValueError("Hotel provider and channel identity mismatch")
            g = matches[0][1]
            for field in ("tenant_id", "property_id"):
                try:
                    uuid.UUID(g.get(field, ""))
                except (TypeError, ValueError, AttributeError):
                    raise ValueError("Missing verified hotel UUID") from None
            service = {
                "actor_type": "SERVICE",
                "actor_id": "green-webhook:" + row["property_code"],
                **matches[0][0],
            }
            service.pop("service_key")
            bindings.append({
                **row,
                "green_tenant_id": str(uuid.UUID(g["tenant_id"])),
                "green_property_id": str(uuid.UUID(g["property_id"])),
                "service": service,
            })
        for field in ("tenant_code", "property_code", "instance", "webhook_token"):
            if len({b[field] for b in bindings}) != len(bindings):
                raise ValueError("Ambiguous webhook bindings")
        return tuple(bindings)
    except (TypeError, ValueError, KeyError):
        raise HTTPException(503, detail="GREEN-API webhook bindings are not configured") from None


def authenticated_binding(request: Request, bindings: tuple[dict[str, str], ...]):
    values = [
        value.decode("latin-1") for key, value in request.scope.get("headers", [])
        if key.lower() == b"authorization"
    ]
    if len(values) != 1:
        raise HTTPException(401, detail="Invalid GREEN-API webhook credential")
    match = AUTH_PATTERN.fullmatch(values[0])
    if not match:
        raise HTTPException(401, detail="Invalid GREEN-API webhook credential")
    # Review all configured secrets without HTTP-provided hotel selection.
    selected = [b for b in bindings if hmac.compare_digest(
        match.group(1), b["webhook_token"]
    )]
    if len(selected) != 1:
        raise HTTPException(401, detail="Invalid GREEN-API webhook credential")
    return selected[0]


def normalize_green_text(body: Any, binding: dict[str, Any]):
    if not isinstance(body, dict):
        raise HTTPException(422, detail="Invalid GREEN-API notification")
    instance = body.get("instanceData")
    if (not isinstance(instance, dict)
            or instance.get("typeInstance") != "whatsapp"
            or str(instance.get("idInstance")) != binding["instance"]):
        raise HTTPException(403, detail="GREEN-API instance is not bound to this hotel")
    if body.get("typeWebhook") != "incomingMessageReceived":
        # Authenticated status/phone/other notifications do not trigger a guest
        # message or a misleading delivery confirmation. Acknowledge to avoid
        # endless provider retries of intentionally unsupported types.
        return None
    sender, data = body.get("senderData"), body.get("messageData")
    if not isinstance(sender, dict) or not isinstance(data, dict):
        raise HTTPException(422, detail="Invalid GREEN-API message format")
    chat_id = sender.get("chatId")
    if not isinstance(chat_id, str) or not DIRECT_CHAT.fullmatch(chat_id):
        # Do not create reservation leads from group conversations.
        return None
    msg_id, kind = body.get("idMessage"), data.get("typeMessage")
    if not isinstance(msg_id, str) or not MESSAGE_ID.fullmatch(msg_id):
        raise HTTPException(422, detail="Invalid GREEN-API message ID")
    if kind == "textMessage":
        block = data.get("textMessageData")
        value = block.get("textMessage") if isinstance(block, dict) else None
    elif kind == "extendedTextMessage":
        block = data.get("extendedTextMessageData")
        value = block.get("text") if isinstance(block, dict) else None
    else:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > 12000:
        raise HTTPException(422, detail="Invalid GREEN-API message text")
    name = sender.get("senderName")
    if not isinstance(name, str) or len(name) > 180:
        name = None
    timestamp = body.get("timestamp")
    if not isinstance(timestamp, int) or isinstance(timestamp, bool) or not 1577836800 <= timestamp <= 2147483647:
        raise HTTPException(422, detail="Invalid GREEN-API timestamp")
    message = NormalizedChannelMessage(
        idempotency_key="green:" + msg_id,
        channel_code=binding["service"]["channel_code"],
        channel_kind="WHATSAPP",
        channel_display_name="WhatsApp",
        external_account_id=binding["instance"],
        external_conversation_id=chat_id,
        external_contact_id=chat_id,
        contact_name=name,
        direction="INBOUND",
        external_message_id=msg_id,
        sender_type="GUEST",
        sender_external_id=chat_id,
        text=value.strip(),
        delivery_status="RECEIVED",
        sent_at=datetime.fromtimestamp(timestamp, tz=timezone.utc),
    )
    require_bound_channel(message, binding["service"])
    return message


@router.post("/webhook", status_code=202)
async def receive_green_webhook(request: Request):
    bindings = rc7_webhook_config()
    binding = authenticated_binding(request, bindings)
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, detail="GREEN-API webhook requires JSON")
    raw = await request.body()
    if len(raw) > 16384:
        raise HTTPException(413, detail="GREEN-API notification is too large")
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeError):
        raise HTTPException(422, detail="Invalid GREEN-API JSON") from None
    # Cross-check the provider's static owner configuration against the
    # currently ACTIVE tenant/property relationship in PostgreSQL. The body
    # is never allowed to choose this property.
    async with request.app.state.db.acquire() as conn:
        row = await conn.fetchrow(
            '''SELECT p.id,p."tenantId" FROM properties p
               JOIN tenants t ON t.id=p."tenantId"
               WHERE p.code=$1 AND t.code=$2 AND t.status='ACTIVE' ''',
            binding["property_code"], binding["tenant_code"],
        )
    if (not row or str(row["id"]) != binding["green_property_id"]
            or str(row["tenantId"]) != binding["green_tenant_id"]):
        raise HTTPException(503, detail="GREEN-API hotel binding is not active")
    message = normalize_green_text(body, binding)
    if message is None:
        return {"accepted": True, "stored": False, "reason": "UNSUPPORTED_EVENT"}
    result = await ingest_normalized_channel_message(
        message, request, binding["service"],
    )
    # Acknowledgement is about DB commit ONLY: it is NOT a provider send or
    # a WhatsApp delivery receipt.
    return {
        "accepted": True, "stored": True,
        "idempotent_replay": result["idempotent_replay"],
        "conversation_id": result["conversation_id"] if "conversation_id" in result else None,
    }
