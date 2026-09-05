import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from .auth import require_roles
from .guest_os import qr_svg
from .service_auth import AUTOMATION_SERVICE_KEY, require_automation_service
from .service_points import resolve_service_point

APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
PAYMENT_BRIDGE_URL = os.environ.get("SERVICE_POINT_PAYMENT_BRIDGE_URL", "").rstrip("/")
TTLOCK_API_BASE_URL = os.environ.get("TTLOCK_API_BASE_URL", "https://api.sciener.com").rstrip("/")
TTLOCK_CLIENT_ID = os.environ.get("TTLOCK_CLIENT_ID", "")
TTLOCK_ACCESS_TOKEN = os.environ.get("TTLOCK_ACCESS_TOKEN", "")
INTENT_TTL_MINUTES = max(3, min(int(os.environ.get("SERVICE_POINT_PAYMENT_TTL_MINUTES", "10")), 30))

admin_router = APIRouter(prefix="/api/v1/admin/service-point-payments", tags=["admin-service-point-payments"])
public_router = APIRouter(prefix="/api/v1/service-point-payments", tags=["service-point-payments"])
integration_router = APIRouter(prefix="/api/v1/integrations/service-point-payments", tags=["service-point-payment-integrations"])
admin_access = require_roles("OWNER", "MANAGER")


class AccessProfilePut(BaseModel):
    mode: Literal["FREE_REQUEST", "PAID_LOCK"]
    amount_kgs: int | None = Field(default=None, ge=1, le=1_000_000)
    provider_code: str | None = Field(default=None, min_length=2, max_length=40)
    lock_provider_code: str | None = Field(default=None, min_length=2, max_length=40)
    lock_external_id: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_paid_lock(self):
        if self.mode == "FREE_REQUEST":
            return self
        if not self.amount_kgs or not self.provider_code or not self.lock_provider_code or not self.lock_external_id:
            raise ValueError("PAID_LOCK requires amount, payment provider and lock configuration")
        if self.lock_provider_code.strip().upper() != "TTLOCK":
            raise ValueError("Only TTLOCK is implemented for automatic lock actuation")
        if not self.lock_external_id.strip().isdigit():
            raise ValueError("TTLOCK lock_external_id must be the numeric lockId")
        return self


class PublicIntentCreate(BaseModel):
    client_request_id: str = Field(min_length=8, max_length=180)


class ProviderConfirmation(BaseModel):
    reference: str = Field(min_length=8, max_length=120)
    provider_payment_id: str = Field(min_length=1, max_length=180)
    amount_kgs: int = Field(ge=1)
    currency: Literal["KGS"] = "KGS"
    status: Literal["PAID", "FAILED"]
    event_id: str | None = Field(default=None, max_length=180)


def _normalized_code(value: str | None) -> str | None:
    if value is None:
        return None
    clean = "".join(ch for ch in value.strip().upper() if ch.isalnum() or ch in {"_", "-"})
    return clean or None


def _bridge_url_is_allowed() -> bool:
    if not PAYMENT_BRIDGE_URL:
        return False
    parsed = urlparse(PAYMENT_BRIDGE_URL)
    if parsed.scheme == "https" and parsed.hostname:
        return True
    return APP_ENV != "production" and parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def _profile_readiness(row) -> dict[str, Any]:
    if not row or row["mode"] != "PAID_LOCK" or not row["isActive"]:
        return {"ready": False, "code": "PAID_ACCESS_NOT_ENABLED"}
    if not _bridge_url_is_allowed() or not AUTOMATION_SERVICE_KEY:
        return {"ready": False, "code": "PAYMENT_BRIDGE_NOT_CONFIGURED"}
    if row["lockProviderCode"].upper() == "TTLOCK" and (not TTLOCK_CLIENT_ID or not TTLOCK_ACCESS_TOKEN):
        return {"ready": False, "code": "TTLOCK_NOT_CONFIGURED"}
    return {"ready": True, "code": "READY"}


def _profile_payload(row) -> dict[str, Any]:
    if not row:
        return {
            "mode": "FREE_REQUEST",
            "is_active": True,
            "amount_kgs": None,
            "currency": "KGS",
            "provider_code": None,
            "lock_provider_code": None,
            "lock_external_id": None,
            "runtime": {"ready": False, "code": "PAID_ACCESS_NOT_ENABLED"},
        }
    return {
        "mode": row["mode"],
        "is_active": bool(row["isActive"]),
        "amount_kgs": row["amountKgs"],
        "currency": row["currency"],
        "provider_code": row["providerCode"],
        "lock_provider_code": row["lockProviderCode"],
        "lock_external_id": row["lockExternalId"],
        "runtime": _profile_readiness(row),
    }


def _intent_payload(row) -> dict[str, Any]:
    payment_qr_source = row.get("qrPayload") or row.get("checkoutUrl")
    return {
        "id": str(row["id"]),
        "reference": row["reference"],
        "provider_code": row["providerCode"],
        "provider_payment_id": row.get("providerPaymentId"),
        "amount_kgs": row["amountKgs"],
        "currency": row["currency"],
        "status": row["status"],
        "checkout_url": row.get("checkoutUrl"),
        "payment_qr_svg": qr_svg(payment_qr_source) if payment_qr_source else None,
        "paid_at": row.get("paidAt"),
        "expires_at": row["expiresAt"],
        "unlocked_at": row.get("unlockedAt"),
        "failure_code": row.get("failureCode"),
        "truth": "UNLOCK_REQUIRES_VERIFIED_PROVIDER_PAYMENT",
    }


async def _profile_row(conn, service_point_id: uuid.UUID):
    return await conn.fetchrow(
        '''SELECT "servicePointId","propertyId",mode::text AS mode,"amountKgs",currency,"providerCode",
                  "lockProviderCode","lockExternalId","isActive"
           FROM service_point_access_profiles WHERE "servicePointId"=$1''',
        service_point_id,
    )


async def _create_bridge_checkout(*, provider_code: str, reference: str, amount_kgs: int, service_point_code: str):
    if not _bridge_url_is_allowed() or not AUTOMATION_SERVICE_KEY:
        raise RuntimeError("PAYMENT_BRIDGE_NOT_CONFIGURED")
    payload = {
        "provider_code": provider_code,
        "reference": reference,
        "amount_kgs": amount_kgs,
        "currency": "KGS",
        "service_point_code": service_point_code,
        "callback_path": f"/api/v1/integrations/service-point-payments/{provider_code}/confirm",
    }
    headers = {"X-Resort-Service-Key": AUTOMATION_SERVICE_KEY}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(f"{PAYMENT_BRIDGE_URL}/v1/service-point-payment-intents", json=payload, headers=headers)
    if response.status_code >= 300:
        raise RuntimeError(f"PAYMENT_BRIDGE_HTTP_{response.status_code}")
    body = response.json()
    provider_payment_id = str(body.get("provider_payment_id") or "").strip()
    checkout_url = str(body.get("checkout_url") or "").strip() or None
    qr_payload = str(body.get("qr_payload") or "").strip() or None
    if not provider_payment_id or not (checkout_url or qr_payload):
        raise RuntimeError("PAYMENT_BRIDGE_INVALID_RESPONSE")
    if checkout_url and urlparse(checkout_url).scheme != "https" and APP_ENV == "production":
        raise RuntimeError("PAYMENT_BRIDGE_INSECURE_CHECKOUT_URL")
    return provider_payment_id, checkout_url, qr_payload


async def _ttlock_unlock(lock_external_id: str) -> tuple[bool, str | None, dict[str, Any]]:
    if not TTLOCK_CLIENT_ID or not TTLOCK_ACCESS_TOKEN:
        return False, "TTLOCK_NOT_CONFIGURED", {}
    if not lock_external_id.isdigit():
        return False, "TTLOCK_INVALID_LOCK_ID", {}
    data = {
        "clientId": TTLOCK_CLIENT_ID,
        "accessToken": TTLOCK_ACCESS_TOKEN,
        "lockId": lock_external_id,
        "date": str(int(time.time() * 1000)),
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{TTLOCK_API_BASE_URL}/v3/lock/unlock", data=data)
        body = response.json()
    except Exception:
        return False, "TTLOCK_NETWORK_ERROR", {}
    errcode = int(body.get("errcode", -1))
    if response.status_code < 300 and errcode == 0:
        return True, None, {"errcode": 0, "description": body.get("description")}
    return False, f"TTLOCK_{errcode}", {"errcode": errcode, "errmsg": body.get("errmsg")}


async def _attempt_unlock(request: Request, intent_id: uuid.UUID) -> dict[str, Any]:
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                '''SELECT i.id,i."propertyId",i."servicePointId",i.status::text AS status,i."paidAt",
                          p."lockProviderCode",p."lockExternalId",p."isActive"
                   FROM service_point_payment_intents i
                   JOIN service_point_access_profiles p ON p."servicePointId"=i."servicePointId"
                   WHERE i.id=$1 FOR UPDATE OF i,p''',
                intent_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail={"code": "SERVICE_POINT_PAYMENT_INTENT_NOT_FOUND"})
            if row["status"] == "UNLOCKED":
                return {"status": "UNLOCKED", "idempotent": True}
            if row["status"] not in {"PAID", "UNLOCK_FAILED"} or not row["paidAt"]:
                raise HTTPException(status_code=409, detail={"code": "PAYMENT_NOT_VERIFIED"})
            action_id = await conn.fetchval(
                '''INSERT INTO service_point_lock_actions (
                     id,"propertyId","servicePointId","intentId","providerCode","lockExternalId",status,attempts,"createdAt","updatedAt"
                   ) VALUES ($1,$2,$3,$4,$5,$6,'PENDING',1,now(),now())
                   ON CONFLICT ("intentId") DO UPDATE SET status='PENDING',attempts=service_point_lock_actions.attempts+1,
                     "lastErrorCode"=NULL,"updatedAt"=now()
                   RETURNING id''',
                uuid.uuid4(), row["propertyId"], row["servicePointId"], row["id"], row["lockProviderCode"], row["lockExternalId"],
            )
            await conn.execute(
                '''UPDATE service_point_payment_intents SET status='UNLOCK_PENDING',"unlockAttemptedAt"=now(),"failureCode"=NULL,"updatedAt"=now() WHERE id=$1''',
                intent_id,
            )
            lock_provider = row["lockProviderCode"].upper()
            lock_external_id = row["lockExternalId"]

    if lock_provider != "TTLOCK":
        success, error_code, result = False, "LOCK_PROVIDER_NOT_IMPLEMENTED", {}
    else:
        success, error_code, result = await _ttlock_unlock(lock_external_id)

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            if success:
                await conn.execute(
                    '''UPDATE service_point_lock_actions SET status='SUCCEEDED',"lastErrorCode"=NULL,"providerResultJson"=$2::jsonb,"updatedAt"=now() WHERE id=$1''',
                    action_id, json.dumps(result),
                )
                await conn.execute(
                    '''UPDATE service_point_payment_intents SET status='UNLOCKED',"unlockedAt"=now(),"failureCode"=NULL,"updatedAt"=now() WHERE id=$1''',
                    intent_id,
                )
                return {"status": "UNLOCKED", "idempotent": False}
            await conn.execute(
                '''UPDATE service_point_lock_actions SET status='FAILED',"lastErrorCode"=$2,"providerResultJson"=$3::jsonb,"updatedAt"=now() WHERE id=$1''',
                action_id, error_code, json.dumps(result),
            )
            await conn.execute(
                '''UPDATE service_point_payment_intents SET status='UNLOCK_FAILED',"failureCode"=$2,"updatedAt"=now() WHERE id=$1''',
                intent_id, error_code,
            )
    return {"status": "UNLOCK_FAILED", "failure_code": error_code}


@public_router.get("/points/{token}/profile")
async def public_access_profile(token: str, request: Request):
    async with request.app.state.db.acquire() as conn:
        point = await resolve_service_point(conn, token)
        if not point:
            raise HTTPException(status_code=404, detail={"code": "SERVICE_POINT_QR_NOT_FOUND"})
        profile = await _profile_row(conn, point["servicePointId"])
    payload = _profile_payload(profile)
    payload["service_point_code"] = point["code"]
    return payload


@public_router.post("/points/{token}/intents", status_code=status.HTTP_201_CREATED)
async def create_public_payment_intent(token: str, payload: PublicIntentCreate, request: Request):
    async with request.app.state.db.acquire() as conn:
        point = await resolve_service_point(conn, token)
        if not point:
            raise HTTPException(status_code=404, detail={"code": "SERVICE_POINT_QR_NOT_FOUND"})
        profile = await _profile_row(conn, point["servicePointId"])
        readiness = _profile_readiness(profile)
        if not readiness["ready"]:
            raise HTTPException(status_code=503, detail={"code": readiness["code"]})
        existing = await conn.fetchrow(
            '''SELECT id,reference,"providerCode","providerPaymentId","amountKgs",currency,status::text AS status,
                      "checkoutUrl","qrPayload","paidAt","expiresAt","unlockedAt","failureCode"
               FROM service_point_payment_intents WHERE "servicePointId"=$1 AND "clientRequestId"=$2''',
            point["servicePointId"], payload.client_request_id,
        )
        if existing:
            return _intent_payload(existing)
        intent_id = uuid.uuid4()
        reference = f"TCSP-{uuid.uuid4().hex[:20].upper()}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=INTENT_TTL_MINUTES)
        await conn.execute(
            '''INSERT INTO service_point_payment_intents (
                 id,"propertyId","servicePointId","clientRequestId",reference,"providerCode","amountKgs",currency,status,"expiresAt","createdAt","updatedAt"
               ) VALUES ($1,$2,$3,$4,$5,$6,$7,'KGS','CREATED',$8,now(),now())''',
            intent_id, point["propertyId"], point["servicePointId"], payload.client_request_id, reference,
            profile["providerCode"], profile["amountKgs"], expires_at,
        )

    try:
        provider_payment_id, checkout_url, qr_payload = await _create_bridge_checkout(
            provider_code=profile["providerCode"],
            reference=reference,
            amount_kgs=profile["amountKgs"],
            service_point_code=point["code"],
        )
    except Exception as exc:
        failure_code = str(exc)[:120]
        async with request.app.state.db.acquire() as conn:
            await conn.execute(
                '''UPDATE service_point_payment_intents SET status='PAYMENT_FAILED',"failureCode"=$2,"updatedAt"=now() WHERE id=$1''',
                intent_id, failure_code,
            )
        raise HTTPException(status_code=503, detail={"code": failure_code})

    async with request.app.state.db.acquire() as conn:
        row = await conn.fetchrow(
            '''UPDATE service_point_payment_intents
               SET status='AWAITING_PAYMENT',"providerPaymentId"=$2,"checkoutUrl"=$3,"qrPayload"=$4,"updatedAt"=now()
               WHERE id=$1
               RETURNING id,reference,"providerCode","providerPaymentId","amountKgs",currency,status::text AS status,
                         "checkoutUrl","qrPayload","paidAt","expiresAt","unlockedAt","failureCode"''',
            intent_id, provider_payment_id, checkout_url, qr_payload,
        )
    return _intent_payload(row)


@public_router.get("/points/{token}/intents/{intent_id}")
async def get_public_payment_intent(token: str, intent_id: uuid.UUID, request: Request):
    async with request.app.state.db.acquire() as conn:
        point = await resolve_service_point(conn, token)
        if not point:
            raise HTTPException(status_code=404, detail={"code": "SERVICE_POINT_QR_NOT_FOUND"})
        row = await conn.fetchrow(
            '''SELECT id,reference,"providerCode","providerPaymentId","amountKgs",currency,status::text AS status,
                      "checkoutUrl","qrPayload","paidAt","expiresAt","unlockedAt","failureCode"
               FROM service_point_payment_intents WHERE id=$1 AND "servicePointId"=$2''',
            intent_id, point["servicePointId"],
        )
        if not row:
            raise HTTPException(status_code=404, detail={"code": "SERVICE_POINT_PAYMENT_INTENT_NOT_FOUND"})
        if row["status"] == "AWAITING_PAYMENT" and row["expiresAt"] < datetime.now(timezone.utc):
            row = await conn.fetchrow(
                '''UPDATE service_point_payment_intents SET status='EXPIRED',"updatedAt"=now() WHERE id=$1
                   RETURNING id,reference,"providerCode","providerPaymentId","amountKgs",currency,status::text AS status,
                             "checkoutUrl","qrPayload","paidAt","expiresAt","unlockedAt","failureCode"''',
                intent_id,
            )
    return _intent_payload(row)


@integration_router.post("/{provider_code}/confirm")
async def confirm_provider_payment(
    provider_code: str,
    payload: ProviderConfirmation,
    request: Request,
    service: dict[str, Any] = Depends(require_automation_service),
):
    normalized_provider = _normalized_code(provider_code)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                '''SELECT id,"propertyId","servicePointId",reference,"providerCode","providerPaymentId","amountKgs",currency,
                          status::text AS status,"paidAt"
                   FROM service_point_payment_intents WHERE reference=$1 FOR UPDATE''',
                payload.reference,
            )
            if not row:
                raise HTTPException(status_code=404, detail={"code": "SERVICE_POINT_PAYMENT_INTENT_NOT_FOUND"})
            if row["providerCode"] != normalized_provider:
                raise HTTPException(status_code=409, detail={"code": "PAYMENT_PROVIDER_MISMATCH"})
            if row["amountKgs"] != payload.amount_kgs or row["currency"] != payload.currency:
                raise HTTPException(status_code=409, detail={"code": "PAYMENT_AMOUNT_MISMATCH"})
            if row["providerPaymentId"] and row["providerPaymentId"] != payload.provider_payment_id:
                raise HTTPException(status_code=409, detail={"code": "PAYMENT_PROVIDER_ID_MISMATCH"})

            await conn.execute(
                '''INSERT INTO service_point_payment_events (
                     id,"propertyId","intentId","providerCode","eventType","providerPaymentId","payloadJson","createdAt"
                   ) VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,now())''',
                uuid.uuid4(), row["propertyId"], row["id"], normalized_provider, payload.status, payload.provider_payment_id,
                json.dumps({"event_id": payload.event_id, "actor": service["actor_id"], "amount_kgs": payload.amount_kgs, "currency": payload.currency}),
            )

            if payload.status == "FAILED":
                if row["status"] not in {"PAID", "UNLOCK_PENDING", "UNLOCKED", "UNLOCK_FAILED"}:
                    await conn.execute(
                        '''UPDATE service_point_payment_intents SET status='PAYMENT_FAILED',"providerPaymentId"=$2,"failureCode"='PROVIDER_PAYMENT_FAILED',"updatedAt"=now() WHERE id=$1''',
                        row["id"], payload.provider_payment_id,
                    )
                return {"status": "PAYMENT_FAILED", "intent_id": str(row["id"])}

            if row["status"] in {"PAID", "UNLOCK_PENDING", "UNLOCKED", "UNLOCK_FAILED"}:
                paid_intent_id = row["id"]
            else:
                await conn.execute(
                    '''UPDATE service_point_payment_intents SET status='PAID',"providerPaymentId"=$2,"paidAt"=now(),"failureCode"=NULL,"updatedAt"=now() WHERE id=$1''',
                    row["id"], payload.provider_payment_id,
                )
                paid_intent_id = row["id"]

    unlock = await _attempt_unlock(request, paid_intent_id)
    return {"intent_id": str(paid_intent_id), "payment_status": "PAID", "unlock": unlock}


@admin_router.get("/profiles")
async def list_access_profiles(request: Request, user: dict[str, Any] = Depends(admin_access)):
    async with request.app.state.db.acquire() as conn:
        rows = await conn.fetch(
            '''SELECT sp.id AS service_point_id,sp.code,sp.name,
                      p."servicePointId",p."propertyId",p.mode::text AS mode,p."amountKgs",p.currency,p."providerCode",
                      p."lockProviderCode",p."lockExternalId",p."isActive"
               FROM service_points sp
               JOIN properties prop ON prop.id=sp."propertyId" AND prop.code=$1
               LEFT JOIN service_point_access_profiles p ON p."servicePointId"=sp.id
               ORDER BY sp.category,sp.name''',
            user["property_code"],
        )
    return {"items": [{"service_point_id": str(row["service_point_id"]), "code": row["code"], "name": row["name"], **_profile_payload(row if row["servicePointId"] else None)} for row in rows]}


@admin_router.put("/service-points/{point_id}")
async def put_access_profile(
    point_id: uuid.UUID,
    payload: AccessProfilePut,
    request: Request,
    user: dict[str, Any] = Depends(admin_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            point = await conn.fetchrow(
                '''SELECT sp.id,sp."propertyId" FROM service_points sp JOIN properties p ON p.id=sp."propertyId"
                   WHERE sp.id=$1 AND p.code=$2 FOR UPDATE OF sp''',
                point_id, user["property_code"],
            )
            if not point:
                raise HTTPException(status_code=404, detail={"code": "SERVICE_POINT_NOT_FOUND"})
            if payload.mode == "FREE_REQUEST":
                amount = provider = lock_provider = lock_external = None
            else:
                amount = payload.amount_kgs
                provider = _normalized_code(payload.provider_code)
                lock_provider = _normalized_code(payload.lock_provider_code)
                lock_external = payload.lock_external_id.strip() if payload.lock_external_id else None
            row = await conn.fetchrow(
                '''INSERT INTO service_point_access_profiles (
                     "servicePointId","propertyId",mode,"amountKgs",currency,"providerCode","lockProviderCode","lockExternalId","isActive","createdAt","updatedAt"
                   ) VALUES ($1,$2,$3::"ServicePointAccessMode",$4,'KGS',$5,$6,$7,$8,now(),now())
                   ON CONFLICT ("servicePointId") DO UPDATE SET mode=EXCLUDED.mode,"amountKgs"=EXCLUDED."amountKgs",
                     "providerCode"=EXCLUDED."providerCode","lockProviderCode"=EXCLUDED."lockProviderCode",
                     "lockExternalId"=EXCLUDED."lockExternalId","isActive"=EXCLUDED."isActive","updatedAt"=now()
                   RETURNING "servicePointId","propertyId",mode::text AS mode,"amountKgs",currency,"providerCode","lockProviderCode","lockExternalId","isActive"''',
                point_id, point["propertyId"], payload.mode, amount, provider, lock_provider, lock_external, payload.is_active,
            )
            await conn.execute(
                '''INSERT INTO audit_logs (
                     id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                   ) VALUES ($1,$2,'STAFF',$3,'CONFIGURE_PAID_ACCESS','ServicePoint',$4,'PMS','SUCCESS',$5::jsonb,now())''',
                uuid.uuid4(), point["propertyId"], user["id"], str(point_id),
                json.dumps({"mode": payload.mode, "amount_kgs": amount, "provider_code": provider, "lock_provider_code": lock_provider, "lock_external_id": lock_external, "is_active": payload.is_active}),
            )
    return _profile_payload(row)


@admin_router.get("/intents")
async def list_payment_intents(request: Request, limit: int = 100, user: dict[str, Any] = Depends(admin_access)):
    safe_limit = max(1, min(limit, 250))
    async with request.app.state.db.acquire() as conn:
        rows = await conn.fetch(
            '''SELECT i.id,i.reference,i."providerCode",i."providerPaymentId",i."amountKgs",i.currency,i.status::text AS status,
                      i."checkoutUrl",i."qrPayload",i."paidAt",i."expiresAt",i."unlockedAt",i."failureCode",
                      sp.code AS service_point_code,sp.name AS service_point_name
               FROM service_point_payment_intents i
               JOIN service_points sp ON sp.id=i."servicePointId"
               JOIN properties p ON p.id=i."propertyId" AND p.code=$1
               ORDER BY i."createdAt" DESC LIMIT $2''',
            user["property_code"], safe_limit,
        )
    return {"items": [{**_intent_payload(row), "service_point_code": row["service_point_code"], "service_point_name": row["service_point_name"]} for row in rows]}


@admin_router.post("/intents/{intent_id}/retry-unlock")
async def retry_unlock(intent_id: uuid.UUID, request: Request, user: dict[str, Any] = Depends(admin_access)):
    async with request.app.state.db.acquire() as conn:
        allowed = await conn.fetchval(
            '''SELECT 1 FROM service_point_payment_intents i JOIN properties p ON p.id=i."propertyId"
               WHERE i.id=$1 AND p.code=$2''',
            intent_id, user["property_code"],
        )
    if not allowed:
        raise HTTPException(status_code=404, detail={"code": "SERVICE_POINT_PAYMENT_INTENT_NOT_FOUND"})
    return await _attempt_unlock(request, intent_id)
