import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import current_user

router = APIRouter(prefix="/api/v1/ops/guest-requests", tags=["staff-guest-requests"])

ROLE_CODES: dict[str, set[str]] = {
    "MAID": {"HOUSEKEEPING", "TOWELS", "LINEN"},
    "TECHNICIAN": {"MAINTENANCE"},
    "DINING_STAFF": {"MEALS"},
    "RECEPTION": {"TRANSFER", "SAUNA", "BILLIARDS", "EXCURSIONS", "ADMIN"},
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
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
        "completed_at": row["completedAt"],
    }


BASE_SELECT = '''
SELECT t.id,t.status::text AS status,t.priority::text AS priority,t.title,t.description,
       t."serviceCode",t."serviceDate",t."serviceTime",t."assignedToId",t."createdAt",t."updatedAt",t."completedAt",
       room.code AS room_code,g."firstName",res."bookingNumber",assignee."displayName" AS assigned_to_name
FROM operational_tasks t
LEFT JOIN rooms room ON room.id=t."roomId"
LEFT JOIN stays stay ON stay.id=t."stayId"
LEFT JOIN guests g ON g.id=stay."guestId"
LEFT JOIN reservations res ON res.id=t."reservationId"
LEFT JOIN staff_users assignee ON assignee.id=t."assignedToId"
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
            WHERE t."propertyId"=$1 AND t.type='GUEST_REQUEST' AND t.source LIKE 'GUEST_OS_%'
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
    return {"items": [row_to_item(row) for row in rows], "allowed_request_codes": sorted(allowed)}


@router.post("/{task_id}/claim")
async def claim_guest_request(task_id: uuid.UUID, request: Request, user: dict[str, Any] = Depends(current_user)):
    allowed = allowed_codes(user["role"])
    if not allowed:
        raise HTTPException(status_code=403, detail="Guest-request queue not available for role")
    actor_id = uuid.UUID(user["id"])
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            task = await conn.fetchrow(
                '''SELECT id,"serviceCode",status::text AS status,"assignedToId","stayId" FROM operational_tasks
                   WHERE id=$1 AND "propertyId"=$2 AND type='GUEST_REQUEST' AND source LIKE 'GUEST_OS_%' FOR UPDATE''',
                task_id, pid,
            )
            if not task:
                raise HTTPException(status_code=404, detail="Guest request not found")
            if not can_handle(user["role"], task["serviceCode"]):
                raise HTTPException(status_code=403, detail="Request type not allowed for role")
            if task["assignedToId"] and task["assignedToId"] != actor_id:
                raise HTTPException(status_code=409, detail="Request already assigned to another employee")
            if task["status"] not in {"OPEN", "IN_PROGRESS"}:
                raise HTTPException(status_code=409, detail={"code": "GUEST_REQUEST_NOT_CLAIMABLE", "status": task["status"]})
            await conn.execute('UPDATE operational_tasks SET "assignedToId"=$1,status=\'IN_PROGRESS\',"updatedAt"=now() WHERE id=$2', actor_id, task_id)
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'CLAIM_GUEST_REQUEST','OperationalTask',$4,'STAFF_GUEST_REQUESTS','SUCCESS',
                     jsonb_build_object('request_code',$5::text,'status','IN_PROGRESS'),now())''',
                uuid.uuid4(), pid, str(actor_id), str(task_id), task["serviceCode"],
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
            task = await conn.fetchrow(
                '''SELECT id,"serviceCode",status::text AS status,"assignedToId","stayId" FROM operational_tasks
                   WHERE id=$1 AND "propertyId"=$2 AND type='GUEST_REQUEST' AND source LIKE 'GUEST_OS_%' FOR UPDATE''',
                task_id, pid,
            )
            if not task:
                raise HTTPException(status_code=404, detail="Guest request not found")
            if not can_handle(user["role"], task["serviceCode"]):
                raise HTTPException(status_code=403, detail="Request type not allowed for role")
            if task["assignedToId"] != actor_id and user["role"] not in {"OWNER", "MANAGER"}:
                raise HTTPException(status_code=403, detail="Claim the request before completing it")
            if task["status"] != "IN_PROGRESS":
                raise HTTPException(status_code=409, detail={"code": "GUEST_REQUEST_NOT_IN_PROGRESS", "status": task["status"]})
            await conn.execute('UPDATE operational_tasks SET status=\'DONE\',"completedAt"=now(),"updatedAt"=now() WHERE id=$1', task_id)
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'COMPLETE_GUEST_REQUEST','OperationalTask',$4,'STAFF_GUEST_REQUESTS','SUCCESS',
                     jsonb_build_object('request_code',$5::text,'status','DONE','financial_effect','NONE_AUTOMATIC','room_state_effect','NONE_AUTOMATIC'),now())''',
                uuid.uuid4(), pid, str(actor_id), str(task_id), task["serviceCode"],
            )
            if task["stayId"]:
                guest_id = await conn.fetchval('SELECT "guestId" FROM stays WHERE id=$1', task["stayId"])
                if guest_id:
                    await conn.execute(
                        '''INSERT INTO guest_history_events (id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt")
                           VALUES ($1,$2,$3,$4,'GUEST_REQUEST_COMPLETED','STAFF_GUEST_REQUESTS',
                             jsonb_build_object('task_id',$5::text,'request_code',$6::text),now(),now())''',
                        uuid.uuid4(), pid, guest_id, task["stayId"], str(task_id), task["serviceCode"],
                    )
    return {"id": str(task_id), "status": "DONE"}
