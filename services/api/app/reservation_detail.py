import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/booking", tags=["admin-reservation-detail"])
reception_access = require_roles("OWNER", "MANAGER", "RECEPTION")


def _select_working_room(status: str, schedule, local_today):
    if not schedule:
        return None
    if status == "CHECKED_IN":
        active = next(
            (row for row in schedule if row["startDate"] <= local_today < row["endDate"]),
            None,
        )
        if active:
            return active
        checkout_boundary = next(
            (row for row in reversed(schedule) if row["endDate"] == local_today),
            None,
        )
        if checkout_boundary:
            return checkout_boundary
        return schedule[-1]
    if status == "CHECKED_OUT":
        return schedule[-1]
    return schedule[0]


@router.get("/reservations/{reservation_id}")
async def reservation_detail(
    reservation_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(reception_access),
):
    async with request.app.state.db.acquire() as conn:
        prop = await conn.fetchrow(
            "SELECT id,timezone FROM properties WHERE code=$1",
            user["property_code"],
        )
        if not prop:
            raise HTTPException(status_code=503, detail="Property not loaded")
        pid = prop["id"]
        local_today = await conn.fetchval(
            "SELECT (now() AT TIME ZONE $1)::date",
            prop["timezone"],
        )

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
            pid,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Reservation not found")

        schedule = await conn.fetch(
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
            ORDER BY ib."startDate",ib."endDate",room.code
            ''',
            reservation_id,
        )
        working_room = _select_working_room(row["status"], schedule, local_today)

        payments = await conn.fetch(
            '''
            SELECT id,"amountKgs",method,status::text AS status,provider,"externalRef","paidAt","createdAt"
            FROM payments
            WHERE "reservationId"=$1
            ORDER BY "createdAt" ASC
            ''',
            reservation_id,
        )

        total_paid = sum(int(p["amountKgs"]) for p in payments if p["status"] == "RECEIVED")
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
            LIMIT 100
            ''',
            pid,
            audit_ids,
        )

        room_ids = sorted({item["roomId"] for item in schedule}, key=str)
        room_tasks = []
        if room_ids:
            room_tasks = await conn.fetch(
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
                pid,
                room_ids,
            )

    return {
        "local_date": local_today,
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
        "room": None if not working_room else {
            "id": str(working_room["roomId"]),
            "code": working_room["room_code"],
            "state": working_room["room_state"],
            "room_type_code": working_room["room_type_code"],
            "room_type_name": working_room["room_type_name"],
            "area": working_room["room_type_area"],
            "segment_start": working_room["startDate"],
            "segment_end": working_room["endDate"],
        },
        "schedule": [
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
                "is_working_room": bool(working_room and item["id"] == working_room["id"]),
            }
            for item in schedule
        ],
        "finance": {
            "total_kgs": int(row["totalKgs"]),
            "paid_kgs": total_paid,
            "remaining_kgs": remaining,
            "payments": [
                {
                    "id": str(p["id"]),
                    "amount_kgs": int(p["amountKgs"]),
                    "method": p["method"],
                    "status": p["status"],
                    "provider": p["provider"],
                    "external_ref": p["externalRef"],
                    "paid_at": p["paidAt"],
                    "created_at": p["createdAt"],
                }
                for p in payments
            ],
        },
        "room_tasks": [
            {
                "id": str(t["id"]),
                "room_id": str(t["roomId"]),
                "room_code": t["room_code"],
                "type": t["type"],
                "status": t["status"],
                "priority": t["priority"],
                "title": t["title"],
                "description": t["description"],
                "assigned_to_name": t["assigned_to_name"],
                "created_at": t["createdAt"],
                "updated_at": t["updatedAt"],
                "completed_at": t["completedAt"],
            }
            for t in room_tasks
        ],
        "audit": [
            {
                "id": str(a["id"]),
                "actor_type": a["actorType"],
                "actor_id": a["actorId"],
                "action": a["action"],
                "resource": a["resource"],
                "resource_id": a["resourceId"],
                "source": a["source"],
                "result": a["result"],
                "before": a["beforeJson"],
                "after": a["afterJson"],
                "created_at": a["createdAt"],
            }
            for a in audit
        ],
    }
