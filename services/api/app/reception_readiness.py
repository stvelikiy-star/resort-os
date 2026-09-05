import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .auth import current_user

router = APIRouter(prefix="/api/v1/admin/reception", tags=["reception-readiness"])
ALLOWED_ROLES = {"OWNER", "MANAGER", "RECEPTION"}


async def _property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval("SELECT id FROM properties WHERE code=$1", property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


@router.post("/reservations/{reservation_id}/housekeeping-request", status_code=status.HTTP_201_CREATED)
async def request_housekeeping_for_arrival(
    reservation_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(current_user),
):
    if user["role"] not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permission")

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await _property_id(conn, user["property_code"])
            arrival = await conn.fetchrow(
                '''
                SELECT r.id AS reservation_id, r."bookingNumber" AS booking_number,
                       r.status::text AS reservation_status, r."checkIn" AS check_in,
                       ib."roomId" AS room_id, rm.code AS room_code,
                       rm."operationalState"::text AS room_state
                FROM reservations r
                JOIN inventory_blocks ib
                  ON ib."reservationId"=r.id
                 AND ib.active=true
                 AND ib."blockType"='RESERVATION'
                JOIN rooms rm ON rm.id=ib."roomId" AND rm."propertyId"=r."propertyId"
                WHERE r.id=$1 AND r."propertyId"=$2
                  AND ib."startDate" <= r."checkIn"
                  AND ib."endDate" > r."checkIn"
                ORDER BY ib."startDate", ib."createdAt"
                LIMIT 1
                FOR UPDATE OF rm
                ''',
                reservation_id,
                pid,
            )
            if not arrival:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "ARRIVAL_ROOM_NOT_ASSIGNED", "message": "Arrival room is not assigned."},
                )
            if arrival["reservation_status"] != "GUARANTEED":
                raise HTTPException(
                    status_code=409,
                    detail={"code": "ARRIVAL_NOT_GUARANTEED", "message": "Housekeeping handoff is only for expected arrivals."},
                )
            if arrival["room_state"] == "CLEAN":
                return {
                    "status": "ALREADY_READY",
                    "room_code": arrival["room_code"],
                    "room_state": "CLEAN",
                    "task_id": None,
                }
            if arrival["room_state"] == "TECH_BLOCK":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "ARRIVAL_ROOM_TECH_BLOCK",
                        "message": "The arrival room is in TECH_BLOCK and requires maintenance resolution before housekeeping.",
                        "room_code": arrival["room_code"],
                    },
                )
            if arrival["room_state"] == "IN_INSPECTION":
                return {
                    "status": "AWAITING_INSPECTION",
                    "room_code": arrival["room_code"],
                    "room_state": "IN_INSPECTION",
                    "task_id": None,
                }

            existing = await conn.fetchrow(
                '''
                SELECT id,status::text AS status
                FROM operational_tasks
                WHERE "propertyId"=$1 AND "roomId"=$2 AND type='HOUSEKEEPING'
                  AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
                ORDER BY "createdAt" DESC
                LIMIT 1
                ''',
                pid,
                arrival["room_id"],
            )
            if existing:
                return {
                    "status": "EXISTING_TASK",
                    "room_code": arrival["room_code"],
                    "room_state": arrival["room_state"],
                    "task_id": str(existing["id"]),
                    "task_status": existing["status"],
                }

            task_id = uuid.uuid4()
            title = f"Подготовить к заезду · №{arrival['room_code']}"
            description = f"Бронь {arrival['booking_number']} · заезд {arrival['check_in']}"
            await conn.execute(
                '''
                INSERT INTO operational_tasks (
                  id,"propertyId","roomId","reservationId",type,status,priority,title,description,
                  "createdByType","createdById",source,"createdAt","updatedAt"
                ) VALUES ($1,$2,$3,$4,'HOUSEKEEPING','OPEN','HIGH',$5,$6,
                  'STAFF',$7,'RECEPTION_READINESS',now(),now())
                ''',
                task_id,
                pid,
                arrival["room_id"],
                arrival["reservation_id"],
                title,
                description,
                user["id"],
            )
            await conn.execute(
                '''UPDATE rooms SET "operationalState"='DIRTY',"updatedAt"=now()
                   WHERE id=$1 AND "operationalState"='UNKNOWN' ''',
                arrival["room_id"],
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'REQUEST_ARRIVAL_HOUSEKEEPING','OperationalTask',$4,
                  'RECEPTION_READINESS','SUCCESS',
                  jsonb_build_object('reservation_id',$5::text,'room_code',$6::text,'previous_room_state',$7::text),now())
                ''',
                uuid.uuid4(),
                pid,
                user["id"],
                str(task_id),
                str(arrival["reservation_id"]),
                arrival["room_code"],
                arrival["room_state"],
            )

    return {
        "status": "CREATED",
        "room_code": arrival["room_code"],
        "room_state": "DIRTY" if arrival["room_state"] == "UNKNOWN" else arrival["room_state"],
        "task_id": str(task_id),
        "task_status": "OPEN",
    }
