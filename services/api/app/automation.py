import json
import os
import uuid
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from .service_auth import require_automation_service

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
router = APIRouter(prefix="/api/v1/automation", tags=["automation"])
service_access = require_automation_service


class AutomationReservationIntake(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=180)
    channel: str = Field(min_length=2, max_length=40)
    guest_name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=5, max_length=40)
    email: str | None = Field(default=None, max_length=200)
    check_in: date
    check_out: date
    adults: int = Field(ge=1, le=20)
    children: int = Field(default=0, ge=0, le=20)
    room_type_code: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=4000)
    external_message_id: str | None = Field(default=None, max_length=180)
    conversation_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_stay_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        if (self.check_out - self.check_in).days > 60:
            raise ValueError("maximum requested stay is 60 nights")
        return self


class AutomationStaffIntake(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=180)
    channel: str = Field(min_length=2, max_length=40)
    intent: Literal["MAINTENANCE", "HOUSEKEEPING", "GUEST_REQUEST"]
    room_code: str | None = Field(default=None, max_length=40)
    transcript: str = Field(min_length=2, max_length=8000)
    summary: str | None = Field(default=None, max_length=180)
    priority: Literal["LOW", "NORMAL", "HIGH", "URGENT"] = "NORMAL"
    external_message_id: str | None = Field(default=None, max_length=180)
    sender_external_id: str | None = Field(default=None, max_length=180)

    @model_validator(mode="after")
    def require_room_for_room_work(self):
        if self.intent in {"MAINTENANCE", "HOUSEKEEPING"} and not self.room_code:
            raise ValueError("room_code is required for maintenance and housekeeping intake")
        return self


async def property_id(conn) -> uuid.UUID:
    value = await conn.fetchval("SELECT id FROM properties WHERE code=$1", PROPERTY_CODE)
    if not value:
        raise HTTPException(status_code=503, detail="Property is not loaded")
    return value


def event_source(channel: str) -> str:
    safe = "".join(ch for ch in channel.upper() if ch.isalnum() or ch in {"_", "-"})
    return f"AI_{safe or 'UNKNOWN'}"[:60]


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


async def claim_automation_event(conn, pid: uuid.UUID, source: str, key: str, event_type: str, payload_json: str):
    event_id = await conn.fetchval(
        '''
        INSERT INTO automation_inbound_events (
          id,"propertyId",source,"idempotencyKey","eventType","payloadJson","createdAt","updatedAt"
        ) VALUES ($1,$2,$3,$4,$5,$6::jsonb,now(),now())
        ON CONFLICT ("propertyId",source,"idempotencyKey") DO NOTHING
        RETURNING id
        ''',
        uuid.uuid4(), pid, source, key, event_type, payload_json,
    )
    if event_id:
        return event_id, None
    existing = await conn.fetchrow(
        '''
        SELECT id,"eventType","payloadJson","resultResource","resultResourceId"
        FROM automation_inbound_events
        WHERE "propertyId"=$1 AND source=$2 AND "idempotencyKey"=$3
        ''',
        pid, source, key,
    )
    if not existing:
        raise HTTPException(status_code=409, detail={"code": "AUTOMATION_IDEMPOTENCY_RECONCILIATION_REQUIRED"})
    if existing["eventType"] != event_type or _json_value(existing["payloadJson"]) != _json_value(payload_json):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "AUTOMATION_IDEMPOTENCY_PAYLOAD_MISMATCH",
                "source": source,
                "idempotency_key": key,
                "existing_event_type": existing["eventType"],
                "requested_event_type": event_type,
            },
        )
    return None, existing


async def _conversation_for_hot_lead(conn, pid: uuid.UUID, conversation_id: uuid.UUID | None):
    if conversation_id is None:
        return None
    conversation = await conn.fetchrow(
        '''
        SELECT c.id,c."reservationRequestId",ch.code AS channel_code,ch.kind::text AS channel_kind
        FROM conversations c
        JOIN communication_channels ch ON ch.id=c."channelId"
        WHERE c.id=$1 AND c."propertyId"=$2
        FOR UPDATE OF c
        ''',
        conversation_id,
        pid,
    )
    if not conversation:
        raise HTTPException(status_code=422, detail={"code": "AUTOMATION_CONVERSATION_NOT_FOUND"})
    return conversation


async def _link_conversation_request(conn, conversation, request_id: str | uuid.UUID) -> bool:
    if not conversation:
        return False
    current = conversation["reservationRequestId"]
    target = uuid.UUID(str(request_id))
    if current and current != target:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "AUTOMATION_CONVERSATION_ALREADY_LINKED",
                "conversation_id": str(conversation["id"]),
                "existing_request_id": str(current),
                "requested_request_id": str(target),
            },
        )
    if not current:
        await conn.execute(
            'UPDATE conversations SET "reservationRequestId"=$1,"updatedAt"=now() WHERE id=$2',
            target,
            conversation["id"],
        )
    return True


@router.get("/capabilities")
async def automation_capabilities(_service: dict[str, Any] = Depends(service_access)):
    return {
        "orchestrator": "n8n",
        "client_channel_architecture": {
            "instagram": "ManyChat -> n8n -> Resort Core unified inbox",
            "whatsapp": "API Green -> n8n -> Resort Core unified inbox",
            "telegram": "Telegram/n8n or direct adapter -> Resort Core unified inbox",
            "website": "Website -> Resort Core /api/v1/booking/requests directly; ReservationRequest is the controlled website artifact",
        },
        "allowed": [
            "GET /api/v1/booking/check-availability",
            "GET /api/v1/automation/read/hotel-facts",
            "GET /api/v1/automation/read/reservation-requests/{request_id}",
            "GET /api/v1/automation/read/reservations/{booking_number}",
            "POST /api/v1/automation/inbox/messages",
            "POST /api/v1/automation/reservation-requests",
            "POST /api/v1/automation/staff-intake",
        ],
        "forbidden_for_ai": [
            "direct PostgreSQL writes",
            "confirm-payment",
            "create-guaranteed-reservation",
            "check-in",
            "check-out",
            "refund",
            "money mutation",
            "nfc-charge",
        ],
        "truth_rule": "Tool failure or unknown result must never be described as success.",
        "reservation_rule": "Automation creates ReservationRequest only; a valid reservation requires the controlled Resort Core payment/management flow.",
        "channel_rule": "Every automated messaging-channel inbound event must be written to the unified inbox before AI/handoff. Provider delivery evidence must be written back as outbound communication evidence; only SENT/DELIVERED counts as a response.",
        "website_rule": "Public website booking stays on the direct Resort Core ReservationRequest contract and must not receive the automation service credential.",
        "idempotency_rule": "Reusing an automation idempotency key with a different payload is a conflict, never a replay.",
        "handoff_rule": "When a hot lead originates from a unified inbox conversation, conversation_id must be supplied so ReservationRequest and Conversation are linked atomically.",
        "database_rule": "n8n must never connect directly to Resort OS PostgreSQL.",
    }


@router.post("/reservation-requests", status_code=status.HTTP_201_CREATED)
async def automation_reservation_request(
    payload: AutomationReservationIntake,
    request: Request,
    service: dict[str, Any] = Depends(service_access),
):
    source = event_source(payload.channel)
    payload_json = payload.model_dump_json()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn)
            conversation = await _conversation_for_hot_lead(conn, pid, payload.conversation_id)
            event_id, existing = await claim_automation_event(
                conn, pid, source, payload.idempotency_key, "RESERVATION_REQUEST", payload_json
            )
            if existing:
                linked = False
                if existing["resultResource"] == "ReservationRequest" and existing["resultResourceId"]:
                    linked = await _link_conversation_request(conn, conversation, existing["resultResourceId"])
                return {
                    "idempotent_replay": True,
                    "resource": existing["resultResource"],
                    "id": existing["resultResourceId"],
                    "is_reservation": False,
                    "conversation_id": str(payload.conversation_id) if payload.conversation_id else None,
                    "conversation_linked": linked,
                }

            room_type_id = None
            if payload.room_type_code:
                room_type_id = await conn.fetchval(
                    'SELECT id FROM room_types WHERE "propertyId"=$1 AND code=$2', pid, payload.room_type_code
                )
                if not room_type_id:
                    raise HTTPException(status_code=422, detail="Unknown room_type_code")

            request_id = uuid.uuid4()
            await conn.execute(
                '''
                INSERT INTO reservation_requests (
                  id,"propertyId",status,source,"guestName",phone,email,"checkIn","checkOut",adults,children,
                  "desiredRoomTypeId",notes,"createdAt","updatedAt"
                ) VALUES ($1,$2,'NEW',$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,now(),now())
                ''',
                request_id, pid, source, payload.guest_name, payload.phone, payload.email,
                payload.check_in, payload.check_out, payload.adults, payload.children, room_type_id, payload.notes,
            )
            linked = await _link_conversation_request(conn, conversation, request_id)

            await conn.execute(
                '''UPDATE automation_inbound_events
                   SET "resultResource"='ReservationRequest',"resultResourceId"=$1,"updatedAt"=now() WHERE id=$2''',
                str(request_id), event_id,
            )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'SERVICE',$3,'CREATE','ReservationRequest',$4,$5,'SUCCESS',
                     jsonb_build_object('conversation_id',$6::text,'conversation_linked',$7::boolean,'is_reservation',false),now())''',
                uuid.uuid4(), pid, service["actor_id"], str(request_id), source,
                str(payload.conversation_id) if payload.conversation_id else None, linked,
            )
    return {
        "idempotent_replay": False,
        "id": str(request_id),
        "status": "NEW",
        "is_reservation": False,
        "source": source,
        "conversation_id": str(payload.conversation_id) if payload.conversation_id else None,
        "conversation_linked": linked,
    }


@router.post("/staff-intake", status_code=status.HTTP_201_CREATED)
async def automation_staff_intake(
    payload: AutomationStaffIntake,
    request: Request,
    service: dict[str, Any] = Depends(service_access),
):
    source = event_source(payload.channel)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn)
            event_id, existing = await claim_automation_event(
                conn, pid, source, payload.idempotency_key, "STAFF_INTAKE", payload.model_dump_json()
            )
            if existing:
                return {
                    "idempotent_replay": True,
                    "resource": existing["resultResource"],
                    "id": existing["resultResourceId"],
                }

            room = None
            if payload.room_code:
                room = await conn.fetchrow(
                    '''SELECT id,code,"operationalState"::text AS state FROM rooms
                       WHERE "propertyId"=$1 AND code=$2 FOR UPDATE''',
                    pid, payload.room_code,
                )
                if not room:
                    raise HTTPException(status_code=422, detail="Unknown room_code")

            default_title = {
                "MAINTENANCE": f"Ремонт · № {payload.room_code}",
                "HOUSEKEEPING": f"Уборка · № {payload.room_code}",
                "GUEST_REQUEST": f"Запрос гостя{f' · № {payload.room_code}' if payload.room_code else ''}",
            }[payload.intent]
            title = payload.summary.strip() if payload.summary and payload.summary.strip() else default_title
            task_id = uuid.uuid4()
            await conn.execute(
                '''
                INSERT INTO operational_tasks (
                  id,"propertyId","roomId",type,status,priority,title,description,
                  "createdByType","createdById",source,"createdAt","updatedAt"
                ) VALUES ($1,$2,$3,$4::"OperationalTaskType",'OPEN',$5::"OperationalTaskPriority",$6,$7,
                  'AUTOMATION',$8,$9,now(),now())
                ''',
                task_id, pid, room["id"] if room else None, payload.intent, payload.priority,
                title, payload.transcript, service["actor_id"], source,
            )

            resulting_room_state = room["state"] if room else None
            if room and payload.intent == "MAINTENANCE":
                await conn.execute(
                    'UPDATE rooms SET "operationalState"=\'TECH_BLOCK\',"updatedAt"=now() WHERE id=$1', room["id"]
                )
                resulting_room_state = "TECH_BLOCK"
            elif room and payload.intent == "HOUSEKEEPING" and room["state"] != "TECH_BLOCK":
                await conn.execute(
                    'UPDATE rooms SET "operationalState"=\'DIRTY\',"updatedAt"=now() WHERE id=$1', room["id"]
                )
                resulting_room_state = "DIRTY"

            await conn.execute(
                '''UPDATE automation_inbound_events
                   SET "resultResource"='OperationalTask',"resultResourceId"=$1,"updatedAt"=now() WHERE id=$2''',
                str(task_id), event_id,
            )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'SERVICE',$3,'CREATE','OperationalTask',$4,$5,'SUCCESS',
                     jsonb_build_object('intent',$6::text,'room_code',$7::text,'room_state',$8::text),now())''',
                uuid.uuid4(), pid, service["actor_id"], str(task_id), source,
                payload.intent, payload.room_code, resulting_room_state,
            )
    return {
        "idempotent_replay": False,
        "id": str(task_id),
        "status": "OPEN",
        "type": payload.intent,
        "room_code": payload.room_code,
        "room_state": resulting_room_state,
        "source": source,
    }
