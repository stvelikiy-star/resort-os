import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/guest-services", tags=["guest-services"])
manager_access = require_roles("OWNER", "MANAGER")

SERVICE_LABELS: dict[str, str] = {
    "TRANSFER": "Трансфер",
    "MEALS": "Питание",
    "PARKING": "Парковка",
    "SAUNA": "Сауна",
    "BILLIARDS": "Бильярд",
    "EXCURSIONS": "Экскурсии / туры",
}
ACTIVE_TASK_STATUSES = {"OPEN", "IN_PROGRESS"}
ALLOWED_TASK_STATUSES = ACTIVE_TASK_STATUSES | {"DONE", "CANCELLED"}
ALLOWED_RESERVATION_STATUSES = {"GUARANTEED", "CHECKED_IN"}


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
        "reservation_id": str(row["reservationId"]),
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
        "assigned_to_name": row["assigned_to_name"],
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
        "completed_at": row["completedAt"],
    }


BASE_SELECT = '''
    SELECT t.id,t."reservationId",t."serviceCode",t."serviceDate",t."serviceTime",
           t.status::text AS status,t.priority::text AS priority,t.title,t.description,
           t."createdAt",t."updatedAt",t."completedAt",
           res."bookingNumber",res.status::text AS reservation_status,
           g."firstName" AS guest_name,g.phone AS guest_phone,
           assignee."displayName" AS assigned_to_name,
           resolved_room.code AS resolved_room_code,
           resolved_room.room_type_name AS resolved_room_type_name
    FROM operational_tasks t
    JOIN reservations res ON res.id=t."reservationId" AND res."propertyId"=t."propertyId"
    LEFT JOIN guests g ON g.id=res."primaryGuestId"
    LEFT JOIN staff_users assignee ON assignee.id=t."assignedToId"
    LEFT JOIN LATERAL (
      SELECT room.code, rt.name AS room_type_name
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
    ) resolved_room ON true
'''


@router.get("")
async def list_guest_services(
    request: Request,
    task_status: str | None = Query(default="ACTIVE", alias="status"),
    service: str | None = Query(default=None, alias="service_code"),
    reservation_id: uuid.UUID | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    user: dict[str, Any] = Depends(manager_access),
):
    if task_status not in {None, "ALL", "ACTIVE", *ALLOWED_TASK_STATUSES}:
        raise HTTPException(status_code=422, detail="Unknown guest-service status")
    normalized_service = service_code(service) if service else None
    if from_date and to_date and to_date < from_date:
        raise HTTPException(status_code=422, detail="to_date must be on or after from_date")

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
              AND ($4::date IS NULL OR t."serviceDate">=$4)
              AND ($5::date IS NULL OR t."serviceDate"<=$5)
              AND (
                $6::text IS NULL OR $6='ALL'
                OR ($6='ACTIVE' AND t.status IN ('OPEN','IN_PROGRESS'))
                OR t.status::text=$6
              )
            ORDER BY
              CASE t.priority::text WHEN 'URGENT' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'NORMAL' THEN 2 ELSE 3 END,
              t."serviceDate" NULLS LAST,t."serviceTime" NULLS LAST,t."createdAt" DESC
            LIMIT $7
            ''',
            pid,
            normalized_service,
            reservation_id,
            from_date,
            to_date,
            task_status,
            limit,
        )
    return {"items": [row_to_item(row) for row in rows], "service_codes": SERVICE_LABELS}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_guest_service(
    payload: GuestServiceCreate,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    code = service_code(payload.service_code)
    description = payload.description.strip() if payload.description and payload.description.strip() else None

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            reservation = await conn.fetchrow(
                '''
                SELECT r.id,r."bookingNumber",r.status::text AS status,r."checkIn",r."checkOut",
                       g."firstName",g.phone
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

            duplicate = await conn.fetchrow(
                '''
                SELECT id,status::text AS status
                FROM operational_tasks
                WHERE "propertyId"=$1 AND type='GUEST_REQUEST' AND "reservationId"=$2
                  AND "serviceCode"=$3 AND "serviceDate" IS NOT DISTINCT FROM $4::date
                  AND "serviceTime" IS NOT DISTINCT FROM $5::text
                  AND status IN ('OPEN','IN_PROGRESS')
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
                    },
                )

            task_id = uuid.uuid4()
            title = f"{SERVICE_LABELS[code]} · {reservation['bookingNumber']}"
            await conn.execute(
                '''
                INSERT INTO operational_tasks (
                  id,"propertyId",type,status,priority,title,description,"reservationId","serviceCode",
                  "serviceDate","serviceTime","createdByType","createdById",source,"createdAt","updatedAt"
                ) VALUES (
                  $1,$2,'GUEST_REQUEST','OPEN',$3::"OperationalTaskPriority",$4,$5,$6,$7,$8,$9,
                  'STAFF',$10,'PMS_GUEST_SERVICE',now(),now()
                )
                ''',
                task_id,
                pid,
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
                    'reservation_id',$5::text,'booking_number',$6::text,'service_code',$7::text,
                    'service_date',$8::text,'service_time',$9::text,'financial_effect','NONE_AUTOMATIC'
                  ),now()
                )
                ''',
                uuid.uuid4(),
                pid,
                user["id"],
                str(task_id),
                str(payload.reservation_id),
                reservation["bookingNumber"],
                code,
                payload.service_date.isoformat() if payload.service_date else None,
                payload.service_time,
            )

        row = await conn.fetchrow(BASE_SELECT + ' WHERE t.id=$1 AND t."propertyId"=$2', task_id, pid)
    return row_to_item(row)
