import hashlib
import hmac
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from .auth import require_roles
from .my_stay import _digest, _guest_context, _property

router = APIRouter(tags=["smart-access"])
manager_access = require_roles("OWNER", "ADMIN", "MANAGER")


class AccessPointCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=160)
    kind: Literal["ROOM", "TOILET", "OTHER"]
    room_id: uuid.UUID | None = None
    price_kgs: int = Field(default=0, ge=0, le=100000)
    controller_ref: str | None = Field(default=None, max_length=240)
    active: bool = False


class AccessPointPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    price_kgs: int | None = Field(default=None, ge=0, le=100000)
    controller_ref: str | None = Field(default=None, max_length=240)
    active: bool | None = None


class UnlockPayload(BaseModel):
    payment_id: uuid.UUID | None = None


def _controller_config() -> tuple[str, bytes]:
    url = os.environ.get("SMART_ACCESS_CONTROLLER_URL", "").strip()
    secret = os.environ.get("SMART_ACCESS_HMAC_SECRET", "")
    if not url or len(secret) < 32:
        raise HTTPException(status_code=503, detail="Physical access controller is not configured")
    if not url.startswith("https://") and os.environ.get("APP_ENV", "development") == "production":
        raise HTTPException(status_code=503, detail="Production access controller must use HTTPS")
    return url.rstrip("/"), secret.encode("utf-8")


def _controller_signature(secret: bytes, body: bytes) -> str:
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


@router.get("/api/v1/admin/smart-access/points")
async def list_access_points(request: Request, user=Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn, user["property_code"])
        rows = await conn.fetch(
            '''SELECT ap.id,ap.code,ap.name,ap.kind,ap."roomId",r.code AS room_code,ap."priceKgs",ap.active,ap."controllerRef",ap."updatedAt"
               FROM smart_access_points ap LEFT JOIN rooms r ON r.id=ap."roomId"
               WHERE ap."propertyId"=$1 ORDER BY ap.kind,ap.code''', prop["id"]
        )
    return {"items": [dict(row) for row in rows]}


@router.post("/api/v1/admin/smart-access/points", status_code=status.HTTP_201_CREATED)
async def create_access_point(payload: AccessPointCreate, request: Request, user=Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            if payload.kind == "ROOM" and not payload.room_id:
                raise HTTPException(status_code=422, detail="ROOM access point requires room_id")
            if payload.room_id:
                room = await conn.fetchrow('SELECT id FROM rooms WHERE id=$1 AND "propertyId"=$2', payload.room_id, prop["id"])
                if not room:
                    raise HTTPException(status_code=422, detail="Room not found")
            point_id = uuid.uuid4()
            try:
                await conn.execute(
                    '''INSERT INTO smart_access_points (id,"propertyId",code,name,kind,"roomId","priceKgs",active,"controllerRef","createdAt","updatedAt")
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,now(),now())''',
                    point_id, prop["id"], payload.code, payload.name, payload.kind, payload.room_id,
                    payload.price_kgs, payload.active, payload.controller_ref,
                )
            except Exception as exc:
                if "unique" in str(exc).lower():
                    raise HTTPException(status_code=409, detail="Access point code already exists") from exc
                raise
    return {"id": str(point_id), "active": payload.active}


@router.patch("/api/v1/admin/smart-access/points/{point_id}")
async def patch_access_point(point_id: uuid.UUID, payload: AccessPointPatch, request: Request, user=Depends(manager_access)):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return {"ok": True}
    columns = {"name": "name", "price_kgs": '"priceKgs"', "controller_ref": '"controllerRef"', "active": "active"}
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn, user["property_code"])
        values: list[Any] = []
        sets = []
        for key, value in changes.items():
            values.append(value)
            sets.append(f"{columns[key]}=${len(values)+2}")
        result = await conn.execute(
            f'''UPDATE smart_access_points SET {', '.join(sets)},"updatedAt"=now() WHERE id=$1 AND "propertyId"=$2''',
            point_id, prop["id"], *values,
        )
        if result.endswith("0"):
            raise HTTPException(status_code=404, detail="Access point not found")
    return {"ok": True}


async def _point_for_guest(conn, ctx: dict[str, Any], code: str):
    point = await conn.fetchrow(
        '''SELECT id,code,name,kind,"roomId","priceKgs",active,"controllerRef"
           FROM smart_access_points WHERE "propertyId"=$1 AND code=$2''', ctx["property_id"], code
    )
    if not point or not point["active"]:
        raise HTTPException(status_code=404, detail="Access point is unavailable")
    if point["kind"] == "ROOM" and (not ctx["room_id"] or point["roomId"] != ctx["room_id"]):
        raise HTTPException(status_code=403, detail="This room is not assigned to the current stay")
    return point


@router.get("/api/v1/guest/access/current-room")
async def guest_current_room_access(request: Request, resort_guest_session: str | None = Cookie(default=None)):
    ctx = await _guest_context(request, resort_guest_session)
    if not ctx["room_id"]:
        raise HTTPException(status_code=409, detail="Current room is not resolved")
    async with request.app.state.db.acquire() as conn:
        point = await conn.fetchrow(
            '''SELECT id,code,name,kind,"roomId","priceKgs",active,"controllerRef"
               FROM smart_access_points
               WHERE "propertyId"=$1 AND kind='ROOM' AND "roomId"=$2 AND active=true
               ORDER BY "updatedAt" DESC, code
               LIMIT 1''',
            ctx["property_id"], ctx["room_id"],
        )
    if not point:
        raise HTTPException(status_code=404, detail="Access point is unavailable")
    return {
        "code": point["code"], "name": point["name"], "kind": point["kind"],
        "price_kgs": int(point["priceKgs"]), "payment_required": int(point["priceKgs"]) > 0,
        "room_match": True, "room_code": ctx["room_code"],
    }


@router.get("/api/v1/guest/access/{code}")
async def guest_access_quote(code: str, request: Request, resort_guest_session: str | None = Cookie(default=None)):
    ctx = await _guest_context(request, resort_guest_session)
    async with request.app.state.db.acquire() as conn:
        point = await _point_for_guest(conn, ctx, code)
    return {
        "code": point["code"], "name": point["name"], "kind": point["kind"],
        "price_kgs": int(point["priceKgs"]), "payment_required": int(point["priceKgs"]) > 0,
        "room_match": point["kind"] != "ROOM" or point["roomId"] == ctx["room_id"],
    }


@router.post("/api/v1/guest/access/{code}/unlock")
async def guest_unlock(code: str, payload: UnlockPayload, request: Request, resort_guest_session: str | None = Cookie(default=None)):
    ctx = await _guest_context(request, resort_guest_session)
    controller_url, controller_secret = _controller_config()
    grant_raw = secrets.token_urlsafe(24)
    grant_id = uuid.uuid4()
    expires = datetime.utcnow() + timedelta(seconds=30)

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            point = await _point_for_guest(conn, ctx, code)
            payment_id = None
            price = int(point["priceKgs"])
            if price > 0:
                if not payload.payment_id:
                    raise HTTPException(status_code=402, detail={"code": "PAYMENT_REQUIRED", "amount_kgs": price})
                payment = await conn.fetchrow(
                    '''SELECT id,"reservationId","amountKgs",status::text AS status FROM payments WHERE id=$1 FOR UPDATE''',
                    payload.payment_id,
                )
                if (
                    not payment
                    or payment["status"] != "RECEIVED"
                    or payment["reservationId"] != ctx["reservation_id"]
                    or int(payment["amountKgs"]) < price
                ):
                    raise HTTPException(status_code=409, detail="A RECEIVED payment for this stay is required")
                used = await conn.fetchval(
                    '''SELECT 1 FROM smart_access_grants WHERE "paymentId"=$1 AND status IN ('ISSUED','USED') LIMIT 1''',
                    payload.payment_id,
                )
                if used:
                    raise HTTPException(status_code=409, detail="Payment has already been used for access")
                payment_id = payment["id"]
            await conn.execute(
                '''INSERT INTO smart_access_grants
                   (id,"propertyId","accessPointId","reservationId","guestSessionId","paymentId","tokenHash",status,"expiresAt","createdAt")
                   VALUES ($1,$2,$3,$4,$5,$6,$7,'ISSUED',$8,now())''',
                grant_id, ctx["property_id"], point["id"], ctx["reservation_id"], ctx["session_id"], payment_id,
                _digest("access-grant", grant_raw), expires,
            )

    command = {
        "grant_id": str(grant_id),
        "access_point_code": point["code"],
        "controller_ref": point["controllerRef"],
        "action": "UNLOCK",
        "duration_seconds": 7,
        "expires_at": expires.isoformat() + "Z",
        "nonce": grant_raw,
    }
    body = json.dumps(command, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = _controller_signature(controller_secret, body)
    controller_ok = False
    controller_status = None
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            result = await client.post(
                f"{controller_url}/unlock", content=body,
                headers={"Content-Type": "application/json", "X-Resort-Signature": signature},
            )
            controller_status = result.status_code
            controller_ok = 200 <= result.status_code < 300
    except httpx.HTTPError:
        controller_ok = False

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                '''UPDATE smart_access_grants SET status=$2,"usedAt"=CASE WHEN $2='USED' THEN now() ELSE NULL END WHERE id=$1''',
                grant_id, "USED" if controller_ok else "REVOKED",
            )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'GUEST',$3,'SMART_ACCESS_UNLOCK','SmartAccessGrant',$4,'MY_STAY',$5,
                           jsonb_build_object('access_point_code',$6::text,'controller_http_status',$7::int),now())''',
                uuid.uuid4(), ctx["property_id"], str(ctx["session_id"]), str(grant_id),
                "SUCCESS" if controller_ok else "FAILED", point["code"], controller_status,
            )
    if not controller_ok:
        raise HTTPException(status_code=503, detail="Door controller did not confirm unlock")
    return {"ok": True, "access_point": point["code"], "unlocked_seconds": 7}
