from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/intelligence", tags=["owner-operations-analytics"])
manager_access = require_roles("OWNER", "MANAGER")
ACTIVE_STATUSES = ("OPEN", "IN_PROGRESS", "IN_INSPECTION")


async def property_context(conn, property_code: str):
    row = await conn.fetchrow(
        'SELECT id,code,name,timezone,currency FROM properties WHERE code=$1',
        property_code,
    )
    if not row:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return row


def summary_item(row) -> dict[str, Any]:
    return {
        "type": row["type"],
        "created_in_period": int(row["created_in_period"] or 0),
        "completed_in_period": int(row["completed_in_period"] or 0),
        "active_now": int(row["active_now"] or 0),
        "urgent_now": int(row["urgent_now"] or 0),
        "avg_completion_minutes": (
            round(float(row["avg_completion_minutes"]), 1)
            if row["avg_completion_minutes"] is not None
            else None
        ),
        "max_completion_minutes": (
            round(float(row["max_completion_minutes"]), 1)
            if row["max_completion_minutes"] is not None
            else None
        ),
    }


@router.get("/operations-performance")
async def operations_performance(
    request: Request,
    from_date: date = Query(),
    to_date: date = Query(),
    user: dict[str, Any] = Depends(manager_access),
):
    if to_date < from_date:
        raise HTTPException(status_code=422, detail="to_date must be on or after from_date")
    if (to_date - from_date).days > 366:
        raise HTTPException(status_code=422, detail="operations analytics range cannot exceed 367 calendar days")
    end_exclusive = to_date + timedelta(days=1)

    async with request.app.state.db.acquire() as conn:
        prop = await property_context(conn, user["property_code"])
        pid = prop["id"]
        timezone = prop["timezone"]
        local_today = await conn.fetchval("SELECT (now() AT TIME ZONE $1)::date", timezone)

        task_rows = await conn.fetch(
            '''
            SELECT type::text AS type,
                   count(*) FILTER (
                     WHERE (("createdAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date >= $2::date
                       AND (("createdAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date < $3::date
                   )::int AS created_in_period,
                   count(*) FILTER (
                     WHERE status='DONE' AND "completedAt" IS NOT NULL
                       AND (("completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date >= $2::date
                       AND (("completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date < $3::date
                   )::int AS completed_in_period,
                   count(*) FILTER (WHERE status IN ('OPEN','IN_PROGRESS','IN_INSPECTION'))::int AS active_now,
                   count(*) FILTER (
                     WHERE priority='URGENT' AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
                   )::int AS urgent_now,
                   AVG(EXTRACT(EPOCH FROM ("completedAt"-"createdAt"))/60.0) FILTER (
                     WHERE status='DONE' AND "completedAt" IS NOT NULL
                       AND (("completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date >= $2::date
                       AND (("completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date < $3::date
                   ) AS avg_completion_minutes,
                   MAX(EXTRACT(EPOCH FROM ("completedAt"-"createdAt"))/60.0) FILTER (
                     WHERE status='DONE' AND "completedAt" IS NOT NULL
                       AND (("completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date >= $2::date
                       AND (("completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date < $3::date
                   ) AS max_completion_minutes
            FROM operational_tasks
            WHERE "propertyId"=$1
            GROUP BY type
            ORDER BY type
            ''',
            pid,
            from_date,
            end_exclusive,
            timezone,
        )
        summaries = {row["type"]: summary_item(row) for row in task_rows}
        empty = {
            "created_in_period": 0,
            "completed_in_period": 0,
            "active_now": 0,
            "urgent_now": 0,
            "avg_completion_minutes": None,
            "max_completion_minutes": None,
        }

        overdue_guest_requests = await conn.fetchval(
            '''
            SELECT count(*)::int
            FROM operational_tasks
            WHERE "propertyId"=$1 AND type='GUEST_REQUEST'
              AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
              AND "serviceDate" IS NOT NULL
              AND "serviceDate" < $2::date
            ''',
            pid,
            local_today,
        )

        guest_services = await conn.fetch(
            '''
            SELECT COALESCE(NULLIF(trim("serviceCode"),''),'UNSPECIFIED') AS service_code,
                   count(*) FILTER (
                     WHERE (("createdAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date >= $2::date
                       AND (("createdAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date < $3::date
                   )::int AS created_in_period,
                   count(*) FILTER (
                     WHERE status='DONE' AND "completedAt" IS NOT NULL
                       AND (("completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date >= $2::date
                       AND (("completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date < $3::date
                   )::int AS completed_in_period,
                   count(*) FILTER (WHERE status IN ('OPEN','IN_PROGRESS','IN_INSPECTION'))::int AS active_now,
                   AVG(EXTRACT(EPOCH FROM ("completedAt"-"createdAt"))/60.0) FILTER (
                     WHERE status='DONE' AND "completedAt" IS NOT NULL
                       AND (("completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date >= $2::date
                       AND (("completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date < $3::date
                   ) AS avg_completion_minutes
            FROM operational_tasks
            WHERE "propertyId"=$1 AND type='GUEST_REQUEST'
            GROUP BY 1
            HAVING count(*) > 0
            ORDER BY created_in_period DESC,active_now DESC,service_code
            ''',
            pid,
            from_date,
            end_exclusive,
            timezone,
        )

        problem_rooms = await conn.fetch(
            '''
            WITH period_maintenance AS (
              SELECT t.*
              FROM operational_tasks t
              WHERE t."propertyId"=$1 AND t.type='MAINTENANCE' AND t."roomId" IS NOT NULL
                AND ((t."createdAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date >= $2::date
                AND ((t."createdAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date < $3::date
            )
            SELECT room.id,room.code,room.name,room."operationalState"::text AS operational_state,
                   count(pm.id)::int AS maintenance_created_in_period,
                   count(pm.id) FILTER (WHERE pm.status='DONE')::int AS completed_from_period,
                   count(pm.id) FILTER (WHERE pm.status IN ('OPEN','IN_PROGRESS','IN_INSPECTION'))::int AS active_from_period,
                   MAX(pm."createdAt") AS last_fault_at
            FROM period_maintenance pm
            JOIN rooms room ON room.id=pm."roomId"
            GROUP BY room.id,room.code,room.name,room."operationalState"
            HAVING count(pm.id) >= 2
            ORDER BY maintenance_created_in_period DESC,last_fault_at DESC,room.code
            LIMIT 30
            ''',
            pid,
            from_date,
            end_exclusive,
            timezone,
        )

        recurring_faults = await conn.fetch(
            '''
            SELECT room.id AS room_id,room.code AS room_code,
                   MIN(t.title) AS title,
                   lower(regexp_replace(trim(t.title),'\\s+',' ','g')) AS normalized_exact_title,
                   count(*)::int AS occurrences,
                   MAX(t."createdAt") AS last_created_at
            FROM operational_tasks t
            JOIN rooms room ON room.id=t."roomId"
            WHERE t."propertyId"=$1 AND t.type='MAINTENANCE' AND t."roomId" IS NOT NULL
              AND ((t."createdAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date >= $2::date
              AND ((t."createdAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date < $3::date
            GROUP BY room.id,room.code,lower(regexp_replace(trim(t.title),'\\s+',' ','g'))
            HAVING count(*) >= 2
            ORDER BY occurrences DESC,last_created_at DESC,room.code
            LIMIT 50
            ''',
            pid,
            from_date,
            end_exclusive,
            timezone,
        )

        staff_rows = await conn.fetch(
            '''
            SELECT u.id,u."displayName",u.role::text AS role,t.type::text AS task_type,
                   count(t.id) FILTER (
                     WHERE t.status='DONE' AND t."completedAt" IS NOT NULL
                       AND ((t."completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date >= $2::date
                       AND ((t."completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date < $3::date
                   )::int AS completed_in_period,
                   count(t.id) FILTER (WHERE t.status IN ('OPEN','IN_PROGRESS','IN_INSPECTION'))::int AS active_now,
                   AVG(EXTRACT(EPOCH FROM (t."completedAt"-t."createdAt"))/60.0) FILTER (
                     WHERE t.status='DONE' AND t."completedAt" IS NOT NULL
                       AND ((t."completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date >= $2::date
                       AND ((t."completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date < $3::date
                   ) AS avg_completion_minutes
            FROM staff_users u
            JOIN operational_tasks t ON t."assignedToId"=u.id AND t.type IN ('HOUSEKEEPING','MAINTENANCE')
            WHERE u."propertyId"=$1 AND u.role IN ('MAID','TECHNICIAN')
            GROUP BY u.id,u."displayName",u.role,t.type
            HAVING count(t.id) FILTER (
                     WHERE t.status='DONE' AND t."completedAt" IS NOT NULL
                       AND ((t."completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date >= $2::date
                       AND ((t."completedAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date < $3::date
                   ) > 0
                OR count(t.id) FILTER (WHERE t.status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')) > 0
            ORDER BY completed_in_period DESC,active_now DESC,u."displayName",task_type
            ''',
            pid,
            from_date,
            end_exclusive,
            timezone,
        )

    guest_summary = dict(empty) | summaries.get("GUEST_REQUEST", {})
    housekeeping = dict(empty) | summaries.get("HOUSEKEEPING", {})
    maintenance = dict(empty) | summaries.get("MAINTENANCE", {})

    return {
        "property": {
            "code": prop["code"],
            "name": prop["name"],
            "timezone": timezone,
            "currency": prop["currency"],
            "local_date": local_today,
        },
        "range": {
            "from": from_date,
            "to": to_date,
            "days": (to_date - from_date).days + 1,
        },
        "guest_services": guest_summary | {
            "past_due_date_active": int(overdue_guest_requests or 0),
            "by_service": [
                {
                    "service_code": row["service_code"],
                    "created_in_period": int(row["created_in_period"] or 0),
                    "completed_in_period": int(row["completed_in_period"] or 0),
                    "active_now": int(row["active_now"] or 0),
                    "avg_completion_minutes": (
                        round(float(row["avg_completion_minutes"]), 1)
                        if row["avg_completion_minutes"] is not None
                        else None
                    ),
                }
                for row in guest_services
            ],
        },
        "guest_service_sla": {
            "status": "NOT_CONFIGURED",
            "configured": False,
            "target_minutes": None,
            "breach_count": None,
            "observed_avg_completion_minutes": guest_summary.get("avg_completion_minutes"),
            "due_date_overdue_active": int(overdue_guest_requests or 0),
        },
        "housekeeping": housekeeping,
        "maintenance": maintenance,
        "problem_rooms": [
            {
                "room_id": str(row["id"]),
                "room_code": row["code"],
                "room_name": row["name"],
                "operational_state": row["operational_state"],
                "maintenance_created_in_period": int(row["maintenance_created_in_period"] or 0),
                "completed_from_period": int(row["completed_from_period"] or 0),
                "active_from_period": int(row["active_from_period"] or 0),
                "last_fault_at": row["last_fault_at"],
            }
            for row in problem_rooms
        ],
        "recurring_faults": [
            {
                "room_id": str(row["room_id"]),
                "room_code": row["room_code"],
                "title": row["title"],
                "normalized_exact_title": row["normalized_exact_title"],
                "occurrences": int(row["occurrences"] or 0),
                "last_created_at": row["last_created_at"],
            }
            for row in recurring_faults
        ],
        "staff_performance": [
            {
                "staff_id": str(row["id"]),
                "display_name": row["displayName"],
                "role": row["role"],
                "task_type": row["task_type"],
                "completed_in_period": int(row["completed_in_period"] or 0),
                "active_now": int(row["active_now"] or 0),
                "avg_completion_minutes": (
                    round(float(row["avg_completion_minutes"]), 1)
                    if row["avg_completion_minutes"] is not None
                    else None
                ),
            }
            for row in staff_rows
        ],
        "truth": {
            "time": "Operational timestamps are stored as UTC-naive PostgreSQL TIMESTAMP values and are converted to the property's local timezone before calendar-period classification.",
            "sla": "No guest-service SLA threshold is configured in Resort Core, so no breach KPI is fabricated. Due-date overdue counts only requests whose stored serviceDate is before the current hotel-local date.",
            "performance": "Completion-time metrics are observed durations from OperationalTask.createdAt to completedAt for DONE tasks completed in the selected period.",
            "problem_rooms": "Problem rooms are factual rooms with at least two MAINTENANCE tasks created in the selected period.",
            "recurring_faults": "Recurring faults require the same physical room and the same normalized exact maintenance title at least twice. No semantic or AI similarity is inferred.",
        },
    }
