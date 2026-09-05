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
from .pms_reservation_create import find_conflicts, load_room, property_context

router = APIRouter(prefix="/api/v1/admin/pms/groups", tags=["admin-pms-groups"])
access = require_roles("OWNER", "MANAGER", "RECEPTION")


class GroupAvailabilityPayload(BaseModel):
    check_in: date
    check_out: date
    adults_per_room: int = Field(default=2, ge=1, le=20)
    children_per_room: int = Field(default=0, ge=0, le=20)

    @model_validator(mode="after")
    def dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        if (self.check_out - self.check_in).days > 60:
            raise ValueError("maximum stay is 60 nights")
        return self


class GroupRoomInput(BaseModel):
    room_id: uuid.UUID
    adults: int = Field(default=2, ge=1, le=20)
    children: int = Field(default=0, ge=0, le=20)
    manager_total_kgs: int | None = Field(default=None, gt=0)
    guest_name: str | None = Field(default=None, max_length=160)
    guest_phone: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def guest_pair(self):
        if bool(self.guest_name and self.guest_name.strip()) != bool(self.guest_phone and self.guest_phone.strip()):
            raise ValueError("guest_name and guest_phone must be supplied together")
        return self


class GroupCommitPayload(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    contact_name: str = Field(min_length=2, max_length=160)
    contact_phone: str = Field(min_length=5, max_length=40)
    contact_email: str | None = Field(default=None, max_length=200)
    check_in: date
    check_out: date
    rooms: list[GroupRoomInput] = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def validate_group(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        if (self.check_out - self.check_in).days > 60:
            raise ValueError("maximum stay is 60 nights")
        ids = [item.room_id for item in self.rooms]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate room in group")
        return self


async def room_candidate(conn, property_id: uuid.UUID, room_id: uuid.UUID, check_in: date, check_out: date, adults: int, children: int, lock: bool = False):
    room = await load_room(conn, property_id, room_id, lock=lock)
    if not room:
        raise HTTPException(status_code=404, detail={"code": "ROOM_NOT_FOUND", "room_id": str(room_id)})
    if room["operational_state"] == "TECH_BLOCK":
        return {"room": room, "available": False, "reason": "TECH_BLOCK", "conflicts": [], "pricing": None}
    if int(room["capacityAdults"]) < adults or int(room["capacityChildren"] or 0) < children:
        return {"room": room, "available": False, "reason": "CAPACITY", "conflicts": [], "pricing": None}
    conflicts = await find_conflicts(conn, room_id, check_in, check_out)
    pricing = await price_room_type(conn, room["roomTypeId"], check_in, check_out)
    return {
        "room": room,
        "available": not conflicts,
        "reason": "CONFLICT" if conflicts else None,
        "conflicts": conflicts,
        "pricing": pricing,
    }


def public_candidate(candidate: dict[str, Any]):
    room = candidate["room"]
    pricing = candidate["pricing"] or {}
    return {
        "room_id": str(room["id"]),
        "code": room["code"],
        "name": room["name"],
        "room_type_id": str(room["roomTypeId"]),
        "room_type_code": room["room_type_code"],
        "room_type_name": room["room_type_name"],
        "building_or_zone": room["buildingOrZone"],
        "floor": room["floorLabel"],
        "beds_raw": room["bedConfiguration"],
        "capacity_adults": int(room["capacityAdults"]),
        "capacity_children": int(room["capacityChildren"] or 0),
        "operational_state": room["operational_state"],
        "available": candidate["available"],
        "reason": candidate["reason"],
        "conflicts": candidate["conflicts"],
        "pricing": {
            "sellable": bool(pricing.get("sellable")),
            "total_kgs": pricing.get("total_kgs"),
            "reason": pricing.get("reason"),
            "nights": pricing.get("nights", []),
        } if candidate["pricing"] is not None else None,
    }


@router.post("/availability")
async def group_availability(payload: GroupAvailabilityPayload, request: Request, user: dict[str, Any] = Depends(access)):
    async with request.app.state.db.acquire() as conn:
        prop = await property_context(conn, user["property_code"])
        rooms = await conn.fetch(
            '''SELECT id FROM rooms WHERE "propertyId"=$1 ORDER BY
                 COALESCE(NULLIF(regexp_replace(code,'\\D','','g'),''),'999999')::int,code''',
            prop["id"],
        )
        items = []
        for row in rooms:
            candidate = await room_candidate(
                conn, prop["id"], row["id"], payload.check_in, payload.check_out,
                payload.adults_per_room, payload.children_per_room,
            )
            items.append(public_candidate(candidate))
    available = [item for item in items if item["available"]]
    sellable = [item for item in available if item["pricing"] and item["pricing"]["sellable"] and item["pricing"]["total_kgs"] is not None]
    return {
        "check_in": payload.check_in,
        "check_out": payload.check_out,
        "nights": (payload.check_out - payload.check_in).days,
        "requested_guests_per_room": {"adults": payload.adults_per_room, "children": payload.children_per_room},
        "available_count": len(available),
        "priced_count": len(sellable),
        "items": items,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def commit_group(payload: GroupCommitPayload, request: Request, user: dict[str, Any] = Depends(access)):
    group_id = uuid.uuid4()
    group_code = f"GR-{date.today():%y%m%d}-{secrets.token_hex(3).upper()}"
    created: list[dict[str, Any]] = []

    async with request.app.state.db.acquire() as conn:
        try:
            async with conn.transaction():
                prop = await property_context(conn, user["property_code"])
                contact = await resolve_or_create_guest(
                    conn,
                    property_id=prop["id"],
                    guest_name=payload.contact_name,
                    phone=payload.contact_phone,
                    email=payload.contact_email,
                )

                # Deterministic room-lock order prevents two simultaneous groups from deadlocking.
                previews: list[tuple[GroupRoomInput, dict[str, Any], int, str]] = []
                for member in sorted(payload.rooms, key=lambda item: str(item.room_id)):
                    candidate = await room_candidate(
                        conn, prop["id"], member.room_id, payload.check_in, payload.check_out,
                        member.adults, member.children, lock=True,
                    )
                    room = candidate["room"]
                    if not candidate["available"]:
                        raise HTTPException(status_code=409, detail={
                            "code": "GROUP_ROOM_UNAVAILABLE", "room_code": room["code"],
                            "reason": candidate["reason"], "conflicts": candidate["conflicts"],
                        })
                    if member.manager_total_kgs is not None:
                        total_kgs = member.manager_total_kgs
                        pricing_source = "MANAGER_OVERRIDE"
                    else:
                        pricing = candidate["pricing"] or {}
                        if not pricing.get("sellable") or pricing.get("total_kgs") is None:
                            raise HTTPException(status_code=409, detail={
                                "code": "GROUP_ROOM_RATE_REQUIRES_OVERRIDE", "room_code": room["code"],
                                "reason": pricing.get("reason"),
                            })
                        total_kgs = int(pricing["total_kgs"])
                        pricing_source = "CORE_RATE"
                    previews.append((member, candidate, total_kgs, pricing_source))

                await conn.execute(
                    '''INSERT INTO booking_groups (
                         id,"propertyId",code,name,"contactGuestId","contactName","contactPhone","contactEmail",
                         "checkIn","checkOut",status,notes,"createdById","createdAt","updatedAt"
                       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,'ACTIVE',$11,$12,now(),now())''',
                    group_id, prop["id"], group_code, payload.name.strip(), contact["guest_id"],
                    payload.contact_name.strip(), payload.contact_phone.strip(), payload.contact_email,
                    payload.check_in, payload.check_out, payload.notes, uuid.UUID(user["id"]),
                )

                for index, (member, candidate, total_kgs, pricing_source) in enumerate(previews, start=1):
                    room = candidate["room"]
                    if member.guest_name and member.guest_phone:
                        identity = await resolve_or_create_guest(
                            conn, property_id=prop["id"], guest_name=member.guest_name,
                            phone=member.guest_phone, email=None,
                        )
                    else:
                        identity = contact
                    reservation_id = uuid.uuid4()
                    request_id = uuid.uuid4()
                    inventory_id = uuid.uuid4()
                    member_id = uuid.uuid4()
                    booking_number = f"TC-{date.today():%y%m%d}-{secrets.token_hex(3).upper()}"
                    guest_display = member.guest_name.strip() if member.guest_name else payload.contact_name.strip()
                    guest_phone = member.guest_phone.strip() if member.guest_phone else payload.contact_phone.strip()
                    notes = f"Группа {group_code} · {payload.name.strip()}" + (f"\n{payload.notes}" if payload.notes else "")

                    await conn.execute(
                        '''INSERT INTO reservation_requests (
                             id,"propertyId",status,source,"guestName",phone,email,"checkIn","checkOut",adults,children,
                             "desiredRoomTypeId","quotedTotalKgs","requiredPrepaymentKgs",notes,"createdAt","updatedAt"
                           ) VALUES ($1,$2,'CONVERTED','PMS_GROUP',$3,$4,$5,$6,$7,$8,$9,$10,$11,NULL,$12,now(),now())''',
                        request_id, prop["id"], guest_display, guest_phone,
                        payload.contact_email if identity["guest_id"] == contact["guest_id"] else None,
                        payload.check_in, payload.check_out, member.adults, member.children, room["roomTypeId"], total_kgs, notes,
                    )
                    await conn.execute(
                        '''INSERT INTO reservations (
                             id,"propertyId","requestId","bookingNumber","primaryGuestId",status,"checkIn","checkOut",
                             adults,children,"totalKgs",notes,"createdAt","updatedAt"
                           ) VALUES ($1,$2,$3,$4,$5,'GUARANTEED',$6,$7,$8,$9,$10,$11,now(),now())''',
                        reservation_id, prop["id"], request_id, booking_number, identity["guest_id"],
                        payload.check_in, payload.check_out, member.adults, member.children, total_kgs, notes,
                    )
                    await conn.execute(
                        '''INSERT INTO inventory_blocks (
                             id,"roomId","reservationId","blockType","startDate","endDate",active,reason,"createdAt","updatedAt"
                           ) VALUES ($1,$2,$3,'RESERVATION',$4,$5,true,$6,now(),now())''',
                        inventory_id, member.room_id, reservation_id, payload.check_in, payload.check_out, f"{group_code} · {booking_number}",
                    )
                    await conn.execute(
                        '''INSERT INTO booking_group_members (id,"groupId","reservationId","roomId","memberLabel","createdAt")
                           VALUES ($1,$2,$3,$4,$5,now())''',
                        member_id, group_id, reservation_id, member.room_id, guest_display,
                    )
                    created.append({
                        "reservation_id": str(reservation_id), "booking_number": booking_number,
                        "room_id": str(member.room_id), "room_code": room["code"], "guest_name": guest_display,
                        "adults": member.adults, "children": member.children, "total_kgs": total_kgs,
                        "pricing_source": pricing_source,
                    })
                    await conn.execute(
                        '''INSERT INTO audit_logs (
                             id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                           ) VALUES ($1,$2,'STAFF',$3,'CREATE_GROUP_MEMBER_RESERVATION','Reservation',$4,'PMS_GROUP','SUCCESS',
                             jsonb_build_object('group_id',$5::text,'group_code',$6::text,'room_code',$7::text,
                               'total_kgs',$8::int,'pricing_source',$9::text,'payment_created',false),now())''',
                        uuid.uuid4(), prop["id"], user["id"], str(reservation_id), str(group_id), group_code,
                        room["code"], total_kgs, pricing_source,
                    )

                await conn.execute(
                    '''INSERT INTO audit_logs (
                         id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                       ) VALUES ($1,$2,'STAFF',$3,'CREATE_BOOKING_GROUP','BookingGroup',$4,'PMS_GROUP','SUCCESS',
                         jsonb_build_object('group_code',$5::text,'rooms',$6::int,'total_kgs',$7::int,'payment_created',false),now())''',
                    uuid.uuid4(), prop["id"], user["id"], str(group_id), group_code, len(created),
                    sum(item["total_kgs"] for item in created),
                )
        except ExclusionViolationError as exc:
            raise HTTPException(status_code=409, detail={
                "code": "GROUP_ROOM_CONFLICT_RACE",
                "message": "Availability changed during group commit. No group reservations were created.",
            }) from exc

    return {
        "group_id": str(group_id), "group_code": group_code, "name": payload.name,
        "check_in": payload.check_in, "check_out": payload.check_out,
        "rooms": created, "room_count": len(created),
        "total_kgs": sum(item["total_kgs"] for item in created),
        "payment_created": False,
        "atomic": True,
    }


@router.get("")
async def list_groups(request: Request, user: dict[str, Any] = Depends(access)):
    async with request.app.state.db.acquire() as conn:
        prop = await property_context(conn, user["property_code"])
        rows = await conn.fetch(
            '''SELECT bg.id,bg.code,bg.name,bg."contactName",bg."contactPhone",bg."checkIn",bg."checkOut",bg.status,bg.notes,
                      count(bgm.id)::int AS room_count,COALESCE(sum(r."totalKgs"),0)::int AS total_kgs,
                      COALESCE(sum(p.paid),0)::int AS paid_kgs
               FROM booking_groups bg
               LEFT JOIN booking_group_members bgm ON bgm."groupId"=bg.id
               LEFT JOIN reservations r ON r.id=bgm."reservationId"
               LEFT JOIN LATERAL (
                 SELECT COALESCE(sum(pay."amountKgs") FILTER (WHERE pay.status='RECEIVED'),0)::int AS paid
                 FROM payments pay WHERE pay."reservationId"=r.id
               ) p ON true
               WHERE bg."propertyId"=$1
               GROUP BY bg.id
               ORDER BY bg."checkIn" DESC,bg."createdAt" DESC LIMIT 200''', prop["id"],
        )
    return {"items": [{
        "id": str(row["id"]), "code": row["code"], "name": row["name"],
        "contact_name": row["contactName"], "contact_phone": row["contactPhone"],
        "check_in": row["checkIn"], "check_out": row["checkOut"], "status": row["status"],
        "notes": row["notes"], "room_count": row["room_count"], "total_kgs": row["total_kgs"], "paid_kgs": row["paid_kgs"],
    } for row in rows]}
