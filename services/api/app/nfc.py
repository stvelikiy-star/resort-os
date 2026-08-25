import hashlib
import os
import uuid
from typing import Any, Literal

from asyncpg.exceptions import RaiseError, UniqueViolationError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from .auth import require_roles

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
NFC_UID_PEPPER = os.environ.get("NFC_UID_PEPPER")

router = APIRouter(tags=["nfc"])
management_access = require_roles("OWNER", "MANAGER")
beach_access = require_roles("BEACH_PARTNER")
balance_access = require_roles("OWNER", "MANAGER", "BEACH_PARTNER")

RetiredBraceletStatus = Literal["BLOCKED", "LOST", "RETURNED"]


class NfcWalletIssue(BaseModel):
    reservation_id: uuid.UUID
    bracelet_uid: str = Field(min_length=4, max_length=160)
    initial_balance_kgs: int = Field(default=0, ge=0, le=10_000_000)
    label: str | None = Field(default=None, max_length=80)


class NfcBraceletLookup(BaseModel):
    bracelet_uid: str = Field(min_length=4, max_length=160)


class NfcBraceletStatusChange(BaseModel):
    status: RetiredBraceletStatus


class NfcBraceletReplacement(BaseModel):
    bracelet_uid: str = Field(min_length=4, max_length=160)
    label: str | None = Field(default=None, max_length=80)
    retire_previous_as: RetiredBraceletStatus


class NfcCharge(BaseModel):
    bracelet_uid: str = Field(min_length=4, max_length=160)
    amount_kgs: int = Field(gt=0, le=1_000_000)
    idempotency_key: str = Field(min_length=8, max_length=180)
    description: str | None = Field(default=None, max_length=500)


def uid_hash(raw_uid: str) -> str:
    if not NFC_UID_PEPPER:
        raise HTTPException(status_code=503, detail="NFC UID hashing is not configured")
    normalized = raw_uid.strip()
    if len(normalized) < 4:
        raise HTTPException(status_code=422, detail="Invalid NFC bracelet UID")
    return hashlib.sha256(f"{NFC_UID_PEPPER}\0{normalized}".encode("utf-8")).hexdigest()


async def property_id(conn) -> uuid.UUID:
    value = await conn.fetchval("SELECT id FROM properties WHERE code=$1", PROPERTY_CODE)
    if not value:
        raise HTTPException(status_code=503, detail="Property is not loaded")
    return value


def map_nfc_database_error(exc: RaiseError) -> HTTPException:
    message = str(exc)
    if "NFC_BRACELET_NOT_FOUND" in message:
        return HTTPException(status_code=404, detail="NFC bracelet not found")
    if "NFC_INSUFFICIENT_FUNDS" in message:
        return HTTPException(status_code=409, detail="Insufficient NFC wallet balance")
    if "NFC_PARTNER_NOT_AUTHORIZED" in message:
        return HTTPException(status_code=403, detail="Beach partner is not authorized")
    if "NFC_BRACELET_NOT_ACTIVE" in message:
        return HTTPException(status_code=409, detail="NFC bracelet is not active")
    if "NFC_WALLET_NOT_ACTIVE" in message:
        return HTTPException(status_code=409, detail="NFC wallet is not active")
    if "NFC_IDEMPOTENCY_CONFLICT" in message:
        return HTTPException(status_code=409, detail="NFC idempotency key belongs to another partner")
    if "NFC_INVALID_AMOUNT" in message or "NFC_INVALID_IDEMPOTENCY_KEY" in message:
        return HTTPException(status_code=422, detail="Invalid NFC charge request")
    return HTTPException(status_code=409, detail="NFC payment could not be processed")


@router.get("/api/v1/admin/nfc/wallets")
async def list_nfc_wallets(
    request: Request,
    _user: dict[str, Any] = Depends(management_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn)
        rows = await conn.fetch(
            '''
            SELECT w.id AS wallet_id,w."reservationId" AS reservation_id,w."guestId" AS guest_id,
                   w."balanceKgs" AS balance_kgs,w.status::text AS wallet_status,
                   r."bookingNumber" AS booking_number,r.status::text AS reservation_status,
                   g."firstName" AS guest_name,
                   b.id AS bracelet_id,b.status::text AS bracelet_status,b.label AS bracelet_label,b."issuedAt" AS issued_at
            FROM nfc_wallets w
            JOIN reservations r ON r.id=w."reservationId"
            LEFT JOIN guests g ON g.id=w."guestId"
            LEFT JOIN LATERAL (
              SELECT nb.id,nb.status,nb.label,nb."issuedAt"
              FROM nfc_bracelets nb
              WHERE nb."walletId"=w.id
              ORDER BY (nb.status='ACTIVE') DESC, nb."issuedAt" DESC NULLS LAST, nb."createdAt" DESC
              LIMIT 1
            ) b ON true
            WHERE w."propertyId"=$1
            ORDER BY w."createdAt" DESC
            ''',
            pid,
        )
    return {
        "items": [
            {
                "wallet_id": str(row["wallet_id"]),
                "reservation_id": str(row["reservation_id"]),
                "guest_id": str(row["guest_id"]),
                "booking_number": row["booking_number"],
                "reservation_status": row["reservation_status"],
                "guest_name": row["guest_name"],
                "balance_kgs": row["balance_kgs"],
                "wallet_status": row["wallet_status"],
                "bracelet_id": str(row["bracelet_id"]) if row["bracelet_id"] else None,
                "bracelet_status": row["bracelet_status"],
                "bracelet_label": row["bracelet_label"],
                "issued_at": row["issued_at"],
            }
            for row in rows
        ]
    }


@router.post("/api/v1/admin/nfc/wallets", status_code=status.HTTP_201_CREATED)
async def issue_nfc_wallet(
    payload: NfcWalletIssue,
    request: Request,
    user: dict[str, Any] = Depends(management_access),
):
    bracelet_hash = uid_hash(payload.bracelet_uid)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn)
            reservation = await conn.fetchrow(
                '''
                SELECT r.id,r.status::text AS status,r."primaryGuestId",r."bookingNumber",
                       w.id AS wallet_id,w."balanceKgs" AS wallet_balance,w.status::text AS wallet_status
                FROM reservations r
                LEFT JOIN nfc_wallets w ON w."reservationId"=r.id
                WHERE r.id=$1 AND r."propertyId"=$2
                FOR UPDATE OF r
                ''',
                payload.reservation_id, pid,
            )
            if not reservation:
                raise HTTPException(status_code=404, detail="Reservation not found")
            if reservation["status"] != "CHECKED_IN":
                raise HTTPException(status_code=409, detail="NFC wallet can be issued only after check-in")
            if not reservation["primaryGuestId"]:
                raise HTTPException(status_code=409, detail="Reservation has no primary guest")

            if reservation["wallet_id"]:
                same_bracelet = await conn.fetchrow(
                    '''SELECT id,status::text AS status,label FROM nfc_bracelets
                       WHERE "walletId"=$1 AND "uidHash"=$2''',
                    reservation["wallet_id"], bracelet_hash,
                )
                if same_bracelet:
                    return {
                        "idempotent_replay": True,
                        "wallet_id": str(reservation["wallet_id"]),
                        "bracelet_id": str(same_bracelet["id"]),
                        "booking_number": reservation["bookingNumber"],
                        "balance_kgs": reservation["wallet_balance"],
                        "wallet_status": reservation["wallet_status"],
                        "bracelet_status": same_bracelet["status"],
                        "label": same_bracelet["label"],
                    }
                raise HTTPException(status_code=409, detail="Reservation already has an NFC wallet; use a controlled bracelet replacement flow")

            wallet_id = uuid.uuid4()
            bracelet_id = uuid.uuid4()
            try:
                await conn.execute(
                    '''
                    INSERT INTO nfc_wallets (
                      id,"propertyId","reservationId","guestId","balanceKgs",status,"createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,$4,$5,'ACTIVE',now(),now())
                    ''',
                    wallet_id, pid, payload.reservation_id, reservation["primaryGuestId"], payload.initial_balance_kgs,
                )
                await conn.execute(
                    '''
                    INSERT INTO nfc_bracelets (
                      id,"propertyId","walletId","uidHash",status,label,"issuedAt","createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,$4,'ACTIVE',$5,now(),now(),now())
                    ''',
                    bracelet_id, pid, wallet_id, bracelet_hash, payload.label,
                )
            except UniqueViolationError as exc:
                raise HTTPException(status_code=409, detail="NFC bracelet is already assigned") from exc

            await conn.execute(
                '''
                INSERT INTO nfc_ledger_entries (
                  id,"walletId","entryType","deltaKgs","balanceBeforeKgs","balanceAfterKgs",note,"createdAt"
                ) VALUES ($1,$2,'INITIAL_BALANCE',$3,0,$3,$4,now())
                ''',
                uuid.uuid4(), wallet_id, payload.initial_balance_kgs,
                f"NFC wallet issued for {reservation['bookingNumber']}",
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'ISSUE_NFC_WALLET','NfcWallet',$4,'PMS','SUCCESS',
                  jsonb_build_object('booking_number',$5::text,'initial_balance_kgs',$6::int,'bracelet_id',$7::text),now())
                ''',
                uuid.uuid4(), pid, user["id"], str(wallet_id), reservation["bookingNumber"],
                payload.initial_balance_kgs, str(bracelet_id),
            )

    return {
        "idempotent_replay": False,
        "wallet_id": str(wallet_id),
        "bracelet_id": str(bracelet_id),
        "booking_number": reservation["bookingNumber"],
        "balance_kgs": payload.initial_balance_kgs,
        "wallet_status": "ACTIVE",
        "bracelet_status": "ACTIVE",
        "label": payload.label,
    }


@router.patch("/api/v1/admin/nfc/wallets/{wallet_id}/bracelets/{bracelet_id}/status")
async def retire_nfc_bracelet(
    wallet_id: uuid.UUID,
    bracelet_id: uuid.UUID,
    payload: NfcBraceletStatusChange,
    request: Request,
    user: dict[str, Any] = Depends(management_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn)
            wallet = await conn.fetchrow(
                '''SELECT id,"balanceKgs",status::text AS status FROM nfc_wallets
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                wallet_id, pid,
            )
            if not wallet:
                raise HTTPException(status_code=404, detail="NFC wallet not found")
            bracelet = await conn.fetchrow(
                '''SELECT id,status::text AS status,label,"returnedAt" FROM nfc_bracelets
                   WHERE id=$1 AND "walletId"=$2 AND "propertyId"=$3 FOR UPDATE''',
                bracelet_id, wallet_id, pid,
            )
            if not bracelet:
                raise HTTPException(status_code=404, detail="NFC bracelet not found")
            if bracelet["status"] == payload.status:
                return {
                    "idempotent_replay": True,
                    "wallet_id": str(wallet_id),
                    "bracelet_id": str(bracelet_id),
                    "bracelet_status": bracelet["status"],
                    "wallet_status": wallet["status"],
                    "balance_kgs": wallet["balanceKgs"],
                }
            if bracelet["status"] != "ACTIVE":
                raise HTTPException(status_code=409, detail="Only an ACTIVE bracelet can be retired by this operation")

            await conn.execute(
                '''
                UPDATE nfc_bracelets
                SET status=$1::"NfcBraceletStatus",
                    "returnedAt"=CASE WHEN $1='RETURNED' THEN now() ELSE NULL END,
                    "updatedAt"=now()
                WHERE id=$2
                ''',
                payload.status, bracelet_id,
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"beforeJson","afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'RETIRE_NFC_BRACELET','NfcBracelet',$4,'PMS','SUCCESS',
                  jsonb_build_object('status',$5::text),
                  jsonb_build_object('status',$6::text,'wallet_id',$7::text,'balance_kgs',$8::int),now())
                ''',
                uuid.uuid4(), pid, user["id"], str(bracelet_id), bracelet["status"], payload.status,
                str(wallet_id), wallet["balanceKgs"],
            )

    return {
        "idempotent_replay": False,
        "wallet_id": str(wallet_id),
        "bracelet_id": str(bracelet_id),
        "bracelet_status": payload.status,
        "wallet_status": wallet["status"],
        "balance_kgs": wallet["balanceKgs"],
    }


@router.post("/api/v1/admin/nfc/wallets/{wallet_id}/bracelets/{bracelet_id}/replace", status_code=status.HTTP_201_CREATED)
async def replace_nfc_bracelet(
    wallet_id: uuid.UUID,
    bracelet_id: uuid.UUID,
    payload: NfcBraceletReplacement,
    request: Request,
    user: dict[str, Any] = Depends(management_access),
):
    replacement_hash = uid_hash(payload.bracelet_uid)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn)
            wallet = await conn.fetchrow(
                '''
                SELECT w.id,w."balanceKgs",w.status::text AS status,r."bookingNumber"
                FROM nfc_wallets w
                JOIN reservations r ON r.id=w."reservationId"
                WHERE w.id=$1 AND w."propertyId"=$2
                FOR UPDATE OF w
                ''',
                wallet_id, pid,
            )
            if not wallet:
                raise HTTPException(status_code=404, detail="NFC wallet not found")
            if wallet["status"] != "ACTIVE":
                raise HTTPException(status_code=409, detail="Bracelet can be replaced only for an ACTIVE wallet")

            source = await conn.fetchrow(
                '''SELECT id,status::text AS status,label FROM nfc_bracelets
                   WHERE id=$1 AND "walletId"=$2 AND "propertyId"=$3 FOR UPDATE''',
                bracelet_id, wallet_id, pid,
            )
            if not source:
                raise HTTPException(status_code=404, detail="Source NFC bracelet not found")

            active = await conn.fetchrow(
                '''SELECT id,"uidHash",status::text AS status,label FROM nfc_bracelets
                   WHERE "walletId"=$1 AND status='ACTIVE'::"NfcBraceletStatus"
                   FOR UPDATE''',
                wallet_id,
            )

            existing_uid = await conn.fetchrow(
                '''SELECT id,"walletId",status::text AS status,label FROM nfc_bracelets
                   WHERE "propertyId"=$1 AND "uidHash"=$2''',
                pid, replacement_hash,
            )
            if existing_uid:
                if existing_uid["walletId"] == wallet_id and existing_uid["status"] == "ACTIVE":
                    return {
                        "idempotent_replay": True,
                        "wallet_id": str(wallet_id),
                        "old_bracelet_id": str(bracelet_id),
                        "new_bracelet_id": str(existing_uid["id"]),
                        "bracelet_status": "ACTIVE",
                        "wallet_status": wallet["status"],
                        "balance_kgs": wallet["balanceKgs"],
                        "label": existing_uid["label"],
                    }
                raise HTTPException(status_code=409, detail="Replacement NFC bracelet UID is already assigned")

            if source["status"] == "ACTIVE":
                if not active or active["id"] != bracelet_id:
                    raise HTTPException(status_code=409, detail="Active bracelet changed; refresh NFC state before replacement")
                await conn.execute(
                    '''
                    UPDATE nfc_bracelets
                    SET status=$1::"NfcBraceletStatus",
                        "returnedAt"=CASE WHEN $1='RETURNED' THEN now() ELSE NULL END,
                        "updatedAt"=now()
                    WHERE id=$2
                    ''',
                    payload.retire_previous_as, bracelet_id,
                )
            elif active:
                raise HTTPException(status_code=409, detail="Wallet already has another ACTIVE bracelet; refresh NFC state")

            new_bracelet_id = uuid.uuid4()
            try:
                await conn.execute(
                    '''
                    INSERT INTO nfc_bracelets (
                      id,"propertyId","walletId","uidHash",status,label,"issuedAt","createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,$4,'ACTIVE',$5,now(),now(),now())
                    ''',
                    new_bracelet_id, pid, wallet_id, replacement_hash, payload.label,
                )
            except UniqueViolationError as exc:
                raise HTTPException(status_code=409, detail="NFC replacement conflicted with another active or assigned bracelet") from exc

            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"beforeJson","afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'REPLACE_NFC_BRACELET','NfcWallet',$4,'PMS','SUCCESS',
                  jsonb_build_object('old_bracelet_id',$5::text,'old_status',$6::text),
                  jsonb_build_object('new_bracelet_id',$7::text,'old_retired_as',$8::text,
                    'balance_kgs',$9::int,'booking_number',$10::text),now())
                ''',
                uuid.uuid4(), pid, user["id"], str(wallet_id), str(bracelet_id), source["status"],
                str(new_bracelet_id), payload.retire_previous_as, wallet["balanceKgs"], wallet["bookingNumber"],
            )

    return {
        "idempotent_replay": False,
        "wallet_id": str(wallet_id),
        "old_bracelet_id": str(bracelet_id),
        "old_bracelet_status": payload.retire_previous_as if source["status"] == "ACTIVE" else source["status"],
        "new_bracelet_id": str(new_bracelet_id),
        "bracelet_status": "ACTIVE",
        "wallet_status": wallet["status"],
        "balance_kgs": wallet["balanceKgs"],
        "label": payload.label,
    }


@router.post("/api/v1/beach/balance")
async def nfc_balance(
    payload: NfcBraceletLookup,
    request: Request,
    _user: dict[str, Any] = Depends(balance_access),
):
    bracelet_hash = uid_hash(payload.bracelet_uid)
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn)
        row = await conn.fetchrow(
            '''
            SELECT w.id AS wallet_id,w."balanceKgs",w.status::text AS wallet_status,
                   b.id AS bracelet_id,b.status::text AS bracelet_status,b.label,
                   r."bookingNumber"
            FROM nfc_bracelets b
            JOIN nfc_wallets w ON w.id=b."walletId"
            JOIN reservations r ON r.id=w."reservationId"
            WHERE b."propertyId"=$1 AND b."uidHash"=$2
            ''',
            pid, bracelet_hash,
        )
        if not row:
            raise HTTPException(status_code=404, detail="NFC bracelet not found")
    return {
        "wallet_id": str(row["wallet_id"]),
        "bracelet_id": str(row["bracelet_id"]),
        "booking_number": row["bookingNumber"],
        "balance_kgs": row["balanceKgs"],
        "wallet_status": row["wallet_status"],
        "bracelet_status": row["bracelet_status"],
        "label": row["label"],
    }


@router.post("/api/v1/beach/charge")
async def charge_nfc_wallet(
    payload: NfcCharge,
    request: Request,
    user: dict[str, Any] = Depends(beach_access),
):
    bracelet_hash = uid_hash(payload.bracelet_uid)
    async with request.app.state.db.acquire() as conn:
        try:
            row = await conn.fetchrow(
                '''
                SELECT * FROM process_nfc_payment($1,$2,$3,$4,$5,$6)
                ''',
                PROPERTY_CODE,
                bracelet_hash,
                uuid.UUID(user["id"]),
                payload.amount_kgs,
                payload.idempotency_key,
                payload.description,
            )
        except RaiseError as exc:
            raise map_nfc_database_error(exc) from exc

        if not row:
            raise HTTPException(status_code=500, detail="NFC payment returned no result")

        pid = await property_id(conn)
        await conn.execute(
            '''
            INSERT INTO audit_logs (
              id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
            ) VALUES ($1,$2,'STAFF',$3,'BEACH_CHARGE','NfcTransaction',$4,'NFC_TERMINAL','SUCCESS',
              jsonb_build_object('amount_kgs',$5::int,'hotel_commission_kgs',$6::int,
                'partner_net_kgs',$7::int,'balance_after_kgs',$8::int,'idempotent_replay',$9::boolean),now())
            ''',
            uuid.uuid4(), pid, user["id"], str(row["transaction_id"]), row["amount_kgs"],
            row["hotel_commission_kgs"], row["partner_net_kgs"], row["balance_after_kgs"],
            row["idempotent_replay"],
        )

    return {
        "transaction_id": str(row["transaction_id"]),
        "wallet_id": str(row["wallet_id"]),
        "balance_before_kgs": row["balance_before_kgs"],
        "balance_after_kgs": row["balance_after_kgs"],
        "amount_kgs": row["amount_kgs"],
        "hotel_commission_kgs": row["hotel_commission_kgs"],
        "partner_net_kgs": row["partner_net_kgs"],
        "commission_bps": row["commission_bps"],
        "idempotent_replay": row["idempotent_replay"],
    }
