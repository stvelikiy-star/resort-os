import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from .service_auth import require_automation_service
from .service_point_payments import ProviderConfirmation, confirm_provider_payment

MKASSA_API_BASE_URL = os.environ.get("MKASSA_API_BASE_URL", "https://api.mkassa.kg").rstrip("/")
MKASSA_API_KEY = os.environ.get("MKASSA_API_KEY", "").strip()
MKASSA_BRANCH_ID = os.environ.get("MKASSA_BRANCH_ID", "").strip()
MKASSA_CASHIER_ID = os.environ.get("MKASSA_CASHIER_ID", "").strip()
MKASSA_LONG_LIVING = os.environ.get("MKASSA_LONG_LIVING", "false").strip().lower() in {"1", "true", "yes", "on"}
MKASSA_SEND_METADATA = os.environ.get("MKASSA_SEND_METADATA", "true").strip().lower() in {"1", "true", "yes", "on"}

router = APIRouter(tags=["mkassa-payment-bridge"])


class BridgeIntentCreate(BaseModel):
    provider_code: str
    reference: str = Field(min_length=8, max_length=120)
    amount_kgs: int = Field(ge=1)
    currency: str
    service_point_code: str = Field(min_length=1, max_length=120)
    callback_path: str | None = None


class MKassaCallback(BaseModel):
    id: str = Field(min_length=1, max_length=180)
    status: str = Field(min_length=1, max_length=40)
    amount: str | int | float
    created_at: str | None = None
    paid_at: str | None = None
    metadata: dict[str, Any] | None = None


def _api_headers() -> dict[str, str]:
    if not MKASSA_API_KEY:
        raise HTTPException(status_code=503, detail={"code": "MKASSA_NOT_CONFIGURED"})
    return {"Authorization": f"api-key {MKASSA_API_KEY}"}


def _optional_int(value: str, name: str) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": f"{name}_INVALID"}) from exc


async def _mkassa_get_transaction(transaction_id: str) -> dict[str, Any]:
    url = f"{MKASSA_API_BASE_URL}/api/partners/transactions/{transaction_id}/"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=_api_headers())
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=500, detail={"code": "MKASSA_STATUS_NETWORK_ERROR"}) from exc
    if response.status_code >= 500:
        raise HTTPException(status_code=500, detail={"code": "MKASSA_STATUS_UPSTREAM_ERROR"})
    if response.status_code >= 300:
        raise HTTPException(status_code=409, detail={"code": f"MKASSA_STATUS_HTTP_{response.status_code}"})
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail={"code": "MKASSA_STATUS_INVALID_JSON"}) from exc


@router.post("/v1/service-point-payment-intents")
async def create_service_point_payment_intent(
    payload: BridgeIntentCreate,
    _: dict[str, Any] = Depends(require_automation_service),
):
    if payload.provider_code.strip().upper() != "MKASSA":
        raise HTTPException(status_code=400, detail={"code": "PAYMENT_PROVIDER_NOT_SUPPORTED"})
    if payload.currency.strip().upper() != "KGS":
        raise HTTPException(status_code=400, detail={"code": "PAYMENT_CURRENCY_NOT_SUPPORTED"})

    body: dict[str, Any] = {
        # MKassa API expects amount in tyiyn; Resort OS stores service-point prices in KGS.
        "amount": payload.amount_kgs * 100,
        "is_long_living": MKASSA_LONG_LIVING,
    }
    branch_id = _optional_int(MKASSA_BRANCH_ID, "MKASSA_BRANCH_ID")
    cashier_id = _optional_int(MKASSA_CASHIER_ID, "MKASSA_CASHIER_ID")
    if branch_id is not None:
        body["branch"] = branch_id
    if cashier_id is not None:
        body["cashier"] = cashier_id
    if MKASSA_SEND_METADATA:
        body["metadata"] = {
            "reference": payload.reference,
            "service_point": payload.service_point_code,
            "source": "THREE_CROWNS",
        }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{MKASSA_API_BASE_URL}/api/partners/transactions/init_payment/",
                headers={**_api_headers(), "Content-Type": "application/json"},
                json=body,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail={"code": "MKASSA_INIT_NETWORK_ERROR"}) from exc

    if response.status_code >= 300:
        raise HTTPException(
            status_code=503,
            detail={"code": f"MKASSA_INIT_HTTP_{response.status_code}", "body": response.text[:300]},
        )
    try:
        result = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail={"code": "MKASSA_INIT_INVALID_JSON"}) from exc

    transaction_id = str(result.get("id") or "").strip()
    payment_token = str(result.get("payment_token") or "").strip()
    if not transaction_id or not payment_token:
        raise HTTPException(status_code=503, detail={"code": "MKASSA_INIT_INVALID_RESPONSE"})

    return {
        "provider_payment_id": transaction_id,
        "checkout_url": payment_token,
        "qr_payload": payment_token,
        "provider_status": result.get("status"),
    }


@router.post("/api/v1/integrations/mkassa/callback")
async def mkassa_callback(payload: MKassaCallback, request: Request):
    # The supplied MKassa document does not define a callback signature or shared secret.
    # Therefore the callback is only a notification: payment truth is re-read server-to-server
    # from MKassa before Resort OS can transition to PAID or actuate a lock.
    if payload.status.strip().lower() != "paid":
        return {"status": "IGNORED", "reason": "NOT_PAID"}

    provider_tx = await _mkassa_get_transaction(payload.id)
    if str(provider_tx.get("id") or "") != payload.id:
        raise HTTPException(status_code=409, detail={"code": "MKASSA_TRANSACTION_ID_MISMATCH"})
    if str(provider_tx.get("status") or "").lower() != "paid":
        raise HTTPException(status_code=409, detail={"code": "MKASSA_TRANSACTION_NOT_PAID"})

    try:
        verified_tyiyn = int(provider_tx.get("amount"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={"code": "MKASSA_AMOUNT_INVALID"}) from exc

    metadata = payload.metadata or {}
    reference_hint = str(metadata.get("reference") or "").strip()

    async with request.app.state.db.acquire() as conn:
        row = await conn.fetchrow(
            '''SELECT id,reference,"providerCode","providerPaymentId","amountKgs",currency,status::text AS status
               FROM service_point_payment_intents
               WHERE "providerCode"='MKASSA' AND "providerPaymentId"=$1
               LIMIT 1''',
            payload.id,
        )
        if not row and reference_hint:
            row = await conn.fetchrow(
                '''SELECT id,reference,"providerCode","providerPaymentId","amountKgs",currency,status::text AS status
                   FROM service_point_payment_intents
                   WHERE "providerCode"='MKASSA' AND reference=$1
                   LIMIT 1''',
                reference_hint,
            )

    if not row:
        raise HTTPException(status_code=404, detail={"code": "MKASSA_INTENT_NOT_FOUND"})
    if verified_tyiyn != int(row["amountKgs"]) * 100:
        raise HTTPException(status_code=409, detail={"code": "MKASSA_AMOUNT_MISMATCH"})
    if row["providerPaymentId"] and row["providerPaymentId"] != payload.id:
        raise HTTPException(status_code=409, detail={"code": "MKASSA_PROVIDER_ID_MISMATCH"})

    # Duplicate successful callbacks must not create an automatic unlock retry after a
    # recorded unlock failure. Retry remains an explicit manager action in Resort OS.
    if row["status"] in {"UNLOCKED", "UNLOCK_PENDING", "UNLOCK_FAILED"}:
        return {"status": "ACCEPTED", "intent_status": row["status"], "idempotent": True}

    event_id = f"mkassa:{payload.id}:{payload.paid_at or provider_tx.get('paid_at') or 'paid'}"[:180]
    confirmation = ProviderConfirmation(
        reference=row["reference"],
        provider_payment_id=payload.id,
        amount_kgs=int(row["amountKgs"]),
        currency="KGS",
        status="PAID",
        event_id=event_id,
    )
    result = await confirm_provider_payment(
        provider_code="MKASSA",
        payload=confirmation,
        request=request,
        service={"actor_type": "SERVICE", "actor_id": "mkassa-verified-callback"},
    )
    return {"status": "ACCEPTED", "verified": True, "result": result}
