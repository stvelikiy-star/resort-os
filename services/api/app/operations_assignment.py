import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .auth import require_roles

router = APIRouter(prefix="/api/v1/ops", tags=["operations-assignment"])
manager_access = require_roles("OWNER", "MANAGER")


class AssigneePatch(BaseModel):
    assigned_to_id: uuid.UUID | None = None


EXPECTED_ROLE = {
    "HOUSEKEEPING": "MAID",
    "MAINTENANCE": "TECHNICIAN",
}


@router.patch("/tasks/{task_id}/assignee")
async def assign_task(
    task_id: uuid.UUID,
    payload: AssigneePatch,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            property_id = await conn.fetchval("SELECT id FROM properties WHERE code=$1", user["property_code"])
            if not property_id:
                raise HTTPException(status_code=503, detail="Property not loaded")

            task = await conn.fetchrow(
                '''
                SELECT id,type::text AS type,status::text AS status,"assignedToId"
                FROM operational_tasks
                WHERE id=$1 AND "propertyId"=$2
                FOR UPDATE
                ''',
                task_id, property_id,
            )
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            if task["status"] in {"DONE", "CANCELLED"}:
                raise HTTPException(status_code=409, detail="Completed/cancelled task cannot be reassigned")

            expected_role = EXPECTED_ROLE.get(task["type"])
            if payload.assigned_to_id is not None and not expected_role:
                raise HTTPException(status_code=422, detail="Direct assignee policy is not defined for this task type")

            assignee = None
            if payload.assigned_to_id is not None:
                assignee = await conn.fetchrow(
                    '''
                    SELECT id,"displayName",role::text AS role
                    FROM staff_users
                    WHERE id=$1 AND "propertyId"=$2 AND "isActive"=true
                    ''',
                    payload.assigned_to_id, property_id,
                )
                if not assignee:
                    raise HTTPException(status_code=422, detail="Active assignee not found")
                if assignee["role"] != expected_role:
                    raise HTTPException(status_code=422, detail=f"Assignee must have role {expected_role}")

            previous = task["assignedToId"]
            if previous == payload.assigned_to_id:
                return {
                    "id": str(task_id),
                    "assigned_to_id": str(previous) if previous else None,
                    "assigned_to_name": assignee["displayName"] if assignee else None,
                    "idempotent": True,
                }

            await conn.execute(
                'UPDATE operational_tasks SET "assignedToId"=$1,"updatedAt"=now() WHERE id=$2',
                payload.assigned_to_id, task_id,
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"beforeJson","afterJson","createdAt"
                ) VALUES (
                  $1,$2,'STAFF',$3,$4,'OperationalTask',$5,'PMS','SUCCESS',
                  jsonb_build_object('assigned_to_id',$6::text),
                  jsonb_build_object('assigned_to_id',$7::text,'assigned_to_name',$8::text),now()
                )
                ''',
                uuid.uuid4(), property_id, user["id"],
                "UNASSIGN" if payload.assigned_to_id is None else "ASSIGN",
                str(task_id), str(previous) if previous else None,
                str(payload.assigned_to_id) if payload.assigned_to_id else None,
                assignee["displayName"] if assignee else None,
            )

    return {
        "id": str(task_id),
        "assigned_to_id": str(payload.assigned_to_id) if payload.assigned_to_id else None,
        "assigned_to_name": assignee["displayName"] if assignee else None,
        "idempotent": False,
    }
