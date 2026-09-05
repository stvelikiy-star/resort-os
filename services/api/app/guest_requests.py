import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Cookie, HTTPException, Request, status
from pydantic import BaseModel, Field

from .folio_service_charges import ensure_guest_service_charge, void_guest_service_charge
from .guest_os import GUEST_COOKIE, current_stay_for_room, resolve_room_qr, valid_guest_session
from .guest_service_settings import load_settings

router = APIRouter(prefix="/api/v1/guest-os", tags=["guest-requests"])

REQUEST_LABELS: dict[str, str] = {
    "HOUSEKEEPING": "Уборка номера",
    "TOWELS": "Полотенца",
    "LINEN": "Замена белья",
    "MAINTENANCE": "Сообщить о поломке",
    "TRANSFER": "Трансфер",
    "MEALS": "Питание",
    "PARKING": "Парковка",
    "SAUNA": "Сауна",
    "BILLIARDS": "Бильярд",
    "EXCURSIONS": "Экскурсии / туры",
    "ADMIN": "Администратор",
}

PAID_ON_DEMAND = {
    "HOUSEKEEPING": "on_demand_housekeeping_price_kgs",
    "LINEN": "on_demand_linen_price_kgs",
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
        "charge_kgs": row["chargeKgs"],
        "charge_status": row["chargeStatus"],
        "charge_source": row["chargeSource"],
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
        "completed_at": row["completedAt"],
    }


TASK_SELECT = '''
SELECT id,type::text AS type,status::text AS status,priority::text AS priority,
       title,description,"serviceCode","serviceDate","serviceTime",source,
       "chargeKgs","chargeStatus","chargeSource","createdAt","updatedAt","completedAt"
FROM operational_tasks
'''


@router.get("/rooms/{token}/service-policy")
async def guest_service_policy(token: str, request: Request, tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE)):
    async with request.app.state.db.acquire() as conn:
        qr, _, _ = await authorized_context(conn, token, tc_guest_session)
        settings = await load_settings(conn, qr["propertyId"])
    return {
        "scheduled_housekeeping_interval_days": settings["scheduled_housekeeping_interval_days"],
        "scheduled_linen_change_included": settings["scheduled_linen_change_included"],
        "on_demand_housekeeping_price_kgs": settings["on_demand_housekeeping_price_kgs"],
        "on_demand_linen_price_kgs": settings["on_demand_linen_price_kgs"],
        "on_demand_housekeeping_paid": True,
        "on_demand_linen_paid": True,
        "truth": "Scheduled housekeeping is included by policy; guest-requested extra housekeeping and linen change are paid services and are never treated as free when price is unconfigured.",
    }


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

            settings = await load_settings(conn, qr["propertyId"])
            charge_kgs: int | None = None
            charge_status = "NONE"
            charge_source: str | None = None
            if code in PAID_ON_DEMAND:
                price_key = PAID_ON_DEMAND[code]
                configured_price = settings[price_key]
                if configured_price is None:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "GUEST_SERVICE_PRICE_NOT_CONFIGURED",
                            "request_code": code,
                            "message": "Management must configure this paid service price before Guest OS can accept the request.",
                        },
                    )
                charge_kgs = int(configured_price)
                charge_status = "PENDING"
                charge_source = "GUEST_OS_OWNER_CONFIGURED_PRICE"

            await conn.execute('SELECT pg_advisory_xact_lock(hashtextextended($1,0))', f'{stay["stayId"]}:{code}')
            duplicate = await conn.fetchrow(
                '''
                SELECT id,status::text AS status,source FROM operational_tasks
                WHERE "stayId"=$1 AND type='GUEST_REQUEST' AND "serviceCode"=$2
                  AND "serviceDate" IS NOT DISTINCT FROM $3::date
                  AND "serviceTime" IS NOT DISTINCT FROM $4::text
                  AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
                ORDER BY "createdAt" DESC LIMIT 1
                ''',
                stay["stayId"], code, payload.service_date, payload.service_time,
            )
            if duplicate:
                raise HTTPException(status_code=409, detail={
                    "code": "GUEST_REQUEST_DUPLICATE_ACTIVE",
                    "task_id": str(duplicate["id"]),
                    "status": duplicate["status"],
                    "existing_source": duplicate["source"],
                })

            task_id = uuid.uuid4()
            title = f"{REQUEST_LABELS[code]} · №{qr['room_code']}"
            await conn.execute(
                '''
                INSERT INTO operational_tasks (
                  id,"propertyId","roomId","reservationId","stayId",type,status,priority,title,description,
                  "serviceCode","serviceDate","serviceTime","createdByType","createdById",source,
                  "chargeKgs","chargeStatus","chargeSource","createdAt","updatedAt"
                ) VALUES ($1,$2,$3,$4,$5,'GUEST_REQUEST','OPEN','NORMAL',$6,$7,$8,$9,$10,'GUEST',$11,$12,
                  $13,$14,$15,now(),now())
                ''',
                task_id, qr["propertyId"], qr["roomId"], stay["reservation_id"], stay["stayId"],
                title, description, code, payload.service_date, payload.service_time, str(stay["guestId"]), source,
                charge_kgs, charge_status, charge_source,
            )
            folio_charge_id = None
            if charge_kgs is not None:
                folio_charge_id = await ensure_guest_service_charge(
                    conn, task_id, actor_type="GUEST", actor_id=str(stay["guestId"]),
                )
                if folio_charge_id:
                    charge_status = "POSTED"
                    charge_source = "FOLIO"

            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'GUEST',$3,'CREATE_GUEST_REQUEST','OperationalTask',$4,'GUEST_OS','SUCCESS',
                  jsonb_build_object('request_code',$5::text,'task_type','GUEST_REQUEST','stay_id',$6::text,'room_id',$7::text,
                    'guest_session_id',$8::text,'charge_kgs',$9::int,'charge_status',$10::text,'folio_charge_id',$11::text,
                    'financial_effect',CASE WHEN $9::int IS NULL THEN 'NONE_AUTOMATIC' ELSE 'OPEN_FOLIO_CHARGE_NOT_PAYMENT' END,
                    'room_state_effect','NONE_AUTOMATIC'),now())
                ''',
                uuid.uuid4(), qr["propertyId"], str(stay["guestId"]), str(task_id), code,
                str(stay["stayId"]), str(qr["roomId"]), str(session["id"]), charge_kgs, charge_status,
                str(folio_charge_id) if folio_charge_id else None,
            )
            await conn.execute(
                '''
                INSERT INTO guest_history_events (
                  id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt"
                ) VALUES ($1,$2,$3,$4,'GUEST_REQUEST_CREATED','GUEST_OS',
                  jsonb_build_object('task_id',$5::text,'request_code',$6::text,'room_id',$7::text,
                    'charge_kgs',$8::int,'charge_status',$9::text,'folio_charge_id',$10::text),now(),now())
                ''',
                uuid.uuid4(), qr["propertyId"], stay["guestId"], stay["stayId"], str(task_id), code, str(qr["roomId"]),
                charge_kgs, charge_status, str(folio_charge_id) if folio_charge_id else None,
            )
            row = await conn.fetchrow(TASK_SELECT + ' WHERE id=$1', task_id)
    return row_to_guest_item(row)


@router.post("/rooms/{token}/requests/{task_id}/cancel")
async def cancel_guest_request(token: str, task_id: uuid.UUID, request: Request, tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            qr, stay, _ = await authorized_context(conn, token, tc_guest_session)
            task = await conn.fetchrow(
                '''SELECT id,status::text AS status,"chargeStatus" FROM operational_tasks
                   WHERE id=$1 AND "stayId"=$2 AND "createdByType"='GUEST' AND source LIKE 'GUEST_OS_%' FOR UPDATE''',
                task_id, stay["stayId"],
            )
            if not task:
                raise HTTPException(status_code=404, detail={"code": "GUEST_REQUEST_NOT_FOUND"})
            if task["status"] != "OPEN":
                raise HTTPException(status_code=409, detail={"code": "GUEST_REQUEST_CANNOT_CANCEL", "status": task["status"]})
            if task["chargeStatus"] in {"PENDING", "POSTED"}:
                await void_guest_service_charge(
                    conn, task_id, actor_type="GUEST", actor_id=str(stay["guestId"]), reason="Guest cancelled request before work started",
                )
                next_charge_status = "CANCELLED"
            else:
                next_charge_status = task["chargeStatus"]
            await conn.execute(
                '''UPDATE operational_tasks SET status='CANCELLED',"chargeStatus"=$2,
                   "updatedAt"=now(),"completedAt"=now() WHERE id=$1''',
                task_id, next_charge_status,
            )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'GUEST',$3,'CANCEL_GUEST_REQUEST','OperationalTask',$4,'GUEST_OS','SUCCESS',
                     jsonb_build_object('from_status','OPEN','status','CANCELLED','charge_status',$5::text),now())''',
                uuid.uuid4(), qr["propertyId"], str(stay["guestId"]), str(task_id), next_charge_status,
            )
            await conn.execute(
                '''INSERT INTO guest_history_events (id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt")
                   VALUES ($1,$2,$3,$4,'GUEST_REQUEST_CANCELLED','GUEST_OS',jsonb_build_object('task_id',$5::text),now(),now())''',
                uuid.uuid4(), qr["propertyId"], stay["guestId"], stay["stayId"], str(task_id),
            )
            row = await conn.fetchrow(TASK_SELECT + ' WHERE id=$1', task_id)
    return row_to_guest_item(row)
