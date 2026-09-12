import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from .auth import require_roles

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
DEFAULT_POLICY_VERSION = os.environ.get("MARKETING_POLICY_VERSION", "2026-09-12")

router = APIRouter(prefix="/api/v1/admin/marketing", tags=["admin-marketing"])
manager_access = require_roles("OWNER", "MANAGER")

MarketingChannel = Literal["WHATSAPP", "EMAIL", "SMS", "TELEGRAM", "PHONE"]


class ConsentPayload(BaseModel):
    channel: MarketingChannel
    opted_in: bool
    source: str = Field(min_length=2, max_length=80)
    policy_version: str = Field(default=DEFAULT_POLICY_VERSION, min_length=2, max_length=80)
    proof: str | None = Field(default=None, max_length=500)


class TouchpointPayload(BaseModel):
    channel: Literal["WHATSAPP", "EMAIL", "SMS", "TELEGRAM", "PHONE", "OTHER"]
    event_type: str = Field(min_length=2, max_length=80)
    direction: Literal["INBOUND", "OUTBOUND", "INTERNAL"] = "OUTBOUND"
    status: str = Field(default="RECORDED", min_length=2, max_length=80)
    campaign_code: str | None = Field(default=None, max_length=120)
    provider_message_id: str | None = Field(default=None, max_length=220)
    metadata: dict[str, Any] | None = None


async def property_id(conn) -> uuid.UUID:
    value = await conn.fetchval("SELECT id FROM properties WHERE code=$1", PROPERTY_CODE)
    if not value:
        raise HTTPException(status_code=503, detail="Property seed is not loaded")
    return value


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        raise HTTPException(status_code=422, detail="Lead has no usable phone number")
    return f"+{digits}"


async def request_identity(conn, pid: uuid.UUID, request_id: uuid.UUID):
    row = await conn.fetchrow(
        '''
        SELECT rr.id,rr."guestName",rr.phone,rr.email,r."primaryGuestId" AS guest_id
        FROM reservation_requests rr
        LEFT JOIN reservations r ON r."requestId"=rr.id
        WHERE rr.id=$1 AND rr."propertyId"=$2
        ''',
        request_id,
        pid,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Reservation request not found")
    return row


def serialize_consent(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "request_id": str(row["requestId"]) if row["requestId"] else None,
        "guest_id": str(row["guestId"]) if row["guestId"] else None,
        "contact_key": row["contactKey"],
        "channel": row["channel"],
        "status": row["status"],
        "source": row["source"],
        "policy_version": row["policyVersion"],
        "proof": row["proof"],
        "occurred_at": row["occurredAt"],
        "created_by_staff_id": str(row["createdByStaffId"]) if row["createdByStaffId"] else None,
    }


@router.post("/requests/{request_id}/consent", status_code=status.HTTP_201_CREATED)
async def record_consent(
    request_id: uuid.UUID,
    payload: ConsentPayload,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn)
            identity = await request_identity(conn, pid, request_id)
            channel = payload.channel.upper()
            if channel == "EMAIL":
                if not identity["email"]:
                    raise HTTPException(status_code=422, detail="Lead has no email")
                contact_key = identity["email"].strip().lower()
            else:
                contact_key = normalize_phone(identity["phone"])

            consent_id = uuid.uuid4()
            consent_status = "OPTED_IN" if payload.opted_in else "OPTED_OUT"
            await conn.execute(
                '''
                INSERT INTO marketing_consents (
                  id,"propertyId","requestId","guestId","contactKey",channel,status,source,
                  "policyVersion",proof,"occurredAt","createdByStaffId","createdAt"
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,now(),$11,now())
                ''',
                consent_id,
                pid,
                request_id,
                identity["guest_id"],
                contact_key,
                channel,
                consent_status,
                payload.source.strip(),
                payload.policy_version.strip(),
                payload.proof.strip() if payload.proof else None,
                user["id"],
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,$4,'MarketingConsent',$5,'PMS','SUCCESS',
                  jsonb_build_object('request_id',$6::text,'channel',$7::text,'status',$8::text,'source',$9::text,'policy_version',$10::text),now())
                ''',
                uuid.uuid4(),
                pid,
                user["id"],
                "MARKETING_OPT_IN" if payload.opted_in else "MARKETING_OPT_OUT",
                str(consent_id),
                str(request_id),
                channel,
                consent_status,
                payload.source.strip(),
                payload.policy_version.strip(),
            )
            row = await conn.fetchrow('SELECT * FROM marketing_consents WHERE id=$1', consent_id)
    return serialize_consent(row)


@router.post("/requests/{request_id}/touchpoints", status_code=status.HTTP_201_CREATED)
async def record_touchpoint(
    request_id: uuid.UUID,
    payload: TouchpointPayload,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn)
            identity = await request_identity(conn, pid, request_id)
            touchpoint_id = uuid.uuid4()
            await conn.execute(
                '''
                INSERT INTO marketing_touchpoints (
                  id,"propertyId","requestId","guestId","campaignCode",channel,direction,"eventType",status,
                  "providerMessageId","metadataJson","occurredAt","createdByStaffId","createdAt"
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,now(),$12,now())
                ''',
                touchpoint_id,
                pid,
                request_id,
                identity["guest_id"],
                payload.campaign_code.strip() if payload.campaign_code else None,
                payload.channel,
                payload.direction,
                payload.event_type.strip().upper(),
                payload.status.strip().upper(),
                payload.provider_message_id.strip() if payload.provider_message_id else None,
                None if payload.metadata is None else __import__("json").dumps(payload.metadata, ensure_ascii=False),
                user["id"],
            )
    return {"id": str(touchpoint_id), "recorded": True}


@router.get("/requests/{request_id}/history")
async def request_marketing_history(
    request_id: uuid.UUID,
    request: Request,
    _user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn)
        await request_identity(conn, pid, request_id)
        consents = await conn.fetch(
            '''SELECT * FROM marketing_consents WHERE "propertyId"=$1 AND "requestId"=$2 ORDER BY "occurredAt" DESC''',
            pid,
            request_id,
        )
        touchpoints = await conn.fetch(
            '''
            SELECT id,"requestId","guestId","campaignCode",channel,direction,"eventType",status,
                   "providerMessageId","metadataJson","occurredAt","createdByStaffId"
            FROM marketing_touchpoints
            WHERE "propertyId"=$1 AND "requestId"=$2
            ORDER BY "occurredAt" DESC
            ''',
            pid,
            request_id,
        )
    return {
        "consents": [serialize_consent(row) for row in consents],
        "touchpoints": [
            {
                "id": str(row["id"]),
                "campaign_code": row["campaignCode"],
                "channel": row["channel"],
                "direction": row["direction"],
                "event_type": row["eventType"],
                "status": row["status"],
                "provider_message_id": row["providerMessageId"],
                "metadata": row["metadataJson"],
                "occurred_at": row["occurredAt"],
                "created_by_staff_id": str(row["createdByStaffId"]) if row["createdByStaffId"] else None,
            }
            for row in touchpoints
        ],
    }


@router.get("/audience")
async def safe_audience(
    request: Request,
    channel: MarketingChannel = Query(...),
    limit: int = Query(default=250, ge=1, le=1000),
    _user: dict[str, Any] = Depends(manager_access),
):
    """Return only contacts whose latest consent for this channel is OPTED_IN.

    This endpoint is the future n8n handoff. It deliberately excludes contacts with
    no consent and contacts whose most recent event is an opt-out.
    """
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn)
        rows = await conn.fetch(
            '''
            WITH latest AS (
              SELECT DISTINCT ON ("contactKey", channel)
                     "contactKey",channel,status,"requestId","guestId","occurredAt","policyVersion",source
              FROM marketing_consents
              WHERE "propertyId"=$1 AND channel=$2
              ORDER BY "contactKey",channel,"occurredAt" DESC,"createdAt" DESC
            )
            SELECT l."contactKey",l.channel,l."occurredAt",l."policyVersion",l.source,
                   rr.id AS request_id,rr."guestName",rr.phone,rr.email,rr.status::text AS request_status,
                   rr."utmSource",rr."utmMedium",rr."utmCampaign",rr."utmContent",rr."utmTerm"
            FROM latest l
            LEFT JOIN reservation_requests rr ON rr.id=l."requestId" AND rr."propertyId"=$1
            WHERE l.status='OPTED_IN'
            ORDER BY l."occurredAt" DESC
            LIMIT $3
            ''',
            pid,
            channel,
            limit,
        )
    return {
        "channel": channel,
        "consent_required": True,
        "count": len(rows),
        "items": [
            {
                "contact_key": row["contactKey"],
                "request_id": str(row["request_id"]) if row["request_id"] else None,
                "guest_name": row["guestName"],
                "phone": row["phone"],
                "email": row["email"],
                "request_status": row["request_status"],
                "consented_at": row["occurredAt"],
                "policy_version": row["policyVersion"],
                "consent_source": row["source"],
                "utm_source": row["utmSource"],
                "utm_medium": row["utmMedium"],
                "utm_campaign": row["utmCampaign"],
                "utm_content": row["utmContent"],
                "utm_term": row["utmTerm"],
            }
            for row in rows
        ],
    }


@router.get("/summary")
async def marketing_summary(
    request: Request,
    _user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn)
        consent_rows = await conn.fetch(
            '''
            WITH latest AS (
              SELECT DISTINCT ON ("contactKey",channel) "contactKey",channel,status
              FROM marketing_consents
              WHERE "propertyId"=$1
              ORDER BY "contactKey",channel,"occurredAt" DESC,"createdAt" DESC
            )
            SELECT channel,status,count(*)::int AS count
            FROM latest
            GROUP BY channel,status
            ORDER BY channel,status
            ''',
            pid,
        )
        touchpoints_30d = await conn.fetchval(
            '''SELECT count(*)::int FROM marketing_touchpoints WHERE "propertyId"=$1 AND "occurredAt">=now()-interval '30 days' ''',
            pid,
        )
        attributed_30d = await conn.fetchval(
            '''
            SELECT count(*)::int FROM reservation_requests
            WHERE "propertyId"=$1 AND "createdAt">=now()-interval '30 days'
              AND ("utmSource" IS NOT NULL OR "utmCampaign" IS NOT NULL)
            ''',
            pid,
        )
    return {
        "generated_at": datetime.now(timezone.utc),
        "consents": [dict(row) for row in consent_rows],
        "touchpoints_30d": touchpoints_30d or 0,
        "attributed_leads_30d": attributed_30d or 0,
    }
