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


class GridReservationPreviewPayload(BaseModel):
    room_id: uuid.UUID
    check_in: date
    check_out: date
    adults: int = Field(default=2, ge=1, le=20)
    children: int = Field(default=0, ge=0, le=20)
    manager_total_kgs: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        if (self.check_out - self.check_in).days > 60:
            raise ValueError("maximum stay is 60 nights")
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
            "start": row["startDate"],
            "end": row["endDate"],
            "booking_number": row["bookingNumber"],
            "reason": row["reason"],
        }
        for row in rows
    ]


def pricing_result(core_pricing: dict[str, Any], manager_total_kgs: int | None):
    if manager_total_kgs is not None:
        return {
            "source": "MANAGER_OVERRIDE",
            "sellable": True,
            "reason": None,
            "total_kgs": manager_total_kgs,
            "core_total_kgs": core_pricing.get("total_kgs"),
            "core_sellable": bool(core_pricing.get("sellable")),
            "core_reason": core_pricing.get("reason"),
            "nights": core_pricing.get("nights", []),
        }
    return {
        "source": "CORE_RATE",
        "sellable": bool(core_pricing.get("sellable")),
        "reason": core_pricing.get("reason"),
        "total_kgs": core_pricing.get("total_kgs"),
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
    if int(room["capacityAdults"]) < payload.adults:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ROOM_CAPACITY_EXCEEDED",
                "room_code": room["code"],
                "capacity_adults": int(room["capacityAdults"]),
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
    pricing = pricing_result(core_pricing, payload.manager_total_kgs)
    nights = (payload.check_out - payload.check_in).days

    return {
        "room": {
            "id": str(room["id"]),
            "code": room["code"],
            "name": room["name"],
            "room_type_code": room["room_type_code"],
            "room_type_name": room["room_type_name"],
            "beds_raw": room["bedConfiguration"],
            "building_or_zone": room["buildingOrZone"],
            "floor": room["floorLabel"],
            "operational_state": room["operational_state"],
            "capacity_adults": int(room["capacityAdults"]),
            "capacity_children": room["capacityChildren"],
        },
        "check_in": payload.check_in,
        "check_out": payload.check_out,
        "nights": nights,
        "adults": payload.adults,
        "children": payload.children,
        "conflicts": conflicts,
        "pricing": pricing,
        "can_commit": not conflicts and pricing["sellable"] and pricing["total_kgs"] is not None,
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
                preview = await build_preview(conn, prop["id"], payload, lock=True)
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
                if int(preview["pricing"]["total_kgs"]) != payload.expected_total_kgs:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "PRICE_CHANGED",
                            "expected_total_kgs": payload.expected_total_kgs,
                            "current_total_kgs": int(preview["pricing"]["total_kgs"]),
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

                await conn.execute(
                    '''
                    INSERT INTO reservation_requests (
                      id,"propertyId",status,source,"guestName",phone,email,"checkIn","checkOut",
                      adults,children,"desiredRoomTypeId","quotedTotalKgs","requiredPrepaymentKgs",notes,
                      "createdAt","updatedAt"
                    ) VALUES ($1,$2,'CONVERTED','PMS',$3,$4,$5,$6,$7,$8,$9,$10,$11,NULL,$12,now(),now())
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
                    uuid.UUID(room["id"]),
                    payload.expected_total_kgs,
                    payload.notes,
                )

                # desiredRoomTypeId references room_types, not rooms.
                await conn.execute(
                    'UPDATE reservation_requests SET "desiredRoomTypeId"=(SELECT "roomTypeId" FROM rooms WHERE id=$1) WHERE id=$2',
                    payload.room_id,
                    request_id,
                )

                await conn.execute(
                    '''
                    INSERT INTO reservations (
                      id,"propertyId","requestId","bookingNumber","primaryGuestId",status,
                      "checkIn","checkOut",adults,children,"totalKgs",notes,"createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,$4,$5,'GUARANTEED',$6,$7,$8,$9,$10,$11,now(),now())
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
                    payload.expected_total_kgs,
                    payload.notes,
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
                        'pricing_source',$12::text,
                        'core_total_kgs',$13::integer,
                        'payment_created',false,
                        'guest_id',$14::text
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
                    payload.expected_total_kgs,
                    preview["pricing"]["source"],
                    preview["pricing"].get("core_total_kgs"),
                    str(identity["guest_id"]),
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
        "total_kgs": payload.expected_total_kgs,
        "pricing_source": preview["pricing"]["source"],
        "payment_created": False,
        "payment_terms": "MANAGER_CONTROLLED",
    }
