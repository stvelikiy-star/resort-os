import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from .service_auth import require_automation_service

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
router = APIRouter(prefix="/api/v1/automation/inbox", tags=["automation-inbox"])
service_access = require_automation_service


class NormalizedChannelMessage(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=180)
    channel_code: str = Field(min_length=2, max_length=80)
    channel_kind: Literal["WEBSITE", "TELEGRAM", "WHATSAPP", "INSTAGRAM", "OTHER"]
    channel_display_name: str = Field(min_length=2, max_length=120)
    external_account_id: str | None = Field(default=None, max_length=180)
    external_conversation_id: str = Field(min_length=1, max_length=240)
    external_contact_id: str | None = Field(default=None, max_length=240)
    contact_name: str | None = Field(default=None, max_length=180)
    contact_phone: str | None = Field(default=None, max_length=60)
    contact_username: str | None = Field(default=None, max_length=180)
    direction: Literal["INBOUND", "OUTBOUND"]
    external_message_id: str | None = Field(default=None, max_length=240)
    sender_type: str = Field(min_length=2, max_length=60)
    sender_external_id: str | None = Field(default=None, max_length=240)
    text: str | None = Field(default=None, max_length=12000)
    content_type: str = Field(default="TEXT", min_length=2, max_length=60)
    delivery_status: Literal["RECEIVED", "QUEUED", "SENT", "DELIVERED", "FAILED", "UNKNOWN"] = "UNKNOWN"
    sent_at: datetime | None = None
    raw_payload: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_content(self):
        if not self.text and not self.raw_payload:
            raise ValueError("text or raw_payload is required")
        return self


def normalized_channel_code(value: str) -> str:
    code = "".join(ch for ch in value.upper().strip() if ch.isalnum() or ch in {"_", "-"})
    if len(code) < 2:
        raise HTTPException(status_code=422, detail="Invalid channel_code")
    return code[:80]


def normalized_message_time(value: datetime | None) -> datetime:
    if value is None:
        return datetime.utcnow()
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


async def _stable_channel(conn, pid: uuid.UUID, code: str, payload: NormalizedChannelMessage):
    existing = await conn.fetchrow(
        '''SELECT id,kind::text AS kind,"displayName","externalAccountId"
           FROM communication_channels WHERE "propertyId"=$1 AND code=$2 FOR UPDATE''',
        pid,
        code,
    )
    if not existing:
        inserted = await conn.fetchval(
            '''
            INSERT INTO communication_channels (
              id,"propertyId",code,kind,"displayName","externalAccountId","isActive",metadata,"createdAt","updatedAt"
            ) VALUES ($1,$2,$3,$4::"CommunicationChannelKind",$5,$6,true,NULL,now(),now())
            ON CONFLICT ("propertyId",code) DO NOTHING
            RETURNING id
            ''',
            uuid.uuid4(),
            pid,
            code,
            payload.channel_kind,
            payload.channel_display_name,
            payload.external_account_id,
        )
        if inserted:
            return inserted
        existing = await conn.fetchrow(
            '''SELECT id,kind::text AS kind,"displayName","externalAccountId"
               FROM communication_channels WHERE "propertyId"=$1 AND code=$2 FOR UPDATE''',
            pid,
            code,
        )
        if not existing:
            raise HTTPException(status_code=409, detail={"code": "CHANNEL_IDENTITY_RECONCILIATION_REQUIRED"})

    if existing["kind"] != payload.channel_kind:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CHANNEL_IDENTITY_KIND_MISMATCH",
                "channel_code": code,
                "existing_kind": existing["kind"],
                "requested_kind": payload.channel_kind,
            },
        )
    if (
        existing["externalAccountId"]
        and payload.external_account_id
        and existing["externalAccountId"] != payload.external_account_id
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CHANNEL_IDENTITY_ACCOUNT_MISMATCH",
                "channel_code": code,
            },
        )
    await conn.execute(
        '''UPDATE communication_channels
           SET "displayName"=$1,
               "externalAccountId"=COALESCE("externalAccountId",$2),
               "isActive"=true,"updatedAt"=now()
           WHERE id=$3''',
        payload.channel_display_name,
        payload.external_account_id,
        existing["id"],
    )
    return existing["id"]


def _delivery_transition_allowed(direction: str, existing: str, requested: str) -> bool:
    if direction == "INBOUND":
        return existing == requested
    allowed = {
        "UNKNOWN": {"UNKNOWN", "QUEUED", "SENT", "DELIVERED", "FAILED"},
        "QUEUED": {"QUEUED", "SENT", "DELIVERED", "FAILED"},
        "SENT": {"SENT", "DELIVERED"},
        "DELIVERED": {"DELIVERED"},
        "FAILED": {"FAILED"},
        "RECEIVED": {"RECEIVED"},
    }
    return requested in allowed.get(existing, {existing})


async def _reconcile_provider_message(
    conn,
    conversation_id: uuid.UUID,
    payload: NormalizedChannelMessage,
    message_time: datetime,
):
    if not payload.external_message_id:
        return None
    existing = await conn.fetchrow(
        '''
        SELECT id,direction::text AS direction,"senderType","senderExternalId",text,"contentType",
               "deliveryStatus"::text AS delivery_status,"rawPayload","sentAt"
        FROM conversation_messages
        WHERE "conversationId"=$1 AND "externalMessageId"=$2
        FOR UPDATE
        ''',
        conversation_id,
        payload.external_message_id,
    )
    if not existing:
        return None

    immutable_match = (
        existing["direction"] == payload.direction
        and existing["senderType"] == payload.sender_type
        and existing["senderExternalId"] == payload.sender_external_id
        and existing["text"] == payload.text
        and existing["contentType"] == payload.content_type
    )
    if not immutable_match:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "PROVIDER_MESSAGE_IDENTITY_MISMATCH",
                "external_message_id": payload.external_message_id,
                "conversation_id": str(conversation_id),
            },
        )

    current_status = existing["delivery_status"]
    if not _delivery_transition_allowed(payload.direction, current_status, payload.delivery_status):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "PROVIDER_MESSAGE_STATUS_REGRESSION",
                "external_message_id": payload.external_message_id,
                "existing_status": current_status,
                "requested_status": payload.delivery_status,
            },
        )

    status_changed = current_status != payload.delivery_status
    becomes_confirmed = (
        payload.direction == "OUTBOUND"
        and current_status not in {"SENT", "DELIVERED"}
        and payload.delivery_status in {"SENT", "DELIVERED"}
    )
    if status_changed or payload.raw_payload is not None or payload.sent_at is not None:
        await conn.execute(
            '''
            UPDATE conversation_messages
            SET "deliveryStatus"=$1::"MessageDeliveryStatus",
                "rawPayload"=CASE WHEN $2::jsonb IS NULL THEN "rawPayload" ELSE $2::jsonb END,
                "sentAt"=CASE WHEN $3::boolean THEN $4::timestamp ELSE "sentAt" END
            WHERE id=$5
            ''',
            payload.delivery_status,
            json.dumps(payload.raw_payload) if payload.raw_payload is not None else None,
            payload.sent_at is not None,
            message_time,
            existing["id"],
        )
    if becomes_confirmed:
        await conn.execute(
            '''
            UPDATE conversations
            SET "lastOutboundAt"=CASE
                  WHEN "lastOutboundAt" IS NULL OR "lastOutboundAt" < $1::timestamp THEN $1::timestamp
                  ELSE "lastOutboundAt" END,
                "firstResponseAt"=CASE
                  WHEN "firstResponseAt" IS NULL AND "lastInboundAt" IS NOT NULL THEN $1::timestamp
                  ELSE "firstResponseAt" END,
                "updatedAt"=now()
            WHERE id=$2
            ''',
            message_time,
            conversation_id,
        )
    return {
        "id": existing["id"],
        "status_changed": status_changed,
        "counts_as_response": payload.direction == "OUTBOUND" and payload.delivery_status in {"SENT", "DELIVERED"},
    }


async def ingest_normalized_channel_message(
    payload: NormalizedChannelMessage,
    request: Request,
    service: dict[str, Any],
) -> dict[str, Any]:
    """Persist one provider-normalized communication event.

    Provider adapters must normalize into this contract instead of writing
    communication tables directly. Only provider-confirmed SENT/DELIVERED
    outbound messages count as an actual response to the guest.
    """
    code = normalized_channel_code(payload.channel_code)
    source = f"INBOX_{code}"[:60]
    message_time = normalized_message_time(payload.sent_at)
    payload_json = payload.model_dump_json()
    is_inbound = payload.direction == "INBOUND"
    is_confirmed_outbound = (
        payload.direction == "OUTBOUND"
        and payload.delivery_status in {"SENT", "DELIVERED"}
    )

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await conn.fetchval("SELECT id FROM properties WHERE code=$1", PROPERTY_CODE)
            if not pid:
                raise HTTPException(status_code=503, detail="Property is not loaded")

            existing_event = await conn.fetchrow(
                '''
                SELECT "eventType","payloadJson","resultResource","resultResourceId"
                FROM automation_inbound_events
                WHERE "propertyId"=$1 AND source=$2 AND "idempotencyKey"=$3
                ''',
                pid,
                source,
                payload.idempotency_key,
            )
            if existing_event:
                if (
                    existing_event["eventType"] != "COMMUNICATION_MESSAGE"
                    or _json_value(existing_event["payloadJson"]) != _json_value(payload_json)
                ):
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "INBOX_IDEMPOTENCY_PAYLOAD_MISMATCH",
                            "channel_code": code,
                            "idempotency_key": payload.idempotency_key,
                        },
                    )
                return {
                    "idempotent_replay": True,
                    "resource": existing_event["resultResource"],
                    "id": existing_event["resultResourceId"],
                }

            channel_id = await _stable_channel(conn, pid, code, payload)

            existing_conversation = await conn.fetchrow(
                '''SELECT id FROM conversations
                   WHERE "channelId"=$1 AND "externalConversationId"=$2''',
                channel_id,
                payload.external_conversation_id,
            )
            if existing_conversation and payload.external_message_id:
                reconciled = await _reconcile_provider_message(
                    conn, existing_conversation["id"], payload, message_time
                )
                if reconciled:
                    await conn.execute(
                        '''
                        INSERT INTO automation_inbound_events (
                          id,"propertyId",source,"idempotencyKey","eventType","payloadJson","resultResource","resultResourceId","createdAt","updatedAt"
                        ) VALUES ($1,$2,$3,$4,'COMMUNICATION_MESSAGE',$5::jsonb,'ConversationMessage',$6,now(),now())
                        ''',
                        uuid.uuid4(), pid, source, payload.idempotency_key, payload_json, str(reconciled["id"]),
                    )
                    return {
                        "idempotent_replay": not reconciled["status_changed"],
                        "reconciled_existing_message": True,
                        "resource": "ConversationMessage",
                        "id": str(reconciled["id"]),
                        "conversation_id": str(existing_conversation["id"]),
                        "delivery_status": payload.delivery_status,
                        "counts_as_response": reconciled["counts_as_response"],
                    }

            event_id = uuid.uuid4()
            await conn.execute(
                '''
                INSERT INTO automation_inbound_events (
                  id,"propertyId",source,"idempotencyKey","eventType","payloadJson","createdAt","updatedAt"
                ) VALUES ($1,$2,$3,$4,'COMMUNICATION_MESSAGE',$5::jsonb,now(),now())
                ''',
                event_id,
                pid,
                source,
                payload.idempotency_key,
                payload_json,
            )

            conversation = await conn.fetchrow(
                '''
                INSERT INTO conversations (
                  id,"propertyId","channelId","externalConversationId","externalContactId",
                  "contactName","contactPhone","contactUsername",status,"lastInboundAt","lastOutboundAt",
                  "firstResponseAt","createdAt","updatedAt"
                ) VALUES (
                  $1,$2,$3,$4,$5,$6,$7,$8,'OPEN',
                  CASE WHEN $9 THEN $11::timestamp ELSE NULL END,
                  CASE WHEN $10 THEN $11::timestamp ELSE NULL END,
                  NULL,now(),now()
                )
                ON CONFLICT ("channelId","externalConversationId") DO UPDATE SET
                  "externalContactId"=COALESCE(EXCLUDED."externalContactId",conversations."externalContactId"),
                  "contactName"=COALESCE(EXCLUDED."contactName",conversations."contactName"),
                  "contactPhone"=COALESCE(EXCLUDED."contactPhone",conversations."contactPhone"),
                  "contactUsername"=COALESCE(EXCLUDED."contactUsername",conversations."contactUsername"),
                  status=CASE WHEN $9 AND conversations.status IN ('RESOLVED','ARCHIVED') THEN 'OPEN'::"ConversationStatus" ELSE conversations.status END,
                  "lastInboundAt"=CASE
                    WHEN $9 AND (conversations."lastInboundAt" IS NULL OR conversations."lastInboundAt" < $11::timestamp)
                    THEN $11::timestamp ELSE conversations."lastInboundAt" END,
                  "lastOutboundAt"=CASE
                    WHEN $10 AND (conversations."lastOutboundAt" IS NULL OR conversations."lastOutboundAt" < $11::timestamp)
                    THEN $11::timestamp ELSE conversations."lastOutboundAt" END,
                  "firstResponseAt"=CASE
                    WHEN $10 AND conversations."firstResponseAt" IS NULL AND conversations."lastInboundAt" IS NOT NULL
                    THEN $11::timestamp ELSE conversations."firstResponseAt" END,
                  "resolvedAt"=CASE WHEN $9 THEN NULL ELSE conversations."resolvedAt" END,
                  "updatedAt"=now()
                RETURNING id
                ''',
                uuid.uuid4(), pid, channel_id, payload.external_conversation_id,
                payload.external_contact_id, payload.contact_name, payload.contact_phone,
                payload.contact_username, is_inbound, is_confirmed_outbound, message_time,
            )

            message_id = uuid.uuid4()
            inserted_message = await conn.fetchval(
                '''
                INSERT INTO conversation_messages (
                  id,"conversationId",direction,"externalMessageId","senderType","senderExternalId",text,
                  "contentType","deliveryStatus","rawPayload","sentAt","createdAt"
                ) VALUES ($1,$2,$3::"MessageDirection",$4,$5,$6,$7,$8,$9::"MessageDeliveryStatus",$10::jsonb,$11,now())
                ON CONFLICT ("conversationId","externalMessageId") DO NOTHING
                RETURNING id
                ''',
                message_id, conversation["id"], payload.direction, payload.external_message_id,
                payload.sender_type, payload.sender_external_id, payload.text, payload.content_type,
                payload.delivery_status, json.dumps(payload.raw_payload) if payload.raw_payload is not None else None,
                message_time,
            )
            if inserted_message is None:
                reconciled = await _reconcile_provider_message(conn, conversation["id"], payload, message_time)
                if not reconciled:
                    raise HTTPException(status_code=409, detail={"code": "INBOX_MESSAGE_RECONCILIATION_REQUIRED"})
                await conn.execute(
                    '''UPDATE automation_inbound_events SET "resultResource"='ConversationMessage',"resultResourceId"=$1,"updatedAt"=now() WHERE id=$2''',
                    str(reconciled["id"]), event_id,
                )
                return {
                    "idempotent_replay": not reconciled["status_changed"],
                    "reconciled_existing_message": True,
                    "resource": "ConversationMessage",
                    "id": str(reconciled["id"]),
                    "conversation_id": str(conversation["id"]),
                    "delivery_status": payload.delivery_status,
                    "counts_as_response": reconciled["counts_as_response"],
                }

            await conn.execute(
                '''UPDATE automation_inbound_events SET "resultResource"='ConversationMessage',"resultResourceId"=$1,"updatedAt"=now() WHERE id=$2''',
                str(message_id), event_id,
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                VALUES ($1,$2,'SERVICE',$3,'INGEST_MESSAGE','ConversationMessage',$4,$5,'SUCCESS',
                  jsonb_build_object('channel_code',$6::text,'direction',$7::text,'delivery_status',$8::text,'conversation_id',$9::text),now())
                ''',
                uuid.uuid4(), pid, service["actor_id"], str(message_id), source, code,
                payload.direction, payload.delivery_status, str(conversation["id"]),
            )

    return {
        "idempotent_replay": False,
        "resource": "ConversationMessage",
        "id": str(message_id),
        "conversation_id": str(conversation["id"]),
        "channel_code": code,
        "direction": payload.direction,
        "delivery_status": payload.delivery_status,
        "counts_as_response": is_confirmed_outbound,
    }


@router.post("/messages", status_code=status.HTTP_201_CREATED)
async def ingest_message(
    payload: NormalizedChannelMessage,
    request: Request,
    service: dict[str, Any] = Depends(service_access),
):
    return await ingest_normalized_channel_message(payload, request, service)
