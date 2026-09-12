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

    The response includes read-only booking/stay lifecycle facts so n8n can build
    review queues for payment reminders, expired leads and post-stay campaigns
    without direct database access. Consent remains the outer fail-closed gate.
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
                   rr."checkIn" AS request_check_in,rr."checkOut" AS request_check_out,
                   rr."quotedTotalKgs",rr."requiredPrepaymentKgs",rr."createdAt" AS request_created_at,
                   rr."utmSource",rr."utmMedium",rr."utmCampaign",rr."utmContent",rr."utmTerm",
                   r.id AS reservation_id,r.status::text AS reservation_status,
                   r."checkIn" AS reservation_check_in,r."checkOut" AS reservation_check_out,
                   s.status::text AS stay_status,s."actualCheckInAt",s."actualCheckOutAt"
            FROM latest l
            LEFT JOIN reservation_requests rr ON rr.id=l."requestId" AND rr."propertyId"=$1
            LEFT JOIN reservations r ON r."requestId"=rr.id AND r."propertyId"=$1
            LEFT JOIN stays s ON s."reservationId"=r.id AND s."propertyId"=$1
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
                "request_check_in": row["request_check_in"],
                "request_check_out": row["request_check_out"],
                "request_created_at": row["request_created_at"],
                "quoted_total_kgs": row["quotedTotalKgs"],
                "required_prepayment_kgs": row["requiredPrepaymentKgs"],
                "reservation_id": str(row["reservation_id"]) if row["reservation_id"] else None,
                "reservation_status": row["reservation_status"],
                "reservation_check_in": row["reservation_check_in"],
                "reservation_check_out": row["reservation_check_out"],
                "stay_status": row["stay_status"],
                "actual_check_in_at": row["actualCheckInAt"],
                "actual_check_out_at": row["actualCheckOutAt"],
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
