import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/dashboard", tags=["admin-dashboard"])
manager_access = require_roles("OWNER", "MANAGER")


async def property_context(conn, property_code: str):
    row = await conn.fetchrow(
        'SELECT id, code, name, timezone, currency FROM properties WHERE code=$1',
        property_code,
    )
    if not row:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return row


@router.get("")
async def manager_dashboard(
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        prop = await property_context(conn, user["property_code"])
        pid: uuid.UUID = prop["id"]
        today = await conn.fetchval("SELECT (now() AT TIME ZONE $1)::date", prop["timezone"])

        room_counts = await conn.fetchrow(
            '''
            SELECT count(*)::int AS total,
                   count(*) FILTER (WHERE "operationalState"='CLEAN')::int AS clean,
                   count(*) FILTER (WHERE "operationalState"='DIRTY')::int AS dirty,
                   count(*) FILTER (WHERE "operationalState"='IN_INSPECTION')::int AS in_inspection,
                   count(*) FILTER (WHERE "operationalState"='TECH_BLOCK')::int AS tech_block,
                   count(*) FILTER (WHERE "operationalState"='UNKNOWN')::int AS unknown
            FROM rooms WHERE "propertyId"=$1
            ''',
            pid,
        )

        stay_counts = await conn.fetchrow(
            '''
            SELECT
              count(*) FILTER (WHERE status='GUARANTEED' AND "checkIn"=$2)::int AS arrivals_today,
              count(*) FILTER (WHERE status='CHECKED_IN' AND "checkOut"=$2)::int AS departures_today,
              count(*) FILTER (WHERE status='CHECKED_IN')::int AS in_house,
              count(*) FILTER (WHERE status='GUARANTEED')::int AS guaranteed
            FROM reservations WHERE "propertyId"=$1
            ''',
            pid,
            today,
        )

        request_counts = await conn.fetchrow(
            '''
            SELECT
              count(*) FILTER (WHERE status='NEW')::int AS new,
              count(*) FILTER (WHERE status='QUOTED')::int AS quoted,
              count(*) FILTER (WHERE status='AWAITING_PREPAYMENT')::int AS awaiting_prepayment,
              count(*) FILTER (WHERE status IN ('NEW','QUOTED','AWAITING_PREPAYMENT'))::int AS active
            FROM reservation_requests WHERE "propertyId"=$1
            ''',
            pid,
        )

        task_counts = await conn.fetchrow(
            '''
            SELECT
              count(*) FILTER (WHERE type='HOUSEKEEPING' AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION'))::int AS housekeeping_active,
              count(*) FILTER (WHERE type='MAINTENANCE' AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION'))::int AS maintenance_active,
              count(*) FILTER (WHERE type='GUEST_REQUEST' AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION'))::int AS guest_requests_active,
              count(*) FILTER (WHERE priority='URGENT' AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION'))::int AS urgent_active
            FROM operational_tasks WHERE "propertyId"=$1
            ''',
            pid,
        )

        communication_counts = await conn.fetchrow(
            '''
            SELECT
              count(*) FILTER (WHERE status NOT IN ('RESOLVED','ARCHIVED'))::int AS active,
              count(*) FILTER (
                WHERE "lastInboundAt" IS NOT NULL
                  AND ("lastOutboundAt" IS NULL OR "lastInboundAt">"lastOutboundAt")
                  AND status NOT IN ('RESOLVED','ARCHIVED')
              )::int AS needs_reply,
              COALESCE(EXTRACT(EPOCH FROM (now()-MIN("lastInboundAt") FILTER (
                WHERE "lastInboundAt" IS NOT NULL
                  AND ("lastOutboundAt" IS NULL OR "lastInboundAt">"lastOutboundAt")
                  AND status NOT IN ('RESOLVED','ARCHIVED')
              ))),0)::bigint AS oldest_waiting_seconds
            FROM conversations WHERE "propertyId"=$1
            ''',
            pid,
        )

        payment_today = await conn.fetchval(
            '''
            SELECT COALESCE(sum(p."amountKgs"),0)::bigint
            FROM payments p
            JOIN reservations r ON r.id=p."reservationId"
            WHERE r."propertyId"=$1
              AND p.status='RECEIVED'
              AND COALESCE(p."paidAt",p."createdAt") IS NOT NULL
              AND (((COALESCE(p."paidAt",p."createdAt") AT TIME ZONE 'UTC') AT TIME ZONE $2)::date)=$3
            ''',
            pid,
            prop["timezone"],
            today,
        )

        active_balance = await conn.fetchrow(
            '''
            WITH paid AS (
              SELECT "reservationId", COALESCE(sum("amountKgs") FILTER (WHERE status='RECEIVED'),0)::bigint AS paid_kgs
              FROM payments
              WHERE "reservationId" IS NOT NULL
              GROUP BY "reservationId"
            )
            SELECT
              COALESCE(sum(r."totalKgs"),0)::bigint AS booked_total_kgs,
              COALESCE(sum(COALESCE(p.paid_kgs,0)),0)::bigint AS paid_kgs,
              COALESCE(sum(GREATEST(r."totalKgs"-COALESCE(p.paid_kgs,0),0)),0)::bigint AS remaining_kgs
            FROM reservations r
            LEFT JOIN paid p ON p."reservationId"=r.id
            WHERE r."propertyId"=$1 AND r.status IN ('GUARANTEED','CHECKED_IN')
            ''',
            pid,
        )

        occupied_rooms = await conn.fetchval(
            '''
            SELECT count(DISTINCT ib."roomId")::int
            FROM inventory_blocks ib
            JOIN reservations r ON r.id=ib."reservationId"
            JOIN rooms room ON room.id=ib."roomId"
            WHERE room."propertyId"=$1
              AND ib.active=true AND ib."blockType"='RESERVATION'
              AND r.status='CHECKED_IN'
            ''',
            pid,
        )

        arrivals = await conn.fetch(
            '''
            SELECT r.id,r."bookingNumber",r."checkIn",r."checkOut",g."firstName",g.phone,room.code AS room_code
            FROM reservations r
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            LEFT JOIN inventory_blocks ib ON ib."reservationId"=r.id AND ib.active=true AND ib."blockType"='RESERVATION'
            LEFT JOIN rooms room ON room.id=ib."roomId"
            WHERE r."propertyId"=$1 AND r.status='GUARANTEED' AND r."checkIn"=$2
            ORDER BY room.code NULLS LAST,r."createdAt"
            LIMIT 50
            ''',
            pid,
            today,
        )

        departures = await conn.fetch(
            '''
            SELECT r.id,r."bookingNumber",r."checkIn",r."checkOut",g."firstName",g.phone,room.code AS room_code
            FROM reservations r
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            LEFT JOIN inventory_blocks ib ON ib."reservationId"=r.id AND ib.active=true AND ib."blockType"='RESERVATION'
            LEFT JOIN rooms room ON room.id=ib."roomId"
            WHERE r."propertyId"=$1 AND r.status='CHECKED_IN' AND r."checkOut"=$2
            ORDER BY room.code NULLS LAST,r."createdAt"
            LIMIT 50
            ''',
            pid,
            today,
        )

        attention_tasks = await conn.fetch(
            '''
            SELECT t.id,t.type::text AS type,t.status::text AS status,t.priority::text AS priority,
                   t.title,t."createdAt",room.code AS room_code,u."displayName" AS assigned_to
            FROM operational_tasks t
            LEFT JOIN rooms room ON room.id=t."roomId"
            LEFT JOIN staff_users u ON u.id=t."assignedToId"
            WHERE t."propertyId"=$1
              AND t.status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
            ORDER BY
              CASE t.priority::text WHEN 'URGENT' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'NORMAL' THEN 2 ELSE 3 END,
              t."createdAt"
            LIMIT 20
            ''',
            pid,
        )

    total_rooms = room_counts["total"] or 0
    occupancy_percent = round((occupied_rooms or 0) * 100 / total_rooms, 1) if total_rooms else 0.0

    def reservation_summary(row):
        return {
            "id": str(row["id"]),
            "booking_number": row["bookingNumber"],
            "guest_name": row["firstName"],
            "phone": row["phone"],
            "room_code": row["room_code"],
            "check_in": row["checkIn"],
            "check_out": row["checkOut"],
        }

    return {
        "property": {
            "code": prop["code"],
            "name": prop["name"],
            "timezone": prop["timezone"],
            "currency": prop["currency"],
            "local_date": today,
        },
        "rooms": dict(room_counts),
        "stays": dict(stay_counts) | {
            "occupied_rooms": occupied_rooms or 0,
            "occupancy_percent": occupancy_percent,
        },
        "requests": dict(request_counts),
        "tasks": dict(task_counts),
        "communications": {
            "active": int(communication_counts["active"] or 0),
            "needs_reply": int(communication_counts["needs_reply"] or 0),
            "oldest_waiting_seconds": int(communication_counts["oldest_waiting_seconds"] or 0),
            "sla_rule": None,
        },
        "finance": {
            "confirmed_payments_today_kgs": int(payment_today or 0),
            "active_reservations_total_kgs": int(active_balance["booked_total_kgs"] or 0),
            "active_reservations_paid_kgs": int(active_balance["paid_kgs"] or 0),
            "active_reservations_remaining_kgs": int(active_balance["remaining_kgs"] or 0),
            "scope_note": "Only hotel reservation payments recorded in Resort Core are included. Calendar classification uses the property timezone over UTC-stored timestamps.",
        },
        "today": {
            "arrivals": [reservation_summary(row) for row in arrivals],
            "departures": [reservation_summary(row) for row in departures],
        },
        "attention_tasks": [
            {
                "id": str(row["id"]),
                "type": row["type"],
                "status": row["status"],
                "priority": row["priority"],
                "title": row["title"],
                "room_code": row["room_code"],
                "assigned_to": row["assigned_to"],
                "created_at": row["createdAt"],
            }
            for row in attention_tasks
        ],
    }
