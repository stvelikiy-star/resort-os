import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/reception", tags=["admin-reception"])
reception_access = require_roles("OWNER", "ADMIN", "MANAGER", "RECEPTION")


async def property_context(conn, property_code: str):
    prop = await conn.fetchrow(
        'SELECT id,timezone FROM properties WHERE code=$1', property_code
    )
    if not prop:
        raise HTTPException(status_code=503, detail="Property not loaded")
    local_today = await conn.fetchval(
        "SELECT (now() AT TIME ZONE $1)::date", prop["timezone"]
    )
    return prop, local_today


@router.get("/reservations")
async def list_reception_reservations(
    request: Request,
    limit: int = Query(default=250, ge=1, le=500),
    user: dict[str, Any] = Depends(reception_access),
):
    async with request.app.state.db.acquire() as conn:
        prop, local_today = await property_context(conn, user["property_code"])
        rows = await conn.fetch(
            '''
            SELECT r.id,r."bookingNumber",r.status::text AS status,r."checkIn",r."checkOut",
                   r.adults,r.children,r."totalKgs",g."firstName",g.phone,
                   selected.room_code,selected.room_type_name,selected.room_state,
                   COALESCE(seg.segment_count,0)::int AS schedule_segments,
                   COALESCE(pay.paid_kgs,0)::bigint AS paid_kgs
            FROM reservations r
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            LEFT JOIN LATERAL (
              SELECT room.code AS room_code,
                     rt.name AS room_type_name,
                     room."operationalState"::text AS room_state,
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
                  WHEN r.status='CHECKED_IN' AND ib."endDate" = $2::date THEN 1
                  WHEN r.status='GUARANTEED' AND ib."startDate" = r."checkIn" THEN 0
                  WHEN r.status='CHECKED_OUT' AND ib."endDate" = r."checkOut" THEN 0
                  ELSE 2
                END,
                CASE WHEN r.status='CHECKED_OUT' THEN ib."endDate" END DESC,
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
            ORDER BY
              CASE r.status::text WHEN 'CHECKED_IN' THEN 0 WHEN 'GUARANTEED' THEN 1 ELSE 2 END,
              r."checkIn",r."createdAt" DESC
            LIMIT $3
            ''',
            prop["id"],
            local_today,
            limit,
        )

    return {
        "local_date": local_today,
        "items": [
            {
                "id": str(row["id"]),
                "bookingNumber": row["bookingNumber"],
                "status": row["status"],
                "checkIn": row["checkIn"],
                "checkOut": row["checkOut"],
                "adults": row["adults"],
                "children": row["children"],
                "totalKgs": int(row["totalKgs"]),
                "paidKgs": int(row["paid_kgs"]),
                "remainingKgs": max(int(row["totalKgs"]) - int(row["paid_kgs"]), 0),
                "firstName": row["firstName"],
                "phone": row["phone"],
                "room_code": row["room_code"],
                "room_type_name": row["room_type_name"],
                "room_state": row["room_state"],
                "schedule_segments": row["schedule_segments"],
                "has_room_move": row["schedule_segments"] > 1,
            }
            for row in rows
        ],
        "truth": "One row per Reservation. Display room is selected from the active room schedule according to stay status and hotel-local date. Payment fields include only staff-recorded RECEIVED facts in Resort Core.",
    }


def choose_display_segment(status: str, schedule: list[dict[str, Any]], local_today):
    if not schedule:
        return None
    if status == "CHECKED_IN":
        active = next(
            (
                item for item in schedule
                if item["start"] <= local_today < item["end"]
            ),
            None,
        )
        if active:
            return active
        ending = next((item for item in schedule if item["end"] == local_today), None)
        if ending:
            return ending
    if status == "GUARANTEED":
        return schedule[0]
    return schedule[-1]


@router.get("/reservations/{reservation_id}")
async def reception_reservation_detail(
    reservation_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(reception_access),
):
    async with request.app.state.db.acquire() as conn:
        prop, local_today = await property_context(conn, user["property_code"])
        row = await conn.fetchrow(
            '''
            SELECT r.id,r."bookingNumber",r.status::text AS status,r."checkIn",r."checkOut",
                   r.adults,r.children,r."totalKgs",r.notes,r."createdAt",r."updatedAt",
                   g.id AS guest_id,g."firstName",g."lastName",g.phone,g.email,
                   rr.id AS request_id,rr.source AS request_source,rr."guestName" AS request_guest_name
            FROM reservations r
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            LEFT JOIN reservation_requests rr ON rr.id=r."requestId"
            WHERE r.id=$1 AND r."propertyId"=$2
            ''',
            reservation_id,
            prop["id"],
        )
        if not row:
            raise HTTPException(status_code=404, detail="Reservation not found")

        schedule_rows = await conn.fetch(
            '''
            SELECT ib.id,ib."roomId",ib."startDate",ib."endDate",
                   room.code AS room_code,room."operationalState"::text AS room_state,
                   rt.code AS room_type_code,rt.name AS room_type_name,rt."areaLabel" AS room_type_area
            FROM inventory_blocks ib
            JOIN rooms room ON room.id=ib."roomId"
            JOIN room_types rt ON rt.id=room."roomTypeId"
            WHERE ib."reservationId"=$1
              AND ib.active=true
              AND ib."blockType"='RESERVATION'
            ORDER BY ib."startDate",ib."endDate"
            ''',
            reservation_id,
        )
        schedule = [
            {
                "inventory_block_id": str(item["id"]),
                "room_id": str(item["roomId"]),
                "room_code": item["room_code"],
                "room_state": item["room_state"],
                "room_type_code": item["room_type_code"],
                "room_type_name": item["room_type_name"],
                "area": item["room_type_area"],
                "start": item["startDate"],
                "end": item["endDate"],
            }
            for item in schedule_rows
        ]
        display_segment = choose_display_segment(row["status"], schedule, local_today)

        payments = await conn.fetch(
            '''
            SELECT id,"amountKgs",method,status::text AS status,provider,"externalRef","paidAt","createdAt"
            FROM payments
            WHERE "reservationId"=$1
            ORDER BY "createdAt" ASC
            ''',
            reservation_id,
        )
        total_paid = sum(int(item["amountKgs"]) for item in payments if item["status"] == "RECEIVED")
        remaining = max(int(row["totalKgs"]) - total_paid, 0)

        audit_ids = [str(reservation_id)]
        if row["request_id"]:
            audit_ids.append(str(row["request_id"]))
        audit = await conn.fetch(
            '''
            SELECT id,"actorType","actorId",action,resource,"resourceId",source,result,
                   "beforeJson","afterJson","createdAt"
            FROM audit_logs
            WHERE "propertyId"=$1 AND "resourceId"=ANY($2::text[])
            ORDER BY "createdAt" DESC
            LIMIT 120
            ''',
            prop["id"],
            audit_ids,
        )

        room_ids = [uuid.UUID(item["room_id"]) for item in schedule]
        tasks = []
        if room_ids:
            tasks = await conn.fetch(
                '''
                SELECT t.id,t."roomId",room.code AS room_code,
                       t.type::text AS type,t.status::text AS status,t.priority::text AS priority,
                       t.title,t.description,t."createdAt",t."updatedAt",t."completedAt",
                       u."displayName" AS assigned_to_name
                FROM operational_tasks t
                JOIN rooms room ON room.id=t."roomId"
                LEFT JOIN staff_users u ON u.id=t."assignedToId"
                WHERE t."propertyId"=$1 AND t."roomId"=ANY($2::uuid[])
                ORDER BY t."createdAt" DESC
                LIMIT 80
                ''',
                prop["id"],
                room_ids,
            )

    room = {
        "id": display_segment["room_id"] if display_segment else None,
        "code": display_segment["room_code"] if display_segment else None,
        "state": display_segment["room_state"] if display_segment else None,
        "room_type_code": display_segment["room_type_code"] if display_segment else None,
        "room_type_name": display_segment["room_type_name"] if display_segment else None,
        "area": display_segment["area"] if display_segment else None,
    }
    return {
        "reservation": {
            "id": str(row["id"]),
            "booking_number": row["bookingNumber"],
            "status": row["status"],
            "check_in": row["checkIn"],
            "check_out": row["checkOut"],
            "adults": row["adults"],
            "children": row["children"],
            "total_kgs": int(row["totalKgs"]),
            "notes": row["notes"],
            "created_at": row["createdAt"],
            "updated_at": row["updatedAt"],
        },
        "guest": {
            "id": str(row["guest_id"]) if row["guest_id"] else None,
            "first_name": row["firstName"],
            "last_name": row["lastName"],
            "phone": row["phone"],
            "email": row["email"],
        },
        "source": {
            "request_id": str(row["request_id"]) if row["request_id"] else None,
            "channel": row["request_source"],
            "original_guest_name": row["request_guest_name"],
        },
        "room": room,
        "schedule": schedule,
        "has_room_move": len(schedule) > 1,
        "local_date": local_today,
        "finance": {
            "total_kgs": int(row["totalKgs"]),
            "paid_kgs": total_paid,
            "remaining_kgs": remaining,
            "payments": [
                {
                    "id": str(item["id"]),
                    "amount_kgs": int(item["amountKgs"]),
                    "method": item["method"],
                    "status": item["status"],
                    "provider": item["provider"],
                    "external_ref": item["externalRef"],
                    "paid_at": item["paidAt"],
                    "created_at": item["createdAt"],
                }
                for item in payments
            ],
        },
        "room_tasks": [
            {
                "id": str(item["id"]),
                "room_id": str(item["roomId"]),
                "room_code": item["room_code"],
                "type": item["type"],
                "status": item["status"],
                "priority": item["priority"],
                "title": item["title"],
                "description": item["description"],
                "assigned_to_name": item["assigned_to_name"],
                "created_at": item["createdAt"],
                "updated_at": item["updatedAt"],
                "completed_at": item["completedAt"],
            }
            for item in tasks
        ],
        "audit": [
            {
                "id": str(item["id"]),
                "actor_type": item["actorType"],
                "actor_id": item["actorId"],
                "action": item["action"],
                "resource": item["resource"],
                "resource_id": item["resourceId"],
                "source": item["source"],
                "result": item["result"],
                "before": item["beforeJson"],
                "after": item["afterJson"],
                "created_at": item["createdAt"],
            }
            for item in audit
        ],
    }
