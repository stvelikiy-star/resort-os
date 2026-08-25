import os
import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import require_roles

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")

router = APIRouter(tags=["nfc-reporting"])
management_access = require_roles("OWNER", "MANAGER")
beach_access = require_roles("BEACH_PARTNER")


async def property_id(conn) -> uuid.UUID:
    value = await conn.fetchval("SELECT id FROM properties WHERE code=$1", PROPERTY_CODE)
    if not value:
        raise HTTPException(status_code=503, detail="Property is not loaded")
    return value


def validate_period(start: date | None, end: date | None) -> None:
    if start and end and end < start:
        raise HTTPException(status_code=422, detail="end must be on or after start")
    if start and end and (end - start).days > 366:
        raise HTTPException(status_code=422, detail="NFC report window is limited to 366 days")


@router.get("/api/v1/admin/nfc/transactions")
async def admin_nfc_transactions(
    request: Request,
    start: date | None = None,
    end: date | None = None,
    partner_id: uuid.UUID | None = None,
    limit: int = Query(default=250, ge=1, le=1000),
    _user: dict[str, Any] = Depends(management_access),
):
    validate_period(start, end)
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn)
        rows = await conn.fetch(
            '''
            SELECT t.id,t."walletId",t."braceletId",t."partnerStaffUserId",u."displayName" AS partner_name,
                   t."amountKgs",t."hotelCommissionKgs",t."partnerNetKgs",t."commissionBps",
                   t.status::text AS status,t.description,t."idempotencyKey",t."createdAt",
                   r."bookingNumber",g."firstName" AS guest_name
            FROM nfc_transactions t
            JOIN staff_users u ON u.id=t."partnerStaffUserId"
            JOIN nfc_wallets w ON w.id=t."walletId"
            JOIN reservations r ON r.id=w."reservationId"
            LEFT JOIN guests g ON g.id=w."guestId"
            WHERE t."propertyId"=$1
              AND ($2::date IS NULL OR t."createdAt" >= $2::date)
              AND ($3::date IS NULL OR t."createdAt" < ($3::date + INTERVAL '1 day'))
              AND ($4::uuid IS NULL OR t."partnerStaffUserId"=$4)
            ORDER BY t."createdAt" DESC
            LIMIT $5
            ''',
            pid, start, end, partner_id, limit,
        )
        totals = await conn.fetchrow(
            '''
            SELECT count(*)::int AS transaction_count,
                   count(*) FILTER (WHERE status='COMPLETED'::"NfcTransactionStatus")::int AS completed_count,
                   count(*) FILTER (WHERE status='REVERSED'::"NfcTransactionStatus")::int AS reversed_count,
                   COALESCE(sum("amountKgs") FILTER (WHERE status='COMPLETED'::"NfcTransactionStatus"),0)::bigint AS gross_kgs,
                   COALESCE(sum("hotelCommissionKgs") FILTER (WHERE status='COMPLETED'::"NfcTransactionStatus"),0)::bigint AS hotel_commission_kgs,
                   COALESCE(sum("partnerNetKgs") FILTER (WHERE status='COMPLETED'::"NfcTransactionStatus"),0)::bigint AS partner_net_kgs
            FROM nfc_transactions
            WHERE "propertyId"=$1
              AND ($2::date IS NULL OR "createdAt" >= $2::date)
              AND ($3::date IS NULL OR "createdAt" < ($3::date + INTERVAL '1 day'))
              AND ($4::uuid IS NULL OR "partnerStaffUserId"=$4)
            ''',
            pid, start, end, partner_id,
        )

    return {
        "period": {"start": start, "end": end},
        "totals": dict(totals),
        "items": [
            {
                "id": str(row["id"]),
                "wallet_id": str(row["walletId"]),
                "bracelet_id": str(row["braceletId"]),
                "partner_id": str(row["partnerStaffUserId"]),
                "partner_name": row["partner_name"],
                "amount_kgs": row["amountKgs"],
                "hotel_commission_kgs": row["hotelCommissionKgs"],
                "partner_net_kgs": row["partnerNetKgs"],
                "commission_bps": row["commissionBps"],
                "status": row["status"],
                "description": row["description"],
                "booking_number": row["bookingNumber"],
                "guest_name": row["guest_name"],
                "created_at": row["createdAt"],
            }
            for row in rows
        ],
    }


@router.get("/api/v1/admin/nfc/partners/summary")
async def admin_nfc_partner_summary(
    request: Request,
    start: date | None = None,
    end: date | None = None,
    _user: dict[str, Any] = Depends(management_access),
):
    validate_period(start, end)
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn)
        rows = await conn.fetch(
            '''
            SELECT u.id AS partner_id,u."displayName" AS partner_name,u.username,
                   count(t.id) FILTER (WHERE t.status='COMPLETED'::"NfcTransactionStatus")::int AS completed_count,
                   COALESCE(sum(t."amountKgs") FILTER (WHERE t.status='COMPLETED'::"NfcTransactionStatus"),0)::bigint AS gross_kgs,
                   COALESCE(sum(t."hotelCommissionKgs") FILTER (WHERE t.status='COMPLETED'::"NfcTransactionStatus"),0)::bigint AS hotel_commission_kgs,
                   COALESCE(sum(t."partnerNetKgs") FILTER (WHERE t.status='COMPLETED'::"NfcTransactionStatus"),0)::bigint AS partner_net_kgs,
                   max(t."createdAt") AS last_transaction_at
            FROM staff_users u
            LEFT JOIN nfc_transactions t ON t."partnerStaffUserId"=u.id
              AND ($2::date IS NULL OR t."createdAt" >= $2::date)
              AND ($3::date IS NULL OR t."createdAt" < ($3::date + INTERVAL '1 day'))
            WHERE u."propertyId"=$1
              AND u.role='BEACH_PARTNER'::"StaffRole"
              AND u."isActive"=true
            GROUP BY u.id,u."displayName",u.username
            ORDER BY gross_kgs DESC,u."displayName"
            ''',
            pid, start, end,
        )
    return {
        "period": {"start": start, "end": end},
        "items": [
            {
                "partner_id": str(row["partner_id"]),
                "partner_name": row["partner_name"],
                "username": row["username"],
                "completed_count": row["completed_count"],
                "gross_kgs": row["gross_kgs"],
                "hotel_commission_kgs": row["hotel_commission_kgs"],
                "partner_net_kgs": row["partner_net_kgs"],
                "last_transaction_at": row["last_transaction_at"],
            }
            for row in rows
        ],
    }


@router.get("/api/v1/beach/transactions")
async def beach_partner_transactions(
    request: Request,
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user: dict[str, Any] = Depends(beach_access),
):
    validate_period(start, end)
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn)
        partner_id = uuid.UUID(user["id"])
        rows = await conn.fetch(
            '''
            SELECT t.id,t."amountKgs",t."hotelCommissionKgs",t."partnerNetKgs",t."commissionBps",
                   t.status::text AS status,t.description,t."createdAt",r."bookingNumber"
            FROM nfc_transactions t
            JOIN nfc_wallets w ON w.id=t."walletId"
            JOIN reservations r ON r.id=w."reservationId"
            WHERE t."propertyId"=$1 AND t."partnerStaffUserId"=$2
              AND ($3::date IS NULL OR t."createdAt" >= $3::date)
              AND ($4::date IS NULL OR t."createdAt" < ($4::date + INTERVAL '1 day'))
            ORDER BY t."createdAt" DESC
            LIMIT $5
            ''',
            pid, partner_id, start, end, limit,
        )
        totals = await conn.fetchrow(
            '''
            SELECT count(*) FILTER (WHERE status='COMPLETED'::"NfcTransactionStatus")::int AS completed_count,
                   COALESCE(sum("amountKgs") FILTER (WHERE status='COMPLETED'::"NfcTransactionStatus"),0)::bigint AS gross_kgs,
                   COALESCE(sum("hotelCommissionKgs") FILTER (WHERE status='COMPLETED'::"NfcTransactionStatus"),0)::bigint AS hotel_commission_kgs,
                   COALESCE(sum("partnerNetKgs") FILTER (WHERE status='COMPLETED'::"NfcTransactionStatus"),0)::bigint AS partner_net_kgs
            FROM nfc_transactions
            WHERE "propertyId"=$1 AND "partnerStaffUserId"=$2
              AND ($3::date IS NULL OR "createdAt" >= $3::date)
              AND ($4::date IS NULL OR "createdAt" < ($4::date + INTERVAL '1 day'))
            ''',
            pid, partner_id, start, end,
        )
    return {
        "period": {"start": start, "end": end},
        "totals": dict(totals),
        "items": [
            {
                "id": str(row["id"]),
                "amount_kgs": row["amountKgs"],
                "hotel_commission_kgs": row["hotelCommissionKgs"],
                "partner_net_kgs": row["partnerNetKgs"],
                "commission_bps": row["commissionBps"],
                "status": row["status"],
                "description": row["description"],
                "booking_number": row["bookingNumber"],
                "created_at": row["createdAt"],
            }
            for row in rows
        ],
    }
