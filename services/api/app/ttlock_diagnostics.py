import os
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import require_roles

APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
TTLOCK_API_BASE_URL = os.environ.get("TTLOCK_API_BASE_URL", "https://api.sciener.com").rstrip("/")
TTLOCK_CLIENT_ID = os.environ.get("TTLOCK_CLIENT_ID", "")
TTLOCK_ACCESS_TOKEN = os.environ.get("TTLOCK_ACCESS_TOKEN", "")

router = APIRouter(prefix="/api/v1/admin/ttlock", tags=["admin-ttlock-diagnostics"])
admin_access = require_roles("OWNER", "MANAGER")


def _endpoint_allowed(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme == "https" and parsed.hostname:
        return True
    return APP_ENV != "production" and parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def _form(lock_id: str) -> dict[str, str]:
    return {
        "clientId": TTLOCK_CLIENT_ID,
        "accessToken": TTLOCK_ACCESS_TOKEN,
        "lockId": lock_id,
        "date": str(int(time.time() * 1000)),
    }


async def _provider_post(path: str, data: dict[str, str]) -> tuple[int | None, dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{TTLOCK_API_BASE_URL}{path}", data=data)
        try:
            body = response.json()
        except Exception:
            return response.status_code, {"error": "NON_JSON_PROVIDER_RESPONSE"}
        return response.status_code, body if isinstance(body, dict) else {"error": "INVALID_PROVIDER_RESPONSE"}
    except Exception:
        return None, {"error": "TTLOCK_NETWORK_ERROR"}


def _provider_error(body: dict[str, Any]) -> dict[str, Any] | None:
    if "errcode" not in body:
        return None
    try:
        code = int(body.get("errcode", -1))
    except (TypeError, ValueError):
        code = -1
    if code == 0:
        return None
    return {"code": code, "message": body.get("errmsg") or body.get("description")}


@router.get("/profiles/{service_point_id}/diagnostics")
async def ttlock_profile_diagnostics(
    service_point_id: str,
    request: Request,
    user: dict[str, Any] = Depends(admin_access),
):
    """Read-only TTLock readiness check for one configured service point.

    It never unlocks or locks anything. The probe verifies that the configured
    credentials can read the exact lock and that the gateway can answer the
    documented queryOpenState endpoint. Provider secrets are never returned.
    """
    if not _endpoint_allowed(TTLOCK_API_BASE_URL):
        raise HTTPException(status_code=503, detail={"code": "TTLOCK_ENDPOINT_NOT_ALLOWED"})
    if not TTLOCK_CLIENT_ID or not TTLOCK_ACCESS_TOKEN:
        raise HTTPException(status_code=503, detail={"code": "TTLOCK_NOT_CONFIGURED"})

    async with request.app.state.db.acquire() as conn:
        row = await conn.fetchrow(
            '''
            SELECT sp.id,sp.code,sp.name,p."lockProviderCode",p."lockExternalId",p.mode::text AS mode,p."isActive"
            FROM service_points sp
            JOIN properties prop ON prop.id=sp."propertyId" AND prop.code=$1
            LEFT JOIN service_point_access_profiles p ON p."servicePointId"=sp.id
            WHERE sp.id::text=$2
            ''',
            user["property_code"],
            service_point_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail={"code": "SERVICE_POINT_NOT_FOUND"})
    if row["mode"] != "PAID_LOCK" or not row["isActive"]:
        raise HTTPException(status_code=409, detail={"code": "PAID_ACCESS_NOT_ENABLED"})
    if (row["lockProviderCode"] or "").upper() != "TTLOCK":
        raise HTTPException(status_code=409, detail={"code": "LOCK_PROVIDER_NOT_IMPLEMENTED"})
    lock_id = str(row["lockExternalId"] or "").strip()
    if not lock_id.isdigit():
        raise HTTPException(status_code=409, detail={"code": "TTLOCK_INVALID_LOCK_ID"})

    detail_http, detail = await _provider_post("/v3/lock/detail", _form(lock_id))
    detail_error = _provider_error(detail)
    detail_ok = bool(detail_http is not None and detail_http < 300 and not detail_error and str(detail.get("lockId")) == lock_id)

    state_http, state = await _provider_post("/v3/lock/queryOpenState", _form(lock_id))
    state_error = _provider_error(state)
    state_value = state.get("state") if state_http is not None and state_http < 300 and not state_error else None
    gateway_ok = state_value in {0, 1, 2}

    return {
        "service_point_id": str(row["id"]),
        "service_point_code": row["code"],
        "service_point_name": row["name"],
        "lock_id": lock_id,
        "provider": "TTLOCK",
        "endpoint": TTLOCK_API_BASE_URL,
        "credentials_configured": True,
        "lock_visible": detail_ok,
        "gateway_query_ok": gateway_ok,
        "ready_for_supervised_unlock_uat": detail_ok and gateway_ok,
        "lock": {
            "name": detail.get("lockName") if detail_ok else None,
            "alias": detail.get("lockAlias") if detail_ok else None,
            "battery": detail.get("electricQuantity") if detail_ok else None,
            "model": detail.get("modelNum") if detail_ok else None,
        },
        "open_state": state_value,
        "detail_error": detail_error or (detail.get("error") if not detail_ok else None),
        "gateway_error": state_error or (state.get("error") if not gateway_ok else None),
        "truth": "READ_ONLY_PROVIDER_DIAGNOSTIC_NO_LOCK_ACTUATION",
    }
