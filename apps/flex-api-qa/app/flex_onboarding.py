"""Isolated MARINA FLEX hotel onboarding API (no PMS linkage or billing).

Run as a separate process ONLY on a dedicated, isolated commercial database.
Provisioning accepts SUPER_ADMIN with verified MFA; new hotels remain PENDING.
It cannot link a hotel to a PMS instance, activate paid features, change a hotel's lifecycle, issue invoices or touch any hotel operational database.

Application authentication is delegated to the read-only control plane.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from .flex_control_plane import (
    lifespan as read_lifespan,
    resolve_platform_principal,
    qa_password_reads,
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
    allow_qa_password = qa_password_reads() and os.environ.get("FLEX_ENABLE_QA_ONBOARDING") == "true"
    if principal.role != "SUPER_ADMIN" or not (principal.mfa_verified or allow_qa_password):
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
                'WHERE actor_subject_id=$1 AND idempotency_key=$2',
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



class HotelNameUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    display_name: str = Field(min_length=2, max_length=180, pattern=r"^[^\x00-\x1f\x7f]+$")
    expected_name: str = Field(min_length=1, max_length=180)


@app.post("/v1/onboarding/hotels/{hotel_id}/name")
async def update_hotel_name(
    hotel_id: uuid.UUID, payload: HotelNameUpdate, request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    allow_qa_password = qa_password_reads() and os.environ.get("FLEX_ENABLE_QA_ONBOARDING") == "true"
    if principal.role != "SUPER_ADMIN" or not (principal.mfa_verified or allow_qa_password):
        raise HTTPException(403, detail="Super Admin required")
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction():
            await _set_writer_context(conn, principal.subject_id)
            row = await conn.fetchrow(
                "SELECT display_name,status FROM flex_hotels WHERE id=$1 "
                "AND status IN ('PENDING','ACTIVE') FOR UPDATE", hotel_id)
            if row is None:
                raise HTTPException(404, detail="Editable hotel not found")
            if row["display_name"] != payload.expected_name:
                raise HTTPException(409, detail="Hotel name changed; reload")
            if row["display_name"] != payload.display_name:
                await conn.execute("UPDATE flex_hotels SET display_name=$2 WHERE id=$1",
                                   hotel_id, payload.display_name)
                await conn.execute(
                    "INSERT INTO flex_audit_events(platform_subject_id,action,resource_type,resource_id,metadata) "
                    "VALUES($1,'HOTEL_NAME_UPDATED','FLEX_HOTEL',$2,$3::jsonb)",
                    principal.subject_id, str(hotel_id),
                    json.dumps({"before": row["display_name"], "after": payload.display_name}))
            return {"hotel_id": str(hotel_id), "name": payload.display_name, "status": row["status"]}


class LinkChallengeRequest(BaseModel):
    """An admin REQUESTS proof; this does not establish a trusted hotel link."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    deployment_id: str = Field(min_length=4, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{3,99}$")
    property_external_id: str = Field(min_length=1, max_length=180)


class SignedLinkProof(BaseModel):
    model_config = ConfigDict(extra="forbid")
    signature_b64: str = Field(min_length=64, max_length=256, pattern=r"^[A-Za-z0-9_\-+/=]+$")


def _require_admin(principal: PlatformPrincipal) -> None:
    if principal.role != "SUPER_ADMIN" or not principal.mfa_verified:
        raise HTTPException(403, detail="MFA Super Admin required")


async def _set_writer_context(conn, subject: str) -> None:
    await conn.execute("SELECT set_config('flex.actor_subject_id',$1,true)", subject)
    await conn.execute("SET LOCAL ROLE flex_onboarding_writer")


def _link_message(*, challenge_id: str, hotel_id: str, deployment_id: str,
                  property_id: str, nonce: str, expires_at: datetime) -> str:
    """Stable signed bytes; PMS must derive each field from its trusted runtime."""
    expires_ms = int(expires_at.timestamp() * 1000)
    return "\n".join((
        "MARINA-FLEX-PMS-LINK-V1", challenge_id, hotel_id,
        deployment_id, property_id, nonce, str(expires_ms),
    ))


@app.post("/v1/onboarding/hotels/{hotel_id}/challenge", status_code=201)
async def request_verified_link(
    hotel_id: uuid.UUID,
    payload: LinkChallengeRequest,
    request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    _require_admin(principal)
    nonce = secrets.token_urlsafe(32)
    challenge_id = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    signed_message = _link_message(
        challenge_id=str(challenge_id), hotel_id=str(hotel_id),
        deployment_id=payload.deployment_id,
        property_id=payload.property_external_id,
        nonce=nonce, expires_at=expires_at,
    )
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction():
            await _set_writer_context(conn, principal.subject_id)
            hotel = await conn.fetchval(
                "SELECT status FROM flex_hotels WHERE id=$1", hotel_id
            )
            if hotel != "PENDING":
                raise HTTPException(404, detail="Pending commercial hotel not found")
            trusted = await conn.fetchval(
                "SELECT deployment_id FROM flex_trusted_deployments "
                "WHERE deployment_id=$1",
                payload.deployment_id,
            )
            if trusted is None:
                raise HTTPException(404, detail="Trusted deployment not found")
            await conn.execute(
                "INSERT INTO flex_hotel_link_challenges("
                "id,hotel_id,deployment_id,property_external_id,nonce,"
                "signed_message,expires_at,created_by"
                ") VALUES($1,$2,$3,$4,$5,$6,$7,$8)",
                challenge_id, hotel_id, payload.deployment_id,
                payload.property_external_id, nonce, signed_message,
                expires_at, principal.subject_id,
            )
    return {
        "challenge_id": str(challenge_id),
        "signed_message": signed_message,
        "expires_at": expires_at.isoformat(),
        "status": "AWAITING_TRUSTED_PMS_SIGNATURE",
    }


@app.post("/v1/onboarding/challenges/{challenge_id}/confirm")
async def confirm_verified_link(
    challenge_id: uuid.UUID,
    proof: SignedLinkProof,
    request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    _require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction():
            await _set_writer_context(conn, principal.subject_id)
            row = await conn.fetchrow(
                "SELECT c.hotel_id,c.deployment_id,c.property_external_id,"
                " c.signed_message,c.expires_at,c.consumed_at,d.public_key_pem "
                "FROM flex_hotel_link_challenges c "
                "JOIN flex_trusted_deployments d ON d.deployment_id=c.deployment_id "
                "WHERE c.id=$1", challenge_id,
            )
            if row is None:
                raise HTTPException(404, detail="Challenge not found")
            if row["consumed_at"] is not None:
                raise HTTPException(409, detail="Challenge already consumed")
            if datetime.now(timezone.utc) >= row["expires_at"]:
                raise HTTPException(410, detail="Challenge expired")
            try:
                key = load_pem_public_key(row["public_key_pem"].encode("utf-8"))
                if not isinstance(key, Ed25519PublicKey):
                    raise ValueError("Unsupported deployment key type")
                signature = base64.b64decode(
                    proof.signature_b64, altchars=b"-_", validate=True
                )
                if len(signature) != 64:
                    raise ValueError("Signature must be 64 bytes")
                key.verify(signature, row["signed_message"].encode("utf-8"))
            except (ValueError, InvalidSignature, binascii.Error):
                raise HTTPException(403, detail="Invalid trusted deployment proof") from None

            # CAS update acquires a row lock. Concurrent replays cannot link
            # twice, and all changes are rolled back if any unique link fails.
            consumed = await conn.fetchval(
                "UPDATE flex_hotel_link_challenges SET consumed_at=now() "
                "WHERE id=$1 AND consumed_at IS NULL AND expires_at>now() "
                "RETURNING consumed_at", challenge_id,
            )
            if consumed is None:
                raise HTTPException(409, detail="Challenge unavailable")
            try:
                await conn.execute(
                    "INSERT INTO flex_hotel_links("
                    "hotel_id,deployment_id,property_external_id,verified_at"
                    ") VALUES($1,$2,$3,now())",
                    row["hotel_id"], row["deployment_id"],
                    row["property_external_id"],
                )
            except Exception as exc:
                # A unique-conflict means another commercial hotel already
                # owns this deployment/property. Never reassign ownership.
                if getattr(exc, "sqlstate", None) == "23505":
                    raise HTTPException(409, detail="PMS property already linked") from None
                raise
            await conn.execute(
                "INSERT INTO flex_audit_events("
                "platform_subject_id,action,resource_type,resource_id,metadata"
                ") VALUES($1,'HOTEL_PMS_LINK_VERIFIED','FLEX_HOTEL',$2,$3::jsonb)",
                principal.subject_id, str(row["hotel_id"]),
                json.dumps({
                    "deployment_id": row["deployment_id"],
                    "property_external_id": row["property_external_id"],
                    "challenge_id": str(challenge_id),
                }),
            )
    return {
        "hotel_id": str(row["hotel_id"]),
        "deployment_id": row["deployment_id"],
        "property_external_id": row["property_external_id"],
        "link_status": "VERIFIED",
        "subscription_activated": False,
    }
