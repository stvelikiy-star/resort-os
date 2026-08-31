import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import current_user

router = APIRouter(prefix="/api/v1/ops/guest-requests", tags=["staff-guest-requests"])

ROLE_CODES: dict[str, set[str]] = {
    "MAID": {"HOUSEKEEPING", "TOWELS", "LINEN"},
    "TECHNICIAN": {"MAINTENANCE"},
    "DINING_STAFF": {"MEALS"},
    "RECEPTION": {"TRANSFER", "PARKING", "SAUNA", "BILLIARDS", "EXCURSIONS", "ADMIN"},
    "OWNER": {"*"},
    "MANAGER": {"*"},
}


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


def allowed_codes(role: str) -> set[str]:
    return ROLE_CODES.get(role, set())


def can_handle(role: str, service_code: str | None) -> bool:
    allowed = allowed_codes(role)
    return "*" in allowed or bool(service_code and service_code in allowed)


def row_to_item(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "request_code": row["serviceCode"],
        "status": row["status"],
        "priority": row["priority"],
        "title": row["title"],
        "description": row["description"],
        "room_code": row["room_code"],
        "guest_first_name": row["firstName"],
        "booking_number": row["bookingNumber"],
        "service_date": row["serviceDate"],
        "service_time": row["serviceTime"],
        "assigned_to_id": str(row["assignedToId"]) if row["assignedToId"] else None,
        "assigned_to_name": row["assigned_to_name"],
        "source": row["source"],
        "stay_id": str(row["stayId"]) if row["stayId"] else None,
        "reservation_id": str(row["reservationId"]) if row["reservationId"] else None,
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
        "completed_at": row["completedAt"],
    }


BASE_SELECT = '''
SELECT t.id,t.status::text AS status,t.priority::text AS priority,t.title,t.description,
       t."serviceCode",t."serviceDate",t."serviceTime",t."assignedToId",t."stayId",t."reservationId",t.source,
       t."createdAt",t."updatedAt",t."completedAt",
       COALESCE(room.code,current_room.code) AS room_code,
       COALESCE(stay_guest."firstName",reservation_guest."firstName") AS "firstName",
       res."bookingNumber",assignee."displayName" AS assigned_to_name
FROM operational_tasks t
LEFT JOIN rooms room ON room.id=t."roomId"
LEFT JOIN stays stay ON stay.id=t."stayId"
LEFT JOIN guests stay_guest ON stay_guest.id=stay."guestId"
LEFT JOIN reservations res ON res.id=t."reservationId"
LEFT JOIN guests reservation_guest ON reservation_guest.id=res."primaryGuestId"
LEFT JOIN staff_users assignee ON assignee.id=t."assignedToId"
LEFT JOIN LATERAL (
  SELECT r.code
  FROM room_assignments ra
  JOIN rooms r ON r.id=ra."roomId"
  WHERE ra."stayId"=t."stayId" AND ra."endedAt" IS NULL
  ORDER BY ra."startedAt" DESC
  LIMIT 1
) current_room ON true
'''


@router.get("")
async def list_staff_guest_requests(
    request: Request,
    task_status: str | None = Query(default="ACTIVE", alias="status"),
    limit: int = Query(default=150, ge=1, le=300),
    user: dict[str, Any] = Depends(current_user),
):
    allowed = allowed_codes(user["role"])
    if not allowed:
        raise HTTPException(status_code=403, detail="Guest-request queue not available for role")
    if task_status not in {"ACTIVE", "ALL", "OPEN", "IN_PROGRESS", "DONE", "CANCELLED"}:
        raise HTTPException(status_code=422, detail="Unknown guest-request status")

    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        rows = await conn.fetch(
            BASE_SELECT + '''
            WHERE t."propertyId"=$1 AND t.type='GUEST_REQUEST' AND t."serviceCode" IS NOT NULL
              AND ($2::boolean OR t."serviceCode"=ANY($3::text[]))
              AND (
                $4='ALL' OR ($4='ACTIVE' AND t.status IN ('OPEN','IN_PROGRESS')) OR t.status::text=$4
              )
            ORDER BY
              CASE t.priority::text WHEN 'URGENT' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'NORMAL' THEN 2 ELSE 3 END,
              t."createdAt" ASC
            LIMIT $5
            ''',
            pid, "*" in allowed, list(allowed - {"*"}), task_status, limit,
        )
    return {
        "items": [row_to_item(row) for row in rows],
        "allowed_request_codes": sorted(allowed),
        "truth": "Role routing is based on canonical OperationalTask.serviceCode, not on the channel that created the request.",
    }


async def load_routed_task_for_update(conn, pid, task_id: uuid.UUID, role: str):
    task = await conn.fetchrow(
        '''SELECT id,"serviceCode",status::text AS status,"assignedToId","stayId",source
           FROM operational_tasks
           WHERE id=$1 AND "propertyId"=$2 AND type='GUEST_REQUEST' AND "serviceCode" IS NOT NULL FOR UPDATE''',
        task_id,
        pid,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Guest request not found")
    if not can_handle(role, task["serviceCode"]):
        raise HTTPException(status_code=403, detail="Request type not allowed for role")
    return task


async def record_guest_history(conn, pid, task, task_id: uuid.UUID, event_type: str, source: str):
    if not task["stayId"]:
        return
    guest_id = await conn.fetchval('SELECT "guestId" FROM stays WHERE id=$1', task["stayId"])
    if not guest_id:
        return
    already_recorded = await conn.fetchval(
        '''SELECT 1 FROM guest_history_events
           WHERE "stayId"=$1 AND "eventType"=$2
             AND "payloadJson"->>'task_id'=$3 LIMIT 1''',
        task["stayId"],
        event_type,
        str(task_id),
    )
    if already_recorded:
        return
    await conn.execute(
        '''INSERT INTO guest_history_events (id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt")
           VALUES ($1,$2,$3,$4,$5,$6,
             jsonb_build_object('task_id',$7::text,'request_code',$8::text,'request_source',$9::text),now(),now())''',
        uuid.uuid4(),
        pid,
        guest_id,
        task["stayId"],
        event_type,
        source,
        str(task_id),
        task["serviceCode"],
        task["source"],
    )


@router.post("/{task_id}/claim")
async def claim_guest_request(task_id: uuid.UUID, request: Request, user: dict[str, Any] = Depends(current_user)):
    allowed = allowed_codes(user["role"])
    if not allowed:
        raise HTTPException(status_code=403, detail="Guest-request queue not available for role")
    actor_id = uuid.UUID(user["id"])
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            task = await load_routed_task_for_update(conn, pid, task_id, user["role"])
            if task["assignedToId"] and task["assignedToId"] != actor_id:
                raise HTTPException(status_code=409, detail="Request already assigned to another employee")
            if task["status"] not in {"OPEN", "IN_PROGRESS"}:
                raise HTTPException(status_code=409, detail={"code": "GUEST_REQUEST_NOT_CLAIMABLE", "status": task["status"]})
            await conn.execute(
                'UPDATE operational_tasks SET "assignedToId"=$1,status=\'IN_PROGRESS\',"updatedAt"=now() WHERE id=$2',
                actor_id,
                task_id,
            )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'CLAIM_GUEST_REQUEST','OperationalTask',$4,'STAFF_GUEST_REQUESTS','SUCCESS',
                     jsonb_build_object('request_code',$5::text,'request_source',$6::text,'status','IN_PROGRESS'),now())''',
                uuid.uuid4(), pid, str(actor_id), str(task_id), task["serviceCode"], task["source"],
            )
    return {"id": str(task_id), "status": "IN_PROGRESS", "assigned_to_id": str(actor_id)}


@router.post("/{task_id}/complete")
async def complete_guest_request(task_id: uuid.UUID, request: Request, user: dict[str, Any] = Depends(current_user)):
    allowed = allowed_codes(user["role"])
    if not allowed:
        raise HTTPException(status_code=403, detail="Guest-request queue not available for role")
    actor_id = uuid.UUID(user["id"])
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            task = await load_routed_task_for_update(conn, pid, task_id, user["role"])
            if task["assignedToId"] != actor_id and user["role"] not in {"OWNER", "MANAGER"}:
                raise HTTPException(status_code=403, detail="Claim the request before completing it")
            if task["status"] != "IN_PROGRESS":
                raise HTTPException(status_code=409, detail={"code": "GUEST_REQUEST_NOT_IN_PROGRESS", "status": task["status"]})
            await conn.execute(
                'UPDATE operational_tasks SET status=\'DONE\',"completedAt"=now(),"updatedAt"=now() WHERE id=$1',
                task_id,
            )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'COMPLETE_GUEST_REQUEST','OperationalTask',$4,'STAFF_GUEST_REQUESTS','SUCCESS',
                     jsonb_build_object('request_code',$5::text,'request_source',$6::text,'status','DONE',
                       'financial_effect','NONE_AUTOMATIC','room_state_effect','NONE_AUTOMATIC'),now())''',
                uuid.uuid4(), pid, str(actor_id), str(task_id), task["serviceCode"], task["source"],
            )
            await record_guest_history(conn, pid, task, task_id, "GUEST_REQUEST_COMPLETED", "STAFF_GUEST_REQUESTS")
    return {"id": str(task_id), "status": "DONE"}


@router.post("/{task_id}/cancel")
async def cancel_guest_request(task_id: uuid.UUID, request: Request, user: dict[str, Any] = Depends(current_user)):
    allowed = allowed_codes(user["role"])
    if not allowed:
        raise HTTPException(status_code=403, detail="Guest-request queue not available for role")
    actor_id = uuid.UUID(user["id"])
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            task = await load_routed_task_for_update(conn, pid, task_id, user["role"])
            if task["status"] not in {"OPEN", "IN_PROGRESS"}:
                raise HTTPException(status_code=409, detail={"code": "GUEST_REQUEST_NOT_CANCELLABLE", "status": task["status"]})
            if task["assignedToId"] and task["assignedToId"] != actor_id and user["role"] not in {"OWNER", "MANAGER"}:
                raise HTTPException(status_code=403, detail="Request is assigned to another employee")
            await conn.execute(
                'UPDATE operational_tasks SET status=\'CANCELLED\',"completedAt"=now(),"updatedAt"=now() WHERE id=$1',
                task_id,
            )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'CANCEL_GUEST_REQUEST','OperationalTask',$4,'STAFF_GUEST_REQUESTS','SUCCESS',
                     jsonb_build_object('request_code',$5::text,'request_source',$6::text,'status','CANCELLED',
                       'financial_effect','NONE_AUTOMATIC','room_state_effect','NONE_AUTOMATIC'),now())''',
                uuid.uuid4(), pid, str(actor_id), str(task_id), task["serviceCode"], task["source"],
            )
            await record_guest_history(conn, pid, task, task_id, "GUEST_REQUEST_CANCELLED", "STAFF_GUEST_REQUESTS")
    return {"id": str(task_id), "status": "CANCELLED"}
