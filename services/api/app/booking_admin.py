import os
import secrets
import uuid
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from .auth import require_roles
from .guest_identity import resolve_or_create_guest
from .payment_idempotency import (
    ensure_same_payment_payload,
    lock_payment_identity,
    normalize_optional_text,
    normalize_required_text,
)

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
RATE_PLAN_CODE = os.environ.get("RATE_PLAN_CODE", "DIRECT_2026_27")
MANUAL_PAYMENT_PROVIDER = "MANAGER_MANUAL"

router = APIRouter(prefix="/api/v1/admin/booking", tags=["admin-booking"])
manager_access = require_roles("OWNER", "MANAGER")


class QuotePayload(BaseModel):
    room_type_code: str = Field(min_length=2, max_length=80)


class ConfirmPaymentPayload(BaseModel):
    amount_kgs: int = Field(gt=0)
    method: str = Field(min_length=2, max_length=60)
    external_ref: str | None = Field(default=None, max_length=160)
    idempotency_key: str = Field(min_length=8, max_length=180)


async def property_id(conn) -> uuid.UUID:
    value = await conn.fetchval("SELECT id FROM properties WHERE code = $1", PROPERTY_CODE)
    if not value:
        raise HTTPException(status_code=503, detail="Property seed is not loaded")
    return value


def nights_between(check_in: date, check_out: date) -> list[date]:
    return [check_in + timedelta(days=i) for i in range((check_out - check_in).days)]


async def price_room_type(conn, room_type_id: uuid.UUID, check_in: date, check_out: date) -> dict[str, Any]:
    nights = nights_between(check_in, check_out)
    rows = await conn.fetch(
        '''
        SELECT rp."validFrom", rp."validTo", rp."priceKgs", rp."saleStatus", rp.label
        FROM rate_periods rp
        JOIN rate_plans p ON p.id = rp."ratePlanId"
        WHERE rp."roomTypeId" = $1
          AND p.code = $2
          AND rp."validFrom" <= $4
          AND rp."validTo" >= $3
        ORDER BY rp."validFrom"
        ''',
        room_type_id,
        RATE_PLAN_CODE,
        check_in,
        check_out - timedelta(days=1),
    )
    total = 0
    for night in nights:
        matched = next((row for row in rows if row["validFrom"] <= night <= row["validTo"]), None)
        if not matched:
            return {"sellable": False, "reason": "RATE_MISSING", "total_kgs": None}
        if str(matched["saleStatus"]) != "OPEN" or matched["priceKgs"] <= 0:
            return {"sellable": False, "reason": "RATE_REQUIRES_CONFIRMATION", "total_kgs": None}
        total += matched["priceKgs"]
    return {"sellable": True, "reason": None, "total_kgs": total}


async def serialize_request(conn, request_id: uuid.UUID) -> dict[str, Any] | None:
    row = await conn.fetchrow(
        '''
        SELECT rr.id, rr.status::text AS status, rr.source, rr."guestName", rr.phone, rr.email,
               rr."checkIn", rr."checkOut", rr.adults, rr.children, rr."quotedTotalKgs",
               rr."requiredPrepaymentKgs", rr.notes, rr."createdAt", rr."updatedAt",
               rt.code AS room_type_code, rt.name AS room_type_name,
               r.id AS reservation_id, r."bookingNumber", r.status::text AS reservation_status
        FROM reservation_requests rr
        LEFT JOIN room_types rt ON rt.id = rr."desiredRoomTypeId"
        LEFT JOIN reservations r ON r."requestId" = rr.id
        WHERE rr.id = $1
        ''',
        request_id,
    )
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "status": row["status"],
        "source": row["source"],
        "guest_name": row["guestName"],
        "phone": row["phone"],
        "email": row["email"],
        "check_in": row["checkIn"],
        "check_out": row["checkOut"],
        "adults": row["adults"],
        "children": row["children"],
        "room_type_code": row["room_type_code"],
        "room_type_name": row["room_type_name"],
        "quoted_total_kgs": row["quotedTotalKgs"],
        "required_prepayment_kgs": row["requiredPrepaymentKgs"],
        "prepayment_decided_by_manager": True,
        "notes": row["notes"],
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
        "reservation": None if not row["reservation_id"] else {
            "id": str(row["reservation_id"]),
            "booking_number": row["bookingNumber"],
            "status": row["reservation_status"],
        },
    }


@router.get("/requests")
async def list_requests(
    request: Request,
    request_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=250),
    _user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn)
        rows = await conn.fetch(
            '''
            SELECT rr.id
            FROM reservation_requests rr
            WHERE rr."propertyId" = $1
              AND ($2::text IS NULL OR rr.status::text = $2)
            ORDER BY rr."createdAt" DESC
            LIMIT $3
            ''',
            pid,
            request_status,
            limit,
        )
        items = [await serialize_request(conn, row["id"]) for row in rows]
    return {"items": [item for item in items if item is not None]}


@router.post("/requests/{request_id}/quote")
async def quote_request(
    request_id: uuid.UUID,
    payload: QuotePayload,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn)
            rr = await conn.fetchrow(
                '''SELECT * FROM reservation_requests WHERE id = $1 AND "propertyId" = $2 FOR UPDATE''',
                request_id,
                pid,
            )
            if not rr:
                raise HTTPException(status_code=404, detail="Request not found")
            if str(rr["status"]) in {"CONVERTED", "CANCELLED", "REJECTED", "EXPIRED"}:
                raise HTTPException(status_code=409, detail="Request cannot be quoted in current state")

            room_type = await conn.fetchrow(
                '''SELECT id, code, name, "capacityAdults" FROM room_types WHERE "propertyId" = $1 AND code = $2''',
                pid,
                payload.room_type_code,
            )
            if not room_type:
                raise HTTPException(status_code=422, detail="Unknown room type")
            if room_type["capacityAdults"] < rr["adults"]:
                raise HTTPException(status_code=409, detail="Room type capacity is below requested adults")

            pricing = await price_room_type(conn, room_type["id"], rr["checkIn"], rr["checkOut"])
            if not pricing["sellable"]:
                raise HTTPException(status_code=409, detail=pricing["reason"])

            available_count = await conn.fetchval(
                '''
                SELECT count(*)
                FROM rooms r
                WHERE r."propertyId" = $1
                  AND r."roomTypeId" = $2
                  AND r."operationalState" <> 'TECH_BLOCK'
                  AND NOT EXISTS (
                    SELECT 1 FROM inventory_blocks ib
                    WHERE ib."roomId" = r.id AND ib.active = true
                      AND daterange(ib."startDate", ib."endDate", '[)')
                        && daterange($3::date, $4::date, '[)')
                  )
                ''',
                pid,
                room_type["id"],
                rr["checkIn"],
                rr["checkOut"],
            )
            if available_count < 1:
                raise HTTPException(status_code=409, detail="No room available for requested dates")

            total = pricing["total_kgs"]
            await conn.execute(
                '''
                UPDATE reservation_requests
                SET status = 'QUOTED', "desiredRoomTypeId" = $1,
                    "quotedTotalKgs" = $2, "requiredPrepaymentKgs" = NULL, "updatedAt" = now()
                WHERE id = $3
                ''',
                room_type["id"],
                total,
                request_id,
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (id, "propertyId", "actorType", "actorId", action, resource,
                  "resourceId", source, result, "afterJson", "createdAt")
                VALUES ($1,$2,'STAFF',$3,'QUOTE','ReservationRequest',$4,'PMS','SUCCESS',
                  jsonb_build_object('room_type_code',$5::text,'total_kgs',$6::integer,'prepayment_rule','MANAGER_DECIDES'),now())
                ''',
                uuid.uuid4(), pid, user["id"], str(request_id), payload.room_type_code, total,
            )
        item = await serialize_request(conn, request_id)
    return item


@router.post("/requests/{request_id}/confirm-payment", status_code=status.HTTP_201_CREATED)
async def confirm_payment_and_reserve(
    request_id: uuid.UUID,
    payload: ConfirmPaymentPayload,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    method = normalize_required_text(payload.method)
    external_ref = normalize_optional_text(payload.external_ref)

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            await lock_payment_identity(conn, payload.idempotency_key, external_ref)

            existing = await conn.fetchrow(
                '''
                SELECT p.id,p."requestId",p."reservationId",p."amountKgs",p.method,p."externalRef",
                       r."bookingNumber",r.status::text AS reservation_status
                FROM payments p
                LEFT JOIN reservations r ON r.id=p."reservationId"
                WHERE p."idempotencyKey"=$1
                ''',
                payload.idempotency_key,
            )
            if existing:
                if existing["requestId"] != request_id:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "IDEMPOTENCY_CONFLICT",
                            "message": "This idempotency key belongs to another reservation request.",
                        },
                    )
                ensure_same_payment_payload(
                    existing,
                    amount_kgs=payload.amount_kgs,
                    method=method,
                    external_ref=external_ref,
                )
                return {
                    "idempotent_replay": True,
                    "payment_id": str(existing["id"]),
                    "reservation_id": str(existing["reservationId"]) if existing["reservationId"] else None,
                    "booking_number": existing["bookingNumber"],
                    "reservation_status": existing["reservation_status"],
                }

            if external_ref:
                reference_payment = await conn.fetchrow(
                    '''
                    SELECT id,"requestId","reservationId","amountKgs",method,status::text AS status
                    FROM payments
                    WHERE provider=$1 AND "externalRef"=$2
                    ''',
                    MANUAL_PAYMENT_PROVIDER,
                    external_ref,
                )
                if reference_payment:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "PAYMENT_EXTERNAL_REF_CONFLICT",
                            "message": "This manager payment reference is already recorded.",
                            "payment_id": str(reference_payment["id"]),
                            "request_id": str(reference_payment["requestId"]) if reference_payment["requestId"] else None,
                            "reservation_id": str(reference_payment["reservationId"]) if reference_payment["reservationId"] else None,
                            "amount_kgs": int(reference_payment["amountKgs"]),
                            "method": reference_payment["method"],
                            "status": reference_payment["status"],
                        },
                    )

            pid = await property_id(conn)
            rr = await conn.fetchrow(
                '''
                SELECT rr.*,rt.code AS room_type_code
                FROM reservation_requests rr
                LEFT JOIN room_types rt ON rt.id=rr."desiredRoomTypeId"
                WHERE rr.id=$1 AND rr."propertyId"=$2
                FOR UPDATE OF rr
                ''',
                request_id,
                pid,
            )
            if not rr:
                raise HTTPException(status_code=404, detail="Request not found")

            already = await conn.fetchrow(
                '''SELECT id,"bookingNumber",status::text AS status FROM reservations WHERE "requestId"=$1''',
                request_id,
            )
            if already:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "REQUEST_ALREADY_CONVERTED",
                        "message": "This reservation request was already converted by another payment operation.",
                        "reservation_id": str(already["id"]),
                        "booking_number": already["bookingNumber"],
                        "reservation_status": already["status"],
                    },
                )

            if str(rr["status"]) not in {"QUOTED", "AWAITING_PREPAYMENT"}:
                raise HTTPException(status_code=409, detail="Request must be quoted before manager confirms prepayment")
            if rr["desiredRoomTypeId"] is None or rr["quotedTotalKgs"] is None:
                raise HTTPException(status_code=409, detail="Request has no complete quote")

            manager_required_payment_kgs = (
                int(rr["requiredPrepaymentKgs"]) if rr["requiredPrepaymentKgs"] is not None else None
            )
            if manager_required_payment_kgs is not None and payload.amount_kgs < manager_required_payment_kgs:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "PAYMENT_BELOW_MANAGER_REQUIREMENT",
                        "message": "Recorded payment is below the manager-set required prepayment. Change the requirement first if an exception is approved.",
                        "required_prepayment_kgs": manager_required_payment_kgs,
                        "received_kgs": payload.amount_kgs,
                    },
                )

            candidates = await conn.fetch(
                '''
                SELECT id,code FROM rooms
                WHERE "propertyId"=$1 AND "roomTypeId"=$2 AND "operationalState"<>'TECH_BLOCK'
                ORDER BY code
                FOR UPDATE
                ''',
                pid,
                rr["desiredRoomTypeId"],
            )
            chosen = None
            for room in candidates:
                blocked = await conn.fetchval(
                    '''
                    SELECT EXISTS(
                      SELECT 1 FROM inventory_blocks ib
                      WHERE ib."roomId"=$1 AND ib.active=true
                        AND daterange(ib."startDate",ib."endDate",'[)') && daterange($2::date,$3::date,'[)')
                    )
                    ''',
                    room["id"],rr["checkIn"],rr["checkOut"],
                )
                if not blocked:
                    chosen = room
                    break
            if not chosen:
                raise HTTPException(status_code=409, detail="Availability changed; no room remains")

            identity = await resolve_or_create_guest(
                conn,
                property_id=pid,
                guest_name=rr["guestName"],
                phone=rr["phone"],
                email=rr["email"],
            )
            guest_id = identity["guest_id"]
            reservation_id = uuid.uuid4()
            payment_id = uuid.uuid4()
            booking_number = f"TC-{date.today():%y%m%d}-{secrets.token_hex(3).upper()}"

            await conn.execute(
                '''
                INSERT INTO reservations (id,"propertyId","requestId","bookingNumber","primaryGuestId",
                  status,"checkIn","checkOut",adults,children,"totalKgs",notes,"createdAt","updatedAt")
                VALUES ($1,$2,$3,$4,$5,'GUARANTEED',$6,$7,$8,$9,$10,$11,now(),now())
                ''',
                reservation_id,pid,request_id,booking_number,guest_id,
                rr["checkIn"],rr["checkOut"],rr["adults"],rr["children"],rr["quotedTotalKgs"],rr["notes"],
            )
            await conn.execute(
                '''
                INSERT INTO inventory_blocks (id,"roomId","reservationId","blockType","startDate","endDate",active,reason,"createdAt","updatedAt")
                VALUES ($1,$2,$3,'RESERVATION',$4,$5,true,$6,now(),now())
                ''',
                uuid.uuid4(),chosen["id"],reservation_id,rr["checkIn"],rr["checkOut"],booking_number,
            )
            await conn.execute(
                '''
                INSERT INTO payments (id,"requestId","reservationId","amountKgs",method,status,provider,
                  "externalRef","idempotencyKey","paidAt","createdAt","updatedAt")
                VALUES ($1,$2,$3,$4,$5,'RECEIVED',$6,$7,$8,now(),now(),now())
                ''',
                payment_id,request_id,reservation_id,payload.amount_kgs,method,
                MANUAL_PAYMENT_PROVIDER,external_ref,payload.idempotency_key,
            )
            await conn.execute(
                '''
                UPDATE reservation_requests
                SET status='CONVERTED',
                    "requiredPrepaymentKgs"=COALESCE("requiredPrepaymentKgs",$2),
                    "updatedAt"=now()
                WHERE id=$1
                ''',
                request_id,
                payload.amount_kgs,
            )
            effective_requirement = manager_required_payment_kgs or payload.amount_kgs
            await conn.execute(
                '''
                INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                VALUES ($1,$2,'STAFF',$3,'MANAGER_CONFIRM_PAYMENT_AND_RESERVE','Reservation',$4,'PMS','SUCCESS',
                  jsonb_build_object('booking_number',$5::text,'room_code',$6::text,'payment_id',$7::text,
                    'manager_confirmed_payment_kgs',$8::integer,'required_prepayment_kgs',$9::integer,
                    'payment_provider',$10::text,'guest_id',$11::text,'guest_identity_created',$12::boolean,
                    'guest_identity_match',$13::text),now())
                ''',
                uuid.uuid4(),pid,user["id"],str(reservation_id),booking_number,chosen["code"],str(payment_id),
                payload.amount_kgs,effective_requirement,MANUAL_PAYMENT_PROVIDER,str(guest_id),
                identity["created"],identity["matched_by"],
            )

    return {
        "idempotent_replay": False,
        "reservation_id": str(reservation_id),
        "booking_number": booking_number,
        "reservation_status": "GUARANTEED",
        "room_code": chosen["code"],
        "payment_id": str(payment_id),
        "manager_confirmed_payment_kgs": payload.amount_kgs,
        "required_prepayment_kgs": effective_requirement,
        "manager_requirement_applied": manager_required_payment_kgs is not None,
        "payment_collection": "MANAGER_MANUAL",
        "guest_id": str(guest_id),
        "guest_identity_created": identity["created"],
        "guest_identity_match": identity["matched_by"],
    }


@router.get("/reservations")
async def list_reservations(
    request: Request,
    limit: int = Query(default=100, ge=1, le=250),
    _user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn)
        rows = await conn.fetch(
            '''
            SELECT r.id,r."bookingNumber",r.status::text AS status,r."checkIn",r."checkOut",
                   r.adults,r.children,r."totalKgs",g."firstName",g.phone,
                   room.code AS room_code,rt.name AS room_type_name
            FROM reservations r
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            LEFT JOIN inventory_blocks ib ON ib."reservationId"=r.id AND ib."blockType"='RESERVATION' AND ib.active=true
            LEFT JOIN rooms room ON room.id=ib."roomId"
            LEFT JOIN room_types rt ON rt.id=room."roomTypeId"
            WHERE r."propertyId"=$1
            ORDER BY r."createdAt" DESC
            LIMIT $2
            ''',
            pid,limit,
        )
    return {"items":[dict(row)|{"id":str(row["id"])} for row in rows]}
