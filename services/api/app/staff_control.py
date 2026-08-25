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
            SELECT u.id,u.username,u."displayName",u.role::text AS role,u."isActive",
                   u."telegramUserId",u."telegramUsername",u."telegramLinkedAt",u."createdAt",u."updatedAt",
                   COALESCE(count(t.id) FILTER (WHERE t.status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')),0)::int AS active_tasks,
                   COALESCE(count(t.id) FILTER (
                     WHERE t."completedAt" IS NOT NULL
                       AND (t."completedAt" AT TIME ZONE $2)::date=$3
                   ),0)::int AS completed_today,
                   COALESCE(count(t.id) FILTER (
                     WHERE t.type='HOUSEKEEPING' AND t.status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
                   ),0)::int AS housekeeping_active,
                   COALESCE(count(t.id) FILTER (
                     WHERE t.type='MAINTENANCE' AND t.status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
                   ),0)::int AS maintenance_active,
                   MAX(s."lastSeenAt") AS last_session_seen_at
            FROM staff_users u
            LEFT JOIN operational_tasks t ON t."assignedToId"=u.id
            LEFT JOIN auth_sessions s ON s."userId"=u.id AND s."revokedAt" IS NULL
            WHERE u."propertyId"=$1
            GROUP BY u.id
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
