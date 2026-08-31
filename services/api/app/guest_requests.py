import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Cookie, HTTPException, Request, status
from pydantic import BaseModel, Field

from .guest_os import GUEST_COOKIE, current_stay_for_room, resolve_room_qr, valid_guest_session

router = APIRouter(prefix="/api/v1/guest-os", tags=["guest-requests"])

REQUEST_LABELS: dict[str, str] = {
    "HOUSEKEEPING": "Уборка номера",
    "TOWELS": "Полотенца",
    "LINEN": "Замена белья",
    "MAINTENANCE": "Сообщить о поломке",
    "TRANSFER": "Трансфер",
    "MEALS": "Питание",
    "SAUNA": "Сауна",
    "BILLIARDS": "Бильярд",
    "EXCURSIONS": "Экскурсии / туры",
    "ADMIN": "Администратор",
}


class GuestRequestCreate(BaseModel):
    request_code: str = Field(min_length=2, max_length=40)
    description: str | None = Field(default=None, max_length=1200)
    service_date: date | None = None
    service_time: str | None = Field(default=None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")


def normalize_request_code(value: str) -> str:
    code = value.strip().upper()
    if code not in REQUEST_LABELS:
        raise HTTPException(status_code=422, detail={"code": "UNKNOWN_GUEST_REQUEST", "request_code": code, "allowed": sorted(REQUEST_LABELS)})
    return code


async def authorized_context(conn, token: str, raw_session: str | None):
    qr = await resolve_room_qr(conn, token)
    if not qr:
        raise HTTPException(status_code=404, detail={"code": "ROOM_QR_NOT_FOUND"})
    stay = await current_stay_for_room(conn, qr["roomId"])
    if not stay:
        raise HTTPException(status_code=401, detail={"code": "GUEST_SESSION_REQUIRED"})
    session = await valid_guest_session(conn, raw_session)
    if not session or session["stayId"] != stay["stayId"] or session["guestId"] != stay["guestId"]:
        raise HTTPException(status_code=401, detail={"code": "GUEST_SESSION_REQUIRED"})
    return qr, stay, session


def row_to_guest_item(row) -> dict[str, Any]:
    source = row["source"] or ""
    code = source.removeprefix("GUEST_OS_") if source.startswith("GUEST_OS_") else (row["serviceCode"] or "ADMIN")
    return {
        "id": str(row["id"]),
        "request_code": code,
        "type": row["type"],
        "status": row["status"],
        "priority": row["priority"],
        "title": row["title"],
        "description": row["description"],
        "service_date": row["serviceDate"],
        "service_time": row["serviceTime"],
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
        "completed_at": row["completedAt"],
    }


TASK_SELECT = '''
SELECT id,type::text AS type,status::text AS status,priority::text AS priority,
       title,description,"serviceCode","serviceDate","serviceTime",source,
       "createdAt","updatedAt","completedAt"
FROM operational_tasks
'''


@router.get("/rooms/{token}/requests")
async def list_guest_requests(token: str, request: Request, tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE)):
    async with request.app.state.db.acquire() as conn:
        _, stay, _ = await authorized_context(conn, token, tc_guest_session)
        rows = await conn.fetch(
            TASK_SELECT + '''
            WHERE "stayId"=$1 AND "createdByType"='GUEST' AND source LIKE 'GUEST_OS_%'
            ORDER BY "createdAt" DESC LIMIT 100
            ''',
            stay["stayId"],
        )
    return {"items": [row_to_guest_item(row) for row in rows]}


@router.post("/rooms/{token}/requests", status_code=status.HTTP_201_CREATED)
async def create_guest_request(token: str, payload: GuestRequestCreate, request: Request, tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE)):
    code = normalize_request_code(payload.request_code)
    source = f"GUEST_OS_{code}"
    description = payload.description.strip() if payload.description and payload.description.strip() else None

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            qr, stay, session = await authorized_context(conn, token, tc_guest_session)
            if payload.service_date and not (stay["checkIn"] <= payload.service_date <= stay["checkOut"]):
                raise HTTPException(status_code=422, detail={"code": "SERVICE_DATE_OUTSIDE_STAY", "check_in": str(stay["checkIn"]), "check_out": str(stay["checkOut"])})

            await conn.execute('SELECT pg_advisory_xact_lock(hashtextextended($1,0))', f'{stay["stayId"]}:{source}')
            duplicate = await conn.fetchrow(
                '''
                SELECT id,status::text AS status FROM operational_tasks
                WHERE "stayId"=$1 AND source=$2
                  AND "serviceDate" IS NOT DISTINCT FROM $3::date
                  AND "serviceTime" IS NOT DISTINCT FROM $4::text
                  AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
                ORDER BY "createdAt" DESC LIMIT 1
                ''',
                stay["stayId"], source, payload.service_date, payload.service_time,
            )
            if duplicate:
                raise HTTPException(status_code=409, detail={"code": "GUEST_REQUEST_DUPLICATE_ACTIVE", "task_id": str(duplicate["id"]), "status": duplicate["status"]})

            task_id = uuid.uuid4()
            title = f"{REQUEST_LABELS[code]} · №{qr['room_code']}"
            await conn.execute(
                '''
                INSERT INTO operational_tasks (
                  id,"propertyId","roomId","reservationId","stayId",type,status,priority,title,description,
                  "serviceCode","serviceDate","serviceTime","createdByType","createdById",source,"createdAt","updatedAt"
                ) VALUES ($1,$2,$3,$4,$5,'GUEST_REQUEST','OPEN','NORMAL',$6,$7,$8,$9,$10,'GUEST',$11,$12,now(),now())
                ''',
                task_id, qr["propertyId"], qr["roomId"], stay["reservation_id"], stay["stayId"],
                title, description, code, payload.service_date, payload.service_time, str(stay["guestId"]), source,
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'GUEST',$3,'CREATE_GUEST_REQUEST','OperationalTask',$4,'GUEST_OS','SUCCESS',
                  jsonb_build_object('request_code',$5::text,'task_type','GUEST_REQUEST','stay_id',$6::text,'room_id',$7::text,
                    'guest_session_id',$8::text,'financial_effect','NONE_AUTOMATIC','room_state_effect','NONE_AUTOMATIC'),now())
                ''',
                uuid.uuid4(), qr["propertyId"], str(stay["guestId"]), str(task_id), code,
                str(stay["stayId"]), str(qr["roomId"]), str(session["id"]),
            )
            await conn.execute(
                '''
                INSERT INTO guest_history_events (
                  id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt"
                ) VALUES ($1,$2,$3,$4,'GUEST_REQUEST_CREATED','GUEST_OS',
                  jsonb_build_object('task_id',$5::text,'request_code',$6::text,'room_id',$7::text),now(),now())
                ''',
                uuid.uuid4(), qr["propertyId"], stay["guestId"], stay["stayId"], str(task_id), code, str(qr["roomId"]),
            )
            row = await conn.fetchrow(TASK_SELECT + ' WHERE id=$1', task_id)
    return row_to_guest_item(row)


@router.post("/rooms/{token}/requests/{task_id}/cancel")
async def cancel_guest_request(token: str, task_id: uuid.UUID, request: Request, tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            qr, stay, _ = await authorized_context(conn, token, tc_guest_session)
            task = await conn.fetchrow(
                '''SELECT id,status::text AS status FROM operational_tasks
                   WHERE id=$1 AND "stayId"=$2 AND "createdByType"='GUEST' AND source LIKE 'GUEST_OS_%' FOR UPDATE''',
                task_id, stay["stayId"],
            )
            if not task:
                raise HTTPException(status_code=404, detail={"code": "GUEST_REQUEST_NOT_FOUND"})
            if task["status"] != "OPEN":
                raise HTTPException(status_code=409, detail={"code": "GUEST_REQUEST_CANNOT_CANCEL", "status": task["status"]})
            await conn.execute('UPDATE operational_tasks SET status=\'CANCELLED\',"updatedAt"=now(),"completedAt"=now() WHERE id=$1', task_id)
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'GUEST',$3,'CANCEL_GUEST_REQUEST','OperationalTask',$4,'GUEST_OS','SUCCESS',
                     jsonb_build_object('from_status','OPEN','status','CANCELLED'),now())''',
                uuid.uuid4(), qr["propertyId"], str(stay["guestId"]), str(task_id),
            )
            await conn.execute(
                '''INSERT INTO guest_history_events (id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt")
                   VALUES ($1,$2,$3,$4,'GUEST_REQUEST_CANCELLED','GUEST_OS',jsonb_build_object('task_id',$5::text),now(),now())''',
                uuid.uuid4(), qr["propertyId"], stay["guestId"], stay["stayId"], str(task_id),
            )
            row = await conn.fetchrow(TASK_SELECT + ' WHERE id=$1', task_id)
    return row_to_guest_item(row)
