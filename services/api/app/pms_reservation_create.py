import re
import secrets
import uuid
from datetime import date
from typing import Any

from asyncpg.exceptions import ExclusionViolationError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from .auth import require_roles
from .guest_identity import resolve_or_create_guest
from .main import price_room_type


router = APIRouter(prefix="/api/v1/admin/pms/reservations", tags=["admin-pms-owner-grid"])
manager_access = require_roles("OWNER", "MANAGER")

# Owner-approved rule: these categories never accept extra places.
EXTRA_BED_DENIED_ROOM_TYPES = {
    "DOUBLE_STANDARD_BASEMENT",
    "DOUBLE_IMPROVED",
    "TWO_ROOM_STANDARD",
}
RETURNING_GUEST_DISCOUNT_PERCENT = 10


class GridReservationPreviewPayload(BaseModel):
    room_id: uuid.UUID
    check_in: date
    check_out: date
    adults: int = Field(default=2, ge=1, le=20)
    children: int = Field(default=0, ge=0, le=20)
    manager_total_kgs: int | None = Field(default=None, gt=0)
    guest_phone: str | None = Field(default=None, max_length=40)
    extra_bed_count: int = Field(default=0, ge=0, le=10)
    extra_bed_unit_kgs: int | None = Field(default=None, gt=0)
    discount_percent: int | None = Field(default=None, ge=0, le=100)
    discount_reason: str | None = Field(default=None, max_length=500)
    agent_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        if (self.check_out - self.check_in).days > 60:
            raise ValueError("maximum stay is 60 nights")
        if self.extra_bed_count > 0 and self.extra_bed_unit_kgs is None:
            raise ValueError("extra_bed_unit_kgs is required when extra_bed_count > 0")
        return self


class GridReservationCommitPayload(GridReservationPreviewPayload):
    guest_name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=5, max_length=40)
    email: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)
    expected_total_kgs: int = Field(gt=0)
    expected_pricing_source: str = Field(pattern="^(CORE_RATE|MANAGER_OVERRIDE)$")


async def property_context(conn, property_code: str):
    row = await conn.fetchrow(
        'SELECT id,timezone,currency FROM properties WHERE code=$1',
        property_code,
    )
    if not row:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return row


async def load_room(conn, property_id: uuid.UUID, room_id: uuid.UUID, lock: bool = False):
    suffix = " FOR UPDATE OF room" if lock else ""
    return await conn.fetchrow(
        f'''
        SELECT room.id,room.code,room.name,room."operationalState"::text AS operational_state,
               room."bedConfiguration",room."buildingOrZone",room."floorLabel",room."roomTypeId",
               rt.code AS room_type_code,rt.name AS room_type_name,
               rt."capacityAdults",rt."capacityChildren"
        FROM rooms room
        JOIN room_types rt ON rt.id=room."roomTypeId"
        WHERE room.id=$1 AND room."propertyId"=$2{suffix}
        ''',
        room_id,
        property_id,
    )


async def find_conflicts(conn, room_id: uuid.UUID, check_in: date, check_out: date):
    rows = await conn.fetch(
        '''
        SELECT ib.id,ib."blockType"::text AS block_type,ib."startDate",ib."endDate",ib.reason,
               r."bookingNumber"
        FROM inventory_blocks ib
        LEFT JOIN reservations r ON r.id=ib."reservationId"
        WHERE ib."roomId"=$1 AND ib.active=true
          AND daterange(ib."startDate",ib."endDate",'[)')
              && daterange($2::date,$3::date,'[)')
        ORDER BY ib."startDate",ib."endDate"
        ''',
        room_id,
        check_in,
        check_out,
    )
    return [
        {
            "inventory_block_id": str(row["id"]),
            "block_type": row["block_type"],
            "start": row["startDate"].isoformat(),
            "end": row["endDate"].isoformat(),
            "booking_number": row["bookingNumber"],
            "reason": row["reason"],
        }
        for row in rows
    ]


def _phone_digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


async def returning_guest_context(conn, property_id: uuid.UUID, phone: str | None) -> dict[str, Any]:
    digits = _phone_digits(phone)
    if len(digits) < 5:
        return {"returning_guest": False, "previous_stays": 0, "auto_discount_percent": 0}
    previous = await conn.fetchval(
        '''
        SELECT count(*)::int
        FROM reservations r
        JOIN guests g ON g.id=r."primaryGuestId"
        WHERE r."propertyId"=$1 AND r.status='CHECKED_OUT'
          AND regexp_replace(coalesce(g.phone,''),'\\D','','g')=$2
        ''',
        property_id,
        digits,
    ) or 0
    return {
        "returning_guest": previous > 0,
        "previous_stays": previous,
        "auto_discount_percent": RETURNING_GUEST_DISCOUNT_PERCENT if previous > 0 else 0,
    }


async def load_agent(conn, property_id: uuid.UUID, agent_id: uuid.UUID | None):
    if not agent_id:
        return None
    row = await conn.fetchrow(
        '''SELECT id,name,status FROM booking_agents WHERE id=$1 AND "propertyId"=$2''',
        agent_id,
        property_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail={"code": "AGENT_NOT_FOUND"})
    if row["status"] != "ACTIVE":
        raise HTTPException(status_code=409, detail={"code": "AGENT_INACTIVE", "agent_name": row["name"]})
    return row


def pricing_result(
    core_pricing: dict[str, Any],
    manager_total_kgs: int | None,
    *,
    nights: int,
    extra_bed_count: int,
    extra_bed_unit_kgs: int | None,
    discount_percent: int,
    returning_guest: dict[str, Any],
):
    if manager_total_kgs is not None:
        source = "MANAGER_OVERRIDE"
        base_total = manager_total_kgs
        sellable = True
        reason = None
    else:
        source = "CORE_RATE"
        base_total = core_pricing.get("total_kgs")
        sellable = bool(core_pricing.get("sellable"))
        reason = core_pricing.get("reason")

    extra_beds_total = extra_bed_count * int(extra_bed_unit_kgs or 0) * nights
    subtotal = (int(base_total) + extra_beds_total) if base_total is not None else None
    discount_kgs = round(subtotal * discount_percent / 100) if subtotal is not None else 0
    final_total = subtotal - discount_kgs if subtotal is not None else None

    return {
        "source": source,
        "sellable": sellable,
        "reason": reason,
        "total_kgs": final_total,
        "base_total_kgs": base_total,
        "extra_beds_total_kgs": extra_beds_total,
        "subtotal_kgs": subtotal,
        "discount_percent": discount_percent,
        "discount_kgs": discount_kgs,
        "returning_guest": returning_guest["returning_guest"],
        "previous_stays": returning_guest["previous_stays"],
        "auto_discount_percent": returning_guest["auto_discount_percent"],
        "core_total_kgs": core_pricing.get("total_kgs"),
        "core_sellable": bool(core_pricing.get("sellable")),
        "core_reason": core_pricing.get("reason"),
        "nights": core_pricing.get("nights", []),
    }


async def build_preview(conn, property_id: uuid.UUID, payload: GridReservationPreviewPayload, *, lock: bool = False):
    room = await load_room(conn, property_id, payload.room_id, lock=lock)
    if not room:
        raise HTTPException(status_code=404, detail={"code": "ROOM_NOT_FOUND"})
    if room["operational_state"] == "TECH_BLOCK":
        raise HTTPException(
            status_code=409,
            detail={"code": "TARGET_ROOM_TECH_BLOCK", "room_code": room["code"]},
        )

    extra_allowed = room["room_type_code"] not in EXTRA_BED_DENIED_ROOM_TYPES
    if payload.extra_bed_count > 0 and not extra_allowed:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "EXTRA_BED_NOT_ALLOWED",
                "room_code": room["code"],
                "room_type_code": room["room_type_code"],
                "room_type_name": room["room_type_name"],
            },
        )
    effective_adult_capacity = int(room["capacityAdults"]) + (payload.extra_bed_count if extra_allowed else 0)
    if effective_adult_capacity < payload.adults:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ROOM_CAPACITY_EXCEEDED",
                "room_code": room["code"],
                "capacity_adults": int(room["capacityAdults"]),
                "extra_bed_count": payload.extra_bed_count,
                "effective_capacity_adults": effective_adult_capacity,
                "requested_adults": payload.adults,
            },
        )

    conflicts = await find_conflicts(conn, payload.room_id, payload.check_in, payload.check_out)
    core_pricing = await price_room_type(
        conn,
        room["roomTypeId"],
        payload.check_in,
        payload.check_out,
    )
    returning = await returning_guest_context(conn, property_id, payload.guest_phone)
    discount_percent = payload.discount_percent if payload.discount_percent is not None else returning["auto_discount_percent"]
    nights = (payload.check_out - payload.check_in).days
    pricing = pricing_result(
        core_pricing,
        payload.manager_total_kgs,
        nights=nights,
        extra_bed_count=payload.extra_bed_count,
        extra_bed_unit_kgs=payload.extra_bed_unit_kgs,
        discount_percent=discount_percent,
        returning_guest=returning,
    )
    agent = await load_agent(conn, property_id, payload.agent_id)

    return {
        "room": {
            "id": str(room["id"]),
            "code": room["code"],
            "name": room["name"],
            "room_type_id": str(room["roomTypeId"]),
            "room_type_code": room["room_type_code"],
            "room_type_name": room["room_type_name"],
            "beds_raw": room["bedConfiguration"],
            "building_or_zone": room["buildingOrZone"],
            "floor": room["floorLabel"],
            "operational_state": room["operational_state"],
            "capacity_adults": int(room["capacityAdults"]),
            "capacity_children": room["capacityChildren"],
            "extra_bed_allowed": extra_allowed,
            "effective_capacity_adults": effective_adult_capacity,
        },
        "check_in": payload.check_in,
        "check_out": payload.check_out,
        "nights": nights,
        "adults": payload.adults,
        "children": payload.children,
        "extra_bed_count": payload.extra_bed_count,
        "extra_bed_unit_kgs": payload.extra_bed_unit_kgs,
        "discount_reason": payload.discount_reason,
        "agent": {"id": str(agent["id"]), "name": agent["name"]} if agent else None,
        "conflicts": conflicts,
        "pricing": pricing,
        "can_commit": not conflicts and pricing["sellable"] and pricing["total_kgs"] is not None and pricing["total_kgs"] > 0,
        "night_semantics": "Occupied nights use [check_in, check_out): checkout day is not occupied by this reservation.",
    }


@router.post("/new/preview")
async def preview_grid_reservation(
    payload: GridReservationPreviewPayload,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        prop = await property_context(conn, user["property_code"])
        return await build_preview(conn, prop["id"], payload)


@router.post("/new/commit", status_code=status.HTTP_201_CREATED)
async def commit_grid_reservation(
    payload: GridReservationCommitPayload,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    reservation_id = uuid.uuid4()
    request_id = uuid.uuid4()
    inventory_block_id = uuid.uuid4()
    booking_number = f"TC-{date.today():%y%m%d}-{secrets.token_hex(3).upper()}"

    async with request.app.state.db.acquire() as conn:
        try:
            async with conn.transaction():
                prop = await property_context(conn, user["property_code"])
                # Commit always prices against the canonical phone field, even if an older client omitted guest_phone.
                commit_preview_payload = GridReservationPreviewPayload(
                    **{
                        **payload.model_dump(exclude={"guest_name", "phone", "email", "notes", "expected_total_kgs", "expected_pricing_source"}),
                        "guest_phone": payload.phone,
                    }
                )
                preview = await build_preview(conn, prop["id"], commit_preview_payload, lock=True)
                if preview["conflicts"]:
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "ROOM_CONFLICT", "conflicts": preview["conflicts"]},
                    )
                if not preview["pricing"]["sellable"] or preview["pricing"]["total_kgs"] is None:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "RATE_REQUIRES_CONFIRMATION",
                            "reason": preview["pricing"].get("reason"),
                            "message": "Enter an explicit manager total and preview again.",
                        },
                    )
                if preview["pricing"]["source"] != payload.expected_pricing_source:
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "PRICING_SOURCE_CHANGED", "current": preview["pricing"]["source"]},
                    )

                committed_total_kgs = int(preview["pricing"]["total_kgs"])
                auto_discount_discovered_at_commit = (
                    payload.guest_phone is None
                    and payload.discount_percent is None
                    and bool(preview["pricing"].get("returning_guest"))
                    and int(preview["pricing"].get("discount_percent") or 0) == RETURNING_GUEST_DISCOUNT_PERCENT
                    and int(preview["pricing"].get("subtotal_kgs") or 0) == payload.expected_total_kgs
                    and committed_total_kgs < payload.expected_total_kgs
                )
                if committed_total_kgs != payload.expected_total_kgs and not auto_discount_discovered_at_commit:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "PRICE_CHANGED",
                            "expected_total_kgs": payload.expected_total_kgs,
                            "current_total_kgs": committed_total_kgs,
                        },
                    )

                room = preview["room"]
                identity = await resolve_or_create_guest(
                    conn,
                    property_id=prop["id"],
                    guest_name=payload.guest_name,
                    phone=payload.phone,
                    email=payload.email,
                )
                agent_id = payload.agent_id
                discount_percent = int(preview["pricing"]["discount_percent"])
                discount_reason = payload.discount_reason
                if discount_percent == RETURNING_GUEST_DISCOUNT_PERCENT and preview["pricing"]["returning_guest"] and not discount_reason:
                    discount_reason = "RETURNING_GUEST_10_PERCENT"
                elif discount_percent > 0 and not discount_reason:
                    discount_reason = "MANAGER_DISCOUNT"

                await conn.execute(
                    '''
                    INSERT INTO reservation_requests (
                      id,"propertyId",status,source,"guestName",phone,email,"checkIn","checkOut",
                      adults,children,"desiredRoomTypeId","quotedTotalKgs","requiredPrepaymentKgs",notes,"agentId",
                      "createdAt","updatedAt"
                    ) VALUES ($1,$2,'CONVERTED','PMS',$3,$4,$5,$6,$7,$8,$9,$10,$11,NULL,$12,$13,now(),now())
                    ''',
                    request_id,
                    prop["id"],
                    payload.guest_name,
                    payload.phone,
                    payload.email,
                    payload.check_in,
                    payload.check_out,
                    payload.adults,
                    payload.children,
                    uuid.UUID(room["room_type_id"]),
                    committed_total_kgs,
                    payload.notes,
                    agent_id,
                )

                await conn.execute(
                    '''
                    INSERT INTO reservations (
                      id,"propertyId","requestId","bookingNumber","primaryGuestId",status,
                      "checkIn","checkOut",adults,children,"totalKgs",notes,"agentId",
                      "extraBedCount","extraBedUnitKgs","discountPercent","discountReason","createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,$4,$5,'GUARANTEED',$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,now(),now())
                    ''',
                    reservation_id,
                    prop["id"],
                    request_id,
                    booking_number,
                    identity["guest_id"],
                    payload.check_in,
                    payload.check_out,
                    payload.adults,
                    payload.children,
                    committed_total_kgs,
                    payload.notes,
                    agent_id,
                    payload.extra_bed_count,
                    payload.extra_bed_unit_kgs if payload.extra_bed_count > 0 else None,
                    discount_percent,
                    discount_reason,
                )
                await conn.execute(
                    '''
                    INSERT INTO inventory_blocks (
                      id,"roomId","reservationId","blockType","startDate","endDate",active,reason,
                      "createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,'RESERVATION',$4,$5,true,$6,now(),now())
                    ''',
                    inventory_block_id,
                    payload.room_id,
                    reservation_id,
                    payload.check_in,
                    payload.check_out,
                    booking_number,
                )
                await conn.execute(
                    '''
                    INSERT INTO audit_logs (
                      id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,
                      "afterJson","createdAt"
                    ) VALUES ($1,$2,'STAFF',$3,'MANAGER_CREATE_RESERVATION_FROM_GRID','Reservation',$4,
                      'PMS_OWNER_GRID','SUCCESS',jsonb_build_object(
                        'booking_number',$5::text,
                        'room_id',$6::text,
                        'room_code',$7::text,
                        'check_in',$8::text,
                        'check_out',$9::text,
                        'nights',$10::integer,
                        'total_kgs',$11::integer,
                        'base_total_kgs',$12::integer,
                        'extra_bed_count',$13::integer,
                        'extra_bed_unit_kgs',$14::integer,
                        'extra_beds_total_kgs',$15::integer,
                        'discount_percent',$16::integer,
                        'discount_kgs',$17::integer,
                        'discount_reason',$18::text,
                        'returning_guest',$19::boolean,
                        'agent_id',$20::text,
                        'pricing_source',$21::text,
                        'core_total_kgs',$22::integer,
                        'payment_created',false,
                        'guest_id',$23::text,
                        'price_adjusted_at_commit',$24::boolean
                      ),now())
                    ''',
                    uuid.uuid4(),
                    prop["id"],
                    user["id"],
                    str(reservation_id),
                    booking_number,
                    str(payload.room_id),
                    room["code"],
                    payload.check_in.isoformat(),
                    payload.check_out.isoformat(),
                    preview["nights"],
                    committed_total_kgs,
                    preview["pricing"].get("base_total_kgs"),
                    payload.extra_bed_count,
                    payload.extra_bed_unit_kgs,
                    preview["pricing"].get("extra_beds_total_kgs"),
                    discount_percent,
                    preview["pricing"].get("discount_kgs"),
                    discount_reason,
                    preview["pricing"].get("returning_guest"),
                    str(agent_id) if agent_id else None,
                    preview["pricing"]["source"],
                    preview["pricing"].get("core_total_kgs"),
                    str(identity["guest_id"]),
                    auto_discount_discovered_at_commit,
                )
        except ExclusionViolationError as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "ROOM_CONFLICT_RACE", "message": "Room availability changed before commit."},
            ) from exc

    return {
        "reservation_id": str(reservation_id),
        "request_id": str(request_id),
        "booking_number": booking_number,
        "status": "GUARANTEED",
        "room_id": str(payload.room_id),
        "room_code": room["code"],
        "check_in": payload.check_in,
        "check_out": payload.check_out,
        "nights": preview["nights"],
        "total_kgs": committed_total_kgs,
        "base_total_kgs": preview["pricing"].get("base_total_kgs"),
        "extra_bed_count": payload.extra_bed_count,
        "extra_beds_total_kgs": preview["pricing"].get("extra_beds_total_kgs"),
        "discount_percent": preview["pricing"].get("discount_percent"),
        "discount_kgs": preview["pricing"].get("discount_kgs"),
        "returning_guest": preview["pricing"].get("returning_guest"),
        "agent_id": str(payload.agent_id) if payload.agent_id else None,
        "pricing_source": preview["pricing"]["source"],
        "price_adjusted_at_commit": auto_discount_discovered_at_commit,
        "payment_created": False,
        "payment_terms": "MANAGER_CONTROLLED",
    }
