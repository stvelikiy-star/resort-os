import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/guest-services", tags=["guest-services"])
center_access = require_roles("OWNER", "MANAGER", "RECEPTION")

SERVICE_LABELS: dict[str, str] = {
    "HOUSEKEEPING": "Уборка во время проживания",
    "TOWELS": "Полотенца",
    "LINEN": "Бельё",
    "MAINTENANCE": "Ремонт / неисправность",
    "TRANSFER": "Трансфер",
    "MEALS": "Питание",
    "PARKING": "Парковка",
    "SAUNA": "Сауна",
    "BILLIARDS": "Бильярд",
    "EXCURSIONS": "Экскурсии / туры",
    "ADMIN": "Администратор / ресепшен",
}
ACTIVE_TASK_STATUSES = {"OPEN", "IN_PROGRESS"}
ALLOWED_TASK_STATUSES = ACTIVE_TASK_STATUSES | {"DONE", "CANCELLED"}
ALLOWED_RESERVATION_STATUSES = {"GUARANTEED", "CHECKED_IN"}
ALLOWED_PRIORITIES = {"LOW", "NORMAL", "HIGH", "URGENT"}


class GuestServiceCreate(BaseModel):
    reservation_id: uuid.UUID
    service_code: str = Field(min_length=2, max_length=40)
    service_date: date | None = None
    service_time: str | None = Field(default=None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    priority: str = Field(default="NORMAL", pattern=r"^(LOW|NORMAL|HIGH|URGENT)$")
    description: str | None = Field(default=None, max_length=2000)


def service_code(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in SERVICE_LABELS:
        raise HTTPException(
            status_code=422,
            detail={"code": "UNKNOWN_GUEST_SERVICE", "service_code": normalized, "allowed": sorted(SERVICE_LABELS)},
        )
    return normalized


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


def row_to_item(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "reservation_id": str(row["reservationId"]) if row["reservationId"] else None,
        "stay_id": str(row["stayId"]) if row["stayId"] else None,
        "room_id": str(row["resolved_room_id"]) if row["resolved_room_id"] else None,
        "booking_number": row["bookingNumber"],
        "reservation_status": row["reservation_status"],
        "guest_name": row["guest_name"],
        "guest_phone": row["guest_phone"],
        "service_code": row["serviceCode"],
        "service_label": SERVICE_LABELS.get(row["serviceCode"], row["serviceCode"]),
        "service_date": row["serviceDate"],
        "service_time": row["serviceTime"],
        "status": row["status"],
        "priority": row["priority"],
        "title": row["title"],
        "description": row["description"],
        "room_code": row["resolved_room_code"],
        "room_type_name": row["resolved_room_type_name"],
        "assigned_to_id": str(row["assignedToId"]) if row["assignedToId"] else None,
        "assigned_to_name": row["assigned_to_name"],
        "source": row["source"],
        "created_by_type": row["createdByType"],
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
        "completed_at": row["completedAt"],
    }


BASE_SELECT = '''
    SELECT t.id,t."reservationId",t."stayId",t."roomId",t."serviceCode",t."serviceDate",t."serviceTime",
           t.status::text AS status,t.priority::text AS priority,t.title,t.description,t.source,t."createdByType",
           t."assignedToId",t."createdAt",t."updatedAt",t."completedAt",
           res."bookingNumber",res.status::text AS reservation_status,
           COALESCE(g."firstName",stay_guest."firstName") AS guest_name,
           COALESCE(g.phone,stay_guest.phone) AS guest_phone,
           assignee."displayName" AS assigned_to_name,
           COALESCE(direct_room.id,scheduled_room.id) AS resolved_room_id,
           COALESCE(direct_room.code,scheduled_room.code) AS resolved_room_code,
           COALESCE(direct_rt.name,scheduled_room.room_type_name) AS resolved_room_type_name
    FROM operational_tasks t
    LEFT JOIN reservations res ON res.id=t."reservationId" AND res."propertyId"=t."propertyId"
    LEFT JOIN guests g ON g.id=res."primaryGuestId"
    LEFT JOIN stays stay ON stay.id=t."stayId"
    LEFT JOIN guests stay_guest ON stay_guest.id=stay."guestId"
    LEFT JOIN staff_users assignee ON assignee.id=t."assignedToId"
    LEFT JOIN rooms direct_room ON direct_room.id=t."roomId"
    LEFT JOIN room_types direct_rt ON direct_rt.id=direct_room."roomTypeId"
    LEFT JOIN LATERAL (
      SELECT room.id,room.code,rt.name AS room_type_name
      FROM inventory_blocks ib
      JOIN rooms room ON room.id=ib."roomId"
      JOIN room_types rt ON rt.id=room."roomTypeId"
      WHERE ib."reservationId"=res.id
        AND ib.active=true
        AND ib."blockType"='RESERVATION'
        AND (
          t."serviceDate" IS NULL
          OR (t."serviceDate">=ib."startDate" AND t."serviceDate"<ib."endDate")
          OR (t."serviceDate"=res."checkOut" AND ib."endDate"=res."checkOut")
        )
      ORDER BY
        CASE WHEN t."serviceDate" IS NOT NULL AND t."serviceDate">=ib."startDate" AND t."serviceDate"<ib."endDate" THEN 0 ELSE 1 END,
        ib."startDate" DESC
      LIMIT 1
    ) scheduled_room ON true
'''


@router.get("")
async def list_guest_services(
    request: Request,
    task_status: str | None = Query(default="ACTIVE", alias="status"),
    service: str | None = Query(default=None, alias="service_code"),
    reservation_id: uuid.UUID | None = None,
    stay_id: uuid.UUID | None = None,
    room: str | None = Query(default=None, max_length=80),
    guest: str | None = Query(default=None, max_length=160),
    assignee: str | None = Query(default=None, max_length=160),
    priority: str | None = Query(default=None),
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    user: dict[str, Any] = Depends(center_access),
):
    if task_status not in {None, "ALL", "ACTIVE", *ALLOWED_TASK_STATUSES}:
        raise HTTPException(status_code=422, detail="Unknown guest-service status")
    normalized_service = service_code(service) if service else None
    normalized_priority = priority.strip().upper() if priority else None
    if normalized_priority and normalized_priority not in ALLOWED_PRIORITIES:
        raise HTTPException(status_code=422, detail="Unknown guest-service priority")
    if from_date and to_date and to_date < from_date:
        raise HTTPException(status_code=422, detail="to_date must be on or after from_date")

    room_needle = (room or "").strip()
    guest_needle = (guest or "").strip()
    assignee_needle = (assignee or "").strip()

    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        rows = await conn.fetch(
            BASE_SELECT
            + '''
            WHERE t."propertyId"=$1
              AND t.type='GUEST_REQUEST'
              AND t."serviceCode" IS NOT NULL
              AND ($2::text IS NULL OR t."serviceCode"=$2)
              AND ($3::uuid IS NULL OR t."reservationId"=$3)
              AND ($4::uuid IS NULL OR t."stayId"=$4)
              AND ($5::text='' OR COALESCE(direct_room.code,scheduled_room.code,'') ILIKE '%'||$5||'%')
              AND ($6::text='' OR COALESCE(g."firstName",stay_guest."firstName",'') ILIKE '%'||$6||'%'
                   OR COALESCE(g.phone,stay_guest.phone,'') ILIKE '%'||$6||'%'
                   OR COALESCE(res."bookingNumber",'') ILIKE '%'||$6||'%')
              AND ($7::text='' OR COALESCE(assignee."displayName",'') ILIKE '%'||$7||'%')
              AND ($8::text IS NULL OR t.priority::text=$8)
              AND ($9::date IS NULL OR COALESCE(t."serviceDate",t."createdAt"::date)>=$9)
              AND ($10::date IS NULL OR COALESCE(t."serviceDate",t."createdAt"::date)<=$10)
              AND (
                $11::text IS NULL OR $11='ALL'
                OR ($11='ACTIVE' AND t.status IN ('OPEN','IN_PROGRESS'))
                OR t.status::text=$11
              )
            ORDER BY
              CASE t.priority::text WHEN 'URGENT' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'NORMAL' THEN 2 ELSE 3 END,
              COALESCE(t."serviceDate",t."createdAt"::date),t."serviceTime" NULLS LAST,t."createdAt" DESC
            LIMIT $12
            ''',
            pid,
            normalized_service,
            reservation_id,
            stay_id,
            room_needle,
            guest_needle,
            assignee_needle,
            normalized_priority,
            from_date,
            to_date,
            task_status,
            limit,
        )
    return {
        "items": [row_to_item(row) for row in rows],
        "service_codes": SERVICE_LABELS,
        "truth": "Unified Guest Services Center reads the canonical OperationalTask GUEST_REQUEST queue from Resort Core. Filters and status are operational facts; service requests never create accommodation payments automatically.",
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_guest_service(
    payload: GuestServiceCreate,
    request: Request,
    user: dict[str, Any] = Depends(center_access),
):
    code = service_code(payload.service_code)
    description = payload.description.strip() if payload.description and payload.description.strip() else None

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            reservation = await conn.fetchrow(
                '''
                SELECT r.id,r."bookingNumber",r.status::text AS status,r."checkIn",r."checkOut",
                       r."primaryGuestId",g."firstName",g.phone
                FROM reservations r
                LEFT JOIN guests g ON g.id=r."primaryGuestId"
                WHERE r.id=$1 AND r."propertyId"=$2
                FOR UPDATE OF r
                ''',
                payload.reservation_id,
                pid,
            )
            if not reservation:
                raise HTTPException(status_code=404, detail="Reservation not found")
            if reservation["status"] not in ALLOWED_RESERVATION_STATUSES:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "GUEST_SERVICE_RESERVATION_NOT_ACTIVE",
                        "reservation_status": reservation["status"],
                    },
                )
            if payload.service_date and not (reservation["checkIn"] <= payload.service_date <= reservation["checkOut"]):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "GUEST_SERVICE_DATE_OUTSIDE_RESERVATION",
                        "check_in": str(reservation["checkIn"]),
                        "check_out": str(reservation["checkOut"]),
                    },
                )

            stay = None
            if reservation["status"] == "CHECKED_IN":
                stay = await conn.fetchrow(
                    '''
                    SELECT s.id,s."guestId",current_assignment."roomId"
                    FROM stays s
                    LEFT JOIN LATERAL (
                      SELECT ra."roomId" FROM room_assignments ra
                      WHERE ra."stayId"=s.id AND ra."endedAt" IS NULL
                      ORDER BY ra."startedAt" DESC LIMIT 1
                    ) current_assignment ON true
                    WHERE s."propertyId"=$1 AND s."reservationId"=$2 AND s.status='ACTIVE'
                    LIMIT 1
                    ''',
                    pid,
                    payload.reservation_id,
                )
                if not stay:
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "GUEST_SERVICE_ACTIVE_STAY_REQUIRED", "reservation_id": str(payload.reservation_id)},
                    )
                if not stay["roomId"]:
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "GUEST_SERVICE_CURRENT_ROOM_REQUIRED", "stay_id": str(stay["id"])},
                    )

            # Serialize active duplicate detection across all request channels.
            # Guest OS uses the same active Stay + service code lock key.
            dedupe_scope = str(stay["id"]) if stay else str(payload.reservation_id)
            await conn.execute('SELECT pg_advisory_xact_lock(hashtextextended($1,0))', f'{dedupe_scope}:{code}')
            duplicate = await conn.fetchrow(
                '''
                SELECT id,status::text AS status,source
                FROM operational_tasks
                WHERE "propertyId"=$1 AND type='GUEST_REQUEST' AND "reservationId"=$2
                  AND "serviceCode"=$3 AND "serviceDate" IS NOT DISTINCT FROM $4::date
                  AND "serviceTime" IS NOT DISTINCT FROM $5::text
                  AND status IN ('OPEN','IN_PROGRESS')
                ORDER BY "createdAt" DESC LIMIT 1
                FOR UPDATE
                ''',
                pid,
                payload.reservation_id,
                code,
                payload.service_date,
                payload.service_time,
            )
            if duplicate:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "GUEST_SERVICE_DUPLICATE_ACTIVE",
                        "task_id": str(duplicate["id"]),
                        "status": duplicate["status"],
                        "existing_source": duplicate["source"],
                    },
                )

            task_id = uuid.uuid4()
            title = f"{SERVICE_LABELS[code]} · {reservation['bookingNumber']}"
            await conn.execute(
                '''
                INSERT INTO operational_tasks (
                  id,"propertyId","roomId","stayId",type,status,priority,title,description,"reservationId","serviceCode",
                  "serviceDate","serviceTime","createdByType","createdById",source,"createdAt","updatedAt"
                ) VALUES (
                  $1,$2,$3,$4,'GUEST_REQUEST','OPEN',$5::"OperationalTaskPriority",$6,$7,$8,$9,$10,$11,
                  'STAFF',$12,'PMS_GUEST_SERVICE',now(),now()
                )
                ''',
                task_id,
                pid,
                stay["roomId"] if stay else None,
                stay["id"] if stay else None,
                payload.priority,
                title,
                description,
                payload.reservation_id,
                code,
                payload.service_date,
                payload.service_time,
                user["id"],
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                ) VALUES (
                  $1,$2,'STAFF',$3,'CREATE_GUEST_SERVICE','OperationalTask',$4,'PMS_GUEST_SERVICE','SUCCESS',
                  jsonb_build_object(
                    'reservation_id',$5::text,'stay_id',$6::text,'room_id',$7::text,'booking_number',$8::text,
                    'service_code',$9::text,'service_date',$10::text,'service_time',$11::text,
                    'financial_effect','NONE_AUTOMATIC','room_state_effect','NONE_AUTOMATIC'
                  ),now()
                )
                ''',
                uuid.uuid4(),
                pid,
                user["id"],
                str(task_id),
                str(payload.reservation_id),
                str(stay["id"]) if stay else None,
                str(stay["roomId"]) if stay and stay["roomId"] else None,
                reservation["bookingNumber"],
                code,
                payload.service_date.isoformat() if payload.service_date else None,
                payload.service_time,
            )
            if stay and stay["guestId"]:
                await conn.execute(
                    '''
                    INSERT INTO guest_history_events (
                      id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt"
                    ) VALUES (
                      $1,$2,$3,$4,'GUEST_REQUEST_CREATED','PMS_GUEST_SERVICE',
                      jsonb_build_object('task_id',$5::text,'request_code',$6::text,'room_id',$7::text),now(),now()
                    )
                    ''',
                    uuid.uuid4(),
                    pid,
                    stay["guestId"],
                    stay["id"],
                    str(task_id),
                    code,
                    str(stay["roomId"]),
                )

        row = await conn.fetchrow(BASE_SELECT + ' WHERE t.id=$1 AND t."propertyId"=$2', task_id, pid)
    return row_to_item(row)
