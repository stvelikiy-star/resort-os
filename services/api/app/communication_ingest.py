import json
import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from .service_auth import require_automation_service

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


@router.post("/messages", status_code=status.HTTP_201_CREATED)
async def ingest_message(
    payload: NormalizedChannelMessage,
    request: Request,
    service: dict[str, Any] = Depends(service_access),
):
    code = normalized_channel_code(payload.channel_code)
    source = f"INBOX_{code}"[:60]
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await conn.fetchval("SELECT id FROM properties WHERE code=$1", "THREE_CROWNS")
            if not pid:
                raise HTTPException(status_code=503, detail="Property is not loaded")

            existing_event = await conn.fetchrow(
                '''
                SELECT "resultResource","resultResourceId"
                FROM automation_inbound_events
                WHERE "propertyId"=$1 AND source=$2 AND "idempotencyKey"=$3
                ''',
                pid,
                source,
                payload.idempotency_key,
            )
            if existing_event:
                return {
                    "idempotent_replay": True,
                    "resource": existing_event["resultResource"],
                    "id": existing_event["resultResourceId"],
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
                payload.model_dump_json(),
            )

            channel = await conn.fetchrow(
                '''
                INSERT INTO communication_channels (
                  id,"propertyId",code,kind,"displayName","externalAccountId","isActive",metadata,"createdAt","updatedAt"
                ) VALUES ($1,$2,$3,$4::"CommunicationChannelKind",$5,$6,true,NULL,now(),now())
                ON CONFLICT ("propertyId",code) DO UPDATE SET
                  kind=EXCLUDED.kind,
                  "displayName"=EXCLUDED."displayName",
                  "externalAccountId"=COALESCE(EXCLUDED."externalAccountId",communication_channels."externalAccountId"),
                  "isActive"=true,
                  "updatedAt"=now()
                RETURNING id
                ''',
                uuid.uuid4(),
                pid,
                code,
                payload.channel_kind,
                payload.channel_display_name,
                payload.external_account_id,
            )

            conversation = await conn.fetchrow(
                '''
                INSERT INTO conversations (
                  id,"propertyId","channelId","externalConversationId","externalContactId",
                  "contactName","contactPhone","contactUsername",status,"lastInboundAt","lastOutboundAt",
                  "firstResponseAt","createdAt","updatedAt"
                ) VALUES (
                  $1,$2,$3,$4,$5,$6,$7,$8,'OPEN',
                  CASE WHEN $9='INBOUND' THEN COALESCE($10,now()) ELSE NULL END,
                  CASE WHEN $9='OUTBOUND' THEN COALESCE($10,now()) ELSE NULL END,
                  NULL,now(),now()
                )
                ON CONFLICT ("channelId","externalConversationId") DO UPDATE SET
                  "externalContactId"=COALESCE(EXCLUDED."externalContactId",conversations."externalContactId"),
                  "contactName"=COALESCE(EXCLUDED."contactName",conversations."contactName"),
                  "contactPhone"=COALESCE(EXCLUDED."contactPhone",conversations."contactPhone"),
                  "contactUsername"=COALESCE(EXCLUDED."contactUsername",conversations."contactUsername"),
                  status=CASE WHEN $9='INBOUND' AND conversations.status IN ('RESOLVED','ARCHIVED') THEN 'OPEN'::"ConversationStatus" ELSE conversations.status END,
                  "lastInboundAt"=CASE WHEN $9='INBOUND' THEN GREATEST(COALESCE(conversations."lastInboundAt",'-infinity'::timestamptz),COALESCE($10,now())) ELSE conversations."lastInboundAt" END,
                  "lastOutboundAt"=CASE WHEN $9='OUTBOUND' THEN GREATEST(COALESCE(conversations."lastOutboundAt",'-infinity'::timestamptz),COALESCE($10,now())) ELSE conversations."lastOutboundAt" END,
                  "firstResponseAt"=CASE WHEN $9='OUTBOUND' AND conversations."firstResponseAt" IS NULL AND conversations."lastInboundAt" IS NOT NULL THEN COALESCE($10,now()) ELSE conversations."firstResponseAt" END,
                  "updatedAt"=now()
                RETURNING id
                ''',
                uuid.uuid4(), pid, channel["id"], payload.external_conversation_id,
                payload.external_contact_id, payload.contact_name, payload.contact_phone,
                payload.contact_username, payload.direction, payload.sent_at,
            )

            if payload.external_message_id:
                duplicate = await conn.fetchval(
                    'SELECT id FROM conversation_messages WHERE "conversationId"=$1 AND "externalMessageId"=$2',
                    conversation["id"], payload.external_message_id,
                )
                if duplicate:
                    await conn.execute(
                        '''UPDATE automation_inbound_events SET "resultResource"='ConversationMessage',"resultResourceId"=$1,"updatedAt"=now() WHERE id=$2''',
                        str(duplicate), event_id,
                    )
                    return {"idempotent_replay": True, "resource": "ConversationMessage", "id": str(duplicate)}

            message_id = uuid.uuid4()
            await conn.execute(
                '''
                INSERT INTO conversation_messages (
                  id,"conversationId",direction,"externalMessageId","senderType","senderExternalId",text,
                  "contentType","deliveryStatus","rawPayload","sentAt","createdAt"
                ) VALUES ($1,$2,$3::"MessageDirection",$4,$5,$6,$7,$8,$9::"MessageDeliveryStatus",$10::jsonb,$11,now())
                ''',
                message_id, conversation["id"], payload.direction, payload.external_message_id,
                payload.sender_type, payload.sender_external_id, payload.text, payload.content_type,
                payload.delivery_status, json.dumps(payload.raw_payload) if payload.raw_payload is not None else None,
                payload.sent_at,
            )

            await conn.execute(
                '''UPDATE automation_inbound_events SET "resultResource"='ConversationMessage',"resultResourceId"=$1,"updatedAt"=now() WHERE id=$2''',
                str(message_id), event_id,
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                VALUES ($1,$2,'SERVICE',$3,'INGEST_MESSAGE','ConversationMessage',$4,$5,'SUCCESS',
                  jsonb_build_object('channel_code',$6::text,'direction',$7::text,'conversation_id',$8::text),now())
                ''',
                uuid.uuid4(), pid, service["actor_id"], str(message_id), source, code,
                payload.direction, str(conversation["id"]),
            )

    return {
        "idempotent_replay": False,
        "resource": "ConversationMessage",
        "id": str(message_id),
        "conversation_id": str(conversation["id"]),
        "channel_code": code,
        "direction": payload.direction,
    }
