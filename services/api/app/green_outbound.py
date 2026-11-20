"""Explicit human-operated WhatsApp send via canonical Inbox, RC8 staging only.

GREEN-API SendMessage acknowledges QUEUEING, never delivery. The existing
GREEN-API RC7 webhook, not this action, later marks SENT or DELIVERED.
No automatic retries after ambiguous provider results.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import HTTPException, Request

from .auth import trusted_property_id
from .communication_ingest import NormalizedChannelMessage, ingest_normalized_channel_message
from .green_api_webhook import DIRECT_CHAT, MESSAGE_ID
from .shared_green_rc8 import rc8_guard
from .shared_inbox_rc5_identity import configured_channel_adapters
from .whatsapp_connection import _configuration


async def _provider_send(config, chat_id: str, text: str) -> str:
    """Return provider-assigned ID, never claim that a phone received it."""
    origin, instance, token = config
    try:
        async with httpx.AsyncClient(timeout=18, follow_redirects=False, trust_env=False) as client:
            response = await client.post(
                f"{origin}/waInstance{instance}/sendMessage/{token}",
                json={"chatId": chat_id, "message": text, "linkPreview": False},
            )
        if response.status_code != 200 or len(response.content) > 4096:
            raise ValueError("GREEN API did not confirm queue acceptance")
        data = response.json()
        identifier = data.get("idMessage") if isinstance(data, dict) else None
        if not isinstance(identifier, str) or not MESSAGE_ID.fullmatch(identifier):
            raise ValueError("GREEN API did not provide a valid message id")
        return identifier
    except (httpx.HTTPError, ValueError):
        # Never log or return the provider URL because it contains credentials.
        raise HTTPException(502, detail="GREEN-API queue acceptance is unconfirmed") from None


def _service_identity(user: dict[str, Any], channel_code: str, instance: str) -> dict[str, str]:
    rows = configured_channel_adapters()
    matched = [
        r for r in rows
        if r["tenant_code"] == user.get("tenant_code")  # user has UUID, see below
        and r["property_code"] == user.get("property_code")
        and r["channel_code"] == channel_code
        and r["external_account_id"] == instance
    ]
    # Tenant codes are NOT carried in AuthUser; they are from trusted DB
    # session UUID. Match solely on property+channel+instance after that DB
    # property UUID was resolved. The adapter's tenant_code is checked again
    # against the database below before any dispatch.
    if not matched:
        matched = [
            r for r in rows if r["property_code"] == user.get("property_code")
            and r["channel_code"] == channel_code
            and r["external_account_id"] == instance
        ]
    if len(matched) != 1:
        raise HTTPException(503, detail="Hotel WhatsApp adapter is not configured")
    row = matched[0]
    return {
        "actor_type": "SERVICE",
        "actor_id": "staff-whatsapp:" + str(user["id"]),
        "tenant_code": row["tenant_code"],
        "property_code": row["property_code"],
        "channel_code": row["channel_code"],
        "external_account_id": row["external_account_id"],
    }


def _json_value(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


async def send_green_text(
    conversation_id: uuid.UUID,
    text: str,
    request: Request,
    user: dict[str, Any],
    key: str,
) -> dict[str, Any] | None:
    """Only WHATSAPP is handled; Telegram retains the existing function."""
    async with request.app.state.db.acquire() as conn:
        pid = await trusted_property_id(conn, user)
        conversation = await conn.fetchrow(
            '''SELECT c.id,c."assignedToId",c."externalConversationId",
                      c."externalContactId",c."contactName",c."contactPhone",
                      c."contactUsername",
                      ch.code AS channel_code,ch.kind::text AS channel_kind,
                      ch."displayName" AS channel_name,
                      ch."externalAccountId" AS external_account_id
               FROM conversations c
               JOIN communication_channels ch ON ch.id=c."channelId"
               WHERE c.id=$1 AND c."propertyId"=$2 AND ch."propertyId"=$2''',
            conversation_id, pid,
        )
    if not conversation:
        raise HTTPException(404, detail="Conversation not found")
    if conversation["channel_kind"] != "WHATSAPP":
        return None

    rc8_guard()
    if user.get("role") == "RECEPTION" and str(conversation["assignedToId"]) != str(user["id"]):
        raise HTTPException(403, detail="Reception must claim this hotel conversation before reply")
    chat_id = conversation["externalConversationId"]
    if not isinstance(chat_id, str) or not DIRECT_CHAT.fullmatch(chat_id):
        raise HTTPException(409, detail="Only tracked personal WhatsApp chats support human replies")
    config = _configuration(user)
    if config is None:
        raise HTTPException(503, detail="GREEN-API connection is not configured")
    _, instance, _ = config
    if conversation["external_account_id"] != instance:
        raise HTTPException(409, detail="Conversation is not bound to the paired WhatsApp account")
    service = _service_identity(user, conversation["channel_code"], instance)
    # Ensure the selected adapter's tenant code refers to the authenticated
    # property's actual tenant UUID, not just a reused display code.
    async with request.app.state.db.acquire() as conn:
        valid = await conn.fetchval(
            '''SELECT 1 FROM properties p JOIN tenants t ON t.id=p."tenantId"
               WHERE p.id=$1 AND p.code=$2 AND t.id=$3 AND t.code=$4
                 AND t.status='ACTIVE' ''',
            pid, user["property_code"], uuid.UUID(str(user["tenant_id"])),
            service["tenant_code"],
        )
    if valid != 1:
        raise HTTPException(503, detail="Authenticated hotel adapter boundary unavailable")

    source = f"OUTBOX_{service['channel_code']}"[:60]
    dispatch = {
        "conversation_id": str(conversation_id),
        "channel_code": service["channel_code"],
        "actor_id": user["id"],
        "text": text,
    }
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            inserted = await conn.fetchval(
                '''INSERT INTO automation_inbound_events
                   (id,"propertyId",source,"idempotencyKey","eventType",
                    "payloadJson","createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,'COMMUNICATION_OUTBOUND_DISPATCH',$5::jsonb,now(),now())
                   ON CONFLICT ("propertyId",source,"idempotencyKey") DO NOTHING
                   RETURNING id''',
                uuid.uuid4(), pid, source, key, json.dumps(dispatch),
            )
            if inserted is None:
                old = await conn.fetchrow(
                    '''SELECT "eventType","payloadJson","resultResource","resultResourceId"
                       FROM automation_inbound_events
                       WHERE "propertyId"=$1 AND source=$2 AND "idempotencyKey"=$3''',
                    pid, source, key,
                )
                if (not old or old["eventType"] != "COMMUNICATION_OUTBOUND_DISPATCH"
                        or _json_value(old["payloadJson"]) != dispatch):
                    raise HTTPException(409, detail={"code": "OUTBOX_IDEMPOTENCY_PAYLOAD_MISMATCH"})
                if old["resultResource"] == "ConversationMessage" and old["resultResourceId"]:
                    original = await conn.fetchrow(
                        '''SELECT m.id,m."deliveryStatus"::text AS delivery_status
                           FROM conversation_messages m
                           JOIN conversations c ON c.id=m."conversationId"
                           WHERE m.id=$1::uuid AND c.id=$2 AND c."propertyId"=$3''',
                        old["resultResourceId"], conversation_id, pid,
                    )
                    if original:
                        return {
                            "idempotent_replay": True,
                            "conversation_id": str(conversation_id),
                            "message_id": str(original["id"]),
                            "delivery_status": original["delivery_status"],
                            "counts_as_response": original["delivery_status"] in {"SENT", "DELIVERED"},
                            "auto_sent": False,
                        }
                raise HTTPException(
                    409,
                    detail={"code": "OUTBOX_RECONCILIATION_REQUIRED",
                            "automatic_retry_safe": False},
                )

    try:
        # A successful HTTP result still means QUEUED, not SENT/DELIVERED.
        provider_message_id = await _provider_send(config, chat_id, text)
        normalized = NormalizedChannelMessage(
            idempotency_key=f"rc8:queued:{key}",
            channel_code=service["channel_code"],
            channel_kind="WHATSAPP",
            channel_display_name=conversation["channel_name"],
            external_account_id=instance,
            external_conversation_id=chat_id,
            external_contact_id=conversation["externalContactId"],
            contact_name=conversation["contactName"],
            contact_phone=conversation["contactPhone"],
            contact_username=conversation["contactUsername"],
            direction="OUTBOUND",
            external_message_id=provider_message_id,
            sender_type="STAFF",
            sender_external_id=str(user["id"]),
            text=text,
            content_type="TEXT",
            delivery_status="QUEUED",
            sent_at=datetime.now(timezone.utc),
            raw_payload={"provider": "green-api", "evidence": "ACCEPTED_TO_QUEUE_ONLY"},
        )
        persisted = await ingest_normalized_channel_message(normalized, request, service)
        async with request.app.state.db.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    '''UPDATE automation_inbound_events
                       SET "resultResource"='ConversationMessage',
                           "resultResourceId"=$1,"updatedAt"=now()
                       WHERE "propertyId"=$2 AND source=$3 AND "idempotencyKey"=$4''',
                    persisted["id"], pid, source, key,
                )
                await conn.execute(
                    '''INSERT INTO audit_logs
                       (id,"propertyId","actorType","actorId",action,resource,
                        "resourceId",source,result,"afterJson","createdAt")
                       VALUES ($1,$2,'STAFF',$3,'SEND_MESSAGE','ConversationMessage',
                               $4,'INBOX','QUEUED',
                               jsonb_build_object('channel','WHATSAPP',
                                   'conversation_id',$5::text,'auto_send',false),now())''',
                    uuid.uuid4(), pid, user["id"], str(persisted["id"]), str(conversation_id),
                )
        return {
            "idempotent_replay": False,
            "conversation_id": str(conversation_id),
            "message_id": persisted["id"],
            "delivery_status": "QUEUED",
            "counts_as_response": False,
            "auto_sent": False,
        }
    except Exception:
        # The provider could have accepted the message before the connection
        # failed. Mark manual reconciliation and NEVER auto-retry with this key.
        async with request.app.state.db.acquire() as conn:
            await conn.execute(
                '''UPDATE automation_inbound_events
                   SET "resultResource"='OutboundReconciliationRequired',
                       "updatedAt"=now()
                   WHERE "propertyId"=$1 AND source=$2 AND "idempotencyKey"=$3
                     AND "resultResource" IS NULL''',
                pid, source, key,
            )
        raise
