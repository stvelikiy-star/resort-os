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
        SELECT id,"resultResource","resultResourceId"
        FROM automation_inbound_events
        WHERE "propertyId"=$1 AND source=$2 AND "idempotencyKey"=$3
        ''',
        pid, source, key,
    )
    return None, existing


@router.get("/capabilities")
async def automation_capabilities(_service: dict[str, Any] = Depends(service_access)):
    return {
        "allowed": [
            "GET /api/v1/booking/check-availability",
            "POST /api/v1/automation/reservation-requests",
            "POST /api/v1/automation/staff-intake",
        ],
        "forbidden_for_ai": [
            "confirm-payment",
            "create-guaranteed-reservation",
            "check-in",
            "check-out",
            "refund",
            "nfc-charge",
        ],
        "truth_rule": "Tool failure or unknown result must never be described as success.",
        "reservation_rule": "Automation creates ReservationRequest only; guaranteed reservation requires controlled payment/management flow.",
    }


@router.post("/reservation-requests", status_code=status.HTTP_201_CREATED)
async def automation_reservation_request(
    payload: AutomationReservationIntake,
    request: Request,
    service: dict[str, Any] = Depends(service_access),
):
    source = event_source(payload.channel)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn)
            event_id, existing = await claim_automation_event(
                conn, pid, source, payload.idempotency_key, "RESERVATION_REQUEST", payload.model_dump_json()
            )
            if existing:
                return {
                    "idempotent_replay": True,
                    "resource": existing["resultResource"],
                    "id": existing["resultResourceId"],
                    "is_reservation": False,
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

            await conn.execute(
                '''UPDATE automation_inbound_events
                   SET "resultResource"='ReservationRequest',"resultResourceId"=$1,"updatedAt"=now() WHERE id=$2''',
                str(request_id), event_id,
            )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"createdAt")
                   VALUES ($1,$2,'SERVICE',$3,'CREATE','ReservationRequest',$4,$5,'SUCCESS',now())''',
                uuid.uuid4(), pid, service["actor_id"], str(request_id), source,
            )
    return {
        "idempotent_replay": False,
        "id": str(request_id),
        "status": "NEW",
        "is_reservation": False,
        "source": source,
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
