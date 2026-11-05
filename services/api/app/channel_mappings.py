"""Property-scoped draft mappings; saving never connects a provider."""
import json
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .auth import trusted_property_id
from .channel_reservations import manager_access

router = APIRouter(prefix="/api/v1/admin/channels/mappings", tags=["channel-mappings"])


class ChannelMappingInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    provider: Literal["BOOKING_COM", "AIRBNB", "OSTROVOK"]
    external_property_id: str = Field(min_length=1, max_length=180)
    external_room_type_id: str = Field(min_length=1, max_length=180)
    external_rate_plan_id: str = Field(min_length=1, max_length=180)
    room_type_id: uuid.UUID
    rate_plan_id: uuid.UUID
    currency: Literal["KGS"] = "KGS"
    active: bool = True
    expected_revision: int = Field(default=0, ge=0, le=2147483646)


def serialize(row):
    return {"id": str(row["id"]), "provider": row["provider"],
            "external_property_id": row["externalPropertyId"], "external_room_type_id": row["externalRoomTypeId"],
            "external_rate_plan_id": row["externalRatePlanId"], "room_type_id": str(row["roomTypeId"]),
            "rate_plan_id": str(row["ratePlanId"]), "currency": row["currency"],
            "active": row["active"], "revision": row["revision"], "updated_at": row["updatedAt"]}


@router.get("")
async def overview(request: Request, user=Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        pid = await trusted_property_id(conn, user)
        rows = await conn.fetch('SELECT * FROM channel_mappings WHERE "propertyId"=$1 ORDER BY provider,"externalPropertyId","externalRoomTypeId","externalRatePlanId"', pid)
        types = await conn.fetch('SELECT id,code,name FROM room_types WHERE "propertyId"=$1 ORDER BY code', pid)
        rates = await conn.fetch('SELECT id,code,name,currency FROM rate_plans WHERE "propertyId"=$1 ORDER BY code', pid)
    return {"items": [serialize(row) for row in rows], "room_types": [dict(row) for row in types],
            "rate_plans": [dict(row) for row in rates], "connected": False, "automatic_sync": False}


@router.put("")
async def save(payload: ChannelMappingInput, request: Request, user=Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await trusted_property_id(conn, user)
            identity = [payload.provider, payload.external_property_id, payload.external_room_type_id, payload.external_rate_plan_id]
            # Same-key writers serialize; optimistic revision prevents silent overwrite.
            await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended($1,0))", json.dumps([str(pid), "channel_mapping", *identity]))
            previous = await conn.fetchrow('SELECT * FROM channel_mappings WHERE "propertyId"=$1 AND provider=$2 AND "externalPropertyId"=$3 AND "externalRoomTypeId"=$4 AND "externalRatePlanId"=$5 FOR UPDATE', pid, *identity)
            if payload.expected_revision != (previous["revision"] if previous else 0):
                raise HTTPException(status_code=409, detail={"code": "CHANNEL_MAPPING_STALE"})
            room = await conn.fetchval('SELECT id FROM room_types WHERE "propertyId"=$1 AND id=$2 FOR KEY SHARE', pid, payload.room_type_id)
            rate = await conn.fetchrow('SELECT id,currency FROM rate_plans WHERE "propertyId"=$1 AND id=$2 FOR KEY SHARE', pid, payload.rate_plan_id)
            if not room or not rate:
                raise HTTPException(status_code=404, detail={"code": "CHANNEL_MAPPING_TARGET_NOT_FOUND"})
            if rate["currency"] != payload.currency:
                raise HTTPException(status_code=409, detail={"code": "CHANNEL_MAPPING_CURRENCY_MISMATCH"})
            row = await conn.fetchrow('INSERT INTO channel_mappings (id,"propertyId",provider,"externalPropertyId","externalRoomTypeId","externalRatePlanId","roomTypeId","ratePlanId",currency,active,revision,"createdAt","updatedAt") VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,1,now(),now()) ON CONFLICT ("propertyId",provider,"externalPropertyId","externalRoomTypeId","externalRatePlanId") DO UPDATE SET "roomTypeId"=EXCLUDED."roomTypeId","ratePlanId"=EXCLUDED."ratePlanId",currency=EXCLUDED.currency,active=EXCLUDED.active,revision=channel_mappings.revision+1,"updatedAt"=now() RETURNING *', uuid.uuid4(), pid, *identity, payload.room_type_id, payload.rate_plan_id, payload.currency, payload.active)
            await conn.execute('INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"beforeJson","afterJson","createdAt") VALUES ($1,$2,\'STAFF\',$3,\'CHANNEL_MAPPING_SAVE\',\'ChannelMapping\',$4,\'CHANNEL_CONFIGURATION\',\'SUCCESS\',$5::jsonb,$6::jsonb,now())', uuid.uuid4(), pid, user["id"], str(row["id"]), json.dumps(serialize(previous), default=str) if previous else None, json.dumps(serialize(row), default=str))
    return {**serialize(row), "connected": False, "automatic_sync": False}
