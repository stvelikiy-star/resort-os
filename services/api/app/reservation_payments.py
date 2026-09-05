import uuid
from datetime import datetime, timezone
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
payment_access = require_roles("OWNER", "MANAGER", "RECEPTION")


class ReservationPaymentPayload(BaseModel):
    amount_kgs: int = Field(gt=0)
    method: str = Field(min_length=2, max_length=80)
    paid_at: datetime | None = None
    external_ref: str | None = Field(default=None, max_length=180)
    note: str | None = Field(default=None, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=180)


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


@router.post("/reservations/{reservation_id}/payments", status_code=status.HTTP_201_CREATED)
async def record_reservation_payment(
    reservation_id: uuid.UUID,
    payload: ReservationPaymentPayload,
    request: Request,
    user: dict[str, Any] = Depends(payment_access),
):
    method = normalize_required_text(payload.method)
    external_ref = normalize_optional_text(payload.external_ref)
    note = normalize_optional_text(payload.note)
    paid_at = payload.paid_at or datetime.now(timezone.utc)
    if paid_at.tzinfo is None:
        paid_at = paid_at.replace(tzinfo=timezone.utc)
    if paid_at > datetime.now(timezone.utc) + __import__("datetime").timedelta(minutes=5):
        raise HTTPException(status_code=422, detail={"code": "PAYMENT_TIME_IN_FUTURE", "message": "Payment time cannot be in the future."})

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
                        "paid_at": existing["paidAt"],
                        "recorded_at": existing["createdAt"],
                    },
                    "finance": totals,
                }

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
                paid_at,
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
