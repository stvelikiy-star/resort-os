from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/finance", tags=["admin-hotel-finance"])
manager_access = require_roles("OWNER", "MANAGER")


@router.get("/summary")
async def finance_summary(
    request: Request,
    from_date: date = Query(),
    to_date: date = Query(),
    user: dict[str, Any] = Depends(manager_access),
):
    if to_date < from_date:
        raise HTTPException(status_code=422, detail="to_date must be on or after from_date")
    if (to_date - from_date).days > 366:
        raise HTTPException(status_code=422, detail="finance report range cannot exceed 367 calendar days")
    end_exclusive = to_date + timedelta(days=1)

    async with request.app.state.db.acquire() as conn:
        prop = await conn.fetchrow(
            'SELECT id,timezone,currency FROM properties WHERE code=$1', user["property_code"]
        )
        if not prop:
            raise HTTPException(status_code=503, detail="Property not loaded")
        pid = prop["id"]

        period = await conn.fetchrow(
            '''
            SELECT
              COALESCE(SUM(p."amountKgs") FILTER (WHERE p.status='RECEIVED'),0)::bigint AS received_kgs,
              COUNT(*) FILTER (WHERE p.status='RECEIVED')::int AS received_count,
              COALESCE(SUM(p."amountKgs") FILTER (WHERE p.status='PENDING'),0)::bigint AS pending_created_kgs,
              COUNT(*) FILTER (WHERE p.status='PENDING')::int AS pending_created_count,
              COUNT(*) FILTER (WHERE p.status='FAILED')::int AS failed_count,
              COUNT(*) FILTER (WHERE p.status='CANCELLED')::int AS cancelled_count
            FROM payments p
            LEFT JOIN reservation_requests rr ON rr.id=p."requestId"
            LEFT JOIN reservations r ON r.id=p."reservationId"
            WHERE COALESCE(rr."propertyId",r."propertyId")=$1
              AND COALESCE(p."paidAt",p."createdAt") >= $2::date
              AND COALESCE(p."paidAt",p."createdAt") < $3::date
            ''',
            pid, from_date, end_exclusive,
        )

        by_method = await conn.fetch(
            '''
            SELECT COALESCE(NULLIF(trim(p.method),''),'UNKNOWN') AS method,
                   COALESCE(SUM(p."amountKgs"),0)::bigint AS amount_kgs,
                   COUNT(*)::int AS payment_count
            FROM payments p
            LEFT JOIN reservation_requests rr ON rr.id=p."requestId"
            LEFT JOIN reservations r ON r.id=p."reservationId"
            WHERE COALESCE(rr."propertyId",r."propertyId")=$1
              AND p.status='RECEIVED'
              AND p."paidAt" >= $2::date
              AND p."paidAt" < $3::date
            GROUP BY 1
            ORDER BY amount_kgs DESC,method
            ''',
            pid, from_date, end_exclusive,
        )

        daily = await conn.fetch(
            '''
            SELECT (p."paidAt" AT TIME ZONE $4)::date AS local_date,
                   COALESCE(SUM(p."amountKgs"),0)::bigint AS amount_kgs,
                   COUNT(*)::int AS payment_count
            FROM payments p
            LEFT JOIN reservation_requests rr ON rr.id=p."requestId"
            LEFT JOIN reservations r ON r.id=p."reservationId"
            WHERE COALESCE(rr."propertyId",r."propertyId")=$1
              AND p.status='RECEIVED'
              AND p."paidAt" >= $2::date
              AND p."paidAt" < $3::date
            GROUP BY 1
            ORDER BY 1
            ''',
            pid, from_date, end_exclusive, prop["timezone"],
        )

        active_reservations = await conn.fetchrow(
            '''
            WITH received AS (
              SELECT "reservationId",COALESCE(SUM("amountKgs"),0)::bigint AS received_kgs
              FROM payments
              WHERE status='RECEIVED' AND "reservationId" IS NOT NULL
              GROUP BY "reservationId"
            )
            SELECT COUNT(*)::int AS reservation_count,
                   COALESCE(SUM(r."totalKgs"),0)::bigint AS booked_total_kgs,
                   COALESCE(SUM(COALESCE(x.received_kgs,0)),0)::bigint AS received_kgs,
                   COALESCE(SUM(GREATEST(r."totalKgs"-COALESCE(x.received_kgs,0),0)),0)::bigint AS outstanding_kgs
            FROM reservations r
            LEFT JOIN received x ON x."reservationId"=r.id
            WHERE r."propertyId"=$1 AND r.status IN ('GUARANTEED','CHECKED_IN')
            ''',
            pid,
        )

        awaiting_requests = await conn.fetchrow(
            '''
            WITH received AS (
              SELECT "requestId",COALESCE(SUM("amountKgs"),0)::bigint AS received_kgs
              FROM payments
              WHERE status='RECEIVED' AND "requestId" IS NOT NULL
              GROUP BY "requestId"
            )
            SELECT COUNT(*)::int AS request_count,
                   COALESCE(SUM(COALESCE(rr."requiredPrepaymentKgs",0)),0)::bigint AS required_kgs,
                   COALESCE(SUM(COALESCE(x.received_kgs,0)),0)::bigint AS received_kgs,
                   COALESCE(SUM(GREATEST(COALESCE(rr."requiredPrepaymentKgs",0)-COALESCE(x.received_kgs,0),0)),0)::bigint AS remaining_kgs
            FROM reservation_requests rr
            LEFT JOIN received x ON x."requestId"=rr.id
            WHERE rr."propertyId"=$1 AND rr.status='AWAITING_PREPAYMENT'
            ''',
            pid,
        )

        refund_snapshot = await conn.fetchrow(
            '''
            SELECT COALESCE(SUM(p."amountKgs"),0)::bigint AS amount_kgs,COUNT(*)::int AS payment_count
            FROM payments p
            LEFT JOIN reservation_requests rr ON rr.id=p."requestId"
            LEFT JOIN reservations r ON r.id=p."reservationId"
            WHERE COALESCE(rr."propertyId",r."propertyId")=$1 AND p.status='REFUNDED'
            ''',
            pid,
        )

        recent = await conn.fetch(
            '''
            SELECT p.id,p."amountKgs",p.method,p.status::text AS status,p.provider,p."externalRef",p."paidAt",p."createdAt",
                   rr.id AS request_id,rr."guestName" AS request_guest,
                   res.id AS reservation_id,res."bookingNumber",g."firstName",g."lastName"
            FROM payments p
            LEFT JOIN reservation_requests rr ON rr.id=p."requestId"
            LEFT JOIN reservations res ON res.id=p."reservationId"
            LEFT JOIN guests g ON g.id=res."primaryGuestId"
            WHERE COALESCE(rr."propertyId",res."propertyId")=$1
            ORDER BY COALESCE(p."paidAt",p."createdAt") DESC,p."createdAt" DESC
            LIMIT 100
            ''',
            pid,
        )

    def reservation_guest(row):
        name = " ".join(part for part in [row["firstName"], row["lastName"]] if part)
        return name or row["request_guest"] or None

    return {
        "range": {"from": from_date, "to": to_date, "timezone": prop["timezone"], "currency": prop["currency"]},
        "period_payments": dict(period),
        "received_by_method": [dict(row) for row in by_method],
        "received_by_day": [dict(row) for row in daily],
        "active_reservations_snapshot": dict(active_reservations),
        "awaiting_prepayment_snapshot": dict(awaiting_requests),
        "refunded_snapshot_all_time": dict(refund_snapshot),
        "recent_payments": [
            {
                "id": str(row["id"]),
                "amount_kgs": row["amountKgs"],
                "method": row["method"],
                "status": row["status"],
                "provider": row["provider"],
                "external_ref": row["externalRef"],
                "paid_at": row["paidAt"],
                "created_at": row["createdAt"],
                "request_id": str(row["request_id"]) if row["request_id"] else None,
                "reservation_id": str(row["reservation_id"]) if row["reservation_id"] else None,
                "booking_number": row["bookingNumber"],
                "guest_name": reservation_guest(row),
            }
            for row in recent
        ],
        "truth": {
            "received": "Period received totals include Payment.status=RECEIVED using paidAt.",
            "pending": "Pending total is a payment-record snapshot for records created in the selected range; it is not recognized revenue.",
            "active_reservations": "Active reservation totals are a current snapshot of GUARANTEED/CHECKED_IN reservation values and received payment facts; they are not an accounting revenue-recognition report.",
            "refunds": "Current Payment model has REFUNDED status but no normalized refund timestamp, so refunded amount is shown only as an all-time snapshot, not attributed to the selected period.",
        },
    }
