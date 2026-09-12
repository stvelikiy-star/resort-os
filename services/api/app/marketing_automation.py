import os
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request

from .service_auth import require_automation_service

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
MarketingChannel = Literal["WHATSAPP", "EMAIL", "SMS", "TELEGRAM", "PHONE"]

router = APIRouter(prefix="/api/v1/integrations/marketing", tags=["marketing-automation"])


async def property_id(conn):
    value = await conn.fetchval("SELECT id FROM properties WHERE code=$1", PROPERTY_CODE)
    if not value:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Property seed is not loaded")
    return value


@router.get("/audience")
async def automation_audience(
    request: Request,
    channel: MarketingChannel = Query(...),
    limit: int = Query(default=250, ge=1, le=1000),
    _service: dict[str, Any] = Depends(require_automation_service),
):
    """Return only contacts whose latest channel consent is OPTED_IN.

    This is the n8n/provider handoff. It intentionally uses service auth rather
    than a staff browser session and fails closed for missing consent or a later
    opt-out/unsubscribe event.
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
        "service_authenticated": True,
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
