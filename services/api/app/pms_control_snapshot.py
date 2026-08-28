from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/pms", tags=["admin-pms-control"])
manager_access = require_roles("OWNER", "MANAGER")


@router.get("/control-snapshot")
async def control_snapshot(
    request: Request,
    start: date = Query(...),
    end: date = Query(...),
    user: dict[str, Any] = Depends(manager_access),
):
    if start >= end:
        raise HTTPException(status_code=422, detail="start must be before end")
    if (end - start).days > 62:
        raise HTTPException(status_code=422, detail="control snapshot window cannot exceed 62 days")

    async with request.app.state.db.acquire() as conn:
        prop = await conn.fetchrow(
            'SELECT id,timezone FROM properties WHERE code=$1', user["property_code"]
        )
        if not prop:
            raise HTTPException(status_code=503, detail="Property not loaded")

        local_today = await conn.fetchval(
            "SELECT (now() AT TIME ZONE $1)::date", prop["timezone"]
        )
        generated_at = await conn.fetchval("SELECT now()")

        reservations = await conn.fetch(
            '''
            SELECT r.id,r."bookingNumber",r.status::text AS status,r."checkIn",r."checkOut",
                   r.adults,r.children,r."totalKgs",
                   g."firstName",g."lastName",g.phone,g.email,
                   selected.room_id,selected.room_code,selected.room_state,selected.room_type_name,
                   COALESCE(seg.segment_count,0)::int AS schedule_segments,
                   COALESCE(pay.paid_kgs,0)::bigint AS paid_kgs
            FROM reservations r
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            LEFT JOIN LATERAL (
              SELECT room.id AS room_id,
                     room.code AS room_code,
                     room."operationalState"::text AS room_state,
                     rt.name AS room_type_name,
                     ib."startDate",ib."endDate"
              FROM inventory_blocks ib
              JOIN rooms room ON room.id=ib."roomId"
              JOIN room_types rt ON rt.id=room."roomTypeId"
              WHERE ib."reservationId"=r.id
                AND ib.active=true
                AND ib."blockType"='RESERVATION'
              ORDER BY
                CASE
                  WHEN r.status='CHECKED_IN' AND ib."startDate" <= $2::date AND $2::date < ib."endDate" THEN 0
                  WHEN r.status='CHECKED_IN' AND ib."endDate" <= $2::date THEN 1
                  WHEN r.status='GUARANTEED' AND ib."startDate" = r."checkIn" THEN 0
                  ELSE 2
                END,
                CASE
                  WHEN r.status='CHECKED_IN' AND ib."endDate" <= $2::date THEN ib."endDate"
                  ELSE NULL
                END DESC NULLS LAST,
                ib."startDate" ASC
              LIMIT 1
            ) selected ON true
            LEFT JOIN LATERAL (
              SELECT count(*)::int AS segment_count
              FROM inventory_blocks ib2
              WHERE ib2."reservationId"=r.id
                AND ib2.active=true
                AND ib2."blockType"='RESERVATION'
            ) seg ON true
            LEFT JOIN LATERAL (
              SELECT COALESCE(SUM(p."amountKgs") FILTER (WHERE p.status='RECEIVED'),0)::bigint AS paid_kgs
              FROM payments p
              WHERE p."reservationId"=r.id
            ) pay ON true
            WHERE r."propertyId"=$1
              AND (
                r.status='CHECKED_IN'
                OR (
                  r.status='GUARANTEED'
                  AND r."checkOut" > $3::date
                  AND r."checkIn" < $4::date
                )
              )
            ORDER BY
              CASE r.status::text WHEN 'CHECKED_IN' THEN 0 ELSE 1 END,
              r."checkIn",r."createdAt" DESC
            ''',
            prop["id"],
            local_today,
            start,
            end,
        )

        tasks = await conn.fetch(
            '''
            SELECT t.id,t.type::text AS type,t.status::text AS status,t.priority::text AS priority,
                   t.title,t.description,t."roomId",room.code AS room_code,
                   room."operationalState"::text AS room_state,
                   t."assignedToId",staff."displayName" AS assigned_to_name,
                   t.source,t."createdAt",t."updatedAt"
            FROM operational_tasks t
            LEFT JOIN rooms room ON room.id=t."roomId"
            LEFT JOIN staff_users staff ON staff.id=t."assignedToId"
            WHERE t."propertyId"=$1
              AND t.status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
            ORDER BY
              CASE t.priority::text WHEN 'URGENT' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'NORMAL' THEN 2 ELSE 3 END,
              t."createdAt" ASC
            ''',
            prop["id"],
        )

        rooms = await conn.fetch(
            '''
            SELECT room.id,room.code,room.name,
                   room."operationalState"::text AS state,
                   room."buildingOrZone" AS building_or_zone,
                   room."floorLabel" AS floor,
                   rt.code AS room_type_code,rt.name AS room_type_name
            FROM rooms room
            JOIN room_types rt ON rt.id=room."roomTypeId"
            WHERE room."propertyId"=$1
            ORDER BY room.code,room.id
            ''',
            prop["id"],
        )

    reservation_items = []
    for row in reservations:
        total = int(row["totalKgs"])
        paid = int(row["paid_kgs"])
        reservation_items.append(
            {
                "id": str(row["id"]),
                "bookingNumber": row["bookingNumber"],
                "status": row["status"],
                "checkIn": row["checkIn"],
                "checkOut": row["checkOut"],
                "adults": row["adults"],
                "children": row["children"],
                "totalKgs": total,
                "paidKgs": paid,
                "remainingKgs": max(total - paid, 0),
                "firstName": row["firstName"],
                "lastName": row["lastName"],
                "phone": row["phone"],
                "email": row["email"],
                "room_id": str(row["room_id"]) if row["room_id"] else None,
                "room_code": row["room_code"],
                "room_state": row["room_state"],
                "room_type_name": row["room_type_name"],
                "schedule_segments": row["schedule_segments"],
                "has_room_move": row["schedule_segments"] > 1,
            }
        )

    task_items = [
        {
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
        }
        for row in tasks
    ]

    room_items = [
        {
            "id": str(row["id"]),
            "code": row["code"],
            "name": row["name"],
            "state": row["state"],
            "building_or_zone": row["building_or_zone"],
            "floor": row["floor"],
            "room_type_code": row["room_type_code"],
            "room_type_name": row["room_type_name"],
        }
        for row in rooms
    ]
    room_states: dict[str, int] = {}
    for item in room_items:
        room_states[item["state"]] = room_states.get(item["state"], 0) + 1

    debt_total = sum(
        item["remainingKgs"]
        for item in reservation_items
        if item["remainingKgs"] > 0
    )

    return {
        "complete": True,
        "generated_at": generated_at,
        "local_date": local_today,
        "window": {"start": start, "end": end},
        "room_states": room_states,
        "rooms": room_items,
        "reservations": reservation_items,
        "tasks": task_items,
        "summary": {
            "room_count": len(room_items),
            "active_reservations": len(reservation_items),
            "active_tasks": len(task_items),
            "debt_total_kgs": debt_total,
            "unassigned_guaranteed": sum(
                1
                for item in reservation_items
                if item["status"] == "GUARANTEED" and not item["room_id"]
            ),
        },
        "truth": "Complete manager read-model for the requested <=62 day guaranteed window plus all currently CHECKED_IN stays. Reservation/payment truth comes from Resort Core; room assignment comes from active RESERVATION inventory segments; overdue in-house room resolves to the latest completed segment; room state comes from rooms; task truth comes from active operational_tasks.",
    }
