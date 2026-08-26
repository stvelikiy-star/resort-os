import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .service_auth import require_automation_service

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")

router = APIRouter(prefix="/api/v1/automation/read", tags=["automation-read"])
service_access = require_automation_service


async def _property_id(conn):
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', PROPERTY_CODE)
    if not value:
        raise HTTPException(status_code=503, detail="Property is not loaded")
    return value


def _normalize_since(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(status_code=422, detail="updated_after must include a timezone offset")
    return value.astimezone(timezone.utc)


def _request_row(row) -> dict[str, Any]:
    nights = max((row["checkOut"] - row["checkIn"]).days, 0)
    received = int(row["received_kgs"] or 0)
    quoted = row["quotedTotalKgs"]
    return {
        "lead_id": str(row["id"]),
        "created_at": row["createdAt"],
        "updated_at": row["sync_updated_at"],
        "channel": row["source"],
        "guest_name": row["guestName"],
        "phone": row["phone"],
        "email": row["email"],
        "check_in": row["checkIn"],
        "check_out": row["checkOut"],
        "nights": nights,
        "adults": row["adults"],
        "children": row["children"],
        "room_type_code": row["room_type_code"],
        "room_type_name": row["room_type_name"],
        "quoted_total_kgs": quoted,
        "status": row["request_status"],
        "booking_id": str(row["reservation_id"]) if row["reservation_id"] else None,
        "booking_number": row["bookingNumber"],
        "booking_status": row["reservation_status"],
        "received_kgs": received,
        "outstanding_kgs": max(int(quoted) - received, 0) if quoted is not None else None,
        "notes": row["notes"],
    }


def _reservation_row(row) -> dict[str, Any]:
    received = int(row["received_kgs"] or 0)
    total = int(row["totalKgs"])
    return {
        "booking_id": str(row["id"]),
        "lead_id": str(row["requestId"]) if row["requestId"] else None,
        "booking_number": row["bookingNumber"],
        "created_at": row["createdAt"],
        "updated_at": row["sync_updated_at"],
        "guest_name": row["guest_name"],
        "phone": row["phone"],
        "email": row["email"],
        "check_in": row["checkIn"],
        "check_out": row["checkOut"],
        "nights": max((row["checkOut"] - row["checkIn"]).days, 0),
        "adults": row["adults"],
        "children": row["children"],
        "total_kgs": total,
        "received_kgs": received,
        "outstanding_kgs": max(total - received, 0),
        "status": row["reservation_status"],
        "source": row["request_source"],
    }


def _payment_row(row) -> dict[str, Any]:
    return {
        "payment_id": str(row["id"]),
        "lead_id": str(row["requestId"]) if row["requestId"] else None,
        "booking_id": str(row["reservationId"]) if row["reservationId"] else None,
        "booking_number": row["bookingNumber"],
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
        "paid_at": row["paidAt"],
        "guest_name": row["guest_name"],
        "amount_kgs": int(row["amountKgs"]),
        "method": row["method"],
        "status": row["payment_status"],
        "provider": row["provider"],
        "external_ref": row["externalRef"],
    }


@router.get("/crm-feed")
async def crm_feed(
    request: Request,
    updated_after: datetime | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=1000),
    _service: dict[str, Any] = Depends(service_access),
):
    """Return an authoritative, read-only CRM mirror feed for n8n/Google Sheets.

    The feed intentionally exposes no CRM write-back operation. Resort Core remains
    the source of truth; external CRM rows are mirrors and must be upserted by the
    stable IDs returned here.
    """

    since = _normalize_since(updated_after)
    generated_at = datetime.now(timezone.utc)

    async with request.app.state.db.acquire() as conn:
        property_id = await _property_id(conn)

        request_rows = await conn.fetch(
            '''
            SELECT rr.id,rr.source,rr."guestName",rr.phone,rr.email,rr."checkIn",rr."checkOut",
                   rr.adults,rr.children,rr."quotedTotalKgs",rr.notes,rr."createdAt",
                   rr.status::text AS request_status,
                   rt.code AS room_type_code,rt.name AS room_type_name,
                   r.id AS reservation_id,r."bookingNumber",r.status::text AS reservation_status,
                   COALESCE(pay.received_kgs,0)::int AS received_kgs,
                   GREATEST(
                     rr."updatedAt",
                     COALESCE(r."updatedAt",rr."updatedAt"),
                     COALESCE(pay.updated_at,rr."updatedAt")
                   ) AS sync_updated_at
            FROM reservation_requests rr
            LEFT JOIN room_types rt ON rt.id=rr."desiredRoomTypeId"
            LEFT JOIN reservations r ON r."requestId"=rr.id
            LEFT JOIN LATERAL (
              SELECT
                COALESCE(SUM(CASE WHEN p.status='RECEIVED' THEN p."amountKgs" ELSE 0 END),0)::int AS received_kgs,
                MAX(p."updatedAt") AS updated_at
              FROM payments p
              WHERE p."requestId"=rr.id OR (r.id IS NOT NULL AND p."reservationId"=r.id)
            ) pay ON true
            WHERE rr."propertyId"=$1
              AND ($2::timestamptz IS NULL OR GREATEST(
                    rr."updatedAt",
                    COALESCE(r."updatedAt",rr."updatedAt"),
                    COALESCE(pay.updated_at,rr."updatedAt")
                  ) > $2)
            ORDER BY sync_updated_at ASC, rr.id ASC
            LIMIT $3
            ''',
            property_id,
            since,
            limit + 1,
        )

        reservation_rows = await conn.fetch(
            '''
            SELECT r.id,r."requestId",r."bookingNumber",r."checkIn",r."checkOut",r.adults,r.children,
                   r."totalKgs",r."createdAt",r.status::text AS reservation_status,
                   g."firstName" AS guest_name,g.phone,g.email,
                   rr.source AS request_source,
                   COALESCE(pay.received_kgs,0)::int AS received_kgs,
                   GREATEST(r."updatedAt",COALESCE(pay.updated_at,r."updatedAt")) AS sync_updated_at
            FROM reservations r
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            LEFT JOIN reservation_requests rr ON rr.id=r."requestId"
            LEFT JOIN LATERAL (
              SELECT
                COALESCE(SUM(CASE WHEN p.status='RECEIVED' THEN p."amountKgs" ELSE 0 END),0)::int AS received_kgs,
                MAX(p."updatedAt") AS updated_at
              FROM payments p
              WHERE p."reservationId"=r.id
            ) pay ON true
            WHERE r."propertyId"=$1
              AND ($2::timestamptz IS NULL OR GREATEST(r."updatedAt",COALESCE(pay.updated_at,r."updatedAt")) > $2)
            ORDER BY sync_updated_at ASC, r.id ASC
            LIMIT $3
            ''',
            property_id,
            since,
            limit + 1,
        )

        payment_rows = await conn.fetch(
            '''
            SELECT p.id,p."requestId",p."reservationId",p."amountKgs",p.method,
                   p.status::text AS payment_status,p.provider,p."externalRef",p."paidAt",
                   p."createdAt",p."updatedAt",r."bookingNumber",
                   COALESCE(g."firstName",rr."guestName") AS guest_name
            FROM payments p
            LEFT JOIN reservation_requests rr ON rr.id=p."requestId"
            LEFT JOIN reservations r ON r.id=p."reservationId"
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            WHERE COALESCE(rr."propertyId",r."propertyId")=$1
              AND ($2::timestamptz IS NULL OR p."updatedAt" > $2)
            ORDER BY p."updatedAt" ASC,p.id ASC
            LIMIT $3
            ''',
            property_id,
            since,
            limit + 1,
        )

    requests_truncated = len(request_rows) > limit
    reservations_truncated = len(reservation_rows) > limit
    payments_truncated = len(payment_rows) > limit

    return {
        "contract_version": "1.0",
        "property_code": PROPERTY_CODE,
        "generated_at": generated_at,
        "updated_after": since,
        "source_of_truth": "RESORT_CORE",
        "mirror_policy": "Google Sheets CRM is a read-only operational mirror. Upsert by stable IDs; do not write booking/payment truth back into Core from the sheet.",
        "sync_guidance": "Use an overlap window on the next poll and upsert by IDs. Advance the external high-water mark only when all truncated flags are false.",
        "requests": {
            "items": [_request_row(row) for row in request_rows[:limit]],
            "truncated": requests_truncated,
        },
        "reservations": {
            "items": [_reservation_row(row) for row in reservation_rows[:limit]],
            "truncated": reservations_truncated,
        },
        "payments": {
            "items": [_payment_row(row) for row in payment_rows[:limit]],
            "truncated": payments_truncated,
        },
    }
