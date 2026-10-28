import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from .auth import require_roles
from .payment_idempotency import (
    ensure_same_payment_payload,
    lock_payment_identity,
    normalize_optional_text,
    normalize_required_text,
)

router = APIRouter(prefix="/api/v1/admin/booking", tags=["admin-reservation-payments"])
payment_access = require_roles("OWNER", "MANAGER", module_grant=False)


class ReservationPaymentPayload(BaseModel):
    amount_kgs: int = Field(gt=0)
    method: str = Field(min_length=2, max_length=80)
    paid_at: datetime | None = None
    external_ref: str | None = Field(default=None, max_length=180)
    note: str | None = Field(default=None, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=180)


def utc_aware(value: datetime | None) -> datetime:
    """Return a canonical UTC-aware timestamp for validation/API/audit semantics."""
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def prisma_timestamp(value: datetime) -> datetime:
    """Convert UTC-aware time to Prisma's PostgreSQL TIMESTAMP(3) representation.

    The canonical schema currently maps Prisma DateTime to `timestamp without time zone`.
    Asyncpg therefore requires a naive datetime at the DB boundary. We retain the UTC
    meaning explicitly everywhere else and strip tzinfo only for the bind parameter.
    """
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def public_timestamp(value: datetime | None) -> datetime | None:
    """Restore the schema's stored UTC-naive timestamp to explicit UTC for API output."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def _totals(conn, reservation_id: uuid.UUID):
    row = await conn.fetchrow(
        '''
        SELECT r."totalKgs",
               COALESCE(sum(p."amountKgs") FILTER (WHERE p.status='RECEIVED'),0)::int AS paid_kgs
        FROM reservations r
        LEFT JOIN payments p ON p."reservationId"=r.id
        WHERE r.id=$1
        GROUP BY r.id,r."totalKgs"
        ''',
        reservation_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Reservation not found")
    total = int(row["totalKgs"])
    paid = int(row["paid_kgs"])
    return {
        "total_kgs": total,
        "paid_kgs": paid,
        "remaining_kgs": max(total - paid, 0),
        "overpaid_kgs": max(paid - total, 0),
    }


@router.get("/reservations/{reservation_id}/acquiring-readiness")
async def reservation_acquiring_readiness(
    reservation_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(payment_access),
):
    """Server-side payment readiness without claiming that a bank is connected.

    Reuses canonical reservation payments; never creates a charge, payment,
    external provider link or confirmed booking.
    """
    async with request.app.state.db.acquire() as conn:
        pid = await conn.fetchval("SELECT id FROM properties WHERE code=$1", user["property_code"])
        if not pid:
            raise HTTPException(status_code=503, detail="Property not loaded")
        row = await conn.fetchrow(
            '''SELECT id,"bookingNumber",status::text AS status,"totalKgs"
               FROM reservations WHERE id=$1 AND "propertyId"=$2''',
            reservation_id, pid,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Reservation not found")
        totals = await _totals(conn, reservation_id)
    closed = row["status"] in {"CANCELLED", "NO_SHOW"}
    remaining = 0 if closed else totals["remaining_kgs"]
    return {
        "reservation_id": str(reservation_id),
        "booking_number": row["bookingNumber"],
        "status": row["status"],
        "currency": "KGS",
        "total_kgs": totals["total_kgs"],
        "paid_kgs": totals["paid_kgs"],
        "remaining_kgs": remaining,
        "remaining_tyiyn": remaining * 100,
        "overpaid_kgs": totals["overpaid_kgs"],
        "payment_collection_eligible": remaining > 0 and not closed,
        "provider_connected": False,
        "payment_link": None,
        "provider_code": None,
        "acquiring_status": "NOT_CONFIGURED",
        "message": "No bank merchant integration configured. Amount is based on existing PMS payment records; no payment was initiated.",
    }


@router.get("/reservations/{reservation_id}/cancellation-finance-review")
async def cancellation_finance_review(
    reservation_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(payment_access),
):
    """Read-only decision support. Not a refund instruction or cancellation."""
    async with request.app.state.db.acquire() as conn:
        pid = await conn.fetchval(
            "SELECT id FROM properties WHERE code=$1", user["property_code"],
        )
        if not pid:
            raise HTTPException(status_code=503, detail="Property not loaded")
        reservation = await conn.fetchrow(
            """SELECT id,"bookingNumber",status::text AS status,"totalKgs"
               FROM reservations WHERE id=$1 AND "propertyId"=$2""",
            reservation_id, pid,
        )
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        rows = await conn.fetch(
            """SELECT status::text AS status,"amountKgs",provider,method
               FROM payments WHERE "reservationId"=$1""", reservation_id,
        )
        stays = await conn.fetchval(
            'SELECT count(*) FROM stays WHERE "reservationId"=$1', reservation_id,
        )
        charges = await conn.fetchrow(
            """SELECT count(*) FILTER (WHERE status NOT IN ('WAIVED','VOID'))::int AS open_count,
                      COALESCE(sum("amountKgs") FILTER (WHERE status NOT IN ('WAIVED','VOID')),0)::bigint AS open_kgs
               FROM guest_folio_charges WHERE "propertyId"=$1 AND "reservationId"=$2""",
            pid, reservation_id,
        )
    received = sum(int(p["amountKgs"]) for p in rows if p["status"] == "RECEIVED")
    refunded = sum(int(p["amountKgs"]) for p in rows if p["status"] == "REFUNDED")
    pending = sum(int(p["amountKgs"]) for p in rows if p["status"] == "PENDING")
    has_payment_history = bool(rows)
    has_stay = bool(stays)
    has_open_charges = bool(charges["open_count"])
    source_payment_methods = sorted({p["method"] for p in rows})
    return {
        "reservation_id": str(reservation_id),
        "booking_number": reservation["bookingNumber"],
        "status": reservation["status"],
        "currency": "KGS",
        "accommodation_original_kgs": int(reservation["totalKgs"]),
        "received_kgs": received,
        "already_refunded_kgs": refunded,
        "pending_kgs": pending,
        "payment_count": len(rows),
        "payment_methods": source_payment_methods,
        "open_folio_charge_count": int(charges["open_count"]),
        "open_folio_charge_kgs": int(charges["open_kgs"]),
        "has_stay_history": has_stay,
        "requires_manual_review": has_payment_history or has_stay or has_open_charges,
        "unpaid_cancel_path_eligible": (
            reservation["status"] == "GUARANTEED"
            and not has_payment_history and not has_stay and not has_open_charges
        ),
        "refund_executed": False,
        "refund_available": False,
        "next_action": "MANUAL_FINANCE_REVIEW" if has_payment_history or has_stay or has_open_charges else "CHECK_CANCELLATION_ELIGIBILITY",
        "truth": "Read-only stored payment and folio facts; refunded status is not independent bank settlement proof. No external refund or cancellation was executed.",
    }


@router.post("/reservations/{reservation_id}/payments", status_code=status.HTTP_201_CREATED)
async def record_reservation_payment(
    reservation_id: uuid.UUID,
    payload: ReservationPaymentPayload,
    request: Request,
    user: dict[str, Any] = Depends(payment_access),
):
    method = normalize_required_text(payload.method)
    if method not in {"CASH", "CARD", "CARD_POS", "BANK_TRANSFER", "OTHER"}:
        raise HTTPException(status_code=422, detail={"code": "PAYMENT_METHOD_NOT_ALLOWED", "message": "Only non-QR manual payments may be recorded."})
    external_ref = normalize_optional_text(payload.external_ref)
    note = normalize_optional_text(payload.note)
    paid_at = utc_aware(payload.paid_at)
    if paid_at > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise HTTPException(status_code=422, detail={"code": "PAYMENT_TIME_IN_FUTURE", "message": "Payment time cannot be in the future."})
    paid_at_db = prisma_timestamp(paid_at)

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            await lock_payment_identity(conn, payload.idempotency_key, external_ref)

            pid = await conn.fetchval(
                "SELECT id FROM properties WHERE code=$1",
                user["property_code"],
            )
            if not pid:
                raise HTTPException(status_code=503, detail="Property not loaded")

            reservation = await conn.fetchrow(
                '''
                SELECT id,"bookingNumber",status::text AS status,"totalKgs"
                FROM reservations
                WHERE id=$1 AND "propertyId"=$2
                FOR UPDATE
                ''',
                reservation_id,
                pid,
            )
            if not reservation:
                raise HTTPException(status_code=404, detail="Reservation not found")

            existing = await conn.fetchrow(
                '''
                SELECT id,"reservationId","amountKgs",method,status::text AS status,"externalRef",
                       metadata->>'note' AS note,"paidAt","createdAt"
                FROM payments
                WHERE "idempotencyKey"=$1
                ''',
                payload.idempotency_key,
            )
            if existing:
                if existing["reservationId"] != reservation_id:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "IDEMPOTENCY_CONFLICT",
                            "message": "This idempotency key belongs to another reservation.",
                        },
                    )
                ensure_same_payment_payload(
                    existing,
                    amount_kgs=payload.amount_kgs,
                    method=method,
                    external_ref=external_ref,
                    note=note,
                    compare_note=True,
                    paid_at=paid_at,
                    compare_paid_at=payload.paid_at is not None,
                )
                totals = await _totals(conn, reservation_id)
                return {
                    "idempotent_replay": True,
                    "payment_id": str(existing["id"]),
                    "reservation_id": str(reservation_id),
                    "booking_number": reservation["bookingNumber"],
                    "payment": {
                        "amount_kgs": int(existing["amountKgs"]),
                        "method": existing["method"],
                        "status": existing["status"],
                        "external_ref": existing["externalRef"],
                        "paid_at": public_timestamp(existing["paidAt"]),
                        "recorded_at": public_timestamp(existing["createdAt"]),
                    },
                    "finance": totals,
                }

            if reservation["status"] in {"CANCELLED", "NO_SHOW"}:
                raise HTTPException(status_code=409, detail={
                    "code": "PAYMENT_REQUIRES_CLOSED_BOOKING_REVIEW",
                    "message": "New payments cannot be recorded against cancelled or no-show reservations. Review historical payments separately.",
                })

            # Enforce the actual outstanding balance while the reservation row is locked.
            # Charge totals and previously received payments are read in one transaction.
            balance = await conn.fetchrow(
                """
                SELECT
                    r."totalKgs"::bigint
                      + COALESCE((
                        SELECT SUM(c."amountKgs")
                        FROM guest_folio_charges c
                        WHERE c."reservationId" = r.id
                          AND c."propertyId" = r."propertyId"
                          AND c.status NOT IN ('WAIVED', 'VOID')
                      ), 0)::bigint AS due_kgs,
                    COALESCE((
                        SELECT SUM(p."amountKgs")
                        FROM payments p
                        WHERE p."reservationId" = r.id AND p.status = 'RECEIVED'
                    ), 0)::bigint AS paid_kgs
                FROM reservations r
                WHERE r.id = $1 AND r."propertyId" = $2
                """,
                reservation_id, pid,
            )
            outstanding = max(0, int(balance["due_kgs"]) - int(balance["paid_kgs"]))
            if payload.amount_kgs > outstanding:
                raise HTTPException(status_code=409, detail={
                    "code": "PAYMENT_EXCEEDS_BALANCE",
                    "message": "Payment exceeds the remaining reservation balance.",
                    "remaining_kgs": outstanding,
                    "attempted_kgs": payload.amount_kgs,
                })

            if external_ref:
                reference_payment = await conn.fetchrow(
                    '''
                    SELECT id,"reservationId","amountKgs",method,status::text AS status
                    FROM payments
                    WHERE provider='MANAGER_MANUAL' AND "externalRef"=$1
                    ''',
                    external_ref,
                )
                if reference_payment:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "PAYMENT_EXTERNAL_REF_CONFLICT",
                            "message": "This payment reference is already recorded.",
                            "payment_id": str(reference_payment["id"]),
                            "reservation_id": str(reference_payment["reservationId"]) if reference_payment["reservationId"] else None,
                            "amount_kgs": int(reference_payment["amountKgs"]),
                            "method": reference_payment["method"],
                            "status": reference_payment["status"],
                        },
                    )

            payment_id = uuid.uuid4()
            await conn.execute(
                '''
                INSERT INTO payments (
                  id,"reservationId","amountKgs",method,status,provider,"externalRef",
                  "idempotencyKey",metadata,"paidAt","createdAt","updatedAt"
                ) VALUES ($1,$2,$3,$4,'RECEIVED','MANAGER_MANUAL',$5,$6,
                  jsonb_build_object(
                    'note',$7::text,
                    'recorded_by_staff_id',$8::text,
                    'recorded_by_role',$9::text,
                    'source','PMS_RECEPTION'
                  ),$10,now(),now())
                ''',
                payment_id,
                reservation_id,
                payload.amount_kgs,
                method,
                external_ref,
                payload.idempotency_key,
                note,
                user["id"],
                user["role"],
                paid_at_db,
            )

            totals = await _totals(conn, reservation_id)
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",
                  source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'RECORD_INTERNAL_PAYMENT','Reservation',$4,
                  'PMS_RECEPTION','SUCCESS',
                  jsonb_build_object(
                    'payment_id',$5::text,
                    'amount_kgs',$6::int,
                    'method',$7::text,
                    'external_ref',$8::text,
                    'paid_at',$9::text,
                    'recorded_by_role',$10::text,
                    'paid_kgs_after',$11::int,
                    'remaining_kgs_after',$12::int,
                    'overpaid_kgs_after',$13::int
                  ),now())
                ''',
                uuid.uuid4(),
                pid,
                user["id"],
                str(reservation_id),
                str(payment_id),
                payload.amount_kgs,
                method,
                external_ref,
                paid_at.isoformat(),
                user["role"],
                totals["paid_kgs"],
                totals["remaining_kgs"],
                totals["overpaid_kgs"],
            )

    return {
        "idempotent_replay": False,
        "payment_id": str(payment_id),
        "reservation_id": str(reservation_id),
        "booking_number": reservation["bookingNumber"],
        "payment": {
            "amount_kgs": payload.amount_kgs,
            "method": method,
            "status": "RECEIVED",
            "provider": "MANAGER_MANUAL",
            "external_ref": external_ref,
            "paid_at": paid_at,
            "recorded_by_staff_id": user["id"],
            "recorded_by_role": user["role"],
        },
        "finance": totals,
        "truth": "Internal staff-recorded payment fact only. Actual payment time and record time are stored separately. No acquiring confirmation is implied.",
    }