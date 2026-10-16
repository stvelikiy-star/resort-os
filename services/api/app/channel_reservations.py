"""Normalized, manager-confirmed external reservations; no provider is connected.

The existing property-scoped inbound ledger holds external identities and their
latest revision. Reservations and inventory remain in the canonical PMS tables.
"""
import hashlib
import json
import uuid
from datetime import date
from typing import Literal

from asyncpg.exceptions import ExclusionViolationError
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .auth import require_roles, trusted_property_id
from .guest_identity import resolve_or_create_guest

router = APIRouter(prefix="/api/v1/admin/channels", tags=["channel-reservations"])
manager_access = require_roles("OWNER", "MANAGER")
PROVIDERS = {"BOOKING_COM": "Booking.com", "AIRBNB": "Airbnb", "OSTROVOK": "Ostrovok"}
EVENT_TYPE = "CHANNEL_RESERVATION"


class ChannelReservationImport(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    provider: Literal["BOOKING_COM", "AIRBNB", "OSTROVOK"]
    external_id: str = Field(min_length=1, max_length=180)
    revision: int = Field(ge=1, le=2147483647)
    status: Literal["CONFIRMED", "CANCELLED"] = "CONFIRMED"
    room_id: uuid.UUID | None = None
    guest_name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    check_in: date | None = None
    check_out: date | None = None
    adults: int = Field(default=1, ge=1, le=20)
    children: int = Field(default=0, ge=0, le=20)
    total_kgs: int | None = Field(default=None, ge=0, le=2147483647)
    currency: Literal["KGS"] = "KGS"

    @model_validator(mode="after")
    def validate_confirmation(self):
        if self.status == "CONFIRMED":
            if any(value is None for value in (self.room_id, self.guest_name, self.check_in, self.check_out, self.total_kgs)):
                raise ValueError("Confirmed import requires room, guest, dates and total in KGS")
            nights = (self.check_out - self.check_in).days
            if not 1 <= nights <= 60:
                raise ValueError("Imported stay must be between 1 and 60 nights")
        return self


def conflict(code: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code})


def ledger_key(external_id: str) -> str:
    return hashlib.sha256(external_id.encode()).hexdigest()


def decode_payload(value):
    return json.loads(value) if isinstance(value, str) else value


def response_for(row, duplicate=False):
    payload = decode_payload(row["payloadJson"])
    return {
        "provider": payload["provider"], "external_id": payload["external_id"],
        "revision": payload["revision"], "status": payload["status"],
        "reservation_id": row["resultResourceId"], "duplicate": duplicate,
        "check_in": payload.get("check_in"), "check_out": payload.get("check_out"),
        "guest_name": payload.get("guest_name"), "total_kgs": payload.get("total_kgs"),
        "room_id": payload.get("room_id"), "phone": payload.get("phone"),
        "adults": payload.get("adults", 1), "children": payload.get("children", 0),
        "updated_at": row["updatedAt"], "mode": "MANUAL_IMPORT",
    }


@router.get("")
async def channel_overview(request: Request, limit: int = Query(default=100, ge=1, le=500), user=Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        pid = await trusted_property_id(conn, user)
        rows = await conn.fetch('SELECT * FROM automation_inbound_events WHERE "propertyId"=$1 AND "eventType"=$2 ORDER BY "updatedAt" DESC,id LIMIT $3', pid, EVENT_TYPE, limit)
        rooms = await conn.fetch('SELECT id,code FROM rooms WHERE "propertyId"=$1 ORDER BY code', pid)
    return {
        "providers": [{"code": code, "name": name, "connected": False, "automatic_sync": False} for code, name in PROVIDERS.items()],
        "items": [response_for(row) for row in rows],
        "rooms": [{"id": str(room["id"]), "code": room["code"]} for room in rooms],
        "mode": "MANUAL_IMPORT", "currency": "KGS",
    }


async def apply_import(conn, pid, user, payload):
    source = "OTA_MANUAL_" + payload.provider
    key = ledger_key(payload.external_id)
    normalized = payload.model_dump(mode="json")
    await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended($1,0))", f"channel:{pid}:{source}:{key}")
    existing = await conn.fetchrow('SELECT * FROM automation_inbound_events WHERE "propertyId"=$1 AND source=$2 AND "idempotencyKey"=$3 FOR UPDATE', pid, source, key)
    previous = decode_payload(existing["payloadJson"]) if existing else None
    if previous:
        if payload.revision < previous["revision"]:
            raise conflict("CHANNEL_STALE_REVISION")
        if payload.revision == previous["revision"]:
            if normalized != previous:
                raise conflict("CHANNEL_REVISION_PAYLOAD_MISMATCH")
            return response_for(existing, duplicate=True)
        if previous["status"] == "CANCELLED" and payload.status != "CANCELLED":
            raise conflict("CHANNEL_CANCELLED_REQUIRES_REVIEW")

    reservation_id = uuid.UUID(existing["resultResourceId"]) if existing and existing["resultResourceId"] else None
    reservation = None
    if reservation_id:
        reservation = await conn.fetchrow('SELECT id,status::text AS status,"requestId","primaryGuestId" FROM reservations WHERE id=$1 AND "propertyId"=$2 FOR UPDATE', reservation_id, pid)
        if not reservation:
            raise conflict("CHANNEL_RESERVATION_RECONCILIATION_REQUIRED")
        if reservation["status"] not in {"GUARANTEED", "CANCELLED"}:
            raise conflict("CHANNEL_ACTIVE_STAY_REQUIRES_REVIEW")
        if reservation["status"] == "CANCELLED" and payload.status == "CONFIRMED":
            raise conflict("CHANNEL_CANCELLED_REQUIRES_REVIEW")

    if payload.status == "CANCELLED":
        if reservation:
            await conn.execute('UPDATE inventory_blocks SET active=false,"updatedAt"=now() WHERE "reservationId"=$1 AND active=true', reservation_id)
            await conn.execute('UPDATE reservations SET status=\'CANCELLED\',"updatedAt"=now() WHERE id=$1 AND "propertyId"=$2', reservation_id, pid)
            await conn.execute('UPDATE reservation_requests SET status=\'CANCELLED\',"updatedAt"=now() WHERE id=$1 AND "propertyId"=$2', reservation["requestId"], pid)
        # A cancellation received before creation is retained as a tombstone.
    else:
        old_rooms = await conn.fetch('SELECT "roomId" FROM inventory_blocks WHERE "reservationId"=$1 AND active=true', reservation_id) if reservation_id else []
        lock_ids = sorted({payload.room_id, *(row["roomId"] for row in old_rooms)}, key=str)
        await conn.fetch('SELECT id FROM rooms WHERE "propertyId"=$1 AND id=ANY($2::uuid[]) ORDER BY id FOR UPDATE', pid, lock_ids)
        room = await conn.fetchrow('SELECT r.id,r."roomTypeId",r."operationalState"::text AS state,rt."capacityAdults",rt."capacityChildren" FROM rooms r JOIN room_types rt ON rt.id=r."roomTypeId" WHERE r.id=$1 AND r."propertyId"=$2', payload.room_id, pid)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        if room["state"] == "TECH_BLOCK":
            raise conflict("CHANNEL_ROOM_TECH_BLOCK")
        if payload.adults > room["capacityAdults"] or payload.children > room["capacityChildren"]:
            raise conflict("CHANNEL_ROOM_CAPACITY")
        occupied = await conn.fetchval('SELECT EXISTS(SELECT 1 FROM inventory_blocks WHERE "roomId"=$1 AND active=true AND ("reservationId" IS DISTINCT FROM $2::uuid) AND daterange("startDate","endDate",\'[)\') && daterange($3::date,$4::date,\'[)\'))', payload.room_id, reservation_id, payload.check_in, payload.check_out)
        if occupied:
            raise conflict("CHANNEL_ROOM_CONFLICT")
        if reservation and not payload.phone and previous.get("guest_name") == payload.guest_name and reservation["primaryGuestId"]:
            identity = {"guest_id": reservation["primaryGuestId"]}
        else:
            identity = await resolve_or_create_guest(conn, property_id=pid, guest_name=payload.guest_name, phone=payload.phone, email=None)
        if not reservation:
            reservation_id, request_id = uuid.uuid4(), uuid.uuid4()
            booking_number = "OTA-" + uuid.uuid4().hex[:16].upper()
            await conn.execute('INSERT INTO reservation_requests (id,"propertyId",status,source,"guestName",phone,"checkIn","checkOut",adults,children,"desiredRoomTypeId","quotedTotalKgs","createdAt","updatedAt") VALUES ($1,$2,\'CONVERTED\',$3,$4,$5,$6,$7,$8,$9,$10,$11,now(),now())', request_id, pid, PROVIDERS[payload.provider], payload.guest_name, payload.phone or "", payload.check_in, payload.check_out, payload.adults, payload.children, room["roomTypeId"], payload.total_kgs)
            await conn.execute('INSERT INTO reservations (id,"propertyId","requestId","bookingNumber","primaryGuestId",status,"checkIn","checkOut",adults,children,"totalKgs","createdAt","updatedAt") VALUES ($1,$2,$3,$4,$5,\'GUARANTEED\',$6,$7,$8,$9,$10,now(),now())', reservation_id, pid, request_id, booking_number, identity["guest_id"], payload.check_in, payload.check_out, payload.adults, payload.children, payload.total_kgs)
        else:
            request_id = reservation["requestId"]
            await conn.execute('UPDATE inventory_blocks SET active=false,"updatedAt"=now() WHERE "reservationId"=$1 AND active=true', reservation_id)
            await conn.execute('UPDATE reservations SET "primaryGuestId"=$3,"checkIn"=$4,"checkOut"=$5,adults=$6,children=$7,"totalKgs"=$8,"updatedAt"=now() WHERE id=$1 AND "propertyId"=$2', reservation_id, pid, identity["guest_id"], payload.check_in, payload.check_out, payload.adults, payload.children, payload.total_kgs)
            await conn.execute('UPDATE reservation_requests SET "guestName"=$3,phone=$4,"checkIn"=$5,"checkOut"=$6,adults=$7,children=$8,"desiredRoomTypeId"=$9,"quotedTotalKgs"=$10,"updatedAt"=now() WHERE id=$1 AND "propertyId"=$2', request_id, pid, payload.guest_name, payload.phone or "", payload.check_in, payload.check_out, payload.adults, payload.children, room["roomTypeId"], payload.total_kgs)
        await conn.execute('INSERT INTO inventory_blocks (id,"roomId","reservationId","blockType","startDate","endDate",active,reason,"createdAt","updatedAt") VALUES ($1,$2,$3,\'RESERVATION\',$4,$5,true,$6,now(),now())', uuid.uuid4(), payload.room_id, reservation_id, payload.check_in, payload.check_out, f"{PROVIDERS[payload.provider]} · {payload.external_id}")

    row = await conn.fetchrow('INSERT INTO automation_inbound_events (id,"propertyId",source,"idempotencyKey","eventType","payloadJson","resultResource","resultResourceId","createdAt","updatedAt") VALUES ($1,$2,$3,$4,$5,$6::jsonb,\'Reservation\',$7,now(),now()) ON CONFLICT ("propertyId",source,"idempotencyKey") DO UPDATE SET "payloadJson"=EXCLUDED."payloadJson","resultResourceId"=EXCLUDED."resultResourceId","updatedAt"=now() RETURNING *', uuid.uuid4(), pid, source, key, EVENT_TYPE, json.dumps(normalized), str(reservation_id) if reservation_id else None)
    await conn.execute('INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt") VALUES ($1,$2,\'STAFF\',$3,\'CHANNEL_MANUAL_IMPORT\',\'Reservation\',$4,$5,\'SUCCESS\',$6::jsonb,now())', uuid.uuid4(), pid, user["id"], str(reservation_id) if reservation_id else payload.external_id, source, json.dumps({"provider": payload.provider, "external_id": payload.external_id, "revision": payload.revision, "status": payload.status}))
    return response_for(row)


@router.post("/reservations/import")
async def import_channel_reservation(payload: ChannelReservationImport, request: Request, user=Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        try:
            async with conn.transaction():
                pid = await trusted_property_id(conn, user)
                return await apply_import(conn, pid, user, payload)
        except ExclusionViolationError as exc:
            raise conflict("CHANNEL_ROOM_CONFLICT") from exc
