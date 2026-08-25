import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/booking", tags=["admin-reservation-detail"])
manager_access = require_roles("OWNER", "MANAGER")


@router.get("/reservations/{reservation_id}")
async def reservation_detail(
    reservation_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await conn.fetchval("SELECT id FROM properties WHERE code=$1", user["property_code"])
        if not pid:
            raise HTTPException(status_code=503, detail="Property not loaded")

        row = await conn.fetchrow(
            '''
            SELECT r.id,r."bookingNumber",r.status::text AS status,r."checkIn",r."checkOut",
                   r.adults,r.children,r."totalKgs",r.notes,r."createdAt",r."updatedAt",
                   g.id AS guest_id,g."firstName",g."lastName",g.phone,g.email,
                   rr.id AS request_id,rr.source AS request_source,rr."guestName" AS request_guest_name,
                   room.id AS room_id,room.code AS room_code,room."operationalState"::text AS room_state,
                   rt.code AS room_type_code,rt.name AS room_type_name,rt."areaLabel" AS room_type_area
            FROM reservations r
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            LEFT JOIN reservation_requests rr ON rr.id=r."requestId"
            LEFT JOIN inventory_blocks ib ON ib."reservationId"=r.id AND ib.active=true AND ib."blockType"='RESERVATION'
            LEFT JOIN rooms room ON room.id=ib."roomId"
            LEFT JOIN room_types rt ON rt.id=room."roomTypeId"
            WHERE r.id=$1 AND r."propertyId"=$2
            ORDER BY ib."createdAt" ASC
            LIMIT 1
            ''',
            reservation_id,
            pid,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Reservation not found")

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
            SELECT id,"actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
            FROM audit_logs
            WHERE "propertyId"=$1 AND "resourceId"=ANY($2::text[])
            ORDER BY "createdAt" DESC
            LIMIT 80
            ''',
            pid,
            audit_ids,
        )

        room_tasks = []
        if row["room_id"]:
            room_tasks = await conn.fetch(
                '''
                SELECT t.id,t.type::text AS type,t.status::text AS status,t.priority::text AS priority,
                       t.title,t.description,t."createdAt",t."updatedAt",t."completedAt",
                       u."displayName" AS assigned_to_name
                FROM operational_tasks t
                LEFT JOIN staff_users u ON u.id=t."assignedToId"
                WHERE t."propertyId"=$1 AND t."roomId"=$2
                ORDER BY t."createdAt" DESC
                LIMIT 30
                ''',
                pid,
                row["room_id"],
            )

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
        "room": {
            "id": str(row["room_id"]) if row["room_id"] else None,
            "code": row["room_code"],
            "state": row["room_state"],
            "room_type_code": row["room_type_code"],
            "room_type_name": row["room_type_name"],
            "area": row["room_type_area"],
        },
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
                "after": a["afterJson"],
                "created_at": a["createdAt"],
            }
            for a in audit
        ],
    }
