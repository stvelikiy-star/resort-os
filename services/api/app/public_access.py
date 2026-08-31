import hashlib
import hmac
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from .service_auth import require_automation_service
from .smart_access import _controller_config, _controller_signature

router = APIRouter(tags=["public-access"])
PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
PUBLIC_ACCESS_CHECKOUT_URL = os.environ.get("PUBLIC_ACCESS_CHECKOUT_URL", "").strip()
PUBLIC_ACCESS_INTENT_MINUTES = int(os.environ.get("PUBLIC_ACCESS_INTENT_MINUTES", "10"))
PUBLIC_ACCESS_UNLOCK_STALE_SECONDS = 45


class PublicIntentToken(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class PublicPaidCallback(BaseModel):
    amount_kgs: int = Field(gt=0, le=100000)
    provider: str = Field(min_length=2, max_length=80)
    external_ref: str = Field(min_length=2, max_length=180)


def _public_secret() -> bytes:
    value = os.environ.get("PUBLIC_ACCESS_TOKEN_SECRET", "")
    if len(value) < 32:
        raise HTTPException(status_code=503, detail="Public access security secret is not configured")
    return value.encode("utf-8")


def _token_hash(raw: str) -> str:
    return hmac.new(_public_secret(), f"public-access:{raw}".encode(), hashlib.sha256).hexdigest()


async def _property(conn):
    row = await conn.fetchrow('SELECT id,code,currency FROM properties WHERE code=$1', PROPERTY_CODE)
    if not row:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return row


async def _public_point(conn, property_id, code: str, lock: bool = False):
    suffix = " FOR UPDATE" if lock else ""
    point = await conn.fetchrow(
        f'''SELECT id,code,name,kind,"priceKgs",active,"controllerRef"
            FROM smart_access_points
            WHERE "propertyId"=$1 AND code=$2{suffix}''',
        property_id,
        code,
    )
    if not point or not point["active"] or point["kind"] not in {"TOILET", "OTHER"}:
        raise HTTPException(status_code=404, detail="Public access point is unavailable")
    return point


def _unlock_claim_is_stale(updated_at: datetime) -> bool:
    return updated_at.replace(tzinfo=None) <= datetime.utcnow() - timedelta(seconds=PUBLIC_ACCESS_UNLOCK_STALE_SECONDS)


async def _recover_stale_unlock_claim(conn, intent_id: uuid.UUID, access_point_id: uuid.UUID, updated_at: datetime) -> bool:
    if not _unlock_claim_is_stale(updated_at):
        return False
    recovered = await conn.fetchval(
        '''UPDATE public_access_payment_intents
           SET status='PAID',"updatedAt"=now()
           WHERE id=$1 AND status='UNLOCKING' AND "updatedAt"=$2
           RETURNING id''',
        intent_id,
        updated_at,
    )
    if not recovered:
        return False
    await conn.execute(
        '''UPDATE smart_access_grants
           SET status='EXPIRED'
           WHERE "accessPointId"=$1 AND status='ISSUED' AND "expiresAt"<=now()''',
        access_point_id,
    )
    return True


@router.get("/api/v1/public/access/{code}")
async def public_access_quote(code: str, request: Request):
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn)
        point = await _public_point(conn, prop["id"], code)
    return {
        "code": point["code"],
        "name": point["name"],
        "kind": point["kind"],
        "price_kgs": int(point["priceKgs"]),
        "currency": prop["currency"],
        "payment_required": int(point["priceKgs"]) > 0,
    }


@router.post("/api/v1/public/access/{code}/checkout", status_code=status.HTTP_201_CREATED)
async def create_public_access_checkout(code: str, request: Request):
    if not PUBLIC_ACCESS_CHECKOUT_URL:
        raise HTTPException(status_code=503, detail="Public access payment provider is not configured")
    _public_secret()
    raw_token = secrets.token_urlsafe(32)
    intent_id = uuid.uuid4()
    expires_at = datetime.utcnow() + timedelta(minutes=max(2, min(PUBLIC_ACCESS_INTENT_MINUTES, 30)))

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn)
            point = await _public_point(conn, prop["id"], code, lock=True)
            amount = int(point["priceKgs"])
            if amount <= 0:
                raise HTTPException(status_code=409, detail="This public access point does not require payment")
            await conn.execute(
                '''INSERT INTO public_access_payment_intents
                   (id,"propertyId","accessPointId","tokenHash","amountKgs",status,"expiresAt","createdAt","updatedAt")
                   VALUES($1,$2,$3,$4,$5,'PENDING',$6,now(),now())''',
                intent_id, prop["id"], point["id"], _token_hash(raw_token), amount, expires_at,
            )
            await conn.execute(
                '''INSERT INTO audit_logs(id,"propertyId","actorType",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES($1,$2,'PUBLIC','CREATE_ACCESS_PAYMENT_INTENT','PublicAccessPaymentIntent',$3,'PUBLIC_QR','SUCCESS',
                   jsonb_build_object('access_point_code',$4::text,'amount_kgs',$5::int),now())''',
                uuid.uuid4(), prop["id"], str(intent_id), point["code"], amount,
            )

    query = urlencode({"intent_id": str(intent_id), "amount_kgs": amount, "currency": "KGS", "access_point": code})
    separator = "&" if "?" in PUBLIC_ACCESS_CHECKOUT_URL else "?"
    return {
        "intent_id": str(intent_id),
        "token": raw_token,
        "amount_kgs": amount,
        "expires_at": expires_at,
        "checkout_url": f"{PUBLIC_ACCESS_CHECKOUT_URL}{separator}{query}",
        "truth": "Access remains locked until Resort Core receives an authenticated PAID callback from the payment bridge.",
    }


@router.post("/api/v1/public/access/intents/{intent_id}/status")
async def public_access_intent_status(intent_id: uuid.UUID, payload: PublicIntentToken, request: Request):
    token_hash = _token_hash(payload.token)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                '''SELECT pai.status,pai."amountKgs",pai."expiresAt",pai."updatedAt",pai."accessPointId",ap.code,ap.name
                   FROM public_access_payment_intents pai
                   JOIN smart_access_points ap ON ap.id=pai."accessPointId"
                   WHERE pai.id=$1 AND pai."tokenHash"=$2
                   FOR UPDATE OF pai''',
                intent_id, token_hash,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Access payment intent not found")
            state = row["status"]
            if state == "UNLOCKING" and await _recover_stale_unlock_claim(
                conn, intent_id, row["accessPointId"], row["updatedAt"]
            ):
                state = "PAID"
            if row["expiresAt"].replace(tzinfo=None) <= datetime.utcnow() and state == "PENDING":
                await conn.execute("UPDATE public_access_payment_intents SET status='EXPIRED',\"updatedAt\"=now() WHERE id=$1", intent_id)
                state = "EXPIRED"
    return {"intent_id": str(intent_id), "status": state, "amount_kgs": int(row["amountKgs"]), "access_point": row["code"], "name": row["name"]}


@router.post("/api/v1/automation/public-access/{intent_id}/paid")
async def mark_public_access_paid(
    intent_id: uuid.UUID,
    payload: PublicPaidCallback,
    request: Request,
    service: dict[str, Any] = Depends(require_automation_service),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                '''SELECT id,"propertyId","amountKgs",status,"expiresAt",provider,"externalRef"
                   FROM public_access_payment_intents WHERE id=$1 FOR UPDATE''', intent_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Public access payment intent not found")
            if int(row["amountKgs"]) != payload.amount_kgs:
                raise HTTPException(status_code=409, detail="Paid amount does not match access price")
            if row["status"] in {"PAID", "UNLOCKING", "USED"}:
                if row["provider"] != payload.provider or row["externalRef"] != payload.external_ref:
                    raise HTTPException(status_code=409, detail="Payment callback conflicts with existing payment fact")
                return {"ok": True, "idempotent": True, "status": row["status"]}
            if row["expiresAt"].replace(tzinfo=None) <= datetime.utcnow():
                if row["status"] == "PENDING":
                    await conn.execute("UPDATE public_access_payment_intents SET status='EXPIRED',\"updatedAt\"=now() WHERE id=$1", intent_id)
                raise HTTPException(status_code=409, detail="Payment intent expired")
            if row["status"] != "PENDING":
                raise HTTPException(status_code=409, detail=f"Intent cannot be paid from {row['status']}")
            duplicate = await conn.fetchval(
                '''SELECT id FROM public_access_payment_intents
                   WHERE provider=$1 AND "externalRef"=$2 AND id<>$3 LIMIT 1''',
                payload.provider, payload.external_ref, intent_id,
            )
            if duplicate:
                raise HTTPException(status_code=409, detail="Provider payment reference is already used")
            await conn.execute(
                '''UPDATE public_access_payment_intents SET status='PAID',provider=$2,"externalRef"=$3,"paidAt"=now(),"updatedAt"=now() WHERE id=$1''',
                intent_id, payload.provider, payload.external_ref,
            )
            await conn.execute(
                '''INSERT INTO audit_logs(id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES($1,$2,'SERVICE',$3,'CONFIRM_PUBLIC_ACCESS_PAYMENT','PublicAccessPaymentIntent',$4,'PAYMENT_BRIDGE','SUCCESS',
                   jsonb_build_object('provider',$5::text,'external_ref',$6::text,'amount_kgs',$7::int),now())''',
                uuid.uuid4(), row["propertyId"], service["actor_id"], str(intent_id), payload.provider, payload.external_ref, payload.amount_kgs,
            )
    return {"ok": True, "idempotent": False, "status": "PAID"}


@router.post("/api/v1/public/access/intents/{intent_id}/unlock")
async def unlock_public_access(intent_id: uuid.UUID, payload: PublicIntentToken, request: Request):
    token_hash = _token_hash(payload.token)
    grant_raw = secrets.token_urlsafe(24)
    grant_id = uuid.uuid4()
    grant_expires = datetime.utcnow() + timedelta(seconds=30)

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                '''SELECT pai.id,pai."propertyId",pai."accessPointId",pai.status,pai."expiresAt",pai."updatedAt",
                          ap.code,ap.kind,ap.active,ap."controllerRef"
                   FROM public_access_payment_intents pai
                   JOIN smart_access_points ap ON ap.id=pai."accessPointId"
                   WHERE pai.id=$1 AND pai."tokenHash"=$2 FOR UPDATE OF pai,ap''',
                intent_id, token_hash,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Access payment intent not found")
            current_status = row["status"]
            if current_status == "UNLOCKING" and await _recover_stale_unlock_claim(
                conn, intent_id, row["accessPointId"], row["updatedAt"]
            ):
                current_status = "PAID"
            if current_status != "PAID":
                raise HTTPException(status_code=409, detail=f"Access payment cannot unlock from {current_status}")
            if row["expiresAt"].replace(tzinfo=None) <= datetime.utcnow():
                raise HTTPException(status_code=409, detail="Access payment intent expired")
            if not row["active"] or row["kind"] not in {"TOILET", "OTHER"}:
                raise HTTPException(status_code=409, detail="Access point is disabled")

            # Fail before claiming the paid intent when the physical controller is unavailable.
            controller_url, controller_secret = _controller_config()
            claimed = await conn.fetchval(
                '''UPDATE public_access_payment_intents
                   SET status='UNLOCKING',"updatedAt"=now()
                   WHERE id=$1 AND status='PAID'
                   RETURNING id''',
                intent_id,
            )
            if not claimed:
                raise HTTPException(status_code=409, detail="Another unlock attempt is already in progress")
            await conn.execute(
                '''INSERT INTO smart_access_grants(id,"propertyId","accessPointId","tokenHash",status,"expiresAt","createdAt")
                   VALUES($1,$2,$3,$4,'ISSUED',$5,now())''',
                grant_id, row["propertyId"], row["accessPointId"], _token_hash(grant_raw), grant_expires,
            )

    command = {
        "grant_id": str(grant_id), "access_point_code": row["code"], "controller_ref": row["controllerRef"],
        "action": "UNLOCK", "duration_seconds": 7, "expires_at": grant_expires.isoformat()+"Z", "nonce": grant_raw,
    }
    body = json.dumps(command, separators=(",", ":"), sort_keys=True).encode()
    signature = _controller_signature(controller_secret, body)
    controller_ok = False
    controller_status = None
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.post(
                f"{controller_url}/unlock", content=body,
                headers={"Content-Type": "application/json", "X-Resort-Signature": signature},
            )
            controller_status = response.status_code
            controller_ok = 200 <= response.status_code < 300
    except httpx.HTTPError:
        controller_ok = False

    finalization_ok = True
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                '''UPDATE smart_access_grants SET status=$2,"usedAt"=CASE WHEN $2='USED' THEN now() ELSE NULL END WHERE id=$1''',
                grant_id, "USED" if controller_ok else "REVOKED",
            )
            if controller_ok:
                finalized = await conn.fetchval(
                    '''UPDATE public_access_payment_intents
                       SET status='USED',"usedAt"=now(),"updatedAt"=now()
                       WHERE id=$1 AND status='UNLOCKING'
                       RETURNING id''',
                    intent_id,
                )
                finalization_ok = bool(finalized)
            else:
                await conn.execute(
                    '''UPDATE public_access_payment_intents
                       SET status='PAID',"updatedAt"=now()
                       WHERE id=$1 AND status='UNLOCKING' ''',
                    intent_id,
                )
            await conn.execute(
                '''INSERT INTO audit_logs(id,"propertyId","actorType",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES($1,$2,'PUBLIC','SMART_ACCESS_UNLOCK','SmartAccessGrant',$3,'PUBLIC_QR',$4,
                   jsonb_build_object('access_point_code',$5::text,'controller_http_status',$6::int,'finalization_ok',$7::boolean),now())''',
                uuid.uuid4(), row["propertyId"], str(grant_id),
                "SUCCESS" if controller_ok and finalization_ok else "FAILED", row["code"], controller_status, finalization_ok,
            )
    if not controller_ok:
        raise HTTPException(status_code=503, detail="Door controller did not confirm unlock")
    if not finalization_ok:
        raise HTTPException(status_code=500, detail="Door opened but access state finalization failed; retry is blocked")
    return {"ok": True, "status": "USED", "access_point": row["code"], "unlocked_seconds": 7}
