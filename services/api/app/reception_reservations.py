from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/reception", tags=["admin-reception"])
manager_access = require_roles("OWNER", "MANAGER")


@router.get("/reservations")
async def list_reception_reservations(
    request: Request,
    limit: int = Query(default=250, ge=1, le=500),
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        prop = await conn.fetchrow(
            'SELECT id,timezone FROM properties WHERE code=$1',
            user["property_code"],
        )
        if not prop:
            raise HTTPException(status_code=503, detail="Property not loaded")
        local_today = await conn.fetchval(
            "SELECT (now() AT TIME ZONE $1)::date",
            prop["timezone"],
        )

        rows = await conn.fetch(
            '''
            SELECT r.id,r."bookingNumber",r.status::text AS status,r."checkIn",r."checkOut",
                   r.adults,r.children,r."totalKgs",g."firstName",g.phone,
                   selected.room_code,selected.room_type_name,selected.room_state,
                   COALESCE(seg.segment_count,0)::int AS schedule_segments
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
                "totalKgs": row["totalKgs"],
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
        "truth": "One row per Reservation. Display room is selected from the active room schedule according to stay status and hotel-local date.",
    }
