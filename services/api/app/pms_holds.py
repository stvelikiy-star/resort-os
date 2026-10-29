"""60-minute inventory holds. Tenant-scoped, transactional, never silently extended."""
import uuid
from datetime import date
from typing import Any

from asyncpg.exceptions import ExclusionViolationError
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/pms/holds", tags=["admin-pms-holds"])
access = require_roles("OWNER", "MANAGER", module_grant=False)


class HoldCreate(BaseModel):
    room_id: uuid.UUID
    check_in: date
    check_out: date
    guest_name: str = Field(min_length=2, max_length=160)
    guest_phone: str = Field(min_length=5, max_length=40)

    @model_validator(mode="after")
    def dates(self):
        if self.check_out <= self.check_in or (self.check_out - self.check_in).days > 60:
            raise ValueError("Invalid stay dates")
        return self


async def expire_holds(conn):
    """Release overdue inventory atomically; safe to call repeatedly and concurrently."""
    rows = await conn.fetch("""
        SELECT h.id, h."inventoryBlockId" FROM marina_reservation_holds h
        WHERE h."releasedAt" IS NULL AND h."confirmedReservationId" IS NULL
          AND h."expiresAt" <= now()
        FOR UPDATE SKIP LOCKED
    """)
    for item in rows:
        await conn.execute("""
          UPDATE inventory_blocks SET active=false,"updatedAt"=now()
          WHERE id=$1 AND active=true
        """, item["inventoryBlockId"])
        await conn.execute("""
          UPDATE marina_reservation_holds SET "releasedAt"=now() WHERE id=$1
        """, item["id"])
    return len(rows)


async def property_id(conn, user):
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', user["property_code"])
    if not value:
        raise HTTPException(503, detail={"code": "PROPERTY_NOT_LOADED"})
    return value


@router.post("", status_code=201)
async def create_hold(payload: HoldCreate, request: Request, user: dict[str, Any] = Depends(access)):
    hold_id, block_id = uuid.uuid4(), uuid.uuid4()
    async with request.app.state.db.acquire() as conn:
        try:
            async with conn.transaction():
                prop = await property_id(conn, user)
                await expire_holds(conn)
                room = await conn.fetchrow("""
                    SELECT id,code FROM rooms WHERE id=$1 AND "propertyId"=$2 FOR UPDATE
                """, payload.room_id, prop)
                if not room:
                    raise HTTPException(404, detail={"code": "ROOM_NOT_FOUND"})
                existing = await conn.fetchval("""
                    SELECT id FROM inventory_blocks WHERE "roomId"=$1 AND active=true
                    AND daterange("startDate","endDate",'[)')
                        && daterange($2::date,$3::date,'[)') LIMIT 1
                """, payload.room_id, payload.check_in, payload.check_out)
                if existing:
                    raise HTTPException(409, detail={"code": "HOLD_ROOM_UNAVAILABLE"})
                await conn.execute("""
                    INSERT INTO inventory_blocks
                      (id,"roomId","reservationId","blockType","startDate","endDate",active,reason,"createdAt","updatedAt")
                    VALUES($1,$2,NULL,'MANUAL',$3,$4,true,$5,now(),now())
                """, block_id, payload.room_id, payload.check_in, payload.check_out, "HOLD 60m " + str(hold_id))
                await conn.execute("""
                    INSERT INTO marina_reservation_holds
                      (id,"propertyId","roomId","inventoryBlockId","createdBy","checkIn","checkOut","guestName","guestPhone")
                    VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)
                """, hold_id, prop, payload.room_id, block_id, user["id"], payload.check_in, payload.check_out, payload.guest_name, payload.guest_phone)
                expiration = await conn.fetchval('SELECT "expiresAt" FROM marina_reservation_holds WHERE id=$1', hold_id)
        except ExclusionViolationError as exc:
            raise HTTPException(409, detail={"code": "HOLD_ROOM_UNAVAILABLE"}) from exc
    return {"id": str(hold_id), "status": "HELD", "expires_at": expiration.isoformat(), "duration_minutes": 60}


@router.get("")
async def list_holds(request: Request, user: dict[str, Any] = Depends(access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await property_id(conn, user)
            await expire_holds(conn)
            rows = await conn.fetch("""
                SELECT id,"roomId","checkIn","checkOut","guestName","expiresAt"
                FROM marina_reservation_holds
                WHERE "propertyId"=$1 AND "releasedAt" IS NULL
                  AND "confirmedReservationId" IS NULL AND "expiresAt">now()
                ORDER BY "expiresAt"
            """, prop)
    return {"holds": [{k: (v.isoformat() if hasattr(v, "isoformat") else str(v)) for k,v in dict(row).items()} for row in rows]}


@router.delete("/{hold_id}")
async def release_hold(hold_id: uuid.UUID, request: Request, user: dict[str, Any] = Depends(access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await property_id(conn, user)
            row = await conn.fetchrow("""
                SELECT "inventoryBlockId","releasedAt","confirmedReservationId"
                FROM marina_reservation_holds WHERE id=$1 AND "propertyId"=$2 FOR UPDATE
            """, hold_id, prop)
            if not row:
                raise HTTPException(404, detail={"code": "HOLD_NOT_FOUND"})
            if row["confirmedReservationId"]:
                raise HTTPException(409, detail={"code": "HOLD_ALREADY_CONFIRMED"})
            if row["releasedAt"] is None:
                await conn.execute('UPDATE inventory_blocks SET active=false,"updatedAt"=now() WHERE id=$1', row["inventoryBlockId"])
                await conn.execute('UPDATE marina_reservation_holds SET "releasedAt"=now() WHERE id=$1', hold_id)
    return {"id": str(hold_id), "status": "RELEASED"}
