from datetime import date, timedelta
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/finance", tags=["admin-hotel-finance"])
manager_access = require_roles("OWNER", "MANAGER")
LEDGER_PREVIEW_LIMIT = 500


class PaymentRequirementPayload(BaseModel):
    amount_kgs: int = Field(gt=0)


def reservation_ledger_item(row) -> dict[str, Any]:
    total = int(row["totalKgs"] or 0)
    received = int(row["received_kgs"] or 0)
    remaining = max(total - received, 0)
    overpaid = max(received - total, 0)
    status = row["status"]
    if status == "CHECKED_OUT":
        balance_stage = "CHECKED_OUT_BALANCE"
    elif status == "CHECKED_IN":
        balance_stage = "IN_HOUSE"
    elif status == "GUARANTEED":
        balance_stage = "PRE_ARRIVAL"
    else:
        balance_stage = "CANCELLED"
    guest_name = " ".join(part for part in [row["firstName"], row["lastName"]] if part) or None
    return {
        "reservation_id": str(row["id"]),
        "booking_number": row["bookingNumber"],
        "status": status,
        "check_in": row["checkIn"],
        "check_out": row["checkOut"],
        "guest_name": guest_name,
        "guest_phone": row["phone"],
        "room_code": row["room_code"],
        "total_kgs": total,
        "received_kgs": received,
        "remaining_kgs": remaining,
        "overpaid_kgs": overpaid,
        "received_payment_count": int(row["received_count"] or 0),
        "last_received_at": row["last_received_at"],
        "balance_stage": balance_stage,
    }


@router.post("/requests/{request_id}/payment-requirement")
async def set_payment_requirement(
    request_id: uuid.UUID,
    payload: PaymentRequirementPayload,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    """Persist the manager's explicit required prepayment amount.

    This is a commercial instruction only. It never creates a Payment and never
    guarantees a Reservation. The payment method remains the manager's choice
    when an actual payment fact is later recorded.
    """
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await conn.fetchrow('SELECT id FROM properties WHERE code=$1', user["property_code"])
            if not prop:
                raise HTTPException(status_code=503, detail="Property not loaded")
            pid = prop["id"]
            row = await conn.fetchrow(
                '''
                SELECT id,status::text AS status,"quotedTotalKgs","requiredPrepaymentKgs"
                FROM reservation_requests
                WHERE id=$1 AND "propertyId"=$2
                FOR UPDATE
                ''',
                request_id,
                pid,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Reservation request not found")
            if row["status"] not in {"QUOTED", "AWAITING_PREPAYMENT"}:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "PAYMENT_REQUIREMENT_REQUEST_NOT_QUOTED", "request_status": row["status"]},
                )
            if row["quotedTotalKgs"] is None:
                raise HTTPException(status_code=409, detail={"code": "PAYMENT_REQUIREMENT_QUOTE_REQUIRED"})
            quoted_total = int(row["quotedTotalKgs"])
            if payload.amount_kgs > quoted_total:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "PAYMENT_REQUIREMENT_EXCEEDS_QUOTE",
                        "quoted_total_kgs": quoted_total,
                        "requested_kgs": payload.amount_kgs,
                    },
                )
            before = int(row["requiredPrepaymentKgs"]) if row["requiredPrepaymentKgs"] is not None else None
            await conn.execute(
                '''UPDATE reservation_requests
                   SET status='AWAITING_PREPAYMENT',"requiredPrepaymentKgs"=$1,"updatedAt"=now()
                   WHERE id=$2''',
                payload.amount_kgs,
                request_id,
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"beforeJson","afterJson","createdAt"
                ) VALUES (
                  $1,$2,'STAFF',$3,'SET_PAYMENT_REQUIREMENT','ReservationRequest',$4,'FINANCE_CONTROL','SUCCESS',
                  jsonb_build_object('required_prepayment_kgs',$5::int),
                  jsonb_build_object(
                    'required_prepayment_kgs',$6::int,'quoted_total_kgs',$7::int,
                    'authority','OWNER_MANAGER','automatic_payment','NONE','automatic_reservation','NONE'
                  ),now()
                )
                ''',
                uuid.uuid4(),
                pid,
                user["id"],
                str(request_id),
                before,
                payload.amount_kgs,
                quoted_total,
            )
    return {
        "request_id": str(request_id),
        "status": "AWAITING_PREPAYMENT",
        "quoted_total_kgs": quoted_total,
        "required_prepayment_kgs": payload.amount_kgs,
        "payment_method": "MANAGER_DECIDES",
        "payment_created": False,
        "reservation_created": False,
        "truth": "Manager-set payment requirement only. Resort OS did not collect or confirm money and did not create a reservation.",
    }


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
    end_exclusive_date = to_date + timedelta(days=1)

    async with request.app.state.db.acquire() as conn:
        prop = await conn.fetchrow(
            'SELECT id,timezone,currency FROM properties WHERE code=$1', user["property_code"]
        )
        if not prop:
            raise HTTPException(status_code=503, detail="Property not loaded")
        pid = prop["id"]

        # Prisma DateTime columns in the current PostgreSQL baseline are TIMESTAMP(3)
        # without timezone and are treated as UTC-naive storage by Resort Core.
        # Convert property-local midnight to the matching UTC-naive timestamp before
        # sending it back through asyncpg; this avoids aware/naive binding drift.
        bounds = await conn.fetchrow(
            '''SELECT (($1::date::timestamp AT TIME ZONE $3) AT TIME ZONE 'UTC') AS from_ts,
                      (($2::date::timestamp AT TIME ZONE $3) AT TIME ZONE 'UTC') AS to_ts''',
            from_date,
            end_exclusive_date,
            prop["timezone"],
        )
        from_ts = bounds["from_ts"]
        to_ts = bounds["to_ts"]

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
              AND COALESCE(p."paidAt",p."createdAt") >= $2
              AND COALESCE(p."paidAt",p."createdAt") < $3
            ''',
            pid,
            from_ts,
            to_ts,
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
              AND COALESCE(p."paidAt",p."createdAt") >= $2
              AND COALESCE(p."paidAt",p."createdAt") < $3
            GROUP BY 1
            ORDER BY amount_kgs DESC,method
            ''',
            pid,
            from_ts,
            to_ts,
        )

        daily = await conn.fetch(
            '''
            SELECT ((COALESCE(p."paidAt",p."createdAt") AT TIME ZONE 'UTC') AT TIME ZONE $4)::date AS local_date,
                   COALESCE(SUM(p."amountKgs"),0)::bigint AS amount_kgs,
                   COUNT(*)::int AS payment_count
            FROM payments p
            LEFT JOIN reservation_requests rr ON rr.id=p."requestId"
            LEFT JOIN reservations r ON r.id=p."reservationId"
            WHERE COALESCE(rr."propertyId",r."propertyId")=$1
              AND p.status='RECEIVED'
              AND COALESCE(p."paidAt",p."createdAt") >= $2
              AND COALESCE(p."paidAt",p."createdAt") < $3
            GROUP BY 1
            ORDER BY 1
            ''',
            pid,
            from_ts,
            to_ts,
            prop["timezone"],
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

        # IMPORTANT: no SQL row limit is applied before receivable/exception calculation.
        # Operational snapshots must be complete even after years of reservation history.
        ledger_rows = await conn.fetch(
            '''
            WITH payment_stats AS (
              SELECT "reservationId",
                     COALESCE(SUM("amountKgs") FILTER (WHERE status='RECEIVED'),0)::bigint AS received_kgs,
                     COUNT(*) FILTER (WHERE status='RECEIVED')::int AS received_count,
                     MAX(COALESCE("paidAt","createdAt")) FILTER (WHERE status='RECEIVED') AS last_received_at
              FROM payments
              WHERE "reservationId" IS NOT NULL
              GROUP BY "reservationId"
            )
            SELECT r.id,r."bookingNumber",r.status::text AS status,r."checkIn",r."checkOut",r."totalKgs",
                   g."firstName",g."lastName",g.phone,
                   COALESCE(ps.received_kgs,0)::bigint AS received_kgs,
                   COALESCE(ps.received_count,0)::int AS received_count,
                   ps.last_received_at,
                   COALESCE(actual_room.code,scheduled_room.code) AS room_code
            FROM reservations r
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            LEFT JOIN payment_stats ps ON ps."reservationId"=r.id
            LEFT JOIN stays s ON s."reservationId"=r.id
            LEFT JOIN LATERAL (
              SELECT room.code
              FROM room_assignments ra
              JOIN rooms room ON room.id=ra."roomId"
              WHERE ra."stayId"=s.id
              ORDER BY ra."startedAt" DESC
              LIMIT 1
            ) actual_room ON true
            LEFT JOIN LATERAL (
              SELECT room.code
              FROM inventory_blocks ib
              JOIN rooms room ON room.id=ib."roomId"
              WHERE ib."reservationId"=r.id AND ib.active=true AND ib."blockType"='RESERVATION'
              ORDER BY ib."startDate",ib."endDate"
              LIMIT 1
            ) scheduled_room ON true
            WHERE r."propertyId"=$1
              AND r.status IN ('GUARANTEED','CHECKED_IN','CHECKED_OUT','CANCELLED')
            ORDER BY r."checkOut" DESC,r."createdAt" DESC
            ''',
            pid,
        )
        reservation_ledger = [reservation_ledger_item(row) for row in ledger_rows]
        debtors = [
            item for item in reservation_ledger
            if item["status"] in {"GUARANTEED", "CHECKED_IN", "CHECKED_OUT"} and item["remaining_kgs"] > 0
        ]
        debtors.sort(
            key=lambda item: (
                0 if item["status"] == "CHECKED_OUT" else 1 if item["status"] == "CHECKED_IN" else 2,
                -item["remaining_kgs"],
                str(item["check_out"]),
            )
        )
        receivables_snapshot = {
            "debtor_count": len(debtors),
            "outstanding_kgs": sum(item["remaining_kgs"] for item in debtors),
            "checked_out_count": sum(1 for item in debtors if item["status"] == "CHECKED_OUT"),
            "checked_out_kgs": sum(item["remaining_kgs"] for item in debtors if item["status"] == "CHECKED_OUT"),
            "in_house_count": sum(1 for item in debtors if item["status"] == "CHECKED_IN"),
            "in_house_kgs": sum(item["remaining_kgs"] for item in debtors if item["status"] == "CHECKED_IN"),
            "pre_arrival_count": sum(1 for item in debtors if item["status"] == "GUARANTEED"),
            "pre_arrival_kgs": sum(item["remaining_kgs"] for item in debtors if item["status"] == "GUARANTEED"),
        }
        overpaid_items = [item for item in reservation_ledger if item["overpaid_kgs"] > 0]
        cancelled_with_received = [
            item for item in reservation_ledger if item["status"] == "CANCELLED" and item["received_kgs"] > 0
        ]
        exception_snapshot = {
            "overpaid_count": len(overpaid_items),
            "overpaid_kgs": sum(item["overpaid_kgs"] for item in overpaid_items),
            "cancelled_with_received_count": len(cancelled_with_received),
            "cancelled_with_received_kgs": sum(item["received_kgs"] for item in cancelled_with_received),
        }
        ledger_preview = reservation_ledger[:LEDGER_PREVIEW_LIMIT]
        ledger_meta = {
            "total_count": len(reservation_ledger),
            "returned_count": len(ledger_preview),
            "preview_limit": LEDGER_PREVIEW_LIMIT,
            "truncated": len(reservation_ledger) > LEDGER_PREVIEW_LIMIT,
            "snapshot_calculation_complete": True,
        }

        recent = await conn.fetch(
            '''
            SELECT p.id,p."amountKgs",p.method,p.status::text AS status,p.provider,p."externalRef",
                   p.metadata->>'note' AS note,p.metadata->>'recorded_by_staff_id' AS recorded_by_staff_id,
                   p."paidAt",p."createdAt",
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
        "scope": {
            "internal_only": True,
            "payment_collection": "MANAGER_MANUAL",
            "manager_decides_prepayment": True,
            "automated_acquiring_required": False,
            "accounting_report": False,
        },
        "range": {
            "from": from_date,
            "to": to_date,
            "timezone": prop["timezone"],
            "currency": prop["currency"],
            "storage_timezone": "UTC",
            "from_timestamp": from_ts,
            "to_timestamp_exclusive": to_ts,
        },
        "period_payments": dict(period),
        "received_by_method": [dict(row) for row in by_method],
        "received_by_day": [dict(row) for row in daily],
        "active_reservations_snapshot": dict(active_reservations),
        "receivables_snapshot": receivables_snapshot,
        "debtors": debtors,
        "reservation_ledger": ledger_preview,
        "reservation_ledger_meta": ledger_meta,
        "finance_exceptions": {
            "snapshot": exception_snapshot,
            "overpaid_reservations": overpaid_items,
            "cancelled_with_received": cancelled_with_received,
        },
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
                "note": row["note"],
                "recorded_by_staff_id": row["recorded_by_staff_id"],
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
            "received": "Period received totals include only stored Payment.status=RECEIVED facts. Property-local calendar boundaries are converted to UTC-naive timestamps because the committed PostgreSQL baseline stores Prisma DateTime values as TIMESTAMP(3) without timezone.",
            "pending": "Pending total is an internal payment-record snapshot; it is not recognized revenue and does not mean automation is collecting payment.",
            "active_reservations": "Active reservation totals are a current internal snapshot of GUARANTEED/CHECKED_IN reservation values and stored RECEIVED payment facts; they are not an accounting revenue-recognition report.",
            "receivables": "Debtor counts and amounts are calculated over the complete GUARANTEED/CHECKED_IN/CHECKED_OUT reservation ledger. A CHECKED_OUT balance remains visible for operational follow-up regardless of historical ledger size.",
            "ledger": "The reservation_ledger response is a newest-first preview capped for payload size; reservation_ledger_meta declares truncation. Receivable and exception snapshots are calculated before that preview cap.",
            "exceptions": "Overpayment and cancelled-reservation-with-received-payment flags are complete operational reconciliation exceptions, not automatic refund decisions.",
            "refunds": "Current Payment model has REFUNDED status but no normalized refund timestamp, so refunded amount is shown only as an all-time snapshot, not attributed to the selected period.",
            "collection": "Prepayment amount and payment method remain manager-owned. Setting a requirement does not create a Payment or Reservation; AI/n8n have no payment-confirmation authority.",
        },
    }
