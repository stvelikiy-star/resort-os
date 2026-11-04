"""GREEN-API webhook adapter for shared MARINA staging RC7.

One provider-specific ingress feeds the EXISTING canonical normalized Inbox.
No direct conversation-table writes, hotel choice from body/header, provider
send APIs, auto replies, or external AI calls. Off by default.
"""
import hmac
import json
import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request

from .communication_ingest import NormalizedChannelMessage, ingest_normalized_channel_message
from .shared_inbox_rc5_identity import (
    configured_channel_adapters,
    resolve_channel_property,
)

router = APIRouter(prefix="/api/v1/automation/green-api", tags=["green-api-webhook"])

DIRECT_CHAT = re.compile(r"^[1-9][0-9]{5,15}@c\.us$")
MESSAGE_ID = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
SERVICE_INSTANCE = re.compile(r"^[0-9]{5,24}$")
SECRET = re.compile(r"^[A-Za-z0-9_-]{32,256}$")
MAX_BODY_BYTES = 32_768


def _webhook_bindings() -> tuple[dict[str, str], ...]:
    """Parse a distinct credential per provider instance, with full RC5 match."""
    try:
        values = json.loads(os.environ.get("MARINA_SHARED_GREEN_RC7_WEBHOOKS_JSON", ""))
        if not isinstance(values, list) or not 2 <= len(values) <= 100:
            raise ValueError("Missing per-property webhook bindings")
        adapters = configured_channel_adapters()
        provider_bindings = json.loads(os.environ.get("MARINA_SHARED_GREEN_RC6_CONFIG_JSON", ""))
        if not isinstance(provider_bindings, list) or len(provider_bindings) != len(adapters):
            raise ValueError("Missing paired provider identities")
        result = []
        for item in values:
            if not isinstance(item, dict) or set(item) != {
                "tenant_code", "property_code", "channel_code",
                "instance", "webhook_token",
            }:
                raise ValueError("Invalid webhook binding schema")
            if any(not isinstance(v, str) for v in item.values()):
                raise ValueError("Invalid webhook binding fields")
            if (not SERVICE_INSTANCE.fullmatch(item["instance"])
                    or not SECRET.fullmatch(item["webhook_token"])):
                raise ValueError("Invalid webhook instance or token")
            if len([r for r in adapters if (
                r["tenant_code"] == item["tenant_code"]
                and r["property_code"] == item["property_code"]
                and r["channel_code"] == item["channel_code"]
                and r["external_account_id"] == item["instance"]
                and r["service_key"] != item["webhook_token"]
            )]) != 1:
                raise ValueError("Webhook binding does not match an independent inbox adapter")
            # The owner-paired GREEN API instance must match as well. Token
            # authentication may never silently retarget a different account.
            if len([p for p in provider_bindings if isinstance(p, dict)
                    and p.get("property_code") == item["property_code"]
                    and p.get("instance") == item["instance"]
                    and p.get("token") != item["webhook_token"]]) != 1:
                raise ValueError("Webhook instance does not match owner pairing")
            result.append(item)
        for field in ("instance", "property_code", "webhook_token"):
            if len({r[field] for r in result}) != len(result):
                raise ValueError("Duplicate webhook binding")
        if len(result) != len(adapters):
            raise ValueError("Missing webhook for a shared Inbox adapter")
        return tuple(result)
    except (TypeError, ValueError, KeyError):
        raise HTTPException(503, detail="GREEN-API webhook bindings are not configured") from None


def _bearer_identity(authorization: str | None) -> dict[str, str]:
    if (not isinstance(authorization, str)
            or not authorization.startswith("Bearer ")
            or not SECRET.fullmatch(authorization[7:])):
        raise HTTPException(401, detail="Invalid GREEN-API webhook credential")
    token = authorization[7:]
    rows = _webhook_bindings()
    matching = [
        r for r in rows if hmac.compare_digest(r["webhook_token"], token)
    ]
    if len(matching) != 1:
        raise HTTPException(401, detail="Invalid GREEN-API webhook credential")
    row = matching[0]
    return {
        "actor_type": "SERVICE",
        "actor_id": "green-webhook:" + row["property_code"],
        "tenant_code": row["tenant_code"],
        "property_code": row["property_code"],
        "channel_code": row["channel_code"],
        "external_account_id": row["instance"],
    }


def _valid_instance(event: dict, service: dict[str, str]) -> None:
    metadata = event.get("instanceData")
    if not isinstance(metadata, dict):
        raise HTTPException(422, detail="Invalid GREEN-API instance metadata")
    instance = metadata.get("idInstance")
    if (isinstance(instance, bool) or not isinstance(instance, (int, str))
            or str(instance) != service["external_account_id"]
            or metadata.get("typeInstance") != "whatsapp"):
        raise HTTPException(403, detail="Webhook does not belong to this WhatsApp account")


def _event_time(event: dict) -> datetime:
    value = event.get("timestamp")
    if isinstance(value, bool) or not isinstance(value, int):
        raise HTTPException(422, detail="Invalid GREEN-API timestamp")
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        raise HTTPException(422, detail="Invalid GREEN-API timestamp") from None


def _message_id(event: dict) -> str:
    value = event.get("idMessage")
    if not isinstance(value, str) or not MESSAGE_ID.fullmatch(value):
        raise HTTPException(422, detail="Invalid GREEN-API message ID")
    return value


def _direct_chat(value) -> str:
    if not isinstance(value, str) or not DIRECT_CHAT.fullmatch(value):
        # Group chats and anonymous/unsupported identifiers require separate
        # consent and access-control acceptance, not silent Inbox ingestion.
        raise HTTPException(422, detail="Only individual WhatsApp chats are reviewed")
    return value


def _incoming(event: dict, service: dict[str, str]) -> NormalizedChannelMessage:
    msg_id = _message_id(event)
    data = event.get("senderData")
    msg = event.get("messageData")
    if not isinstance(data, dict) or not isinstance(msg, dict):
        raise HTTPException(422, detail="Invalid incoming GREEN-API message")
    chat_id = _direct_chat(data.get("chatId"))
    if data.get("sender") != chat_id or msg.get("typeMessage") != "textMessage":
        raise HTTPException(422, detail="Unsupported incoming WhatsApp message type")
    text_data = msg.get("textMessageData")
    if not isinstance(text_data, dict):
        raise HTTPException(422, detail="Missing WhatsApp text")
    text = text_data.get("textMessage")
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 12000:
        raise HTTPException(422, detail="Invalid WhatsApp text")
    name = data.get("senderName")
    if not isinstance(name, str):
        name = None
    return NormalizedChannelMessage(
        idempotency_key="green7:in:" + msg_id,
        channel_code=service["channel_code"],
        channel_kind="WHATSAPP",
        channel_display_name="WhatsApp",
        external_account_id=service["external_account_id"],
        external_conversation_id=chat_id,
        external_contact_id=chat_id,
        contact_name=name.strip()[:180] if name else None,
        direction="INBOUND",
        external_message_id=msg_id,
        sender_type="GUEST",
        sender_external_id=chat_id,
        text=text,
        content_type="TEXT",
        delivery_status="RECEIVED",
        sent_at=_event_time(event),
    )


async def _outbound_status(event: dict, service: dict[str, str], request: Request) -> NormalizedChannelMessage:
    msg_id = _message_id(event)
    chat_id = _direct_chat(event.get("chatId"))
    if event.get("sendByApi") is not True:
        raise HTTPException(422, detail="Only provider API dispatch statuses are reviewed")
    raw_status = event.get("status")
    statuses = {"sent": "SENT", "delivered": "DELIVERED", "read": "DELIVERED", "failed": "FAILED"}
    if not isinstance(raw_status, str) or raw_status not in statuses:
        raise HTTPException(422, detail="Unsupported GREEN-API delivery status")

    # A callback must NEVER create an outgoing message. It may only reconcile
    # one already present in this exact hotel's conversation and channel.
    async with request.app.state.db.acquire() as conn:
        property_id = await resolve_channel_property(conn, service)
        if not property_id:
            raise HTTPException(503, detail="Property not available")
        prior = await conn.fetchrow(
            """SELECT m.direction::text AS direction,m."senderType" AS sender_type,
                      m."senderExternalId" AS sender_external_id,m.text,
                      m."contentType" AS content_type
               FROM conversation_messages m
               JOIN conversations c ON c.id=m."conversationId"
               JOIN communication_channels ch ON ch.id=c."channelId"
               WHERE c."propertyId"=$1 AND ch."propertyId"=$1
                 AND ch.code=$2 AND ch.kind='WHATSAPP'
                 AND ch."externalAccountId"=$3
                 AND c."externalConversationId"=$4
                 AND m."externalMessageId"=$5 AND m.direction='OUTBOUND'""",
            property_id, service["channel_code"],
            service["external_account_id"], chat_id, msg_id,
        )
    if not prior or not isinstance(prior["text"], str) or not prior["text"]:
        raise HTTPException(409, detail="Provider status requires a previously recorded outbound message")
    return NormalizedChannelMessage(
        idempotency_key="green7:status:" + raw_status + ":" + msg_id,
        channel_code=service["channel_code"],
        channel_kind="WHATSAPP",
        channel_display_name="WhatsApp",
        external_account_id=service["external_account_id"],
        external_conversation_id=chat_id,
        external_contact_id=chat_id,
        direction="OUTBOUND",
        external_message_id=msg_id,
        sender_type=prior["sender_type"],
        sender_external_id=prior["sender_external_id"],
        text=prior["text"],
        content_type=prior["content_type"],
        delivery_status=statuses[raw_status],
        sent_at=_event_time(event),
    )


@router.post("/webhook", status_code=202)
async def green_api_webhook(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    # The RC7 middleware authorizes the explicit staging stage; token picks
    # one hotel. Neither URL params nor payload can supply a property ID.
    service = _bearer_identity(authorization)
    chunks = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_BODY_BYTES:
            raise HTTPException(413, detail="GREEN-API webhook too large")
        chunks.append(chunk)
    try:
        event = json.loads(b"".join(chunks))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(422, detail="Invalid GREEN-API JSON") from None
    if not isinstance(event, dict):
        raise HTTPException(422, detail="Invalid GREEN-API event")
    _valid_instance(event, service)
    if event.get("typeWebhook") == "incomingMessageReceived":
        normalized = _incoming(event, service)
    elif event.get("typeWebhook") == "outgoingMessageStatus":
        normalized = await _outbound_status(event, service, request)
    else:
        # Never silently ingest unknown media, phone-origin messages, group
        # content or login state as customer text.
        raise HTTPException(422, detail="GREEN-API event type not yet reviewed")
    result = await ingest_normalized_channel_message(normalized, request, service)
    return {
        "accepted": True,
        "idempotent_replay": result.get("idempotent_replay", False),
        "conversation_id": result.get("conversation_id"),
        "resource": result.get("resource"),
    }
