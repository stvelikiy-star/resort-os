"""Isolated MARINA FLEX hotel onboarding API (no PMS linkage or billing).

Run as a separate process ONLY on a dedicated, isolated commercial database.
Provisioning accepts SUPER_ADMIN with verified MFA; new hotels remain PENDING.
It cannot link a hotel to a PMS instance, activate paid features, change an
existing hotel, issue invoices or touch any hotel operational database.

Application authentication is delegated to the read-only control plane.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from .flex_control_plane import (
    lifespan as read_lifespan,
    resolve_platform_principal,
)
from .flex_foundation import PlatformPrincipal


class HotelRegistration(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    display_name: str = Field(min_length=2, max_length=180)
    currency: Literal["KGS"] = "KGS"


async def _onboarding_writer_ready(pool) -> None:
    async with pool.acquire() as conn:
        elevated = await conn.fetchval(
            "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user"
        )
        if elevated:
            raise RuntimeError("Onboarding runtime must not bypass RLS")
        if not await conn.fetchval(
            "SELECT pg_has_role(current_user,'flex_onboarding_writer','MEMBER')"
        ):
            raise RuntimeError("Dedicated onboarding writer membership required")
        if await conn.fetchval(
            "SELECT pg_has_role(current_user,'flex_onboarding_writer','USAGE')"
        ):
            raise RuntimeError("Onboarding writer privileges must not be inherited")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with read_lifespan(app):
        await _onboarding_writer_ready(app.state.flex_pool)
        yield


app = FastAPI(
    title="MARINA FLEX Hotel Registration Preview",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get("/health")
async def health():
    return {"service": "marina-flex-onboarding", "status": "ok", "billable": False}


@app.post("/v1/onboarding/hotels", status_code=status.HTTP_201_CREATED)
async def register_hotel(
    payload: HotelRegistration,
    request: Request,
    response: Response,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=12,
        max_length=128,
        pattern=r"^[A-Za-z0-9._:-]+$",
    ),
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    if principal.role != "SUPER_ADMIN" or not principal.mfa_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="MFA Super Admin required")

    canonical = json.dumps(
        {"display_name": payload.display_name, "currency": payload.currency},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction():
            # A user-supplied idempotency key is namespaced under the DB-verified
            # actor. The database session never inherits this privileged role.
            await conn.execute(
                "SELECT set_config('flex.actor_subject_id',$1,true)",
                principal.subject_id,
            )
            await conn.execute("SET LOCAL ROLE flex_onboarding_writer")

            # A transaction-level lock prevents duplicate orphan PENDING hotels
            # when two registrations race with the same idempotency key.
            lock_label = principal.subject_id + ":" + idempotency_key
            await conn.fetchval(
                "SELECT pg_advisory_xact_lock(hashtextextended($1,0))", lock_label
            )
            previous = await conn.fetchrow(
                'SELECT hotel_id,payload_sha256 FROM flex_hotel_onboarding_requests '
                'WHERE actor_subject_id=$1 AND idempotency_key=$2 FOR UPDATE',
                principal.subject_id, idempotency_key,
            )
            if previous is not None:
                if previous["payload_sha256"].strip() != fingerprint:
                    raise HTTPException(
                        status.HTTP_409_CONFLICT,
                        detail="Idempotency-Key already used for different registration",
                    )
                response.status_code = status.HTTP_200_OK
                return {
                    "hotel_id": str(previous["hotel_id"]),
                    "status": "PENDING",
                    "billable": False,
                    "idempotent_replay": True,
                }

            hotel = await conn.fetchrow(
                "INSERT INTO flex_hotels(display_name,billing_currency,status) "
                "VALUES($1,$2,'PENDING') RETURNING id",
                payload.display_name, payload.currency,
            )
            hotel_id = hotel["id"]
            await conn.execute(
                "INSERT INTO flex_hotel_onboarding_requests("
                "actor_subject_id,idempotency_key,payload_sha256,hotel_id"
                ") VALUES($1,$2,$3,$4)",
                principal.subject_id, idempotency_key, fingerprint, hotel_id,
            )
            await conn.execute(
                "INSERT INTO flex_audit_events("
                "platform_subject_id,action,resource_type,resource_id,metadata"
                ") VALUES($1,'HOTEL_REGISTERED','FLEX_HOTEL',$2,$3::jsonb)",
                principal.subject_id, str(hotel_id),
                json.dumps({"name": payload.display_name, "currency": "KGS"}),
            )
            return {
                "hotel_id": str(hotel_id), "status": "PENDING",
                "billable": False, "idempotent_replay": False,
            }
