import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/ops/kitchen", tags=["kitchen-arrivals"])
kitchen_access = require_roles("OWNER", "MANAGER", "DINING_STAFF")

ARRIVAL_CODE = "NEW_GUEST_CHECKED_IN"
ARRIVAL_SOURCE = "CHECK_IN_ARRIVAL_SYNC"


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


async def create_arrival_notification(
    conn,
    *,
    property_id: uuid.UUID,
    reservation_id: uuid.UUID,
    stay_id: uuid.UUID,
    room_id: uuid.UUID,
    room_code: str,
    booking_number: str,
    check_in,
    check_out,
    adults: int,
    children: int,
    actor_id: str | None,
) -> uuid.UUID | None:
    """Create exactly one kitchen arrival card for a successful check-in."""
    await conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
        f"kitchen-arrival:{reservation_id}",
    )
    exists = await conn.fetchval(
        '''SELECT id FROM operational_tasks
           WHERE "propertyId"=$1 AND "reservationId"=$2
             AND "serviceCode"=$3 AND source=$4
           LIMIT 1''',
        property_id,
        reservation_id,
        ARRIVAL_CODE,
        ARRIVAL_SOURCE,
    )
    if exists:
        return None

    task_id = uuid.uuid4()
    description = (
        f"Номер {room_code} · взрослых: {adults} · детей: {children} · "
        f"проживание {check_in} — {check_out}. "
        "Питание по брони не предполагается автоматически: при необходимости уточнить на ресепшене."
    )
    await conn.execute(
        '''INSERT INTO operational_tasks (
             id,"propertyId","roomId","reservationId","stayId",type,status,priority,title,
             description,"createdByType","createdById",source,"serviceCode","createdAt","updatedAt"
           ) VALUES ($1,$2,$3,$4,$5,'GUEST_REQUEST','OPEN','HIGH',$6,$7,'SYSTEM',$8,$9,$10,now(),now())''',
        task_id,
        property_id,
        room_id,
        reservation_id,
        stay_id,
        f"Новый заезд · номер {room_code}",
        description,
        actor_id,
        ARRIVAL_SOURCE,
        ARRIVAL_CODE,
    )
    await conn.execute(
        '''INSERT INTO audit_logs (
             id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,
             "afterJson","createdAt"
           ) VALUES ($1,$2,'SYSTEM',$3,'KITCHEN_ARRIVAL_NOTIFICATION','OperationalTask',$4,$5,'SUCCESS',
             jsonb_build_object(
               'reservation_id',$6::text,'stay_id',$7::text,'room_code',$8::text,'booking_number',$9::text,
               'adults',$10::int,'children',$11::int,
               'financial_effect','NONE','sensitive_guest_data','EXCLUDED'
             ),now())''',
        uuid.uuid4(),
        property_id,
        actor_id,
        str(task_id),
        ARRIVAL_SOURCE,
        str(reservation_id),
        str(stay_id),
        room_code,
        booking_number,
        adults,
        children,
    )
    return task_id


@router.post("/sync-arrivals")
async def sync_recent_arrivals(
    request: Request,
    user: dict[str, Any] = Depends(kitchen_access),
):
    """Repair missed arrival cards for successful check-ins from the last 24 hours."""
    created: list[str] = []
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            arrivals = await conn.fetch(
                '''SELECT res.id AS reservation_id,res."bookingNumber",res."checkIn",res."checkOut",
                          res.adults,res.children,stay.id AS stay_id,room.id AS room_id,room.code AS room_code
                   FROM reservations res
                   JOIN stays stay ON stay."reservationId"=res.id
                     AND stay."propertyId"=res."propertyId" AND stay.status='ACTIVE'
                   JOIN room_assignments ra ON ra."stayId"=stay.id AND ra."endedAt" IS NULL
                   JOIN rooms room ON room.id=ra."roomId"
                   WHERE res."propertyId"=$1 AND res.status='CHECKED_IN'
                     AND stay."actualCheckInAt" >= now() - interval '24 hours'
                   ORDER BY stay."actualCheckInAt" ASC''',
                pid,
            )
            for row in arrivals:
                task_id = await create_arrival_notification(
                    conn,
                    property_id=pid,
                    reservation_id=row["reservation_id"],
                    stay_id=row["stay_id"],
                    room_id=row["room_id"],
                    room_code=row["room_code"],
                    booking_number=row["bookingNumber"],
                    check_in=row["checkIn"],
                    check_out=row["checkOut"],
                    adults=row["adults"],
                    children=row["children"],
                    actor_id=user["id"],
                )
                if task_id:
                    created.append(str(task_id))
    return {
        "created": len(created),
        "task_ids": created,
        "request_code": ARRIVAL_CODE,
        "truth": "Successful check-ins are surfaced to Dining Staff without payment or sensitive guest data.",
    }


@router.get("/arrivals")
async def list_arrivals(request: Request, user: dict[str, Any] = Depends(kitchen_access)):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        rows = await conn.fetch(
            '''SELECT t.id,t.status::text AS status,t.title,t.description,t."createdAt",
                      r.code AS room_code,res."bookingNumber"
               FROM operational_tasks t
               LEFT JOIN rooms r ON r.id=t."roomId"
               LEFT JOIN reservations res ON res.id=t."reservationId"
               WHERE t."propertyId"=$1 AND t."serviceCode"=$2 AND t.source=$3
                 AND t.status IN ('OPEN','IN_PROGRESS')
               ORDER BY t."createdAt" ASC LIMIT 200''',
            pid,
            ARRIVAL_CODE,
            ARRIVAL_SOURCE,
        )
    return {
        "items": [
            {
                "id": str(row["id"]),
                "status": row["status"],
                "title": row["title"],
                "description": row["description"],
                "room_code": row["room_code"],
                "booking_number": row["bookingNumber"],
                "created_at": row["createdAt"],
            }
            for row in rows
        ]
    }


@router.post("/arrivals/{task_id}/ack")
async def acknowledge_arrival(task_id: uuid.UUID, request: Request, user: dict[str, Any] = Depends(kitchen_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            row = await conn.fetchrow(
                '''SELECT id,status::text AS status FROM operational_tasks
                   WHERE id=$1 AND "propertyId"=$2 AND "serviceCode"=$3 AND source=$4 FOR UPDATE''',
                task_id,
                pid,
                ARRIVAL_CODE,
                ARRIVAL_SOURCE,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Kitchen arrival notification not found")
            if row["status"] not in {"OPEN", "IN_PROGRESS"}:
                raise HTTPException(status_code=409, detail={"code": "ARRIVAL_ALREADY_CLOSED", "status": row["status"]})
            await conn.execute(
                '''UPDATE operational_tasks SET status='DONE',"completedAt"=now(),"updatedAt"=now() WHERE id=$1''',
                task_id,
            )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'ACK_KITCHEN_ARRIVAL','OperationalTask',$4,'KITCHEN','SUCCESS',
                     jsonb_build_object('status','DONE','financial_effect','NONE'),now())''',
                uuid.uuid4(),
                pid,
                user["id"],
                str(task_id),
            )
    return {"id": str(task_id), "status": "DONE"}
