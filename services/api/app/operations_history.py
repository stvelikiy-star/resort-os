import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/ops", tags=["operations-history"])
manager_access = require_roles("OWNER", "MANAGER")


@router.get("/tasks/{task_id}/history")
async def task_history(
    task_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        property_id = await conn.fetchval("SELECT id FROM properties WHERE code=$1", user["property_code"])
        if not property_id:
            raise HTTPException(status_code=503, detail="Property not loaded")

        task = await conn.fetchrow(
            '''
            SELECT t.id,t.type::text AS type,t.status::text AS status,t.title,r.code AS room_code
            FROM operational_tasks t
            LEFT JOIN rooms r ON r.id=t."roomId"
            WHERE t.id=$1 AND t."propertyId"=$2
            ''',
            task_id, property_id,
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        rows = await conn.fetch(
            '''
            SELECT a.id,a."actorType",a."actorId",a.action,a.source,a.result,a."afterJson",a."createdAt",
                   u."displayName" AS actor_name,u.role::text AS actor_role
            FROM audit_logs a
            LEFT JOIN staff_users u
              ON u."propertyId"=$1 AND u.id::text=a."actorId"
            WHERE a."propertyId"=$1
              AND a.resource='OperationalTask'
              AND a."resourceId"=$2
            ORDER BY a."createdAt",a.id
            LIMIT 500
            ''',
            property_id, str(task_id),
        )

    return {
        "task": {
            "id": str(task["id"]),
            "type": task["type"],
            "status": task["status"],
            "title": task["title"],
            "room_code": task["room_code"],
        },
        "history": [
            {
                "id": str(row["id"]),
                "actor_type": row["actorType"],
                "actor_id": row["actorId"],
                "actor_name": row["actor_name"],
                "actor_role": row["actor_role"],
                "action": row["action"],
                "source": row["source"],
                "result": row["result"],
                "after": row["afterJson"],
                "created_at": row["createdAt"],
            }
            for row in rows
        ],
    }
