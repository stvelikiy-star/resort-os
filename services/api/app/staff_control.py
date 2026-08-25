from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/staff", tags=["admin-staff"])
manager_access = require_roles("OWNER", "MANAGER")


@router.get("/overview")
async def staff_overview(
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        prop = await conn.fetchrow(
            'SELECT id,timezone FROM properties WHERE code=$1',
            user["property_code"],
        )
        if not prop:
            raise HTTPException(status_code=503, detail="Property not loaded")
        pid = prop["id"]
        today = await conn.fetchval("SELECT (now() AT TIME ZONE $1)::date", prop["timezone"])

        staff = await conn.fetch(
            '''
            WITH task_stats AS (
              SELECT "assignedToId" AS user_id,
                     count(*) FILTER (WHERE status IN ('OPEN','IN_PROGRESS','IN_INSPECTION'))::int AS active_tasks,
                     count(*) FILTER (
                       WHERE "completedAt" IS NOT NULL
                         AND ("completedAt" AT TIME ZONE $2)::date=$3
                     )::int AS completed_today,
                     count(*) FILTER (
                       WHERE type='HOUSEKEEPING' AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
                     )::int AS housekeeping_active,
                     count(*) FILTER (
                       WHERE type='MAINTENANCE' AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
                     )::int AS maintenance_active
              FROM operational_tasks
              WHERE "propertyId"=$1 AND "assignedToId" IS NOT NULL
              GROUP BY "assignedToId"
            ),
            session_stats AS (
              SELECT "userId" AS user_id,MAX("lastSeenAt") AS last_session_seen_at
              FROM auth_sessions
              WHERE "revokedAt" IS NULL
              GROUP BY "userId"
            )
            SELECT u.id,u.username,u."displayName",u.role::text AS role,u."isActive",
                   u."telegramUserId",u."telegramUsername",u."telegramLinkedAt",u."createdAt",u."updatedAt",
                   COALESCE(ts.active_tasks,0)::int AS active_tasks,
                   COALESCE(ts.completed_today,0)::int AS completed_today,
                   COALESCE(ts.housekeeping_active,0)::int AS housekeeping_active,
                   COALESCE(ts.maintenance_active,0)::int AS maintenance_active,
                   ss.last_session_seen_at
            FROM staff_users u
            LEFT JOIN task_stats ts ON ts.user_id=u.id
            LEFT JOIN session_stats ss ON ss.user_id=u.id
            WHERE u."propertyId"=$1
            ORDER BY
              CASE u.role::text WHEN 'OWNER' THEN 0 WHEN 'MANAGER' THEN 1 WHEN 'MAID' THEN 2 WHEN 'TECHNICIAN' THEN 3 ELSE 4 END,
              u."displayName"
            ''',
            pid, prop["timezone"], today,
        )

        unassigned = await conn.fetchrow(
            '''
            SELECT
              count(*) FILTER (WHERE type='HOUSEKEEPING')::int AS housekeeping,
              count(*) FILTER (WHERE type='MAINTENANCE')::int AS maintenance,
              count(*) FILTER (WHERE type='GUEST_REQUEST')::int AS guest_requests,
              count(*)::int AS total
            FROM operational_tasks
            WHERE "propertyId"=$1
              AND "assignedToId" IS NULL
              AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
            ''',
            pid,
        )

    return {
        "local_date": today,
        "timezone": prop["timezone"],
        "staff": [
            {
                "id": str(row["id"]),
                "username": row["username"],
                "display_name": row["displayName"],
                "role": row["role"],
                "active": row["isActive"],
                "telegram_linked": row["telegramUserId"] is not None,
                "telegram_username": row["telegramUsername"],
                "telegram_linked_at": row["telegramLinkedAt"],
                "active_tasks": row["active_tasks"],
                "completed_today": row["completed_today"],
                "housekeeping_active": row["housekeeping_active"],
                "maintenance_active": row["maintenance_active"],
                "last_session_seen_at": row["last_session_seen_at"],
            }
            for row in staff
        ],
        "unassigned_active_tasks": dict(unassigned),
        "truth": "This is task/session visibility only. It is not an attendance, payroll or employee-performance score.",
    }
