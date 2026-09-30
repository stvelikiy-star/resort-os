import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/pms", tags=["admin-pms-chessboard"])
manager_access = require_roles("OWNER", "MANAGER")


@router.get("/reservations/{reservation_id}/schedule")
async def get_reservation_schedule(
    reservation_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        prop = await conn.fetchrow(
            'SELECT id,timezone,currency FROM properties WHERE code=$1',
            user["property_code"],
        )
        if not prop:
            raise HTTPException(status_code=503, detail="Property not loaded")

        reservation = await conn.fetchrow(
            '''
            SELECT r.id,r."bookingNumber",r.status::text AS status,r."checkIn",r."checkOut",r."totalKgs",
                   r.adults,r.children,to_char(r."updatedAt", 'YYYY-MM-DD"T"HH24:MI:SS.US') AS version,
                   g."firstName",g."lastName",g.phone,g.email
            FROM reservations r
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            WHERE r.id=$1 AND r."propertyId"=$2
            ''',
            reservation_id,
            prop["id"],
        )
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")

        blocks = await conn.fetch(
            '''
            SELECT ib.id,ib."roomId",ib."startDate",ib."endDate",room.code AS room_code,
                   room."operationalState"::text AS room_state,
                   rt.code AS room_type_code,rt.name AS room_type_name
            FROM inventory_blocks ib
            JOIN rooms room ON room.id=ib."roomId"
            JOIN room_types rt ON rt.id=room."roomTypeId"
            WHERE ib."reservationId"=$1 AND ib.active=true AND ib."blockType"='RESERVATION'
            ORDER BY ib."startDate",ib."endDate"
            ''',
            reservation_id,
        )
        local_today = await conn.fetchval(
            "SELECT (now() AT TIME ZONE $1)::date",
            prop["timezone"],
        )

    guest_name = " ".join(
        part for part in [reservation["firstName"], reservation["lastName"]] if part
    ) or None
    return {
        "reservation": {
            "id": str(reservation["id"]),
            "booking_number": reservation["bookingNumber"],
            "status": reservation["status"],
            "check_in": reservation["checkIn"],
            "check_out": reservation["checkOut"],
            "adults": reservation["adults"],
            "children": reservation["children"],
            "stored_total_kgs": reservation["totalKgs"],
            "version": reservation["version"],
        },
        "guest": {
            "name": guest_name,
            "phone": reservation["phone"],
            "email": reservation["email"],
        },
        "schedule": [
            {
                "inventory_block_id": str(row["id"]),
                "room_id": str(row["roomId"]),
                "room_code": row["room_code"],
                "room_state": row["room_state"],
                "room_type_code": row["room_type_code"],
                "room_type_name": row["room_type_name"],
                "start": row["startDate"],
                "end": row["endDate"],
            }
            for row in blocks
        ],
        "local_today": local_today,
        "rules": {
            "checked_in_past_room_history_immutable": True,
            "stored_total_changes_automatically": False,
        },
    }
