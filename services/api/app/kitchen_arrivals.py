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


@router.post("/sync-arrivals")
async def sync_recent_arrivals(
    request: Request,
    user: dict[str, Any] = Depends(kitchen_access),
):
    """Materialize one kitchen queue notification per recent successful check-in.

    The operation is idempotent and deliberately carries no payment, passport,
    phone or other unnecessary guest data. It exists so an open Dining Staff
    shift receives a new-arrival card automatically on its normal queue poll.
    """
    actor_id = uuid.UUID(user["id"])
    created: list[str] = []
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            arrivals = await conn.fetch(
                '''
                SELECT res.id AS reservation_id,res."bookingNumber",res."checkIn",res."checkOut",
                       res.adults,res.children,stay.id AS stay_id,room.id AS room_id,room.code AS room_code
                FROM reservations res
                JOIN stays stay ON stay."reservationId"=res.id
                  AND stay."propertyId"=res."propertyId" AND stay.status='ACTIVE'
                JOIN room_assignments ra ON ra."stayId"=stay.id AND ra."endedAt" IS NULL
                JOIN rooms room ON room.id=ra."roomId"
                WHERE res."propertyId"=$1 AND res.status='CHECKED_IN'
                  AND stay."actualCheckInAt" >= now() - interval '24 hours'
                ORDER BY stay."actualCheckInAt" ASC
                ''',
                pid,
            )
            for row in arrivals:
                exists = await conn.fetchval(
                    '''
                    SELECT id FROM operational_tasks
                    WHERE "propertyId"=$1 AND "reservationId"=$2
                      AND "serviceCode"=$3 AND source=$4
                    LIMIT 1
                    ''',
                    pid,
                    row["reservation_id"],
                    ARRIVAL_CODE,
                    ARRIVAL_SOURCE,
                )
                if exists:
                    continue
                task_id = uuid.uuid4()
                description = (
                    f"Номер {row['room_code']} · взрослых: {row['adults']} · детей: {row['children']} · "
                    f"проживание {row['checkIn']} — {row['checkOut']}. "
                    "Питание по брони не предполагается автоматически: при необходимости уточнить на ресепшене."
                )
                await conn.execute(
                    '''
                    INSERT INTO operational_tasks (
                      id,"propertyId","roomId","reservationId","stayId",type,status,priority,title,
                      description,"createdByType","createdById",source,"serviceCode","createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,$4,$5,'GUEST_REQUEST','OPEN','HIGH',$6,$7,'SYSTEM',$8,$9,$10,now(),now())
                    ''',
                    task_id,
                    pid,
                    row["room_id"],
                    row["reservation_id"],
                    row["stay_id"],
                    f"Новый заезд · номер {row['room_code']}",
                    description,
                    str(actor_id),
                    ARRIVAL_SOURCE,
                    ARRIVAL_CODE,
                )
                await conn.execute(
                    '''
                    INSERT INTO audit_logs (
                      id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,
                      "afterJson","createdAt"
                    ) VALUES ($1,$2,'SYSTEM',$3,'KITCHEN_ARRIVAL_NOTIFICATION','OperationalTask',$4,$5,'SUCCESS',
                      jsonb_build_object(
                        'reservation_id',$6::text,'stay_id',$7::text,'room_code',$8::text,
                        'adults',$9::int,'children',$10::int,
                        'financial_effect','NONE','sensitive_guest_data','EXCLUDED'
                      ),now())
                    ''',
                    uuid.uuid4(),
                    pid,
                    str(actor_id),
                    str(task_id),
                    ARRIVAL_SOURCE,
                    str(row["reservation_id"]),
                    str(row["stay_id"]),
                    row["room_code"],
                    row["adults"],
                    row["children"],
                )
                created.append(str(task_id))
    return {
        "created": len(created),
        "task_ids": created,
        "request_code": ARRIVAL_CODE,
        "truth": "Recent successful check-ins are surfaced to Dining Staff without payment or sensitive guest data.",
    }
