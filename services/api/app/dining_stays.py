import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/dining", tags=["dining-stays"])
access = require_roles("OWNER", "MANAGER", "RECEPTION", "DINING_STAFF")


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


@router.get("/stays")
async def list_dining_stays(
    request: Request,
    query: str | None = Query(default=None),
    include_future_days: int = Query(default=14, ge=0, le=120),
    user: dict[str, Any] = Depends(access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        local_today: date = await conn.fetchval(
            '''SELECT (now() AT TIME ZONE COALESCE(timezone,'Asia/Bishkek'))::date FROM properties WHERE id=$1''', pid,
        )
        rows = await conn.fetch(
            '''SELECT s.id AS stay_id,s.status::text AS stay_status,s."reservationId",r."bookingNumber",
                      r.status::text AS reservation_status,r."checkIn",r."checkOut",r.adults,r.children,
                      g.id AS guest_id,g."firstName",g."lastName",g.phone,room.code AS room_code,
                      COALESCE(count(e.id) FILTER (WHERE e.status='ACTIVE'),0)::int AS entitlement_count
               FROM stays s
               JOIN reservations r ON r.id=s."reservationId"
               JOIN guests g ON g.id=s."guestId"
               LEFT JOIN room_assignments ra ON ra."stayId"=s.id AND ra."endedAt" IS NULL
               LEFT JOIN rooms room ON room.id=ra."roomId"
               LEFT JOIN dining_entitlements e ON e."stayId"=s.id
               WHERE s."propertyId"=$1
                 AND s.status IN ('PENDING','ACTIVE')
                 AND r.status IN ('GUARANTEED','CHECKED_IN')
                 AND r."checkOut" >= $2
                 AND r."checkIn" <= $2 + $3::int
               GROUP BY s.id,s.status,s."reservationId",r."bookingNumber",r.status,r."checkIn",r."checkOut",
                        r.adults,r.children,g.id,g."firstName",g."lastName",g.phone,room.code
               ORDER BY CASE r.status WHEN 'CHECKED_IN' THEN 0 ELSE 1 END,r."checkIn",room.code NULLS LAST,r."bookingNumber"''',
            pid, local_today, include_future_days,
        )
    q = (query or "").strip().lower()
    items = []
    for row in rows:
        guest_name = " ".join(part for part in [row["firstName"], row["lastName"]] if part) or "Гость"
        item = {
            "stay_id": str(row["stay_id"]),
            "stay_status": row["stay_status"],
            "reservation_id": str(row["reservationId"]),
            "reservation_status": row["reservation_status"],
            "booking_number": row["bookingNumber"],
            "check_in": row["checkIn"],
            "check_out": row["checkOut"],
            "adults": row["adults"],
            "children": row["children"],
            "guest_id": str(row["guest_id"]),
            "guest_name": guest_name,
            "phone": row["phone"],
            "room_code": row["room_code"],
            "entitlement_count": row["entitlement_count"],
        }
        if q and not any(q in str(value or "").lower() for value in [guest_name, row["phone"], row["room_code"], row["bookingNumber"]]):
            continue
        items.append(item)
    return {"local_date": local_today, "items": items}
