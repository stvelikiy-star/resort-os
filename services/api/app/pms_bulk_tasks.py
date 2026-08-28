import json
import uuid
from typing import Any, Literal

from asyncpg.exceptions import UniqueViolationError
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/pms", tags=["admin-pms-bulk"])
manager_access = require_roles("OWNER", "MANAGER")


class BulkTaskItem(BaseModel):
    room_id: uuid.UUID
    type: Literal["HOUSEKEEPING", "MAINTENANCE"]
    priority: Literal["LOW", "NORMAL", "HIGH", "URGENT"] = "NORMAL"
    title: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=4000)


class BulkTaskPayload(BaseModel):
    items: list[BulkTaskItem] = Field(min_length=1, max_length=100)
    source: str = Field(default="PMS_BULK", min_length=2, max_length=60)


@router.post("/tasks/bulk-create")
async def bulk_create_tasks(
    payload: BulkTaskPayload,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    room_ids = sorted({item.room_id for item in payload.items}, key=str)
    try:
        async with request.app.state.db.acquire() as conn:
            async with conn.transaction():
                prop_id = await conn.fetchval(
                    "SELECT id FROM properties WHERE code=$1", user["property_code"]
                )
                if not prop_id:
                    raise HTTPException(status_code=503, detail="Property not loaded")

                rooms = await conn.fetch(
                    '''
                    SELECT id,code,"operationalState"::text AS state
                    FROM rooms
                    WHERE "propertyId"=$1 AND id=ANY($2::uuid[])
                    ORDER BY code,id
                    FOR UPDATE
                    ''',
                    prop_id,
                    room_ids,
                )
                room_by_id = {row["id"]: row for row in rooms}
                missing = [str(room_id) for room_id in room_ids if room_id not in room_by_id]
                if missing:
                    raise HTTPException(status_code=422, detail={"code": "ROOM_NOT_FOUND", "room_ids": missing})

                created: list[dict[str, Any]] = []
                skipped: list[dict[str, Any]] = []

                for item in payload.items:
                    room = room_by_id[item.room_id]
                    expected_state = "DIRTY" if item.type == "HOUSEKEEPING" else "TECH_BLOCK"
                    if room["state"] != expected_state:
                        skipped.append(
                            {
                                "room_id": str(item.room_id),
                                "room_code": room["code"],
                                "type": item.type,
                                "room_state": room["state"],
                                "expected_room_state": expected_state,
                                "reason": "ROOM_STATE_CHANGED",
                            }
                        )
                        continue

                    existing = await conn.fetchrow(
                        '''
                        SELECT id,status::text AS status
                        FROM operational_tasks
                        WHERE "roomId"=$1 AND type=$2::"OperationalTaskType"
                          AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
                        ORDER BY "createdAt" DESC
                        LIMIT 1
                        ''',
                        item.room_id,
                        item.type,
                    )
                    if existing:
                        skipped.append(
                            {
                                "room_id": str(item.room_id),
                                "room_code": room["code"],
                                "type": item.type,
                                "existing_task_id": str(existing["id"]),
                                "existing_status": existing["status"],
                                "reason": "ACTIVE_TASK_EXISTS",
                            }
                        )
                        continue

                    task_id = uuid.uuid4()
                    await conn.execute(
                        '''
                        INSERT INTO operational_tasks (
                          id,"propertyId","roomId",type,status,priority,title,description,
                          "createdByType","createdById",source,"createdAt","updatedAt"
                        ) VALUES ($1,$2,$3,$4::"OperationalTaskType",'OPEN',$5::"OperationalTaskPriority",
                          $6,$7,'STAFF',$8,$9,now(),now())
                        ''',
                        task_id,
                        prop_id,
                        item.room_id,
                        item.type,
                        item.priority,
                        item.title,
                        item.description,
                        user["id"],
                        payload.source,
                    )

                    after = {
                        "room_id": str(item.room_id),
                        "room_code": room["code"],
                        "type": item.type,
                        "status": "OPEN",
                        "priority": item.priority,
                        "title": item.title,
                        "room_state": room["state"],
                    }
                    await conn.execute(
                        '''
                        INSERT INTO audit_logs (
                          id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,
                          "afterJson","createdAt"
                        ) VALUES ($1,$2,'STAFF',$3,'CREATE','OperationalTask',$4,$5,'SUCCESS',$6::jsonb,now())
                        ''',
                        uuid.uuid4(),
                        prop_id,
                        user["id"],
                        str(task_id),
                        payload.source,
                        json.dumps(after),
                    )
                    created.append({"id": str(task_id), **after})

                return {
                    "ok": True,
                    "created": created,
                    "skipped": skipped,
                    "created_count": len(created),
                    "skipped_count": len(skipped),
                    "message": "Rooms were locked in deterministic order. Room state and active same-room/same-type tasks were rechecked under lock; stale or duplicate items were skipped.",
                }
    except UniqueViolationError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ACTIVE_TASK_EXISTS_RACE",
                "message": "Another manager or automation created an active task before commit; the bulk transaction was rolled back.",
            },
        ) from exc
