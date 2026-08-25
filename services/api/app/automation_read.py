import json
import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from .service_auth import require_automation_service

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
RATE_PLAN_CODE = os.environ.get("RATE_PLAN_CODE", "DIRECT_2026_27")
GUEST_FACTS_PATH = Path(__file__).resolve().parent.parent / "data" / "three_crowns_guest_facts.json"

router = APIRouter(prefix="/api/v1/automation/read", tags=["automation-read"])
service_access = require_automation_service


@lru_cache(maxsize=1)
def _guest_facts() -> dict[str, Any]:
    try:
        payload = json.loads(GUEST_FACTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="Guest facts source is unavailable") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=503, detail="Guest facts source is invalid")
    return payload


async def _property(conn):
    row = await conn.fetchrow(
        'SELECT id,code,name,timezone,currency FROM properties WHERE code=$1',
        PROPERTY_CODE,
    )
    if not row:
        raise HTTPException(status_code=503, detail="Property is not loaded")
    return row


@router.get("/hotel-facts")
async def hotel_facts(request: Request, _service: dict[str, Any] = Depends(service_access)):
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn)
        room_count = await conn.fetchval('SELECT COUNT(*) FROM rooms WHERE "propertyId"=$1', prop["id"])
        room_types = await conn.fetch(
            '''
            SELECT rt.code,rt.name,rt."capacityAdults",rt."capacityChildren",rt."areaLabel",
                   COUNT(r.id)::int AS room_count
            FROM room_types rt
            LEFT JOIN rooms r ON r."roomTypeId"=rt.id
            WHERE rt."propertyId"=$1
            GROUP BY rt.id
            ORDER BY rt.name
            ''',
            prop["id"],
        )
        rate_period_count = await conn.fetchval(
            '''SELECT COUNT(*) FROM rate_periods rp
               JOIN rate_plans p ON p.id=rp."ratePlanId"
               WHERE p."propertyId"=$1 AND p.code=$2''',
            prop["id"], RATE_PLAN_CODE,
        )

    return {
        "property": {"code": prop["code"], "name": prop["name"], "timezone": prop["timezone"], "currency": prop["currency"]},
        "inventory": {
            "room_count": room_count,
            "room_type_count": len(room_types),
            "room_types": [
                {
                    "code": row["code"],
                    "name": row["name"],
                    "capacity_adults": row["capacityAdults"],
                    "capacity_children": row["capacityChildren"],
                    "children_capacity_confirmed": row["capacityChildren"] is not None,
                    "area": row["areaLabel"],
                    "room_count": row["room_count"],
                }
                for row in room_types
            ],
        },
        "rates": {
            "rate_plan_code": RATE_PLAN_CODE,
            "rate_period_count": rate_period_count,
            "truth": "Use check-availability for date-specific sellability and price.",
        },
        "reservation_rules": {
            "reservation_request_is_reservation": False,
            "confirmed_prepayment_required_for_valid_reservation": True,
            "unpaid_request_creates_inventory_hold": False,
            "old_two_day_unpaid_booking_rule_active": False,
            "prepayment_amount_rule": "Read required_prepayment_kgs from the current request; client automation must not assume a global percentage.",
        },
        "guest_facts": _guest_facts(),
        "truth_rules": [
            "Availability and price must come from Resort Core.",
            "A ReservationRequest is not a guaranteed reservation.",
            "Do not claim payment is received without a RECEIVED payment fact.",
            "Do not claim a room is booked without a Reservation fact.",
            "Use only CONFIRMED guest facts as certain; PARTIAL/UNKNOWN facts require clarification.",
            "STALE_DO_NOT_USE facts must never drive client replies.",
            "Unknown policy remains unknown rather than being invented.",
        ],
    }


@router.get("/reservation-requests/{request_id}")
async def reservation_request_status(
    request_id: uuid.UUID,
    request: Request,
    _service: dict[str, Any] = Depends(service_access),
):
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn)
        row = await conn.fetchrow(
            '''
            SELECT rr.id,rr.status::text AS status,rr.source,rr."checkIn",rr."checkOut",rr.adults,rr.children,
                   rr."quotedTotalKgs",rr."requiredPrepaymentKgs",rt.code AS room_type_code,rt.name AS room_type_name,
                   r.id AS reservation_id,r."bookingNumber",r.status::text AS reservation_status,r."totalKgs" AS reservation_total_kgs
            FROM reservation_requests rr
            LEFT JOIN room_types rt ON rt.id=rr."desiredRoomTypeId"
            LEFT JOIN reservations r ON r."requestId"=rr.id
            WHERE rr.id=$1 AND rr."propertyId"=$2
            ''',
            request_id, prop["id"],
        )
        if not row:
            raise HTTPException(status_code=404, detail="Reservation request not found")
        payment = await conn.fetchrow(
            '''SELECT
                 COALESCE(SUM(CASE WHEN status='RECEIVED' THEN "amountKgs" ELSE 0 END),0)::int AS received_kgs,
                 COALESCE(SUM(CASE WHEN status='PENDING' THEN "amountKgs" ELSE 0 END),0)::int AS pending_kgs
               FROM payments WHERE "requestId"=$1 OR "reservationId"=$2''',
            request_id, row["reservation_id"],
        )

    reservation = None
    if row["reservation_id"]:
        reservation = {
            "id": str(row["reservation_id"]),
            "booking_number": row["bookingNumber"],
            "status": row["reservation_status"],
            "total_kgs": row["reservation_total_kgs"],
        }
    return {
        "request": {
            "id": str(row["id"]), "status": row["status"], "source": row["source"],
            "check_in": row["checkIn"], "check_out": row["checkOut"],
            "adults": row["adults"], "children": row["children"],
            "room_type_code": row["room_type_code"], "room_type_name": row["room_type_name"],
            "quoted_total_kgs": row["quotedTotalKgs"], "required_prepayment_kgs": row["requiredPrepaymentKgs"],
            "is_reservation": False,
        },
        "payments": {"received_kgs": payment["received_kgs"], "pending_kgs": payment["pending_kgs"]},
        "reservation": reservation,
        "truth": "The request itself is not a reservation. Use the reservation object, when present, for booking truth.",
    }


@router.get("/reservations/{booking_number}")
async def reservation_status(
    booking_number: str,
    request: Request,
    _service: dict[str, Any] = Depends(service_access),
):
    if not booking_number.strip() or len(booking_number) > 80:
        raise HTTPException(status_code=422, detail="Invalid booking number")
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn)
        row = await conn.fetchrow(
            '''
            SELECT r.id,r."bookingNumber",r.status::text AS status,r."checkIn",r."checkOut",r.adults,r.children,r."totalKgs",
                   room.code AS room_code,rt.name AS room_type_name
            FROM reservations r
            LEFT JOIN inventory_blocks ib ON ib."reservationId"=r.id AND ib.active=true AND ib."blockType"='RESERVATION'
            LEFT JOIN rooms room ON room.id=ib."roomId"
            LEFT JOIN room_types rt ON rt.id=room."roomTypeId"
            WHERE r."propertyId"=$1 AND r."bookingNumber"=$2
            ORDER BY ib."createdAt" DESC LIMIT 1
            ''',
            prop["id"], booking_number.strip(),
        )
        if not row:
            raise HTTPException(status_code=404, detail="Reservation not found")
        payment = await conn.fetchrow(
            '''SELECT
                 COALESCE(SUM(CASE WHEN status='RECEIVED' THEN "amountKgs" ELSE 0 END),0)::int AS received_kgs,
                 COALESCE(SUM(CASE WHEN status='PENDING' THEN "amountKgs" ELSE 0 END),0)::int AS pending_kgs
               FROM payments WHERE "reservationId"=$1''',
            row["id"],
        )
    received = payment["received_kgs"]
    return {
        "reservation": {
            "id": str(row["id"]), "booking_number": row["bookingNumber"], "status": row["status"],
            "check_in": row["checkIn"], "check_out": row["checkOut"], "adults": row["adults"], "children": row["children"],
            "total_kgs": row["totalKgs"], "room_code": row["room_code"], "room_type_name": row["room_type_name"],
        },
        "payments": {
            "received_kgs": received, "pending_kgs": payment["pending_kgs"],
            "outstanding_kgs": max(row["totalKgs"] - received, 0),
        },
        "truth": "Stored Resort Core reservation/payment facts only.",
    }
