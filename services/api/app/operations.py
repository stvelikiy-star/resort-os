import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .auth import current_user, require_roles

router = APIRouter(prefix="/api/v1/ops", tags=["operations"])

TASK_TYPES = {"HOUSEKEEPING", "MAINTENANCE", "GUEST_REQUEST"}
TASK_STATUSES = {"OPEN", "IN_PROGRESS", "IN_INSPECTION", "DONE", "CANCELLED"}
TASK_PRIORITIES = {"LOW", "NORMAL", "HIGH", "URGENT"}
ROOM_STATES = {"UNKNOWN", "CLEAN", "DIRTY", "IN_INSPECTION", "TECH_BLOCK"}

TASK_TRANSITIONS: dict[str, dict[str, set[str]]] = {
    "HOUSEKEEPING": {
        "OPEN": {"IN_PROGRESS", "CANCELLED"},
        "IN_PROGRESS": {"IN_INSPECTION", "CANCELLED"},
        "IN_INSPECTION": {"IN_PROGRESS", "DONE", "CANCELLED"},
        "DONE": set(),
        "CANCELLED": set(),
    },
    "MAINTENANCE": {
        "OPEN": {"IN_PROGRESS", "CANCELLED"},
        "IN_PROGRESS": {"DONE", "CANCELLED"},
        "IN_INSPECTION": set(),
        "DONE": set(),
        "CANCELLED": set(),
    },
    "GUEST_REQUEST": {
        "OPEN": {"IN_PROGRESS", "CANCELLED"},
        "IN_PROGRESS": {"DONE", "CANCELLED"},
        "IN_INSPECTION": set(),
        "DONE": set(),
        "CANCELLED": set(),
    },
}


class TaskCreate(BaseModel):
    type: str
    room_id: uuid.UUID | None = None
    priority: str = "NORMAL"
    title: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=4000)
    assigned_to_id: uuid.UUID | None = None
    source: str = Field(default="PMS", max_length=60)


class TaskStatusPatch(BaseModel):
    status: str


class RoomStatePatch(BaseModel):
    state: str


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval("SELECT id FROM properties WHERE code=$1", property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


def allowed_types_for_role(role: str) -> set[str]:
    if role in {"OWNER", "MANAGER"}:
        return TASK_TYPES
    if role == "MAID":
        return {"HOUSEKEEPING"}
    if role == "TECHNICIAN":
        return {"MAINTENANCE"}
    return set()


def task_to_dict(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "type": row["type"],
        "status": row["status"],
        "priority": row["priority"],
        "title": row["title"],
        "description": row["description"],
        "room_id": str(row["roomId"]) if row["roomId"] else None,
        "room_code": row["room_code"],
        "room_state": row["room_state"],
        "assigned_to_id": str(row["assignedToId"]) if row["assignedToId"] else None,
        "assigned_to_name": row["assigned_to_name"],
        "source": row["source"],
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
        "completed_at": row["completedAt"],
    }


async def settle_terminal_maintenance_room(conn, property_id_value, room_id, task_id, actor_id):
    """Serialize terminal maintenance transitions on the room.

    The room remains TECH_BLOCK while any other maintenance task is active. When
    the last repair is completed/cancelled, force DIRTY and create/reuse a
    housekeeping task so the room cannot jump directly from repair to sellable.
    """
    room = await conn.fetchrow(
        '''SELECT id,code,"operationalState"::text AS state FROM rooms
           WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
        room_id,
        property_id_value,
    )
    if not room:
        raise HTTPException(status_code=409, detail="Task room no longer exists")

    remaining = int(
        await conn.fetchval(
            '''
            SELECT count(*)::int FROM operational_tasks
            WHERE "propertyId"=$1 AND "roomId"=$2 AND type='MAINTENANCE'
              AND id<>$3 AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
            ''',
            property_id_value,
            room_id,
            task_id,
        )
        or 0
    )
    if remaining > 0:
        await conn.execute(
            '''UPDATE rooms SET "operationalState"='TECH_BLOCK',"updatedAt"=now() WHERE id=$1''',
            room_id,
        )
        return {"room_state": "TECH_BLOCK", "remaining_maintenance_tasks": remaining, "housekeeping_task_id": None}

    await conn.execute(
        '''UPDATE rooms SET "operationalState"='DIRTY',"updatedAt"=now() WHERE id=$1''',
        room_id,
    )
    housekeeping_task_id = await conn.fetchval(
        '''
        SELECT id FROM operational_tasks
        WHERE "roomId"=$1 AND type='HOUSEKEEPING'
          AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
        ORDER BY "createdAt" DESC LIMIT 1
        ''',
        room_id,
    )
    if not housekeeping_task_id:
        housekeeping_task_id = uuid.uuid4()
        await conn.execute(
            '''
            INSERT INTO operational_tasks (
              id,"propertyId","roomId",type,status,priority,title,description,
              "createdByType","createdById",source,"createdAt","updatedAt"
            ) VALUES ($1,$2,$3,'HOUSEKEEPING','OPEN','HIGH',$4,$5,'SYSTEM',$6,'MAINTENANCE_TERMINAL',now(),now())
            ''',
            housekeeping_task_id,
            property_id_value,
            room_id,
            f"Уборка после ремонта · {room['code']}",
            f"Создано после завершения/отмены ремонта {task_id}",
            actor_id,
        )
    return {
        "room_state": "DIRTY",
        "remaining_maintenance_tasks": 0,
        "housekeeping_task_id": str(housekeeping_task_id),
    }


@router.get("/tasks")
async def list_tasks(
    request: Request,
    task_status: str | None = Query(default=None, alias="status"),
    task_type: str | None = Query(default=None, alias="type"),
    limit: int = Query(default=150, ge=1, le=300),
    user: dict[str, Any] = Depends(current_user),
):
    allowed = allowed_types_for_role(user["role"])
    if task_type and task_type not in allowed:
        raise HTTPException(status_code=403, detail="Task type not allowed for role")
    if task_status and task_status not in TASK_STATUSES:
        raise HTTPException(status_code=422, detail="Unknown task status")
    line_staff_id = uuid.UUID(user["id"]) if user["role"] in {"MAID", "TECHNICIAN"} else None
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        rows = await conn.fetch(
            '''
            SELECT t.id, t.type::text AS type, t.status::text AS status, t.priority::text AS priority,
                   t.title, t.description, t."roomId", t."assignedToId", t.source, t."createdAt",
                   t."updatedAt", t."completedAt", r.code AS room_code,
                   r."operationalState"::text AS room_state, u."displayName" AS assigned_to_name
            FROM operational_tasks t
            LEFT JOIN rooms r ON r.id=t."roomId"
            LEFT JOIN staff_users u ON u.id=t."assignedToId"
            WHERE t."propertyId"=$1
              AND t.type::text = ANY($2::text[])
              AND ($3::text IS NULL OR t.status::text=$3)
              AND ($4::text IS NULL OR t.type::text=$4)
              AND ($6::uuid IS NULL OR t."assignedToId" IS NULL OR t."assignedToId"=$6)
            ORDER BY
              CASE t.priority::text WHEN 'URGENT' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'NORMAL' THEN 2 ELSE 3 END,
              t."createdAt" DESC
            LIMIT $5
            ''',
            pid, list(allowed), task_status, task_type, limit, line_staff_id,
        )
    return {"items": [task_to_dict(row) for row in rows]}


@router.post("/tasks", status_code=201)
async def create_task(
    payload: TaskCreate,
    request: Request,
    user: dict[str, Any] = Depends(current_user),
):
    if payload.type not in TASK_TYPES or payload.type not in allowed_types_for_role(user["role"]):
        raise HTTPException(status_code=403, detail="Task type not allowed for role")
    if payload.priority not in TASK_PRIORITIES:
        raise HTTPException(status_code=422, detail="Unknown priority")

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            if payload.room_id:
                room = await conn.fetchrow(
                    '''SELECT id, code FROM rooms WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                    payload.room_id, pid,
                )
                if not room:
                    raise HTTPException(status_code=422, detail="Room not found")
            if payload.assigned_to_id:
                assignee_role = await conn.fetchval(
                    '''SELECT role::text FROM staff_users WHERE id=$1 AND "propertyId"=$2 AND "isActive"=true''',
                    payload.assigned_to_id, pid,
                )
                expected = "MAID" if payload.type == "HOUSEKEEPING" else "TECHNICIAN" if payload.type == "MAINTENANCE" else None
                if expected and assignee_role != expected:
                    raise HTTPException(status_code=422, detail=f"Assignee must have role {expected}")

            task_id = uuid.uuid4()
            await conn.execute(
                '''
                INSERT INTO operational_tasks (id,"propertyId","roomId",type,status,priority,title,description,
                  "assignedToId","createdByType","createdById",source,"createdAt","updatedAt")
                VALUES ($1,$2,$3,$4::"OperationalTaskType",'OPEN',$5::"OperationalTaskPriority",$6,$7,$8,
                  'STAFF',$9,$10,now(),now())
                ''',
                task_id, pid, payload.room_id, payload.type, payload.priority, payload.title,
                payload.description, payload.assigned_to_id, user["id"], payload.source,
            )
            if payload.room_id and payload.type == "MAINTENANCE":
                await conn.execute('UPDATE rooms SET "operationalState"=\'TECH_BLOCK\', "updatedAt"=now() WHERE id=$1', payload.room_id)
            elif payload.room_id and payload.type == "HOUSEKEEPING":
                await conn.execute('UPDATE rooms SET "operationalState"=\'DIRTY\', "updatedAt"=now() WHERE id=$1 AND "operationalState"<>\'TECH_BLOCK\'', payload.room_id)

            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"createdAt")
                   VALUES ($1,$2,'STAFF',$3,'CREATE','OperationalTask',$4,$5,'SUCCESS',now())''',
                uuid.uuid4(), pid, user["id"], str(task_id), payload.source,
            )
    return {"id": str(task_id), "status": "OPEN"}


@router.post("/tasks/{task_id}/claim")
async def claim_task(
    task_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(current_user),
):
    if user["role"] not in {"MAID", "TECHNICIAN"}:
        raise HTTPException(status_code=403, detail="Only line staff claims tasks through this endpoint")
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            task = await conn.fetchrow(
                '''SELECT id,type::text AS type,status::text AS status,"assignedToId" FROM operational_tasks
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                task_id, pid,
            )
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            if task["type"] not in allowed_types_for_role(user["role"]):
                raise HTTPException(status_code=403, detail="Task type not allowed for role")
            current_user_id = uuid.UUID(user["id"])
            if task["assignedToId"] and task["assignedToId"] != current_user_id:
                raise HTTPException(status_code=409, detail="Task is already assigned to another employee")
            if task["status"] not in {"OPEN", "IN_PROGRESS"}:
                raise HTTPException(status_code=409, detail="Task cannot be claimed in current state")
            await conn.execute(
                '''UPDATE operational_tasks SET "assignedToId"=$1,status='IN_PROGRESS',"updatedAt"=now() WHERE id=$2''',
                current_user_id, task_id,
            )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'CLAIM','OperationalTask',$4,'STAFF_PWA','SUCCESS',
                     jsonb_build_object('from_status',$5::text,'status','IN_PROGRESS'),now())''',
                uuid.uuid4(), pid, user["id"], str(task_id), task["status"],
            )
    return {"id": str(task_id), "status": "IN_PROGRESS", "assigned_to_id": user["id"]}


@router.patch("/tasks/{task_id}/status")
async def change_task_status(
    task_id: uuid.UUID,
    payload: TaskStatusPatch,
    request: Request,
    user: dict[str, Any] = Depends(current_user),
):
    if payload.status not in TASK_STATUSES:
        raise HTTPException(status_code=422, detail="Unknown task status")

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            task = await conn.fetchrow(
                '''SELECT id,type::text AS type,status::text AS status,"roomId","assignedToId" FROM operational_tasks
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                task_id, pid,
            )
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            if task["type"] not in allowed_types_for_role(user["role"]):
                raise HTTPException(status_code=403, detail="Task type not allowed for role")
            if user["role"] in {"MAID", "TECHNICIAN"} and task["assignedToId"] != uuid.UUID(user["id"]):
                raise HTTPException(status_code=403, detail="Claim the task before changing its status")

            current_status = task["status"]
            allowed_targets = TASK_TRANSITIONS.get(task["type"], {}).get(current_status, set())
            if payload.status not in allowed_targets:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "INVALID_TASK_TRANSITION",
                        "task_type": task["type"],
                        "from_status": current_status,
                        "to_status": payload.status,
                    },
                )

            is_manager = user["role"] in {"OWNER", "MANAGER"}
            if payload.status == "CANCELLED" and not is_manager:
                raise HTTPException(status_code=403, detail="Only management can cancel an operational task")
            if task["type"] == "HOUSEKEEPING" and current_status == "IN_INSPECTION" and payload.status in {"IN_PROGRESS", "DONE"} and not is_manager:
                raise HTTPException(status_code=403, detail="Inspection decision can only be made by management")

            room_state = None
            if task["roomId"]:
                room_state = await conn.fetchval(
                    'SELECT "operationalState"::text FROM rooms WHERE id=$1 AND "propertyId"=$2 FOR UPDATE',
                    task["roomId"], pid,
                )

            maintenance_result = None
            if task["type"] == "HOUSEKEEPING" and payload.status == "IN_INSPECTION" and task["roomId"]:
                if room_state != "TECH_BLOCK":
                    await conn.execute('UPDATE rooms SET "operationalState"=\'IN_INSPECTION\', "updatedAt"=now() WHERE id=$1', task["roomId"])
            if task["type"] == "HOUSEKEEPING" and current_status == "IN_INSPECTION" and payload.status == "IN_PROGRESS" and task["roomId"]:
                await conn.execute(
                    'UPDATE rooms SET "operationalState"=\'DIRTY\', "updatedAt"=now() WHERE id=$1 AND "operationalState"=\'IN_INSPECTION\'',
                    task["roomId"],
                )
            if task["type"] == "HOUSEKEEPING" and payload.status == "DONE" and task["roomId"]:
                if room_state != "IN_INSPECTION":
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "HOUSEKEEPING_ROOM_NOT_IN_INSPECTION", "room_state": room_state},
                    )
                await conn.execute('UPDATE rooms SET "operationalState"=\'CLEAN\', "updatedAt"=now() WHERE id=$1', task["roomId"])
            if task["type"] == "MAINTENANCE" and payload.status in {"DONE", "CANCELLED"} and task["roomId"]:
                maintenance_result = await settle_terminal_maintenance_room(
                    conn,
                    pid,
                    task["roomId"],
                    task_id,
                    user["id"],
                )

            await conn.execute(
                '''UPDATE operational_tasks SET status=$1::"OperationalTaskStatus",
                   "completedAt"=CASE WHEN $1='DONE' THEN now() ELSE NULL END, "updatedAt"=now() WHERE id=$2''',
                payload.status, task_id,
            )
            after_payload = {"from_status": current_status, "status": payload.status}
            if maintenance_result:
                after_payload.update(maintenance_result)
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'STATUS_CHANGE','OperationalTask',$4,'OPS','SUCCESS',$5::jsonb,now())''',
                uuid.uuid4(), pid, user["id"], str(task_id), __import__("json").dumps(after_payload),
            )
    return {"id": str(task_id), "status": payload.status, **(maintenance_result or {})}


@router.patch("/rooms/{room_id}/state")
async def change_room_state(
    room_id: uuid.UUID,
    payload: RoomStatePatch,
    request: Request,
    user: dict[str, Any] = Depends(require_roles("OWNER", "MANAGER")),
):
    if payload.state not in ROOM_STATES:
        raise HTTPException(status_code=422, detail="Unknown room state")
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        result = await conn.execute(
            '''UPDATE rooms SET "operationalState"=$1::"RoomOperationalState", "updatedAt"=now()
               WHERE id=$2 AND "propertyId"=$3''',
            payload.state, room_id, pid,
        )
        if result.endswith("0"):
            raise HTTPException(status_code=404, detail="Room not found")
    return {"room_id": str(room_id), "state": payload.state}
