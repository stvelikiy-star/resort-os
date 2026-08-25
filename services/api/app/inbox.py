import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/inbox", tags=["admin-inbox"])
manager_access = require_roles("OWNER", "MANAGER")
CONVERSATION_STATUSES = {"OPEN", "WAITING_GUEST", "WAITING_STAFF", "RESOLVED", "ARCHIVED"}


class ConversationStatusPatch(BaseModel):
    status: str


class ConversationAssignPatch(BaseModel):
    assignee_id: uuid.UUID | None = None


class ConversationLinkRequestPatch(BaseModel):
    reservation_request_id: uuid.UUID | None = None


class InternalNoteCreate(BaseModel):
    text: str = Field(min_length=1, max_length=12000)


async def property_id(conn, property_code: str) -> uuid.UUID:
    pid = await conn.fetchval("SELECT id FROM properties WHERE code=$1", property_code)
    if not pid:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return pid


def conversation_summary(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "channel_code": row["channel_code"],
        "channel_kind": row["channel_kind"],
        "channel_name": row["channel_name"],
        "status": row["status"],
        "contact_name": row["contactName"],
        "contact_phone": row["contactPhone"],
        "contact_username": row["contactUsername"],
        "assigned_to_id": str(row["assignedToId"]) if row["assignedToId"] else None,
        "assigned_to_name": row["assigned_to_name"],
        "reservation_request_id": str(row["reservationRequestId"]) if row["reservationRequestId"] else None,
        "reservation_request_status": row["request_status"],
        "last_inbound_at": row["lastInboundAt"],
        "last_outbound_at": row["lastOutboundAt"],
        "first_response_at": row["firstResponseAt"],
        "needs_reply": row["needs_reply"],
        "waiting_seconds": int(row["waiting_seconds"]) if row["waiting_seconds"] is not None else None,
        "last_message_text": row["last_message_text"],
        "last_message_direction": row["last_message_direction"],
        "last_message_at": row["last_message_at"],
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
    }


@router.get("/conversations")
async def list_conversations(
    request: Request,
    conversation_status: str | None = Query(default=None, alias="status"),
    needs_reply: bool | None = Query(default=None),
    limit: int = Query(default=150, ge=1, le=300),
    user: dict[str, Any] = Depends(manager_access),
):
    if conversation_status and conversation_status not in CONVERSATION_STATUSES:
        raise HTTPException(status_code=422, detail="Unknown conversation status")

    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        rows = await conn.fetch(
            '''
            SELECT c.id,c.status::text AS status,c."contactName",c."contactPhone",c."contactUsername",
                   c."assignedToId",c."reservationRequestId",c."lastInboundAt",c."lastOutboundAt",
                   c."firstResponseAt",c."createdAt",c."updatedAt",
                   ch.code AS channel_code,ch.kind::text AS channel_kind,ch."displayName" AS channel_name,
                   u."displayName" AS assigned_to_name,rr.status::text AS request_status,
                   (c."lastInboundAt" IS NOT NULL AND (c."lastOutboundAt" IS NULL OR c."lastInboundAt">c."lastOutboundAt")
                     AND c.status NOT IN ('RESOLVED','ARCHIVED')) AS needs_reply,
                   CASE WHEN c."lastInboundAt" IS NOT NULL AND (c."lastOutboundAt" IS NULL OR c."lastInboundAt">c."lastOutboundAt")
                     AND c.status NOT IN ('RESOLVED','ARCHIVED')
                     THEN EXTRACT(EPOCH FROM (now()-c."lastInboundAt")) ELSE NULL END AS waiting_seconds,
                   lm.text AS last_message_text,lm.direction::text AS last_message_direction,lm."createdAt" AS last_message_at
            FROM conversations c
            JOIN communication_channels ch ON ch.id=c."channelId"
            LEFT JOIN staff_users u ON u.id=c."assignedToId"
            LEFT JOIN reservation_requests rr ON rr.id=c."reservationRequestId"
            LEFT JOIN LATERAL (
              SELECT m.text,m.direction,m."createdAt"
              FROM conversation_messages m WHERE m."conversationId"=c.id
              ORDER BY COALESCE(m."sentAt",m."createdAt") DESC,m."createdAt" DESC LIMIT 1
            ) lm ON true
            WHERE c."propertyId"=$1
              AND ($2::text IS NULL OR c.status::text=$2)
              AND ($3::boolean IS NULL OR
                (c."lastInboundAt" IS NOT NULL AND (c."lastOutboundAt" IS NULL OR c."lastInboundAt">c."lastOutboundAt")
                  AND c.status NOT IN ('RESOLVED','ARCHIVED'))=$3)
            ORDER BY
              CASE WHEN c."lastInboundAt" IS NOT NULL AND (c."lastOutboundAt" IS NULL OR c."lastInboundAt">c."lastOutboundAt")
                AND c.status NOT IN ('RESOLVED','ARCHIVED') THEN 0 ELSE 1 END,
              COALESCE(lm."createdAt",c."updatedAt") DESC
            LIMIT $4
            ''',
            pid,
            conversation_status,
            needs_reply,
            limit,
        )
    return {"items": [conversation_summary(row) for row in rows]}


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        row = await conn.fetchrow(
            '''
            SELECT c.id,c.status::text AS status,c."contactName",c."contactPhone",c."contactUsername",
                   c."externalConversationId",c."externalContactId",c."assignedToId",c."reservationRequestId",
                   c."lastInboundAt",c."lastOutboundAt",c."firstResponseAt",c."resolvedAt",c."createdAt",c."updatedAt",
                   ch.code AS channel_code,ch.kind::text AS channel_kind,ch."displayName" AS channel_name,
                   u."displayName" AS assigned_to_name,rr.status::text AS request_status,
                   (c."lastInboundAt" IS NOT NULL AND (c."lastOutboundAt" IS NULL OR c."lastInboundAt">c."lastOutboundAt")
                     AND c.status NOT IN ('RESOLVED','ARCHIVED')) AS needs_reply,
                   CASE WHEN c."lastInboundAt" IS NOT NULL AND (c."lastOutboundAt" IS NULL OR c."lastInboundAt">c."lastOutboundAt")
                     AND c.status NOT IN ('RESOLVED','ARCHIVED')
                     THEN EXTRACT(EPOCH FROM (now()-c."lastInboundAt")) ELSE NULL END AS waiting_seconds,
                   NULL::text AS last_message_text,NULL::text AS last_message_direction,NULL::timestamp AS last_message_at
            FROM conversations c
            JOIN communication_channels ch ON ch.id=c."channelId"
            LEFT JOIN staff_users u ON u.id=c."assignedToId"
            LEFT JOIN reservation_requests rr ON rr.id=c."reservationRequestId"
            WHERE c.id=$1 AND c."propertyId"=$2
            ''',
            conversation_id,
            pid,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = await conn.fetch(
            '''
            SELECT id,direction::text AS direction,"externalMessageId","senderType","senderExternalId",text,
                   "contentType","deliveryStatus"::text AS delivery_status,"sentAt","createdAt"
            FROM conversation_messages
            WHERE "conversationId"=$1
            ORDER BY COALESCE("sentAt","createdAt") ASC,"createdAt" ASC
            LIMIT 500
            ''',
            conversation_id,
        )

    return {
        "conversation": conversation_summary(row) | {
            "external_conversation_id": row["externalConversationId"],
            "external_contact_id": row["externalContactId"],
            "resolved_at": row["resolvedAt"],
        },
        "messages": [
            {
                "id": str(m["id"]),
                "direction": m["direction"],
                "external_message_id": m["externalMessageId"],
                "sender_type": m["senderType"],
                "sender_external_id": m["senderExternalId"],
                "text": m["text"],
                "content_type": m["contentType"],
                "delivery_status": m["delivery_status"],
                "sent_at": m["sentAt"],
                "created_at": m["createdAt"],
            }
            for m in messages
        ],
    }


@router.patch("/conversations/{conversation_id}/status")
async def set_conversation_status(
    conversation_id: uuid.UUID,
    payload: ConversationStatusPatch,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    if payload.status not in CONVERSATION_STATUSES:
        raise HTTPException(status_code=422, detail="Unknown conversation status")
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            result = await conn.execute(
                '''
                UPDATE conversations SET status=$1::"ConversationStatus",
                  "resolvedAt"=CASE WHEN $1='RESOLVED' THEN now() ELSE NULL END,"updatedAt"=now()
                WHERE id=$2 AND "propertyId"=$3
                ''',
                payload.status, conversation_id, pid,
            )
            if result.endswith("0"):
                raise HTTPException(status_code=404, detail="Conversation not found")
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'STATUS_CHANGE','Conversation',$4,'INBOX','SUCCESS',jsonb_build_object('status',$5::text),now())''',
                uuid.uuid4(), pid, user["id"], str(conversation_id), payload.status,
            )
    return {"id": str(conversation_id), "status": payload.status}


@router.patch("/conversations/{conversation_id}/assignee")
async def assign_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationAssignPatch,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            if payload.assignee_id:
                valid = await conn.fetchval(
                    '''SELECT id FROM staff_users WHERE id=$1 AND "propertyId"=$2 AND "isActive"=true AND role IN ('OWNER','MANAGER')''',
                    payload.assignee_id, pid,
                )
                if not valid:
                    raise HTTPException(status_code=422, detail="Assignee must be an active owner or manager")
            result = await conn.execute(
                'UPDATE conversations SET "assignedToId"=$1,"updatedAt"=now() WHERE id=$2 AND "propertyId"=$3',
                payload.assignee_id, conversation_id, pid,
            )
            if result.endswith("0"):
                raise HTTPException(status_code=404, detail="Conversation not found")
    return {"id": str(conversation_id), "assigned_to_id": str(payload.assignee_id) if payload.assignee_id else None}


@router.post("/conversations/{conversation_id}/claim")
async def claim_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        result = await conn.execute(
            '''UPDATE conversations SET "assignedToId"=$1,"updatedAt"=now()
               WHERE id=$2 AND "propertyId"=$3 AND ("assignedToId" IS NULL OR "assignedToId"=$1)''',
            uuid.UUID(user["id"]), conversation_id, pid,
        )
        if result.endswith("0"):
            raise HTTPException(status_code=409, detail="Conversation is assigned to another manager or not found")
    return {"id": str(conversation_id), "assigned_to_id": user["id"], "assigned_to_name": user["display_name"]}


@router.patch("/conversations/{conversation_id}/reservation-request")
async def link_reservation_request(
    conversation_id: uuid.UUID,
    payload: ConversationLinkRequestPatch,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            if payload.reservation_request_id:
                exists = await conn.fetchval(
                    'SELECT id FROM reservation_requests WHERE id=$1 AND "propertyId"=$2',
                    payload.reservation_request_id, pid,
                )
                if not exists:
                    raise HTTPException(status_code=422, detail="Reservation request not found")
            result = await conn.execute(
                'UPDATE conversations SET "reservationRequestId"=$1,"updatedAt"=now() WHERE id=$2 AND "propertyId"=$3',
                payload.reservation_request_id, conversation_id, pid,
            )
            if result.endswith("0"):
                raise HTTPException(status_code=404, detail="Conversation not found")
    return {"id": str(conversation_id), "reservation_request_id": str(payload.reservation_request_id) if payload.reservation_request_id else None}


@router.post("/conversations/{conversation_id}/notes", status_code=201)
async def create_internal_note(
    conversation_id: uuid.UUID,
    payload: InternalNoteCreate,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            exists = await conn.fetchval('SELECT id FROM conversations WHERE id=$1 AND "propertyId"=$2', conversation_id, pid)
            if not exists:
                raise HTTPException(status_code=404, detail="Conversation not found")
            message_id = uuid.uuid4()
            await conn.execute(
                '''
                INSERT INTO conversation_messages (
                  id,"conversationId",direction,"senderType","senderExternalId",text,"contentType","deliveryStatus","createdAt"
                ) VALUES ($1,$2,'INTERNAL','STAFF',$3,$4,'TEXT','UNKNOWN',now())
                ''',
                message_id, conversation_id, user["id"], payload.text,
            )
            await conn.execute('UPDATE conversations SET "updatedAt"=now() WHERE id=$1', conversation_id)
    return {"id": str(message_id), "conversation_id": str(conversation_id), "direction": "INTERNAL"}
