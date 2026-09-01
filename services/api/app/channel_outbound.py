import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .auth import require_roles
from .communication_ingest import NormalizedChannelMessage, ingest_normalized_channel_message
from .telegram_sales import (
    TELEGRAM_SALES_CHANNEL_CODE,
    send_telegram_text,
    telegram_sales_inbound_configured,
    telegram_sales_outbound_configured,
)

router = APIRouter(prefix="/api/v1/admin/inbox", tags=["admin-inbox-outbound"])
manager_access = require_roles("OWNER", "MANAGER")
PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")


class OutboundTextCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4096)


def _validate_idempotency_key(value: str | None) -> str:
    if value is None:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")
    key = value.strip()
    if len(key) < 8 or len(key) > 160:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be 8..160 characters")
    return key


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


async def _property_id(conn, property_code: str) -> uuid.UUID:
    pid = await conn.fetchval("SELECT id FROM properties WHERE code=$1", property_code)
    if not pid:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return pid


@router.get("/outbound-capabilities")
async def outbound_capabilities(
    user: dict[str, Any] = Depends(manager_access),
):
    return {
        "telegram": {
            "channel_code": TELEGRAM_SALES_CHANNEL_CODE,
            "inbound_configured": telegram_sales_inbound_configured(),
            "outbound_configured": telegram_sales_outbound_configured(),
            "max_text_length": 4096,
        },
        "whatsapp": {
            "configured": False,
            "configured_in_core": False,
            "delivery_owner": "n8n/provider adapter",
            "evidence_endpoint": "/api/v1/automation/inbox/messages",
        },
        "instagram": {
            "configured": False,
            "configured_in_core": False,
            "delivery_owner": "n8n/provider adapter",
            "evidence_endpoint": "/api/v1/automation/inbox/messages",
        },
        "truth": "Only provider-confirmed SENT/DELIVERED clears needs_reply. Resort Core does not claim WhatsApp/Instagram delivery without provider evidence.",
    }


@router.post("/conversations/{conversation_id}/send-text")
async def send_text_message(
    conversation_id: uuid.UUID,
    payload: OutboundTextCreate,
    request: Request,
    idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key"),
    user: dict[str, Any] = Depends(manager_access),
):
    idempotency_key = _validate_idempotency_key(idempotency_key_header)

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await _property_id(conn, user["property_code"])
            row = await conn.fetchrow(
                '''
                SELECT c.id,c."externalConversationId",c."externalContactId",c."contactName",c."contactPhone",c."contactUsername",
                       ch.code AS channel_code,ch.kind::text AS channel_kind,ch."displayName" AS channel_name,
                       ch."externalAccountId" AS external_account_id
                FROM conversations c
                JOIN communication_channels ch ON ch.id=c."channelId"
                WHERE c.id=$1 AND c."propertyId"=$2
                ''',
                conversation_id,
                pid,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Conversation not found")
            if row["channel_kind"] != "TELEGRAM" or row["channel_code"] != TELEGRAM_SALES_CHANNEL_CODE:
                raise HTTPException(status_code=409, detail="Outbound adapter is not configured for this conversation channel")
            if not row["externalConversationId"]:
                raise HTTPException(status_code=409, detail="Conversation has no external Telegram chat id")
            if not telegram_sales_outbound_configured():
                raise HTTPException(status_code=503, detail="Telegram Sales outbound is not configured")

            source = f"OUTBOX_{row['channel_code']}"[:60]
            dispatch_payload = {
                "conversation_id": str(conversation_id),
                "channel_code": row["channel_code"],
                "actor_id": user["id"],
                "text": payload.text,
            }
            event_id = uuid.uuid4()
            inserted = await conn.fetchval(
                '''
                INSERT INTO automation_inbound_events (
                  id,"propertyId",source,"idempotencyKey","eventType","payloadJson","createdAt","updatedAt"
                ) VALUES ($1,$2,$3,$4,'COMMUNICATION_OUTBOUND_DISPATCH',$5::jsonb,now(),now())
                ON CONFLICT ("propertyId",source,"idempotencyKey") DO NOTHING
                RETURNING id
                ''',
                event_id,
                pid,
                source,
                idempotency_key,
                json.dumps(dispatch_payload),
            )

            if inserted is None:
                existing = await conn.fetchrow(
                    '''
                    SELECT "eventType","payloadJson","resultResource","resultResourceId"
                    FROM automation_inbound_events
                    WHERE "propertyId"=$1 AND source=$2 AND "idempotencyKey"=$3
                    ''',
                    pid,
                    source,
                    idempotency_key,
                )
                if not existing:
                    raise HTTPException(status_code=409, detail={"code": "OUTBOX_IDEMPOTENCY_RECONCILIATION_REQUIRED"})
                if (
                    existing["eventType"] != "COMMUNICATION_OUTBOUND_DISPATCH"
                    or _json_value(existing["payloadJson"]) != dispatch_payload
                ):
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "OUTBOX_IDEMPOTENCY_PAYLOAD_MISMATCH",
                            "conversation_id": str(conversation_id),
                            "idempotency_key": idempotency_key,
                        },
                    )
                if existing["resultResource"] == "ConversationMessage" and existing["resultResourceId"]:
                    previous = await conn.fetchrow(
                        '''SELECT id,"deliveryStatus"::text AS delivery_status
                           FROM conversation_messages WHERE id=$1::uuid''',
                        existing["resultResourceId"],
                    )
                    return {
                        "idempotent_replay": True,
                        "conversation_id": str(conversation_id),
                        "message_id": str(previous["id"]) if previous else existing["resultResourceId"],
                        "delivery_status": previous["delivery_status"] if previous else "UNKNOWN",
                    }
                if existing["resultResource"] == "OutboundReconciliationRequired":
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "OUTBOX_RECONCILIATION_REQUIRED",
                            "conversation_id": str(conversation_id),
                            "idempotency_key": idempotency_key,
                            "automatic_retry_safe": False,
                        },
                    )
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "OUTBOX_DISPATCH_IN_PROGRESS",
                        "conversation_id": str(conversation_id),
                        "idempotency_key": idempotency_key,
                        "automatic_retry_safe": False,
                    },
                )

    provider_result = await send_telegram_text(str(row["externalConversationId"]), payload.text)
    provider_state = provider_result["state"]
    provider_message_id = provider_result.get("message_id")
    provider_sent_at = provider_result.get("sent_at")
    external_message_id = (
        f"{row['externalConversationId']}:{provider_message_id}"
        if provider_state == "SENT" and provider_message_id is not None
        else None
    )

    normalized = NormalizedChannelMessage(
        idempotency_key=f"outbound:{idempotency_key}",
        channel_code=row["channel_code"],
        channel_kind="TELEGRAM",
        channel_display_name=row["channel_name"],
        external_account_id=row["external_account_id"],
        external_conversation_id=str(row["externalConversationId"]),
        external_contact_id=row["externalContactId"],
        contact_name=row["contactName"],
        contact_phone=row["contactPhone"],
        contact_username=row["contactUsername"],
        direction="OUTBOUND",
        external_message_id=external_message_id,
        sender_type="STAFF",
        sender_external_id=user["id"],
        text=payload.text,
        content_type="TEXT",
        delivery_status=provider_state,
        sent_at=provider_sent_at or datetime.now(timezone.utc),
        raw_payload={
            "provider": "telegram",
            "provider_status_code": provider_result.get("provider_status_code"),
            "provider_response": provider_result.get("provider_payload"),
            "description": provider_result.get("description"),
        },
    )

    try:
        message_result = await ingest_normalized_channel_message(
            normalized,
            request,
            {"actor_type": "SERVICE", "actor_id": f"staff-outbound:{user['id']}"},
        )
    except Exception:
        # Provider may already have accepted the message. Mark this dispatch as
        # reconciliation-required so the same idempotency key cannot send again.
        async with request.app.state.db.acquire() as conn:
            await conn.execute(
                '''
                UPDATE automation_inbound_events
                SET "resultResource"='OutboundReconciliationRequired',"updatedAt"=now()
                WHERE "propertyId"=$1 AND source=$2 AND "idempotencyKey"=$3
                ''',
                pid,
                source,
                idempotency_key,
            )
        raise

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                '''
                UPDATE automation_inbound_events
                SET "resultResource"='ConversationMessage',"resultResourceId"=$1,"updatedAt"=now()
                WHERE "propertyId"=$2 AND source=$3 AND "idempotencyKey"=$4
                ''',
                message_result["id"],
                pid,
                source,
                idempotency_key,
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                VALUES ($1,$2,'STAFF',$3,'SEND_MESSAGE','ConversationMessage',$4,'INBOX',$5,
                  jsonb_build_object('conversation_id',$6::text,'channel',$7::text,'delivery_status',$8::text),now())
                ''',
                uuid.uuid4(),
                pid,
                user["id"],
                message_result["id"],
                "SUCCESS" if provider_state == "SENT" else provider_state,
                str(conversation_id),
                row["channel_code"],
                provider_state,
            )

    response_payload = {
        "idempotent_replay": False,
        "conversation_id": str(conversation_id),
        "message_id": message_result["id"],
        "delivery_status": provider_state,
        "counts_as_response": provider_state == "SENT",
        "provider_description": provider_result.get("description"),
    }
    if provider_state == "SENT":
        return response_payload
    return JSONResponse(status_code=502, content=response_payload)
