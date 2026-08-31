import base64
import hashlib
import hmac
import io
import os
import secrets
import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import qrcode
import qrcode.image.svg
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from .auth import require_roles

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
PUBLIC_BASE_URL = os.environ.get("GUEST_OS_PUBLIC_BASE_URL", "https://3korony.com").rstrip("/")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() not in {"0", "false", "no"}
GUEST_COOKIE = "tc_guest_session"
PIN_FAILURE_LIMIT = 5
PIN_FAILURE_WINDOW_MINUTES = 10
SESSION_MAX_DAYS = 30

admin_router = APIRouter(prefix="/api/v1/admin/guest-os", tags=["admin-guest-os"])
public_router = APIRouter(prefix="/api/v1/guest-os", tags=["guest-os"])
admin_access = require_roles("OWNER", "MANAGER", "RECEPTION")


class VerifyPinPayload(BaseModel):
    pin: str = Field(pattern=r"^\d{6}$")


class BatchIssuePayload(BaseModel):
    include_existing: bool = False


def hash_secret(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def qr_svg(public_url: str) -> str:
    image = qrcode.make(public_url, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=3)
    buffer = io.BytesIO()
    image.save(buffer)
    return buffer.getvalue().decode("utf-8")


def verify_pin_hash(pin: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        scheme, iterations_raw, salt_raw, digest_raw = stored.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = base64.urlsafe_b64decode(salt_raw.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_raw.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def client_key_hash(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    host = forwarded or (request.client.host if request.client else "unknown")
    agent = request.headers.get("user-agent", "unknown")[:300]
    return hashlib.sha256(f"{host}|{agent}".encode("utf-8")).hexdigest()


async def property_context(conn):
    prop = await conn.fetchrow(
        'SELECT id,code,name,timezone FROM properties WHERE code=$1', PROPERTY_CODE
    )
    if not prop:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return prop


async def resolve_room_qr(conn, raw_token: str, *, lock: bool = False):
    if not (20 <= len(raw_token) <= 256):
        return None
    suffix = " FOR UPDATE OF qr" if lock else ""
    return await conn.fetchrow(
        f'''
        SELECT qr.id AS qr_id,qr."propertyId",qr."roomId",qr.status::text AS qr_status,
               qr.label,qr."issuedAt",room.code AS room_code,room.name AS room_name,
               room."buildingOrZone",room."floorLabel",room."bedConfiguration",
               rt.code AS room_type_code,rt.name AS room_type_name
        FROM room_qrs qr
        JOIN rooms room ON room.id=qr."roomId"
        JOIN room_types rt ON rt.id=room."roomTypeId"
        WHERE qr."tokenHash"=$1 AND qr.status='ACTIVE'{suffix}
        ''',
        hash_secret(raw_token),
    )


async def current_stay_for_room(conn, room_id: uuid.UUID):
    return await conn.fetchrow(
        '''
        SELECT ra.id AS assignment_id,ra."stayId",s."guestId",s.status::text AS stay_status,
               s."guestAccessPinHash",s."guestAccessPinExpiresAt",
               r.id AS reservation_id,r."bookingNumber",r."checkIn",r."checkOut",
               g."firstName",g."lastName",p.timezone
        FROM room_assignments ra
        JOIN stays s ON s.id=ra."stayId"
        JOIN reservations r ON r.id=s."reservationId"
        JOIN guests g ON g.id=s."guestId"
        JOIN properties p ON p.id=s."propertyId"
        WHERE ra."roomId"=$1 AND ra."endedAt" IS NULL AND s.status='ACTIVE'
        LIMIT 1
        ''',
        room_id,
    )


async def valid_guest_session(conn, raw_session: str | None):
    if not raw_session or not (20 <= len(raw_session) <= 256):
        return None
    token_hash = hash_secret(raw_session)
    await conn.execute(
        '''
        UPDATE guest_sessions
        SET status='EXPIRED',"updatedAt"=now()
        WHERE "tokenHash"=$1 AND status='ACTIVE' AND "expiresAt" <= now()
        ''',
        token_hash,
    )
    row = await conn.fetchrow(
        '''
        SELECT gs.id,gs."stayId",gs."guestId",gs."roomQrId",gs."expiresAt",
               s.status::text AS stay_status
        FROM guest_sessions gs
        JOIN stays s ON s.id=gs."stayId"
        WHERE gs."tokenHash"=$1 AND gs.status='ACTIVE' AND gs."expiresAt" > now()
          AND s.status='ACTIVE'
        ''',
        token_hash,
    )
    if row:
        await conn.execute(
            'UPDATE guest_sessions SET "lastSeenAt"=now(),"updatedAt"=now() WHERE id=$1',
            row["id"],
        )
    return row


def generic_room_context(qr, active_stay: bool):
    return {
        "qr_valid": True,
        "authenticated": False,
        "verification_required": active_stay,
        "active_stay": active_stay,
        "room": {
            "code": qr["room_code"],
            "name": qr["room_name"],
            "room_type_name": qr["room_type_name"],
            "building_or_zone": qr["buildingOrZone"],
            "floor": qr["floorLabel"],
        },
        "guest": None,
        "stay": None,
        "privacy": "ROOM_QR_DOES_NOT_AUTHENTICATE_GUEST",
    }


def session_expiry(check_out, timezone_name: str) -> datetime:
    local_tz = ZoneInfo(timezone_name)
    checkout_local = datetime.combine(check_out, time(hour=12), tzinfo=local_tz)
    checkout_utc_naive = checkout_local.astimezone(timezone.utc).replace(tzinfo=None)
    max_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=SESSION_MAX_DAYS)
    return min(checkout_utc_naive, max_expiry)


async def write_verify_audit(
    conn,
    *,
    property_id: uuid.UUID,
    qr_id: uuid.UUID,
    result: str,
    client_hash: str,
    reason: str,
    stay_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
):
    await conn.execute(
        '''
        INSERT INTO audit_logs (
          id,"propertyId","actorType",action,resource,"resourceId",source,result,"afterJson","createdAt"
        ) VALUES ($1,$2,'GUEST','VERIFY_PIN','RoomQr',$3,'GUEST_OS',$4,
          jsonb_build_object(
            'client_key_hash',$5::text,
            'reason',$6::text,
            'stay_id',$7::text,
            'session_id',$8::text
          ),now())
        ''',
        uuid.uuid4(),
        property_id,
        str(qr_id),
        result,
        client_hash,
        reason,
        str(stay_id) if stay_id else None,
        str(session_id) if session_id else None,
    )


async def issue_room_qr(conn, *, property_id: uuid.UUID, room_id: uuid.UUID, room_code: str, label: str | None = None):
    existing = await conn.fetchrow(
        '''SELECT id,"issuedAt",label FROM room_qrs WHERE "roomId"=$1 AND status='ACTIVE' FOR UPDATE''',
        room_id,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ROOM_QR_ALREADY_ACTIVE",
                "room_code": room_code,
                "reprint_requires_rotation": True,
            },
        )
    raw_token = secrets.token_urlsafe(32)
    qr_id = uuid.uuid4()
    public_url = f"{PUBLIC_BASE_URL}/g/{raw_token}"
    await conn.execute(
        '''
        INSERT INTO room_qrs (
          id,"propertyId","roomId","tokenHash",status,label,"issuedAt","createdAt","updatedAt"
        ) VALUES ($1,$2,$3,$4,'ACTIVE',$5,now(),now(),now())
        ''',
        qr_id,
        property_id,
        room_id,
        hash_secret(raw_token),
        label or f"Room {room_code} permanent QR",
    )
    return {
        "qr_id": str(qr_id),
        "room_id": str(room_id),
        "room_code": room_code,
        "token": raw_token,
        "public_url": public_url,
        "qr_svg": qr_svg(public_url),
        "token_display_once": True,
        "reprint_requires_rotation": True,
    }


@admin_router.get("/room-qrs")
async def list_room_qrs(request: Request, user: dict[str, Any] = Depends(admin_access)):
    async with request.app.state.db.acquire() as conn:
        prop = await property_context(conn)
        rows = await conn.fetch(
            '''
            SELECT room.id AS room_id,room.code AS room_code,room."bedConfiguration",
                   qr.id AS qr_id,qr.status::text AS qr_status,qr.label,qr."issuedAt",qr."revokedAt"
            FROM rooms room
            LEFT JOIN room_qrs qr ON qr."roomId"=room.id AND qr.status='ACTIVE'
            WHERE room."propertyId"=$1
            ORDER BY room.code
            ''',
            prop["id"],
        )
    return {
        "property": prop["code"],
        "items": [
            {
                "room_id": str(row["room_id"]),
                "room_code": row["room_code"],
                "beds_raw": row["bedConfiguration"],
                "qr_id": str(row["qr_id"]) if row["qr_id"] else None,
                "status": row["qr_status"],
                "label": row["label"],
                "issued_at": row["issuedAt"],
                "raw_token_recoverable": False,
                "reprint_requires_rotation": bool(row["qr_id"]),
            }
            for row in rows
        ],
    }


@admin_router.post("/room-qrs/{room_id}/issue", status_code=status.HTTP_201_CREATED)
async def issue_qr(room_id: uuid.UUID, request: Request, user: dict[str, Any] = Depends(admin_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await property_context(conn)
            room = await conn.fetchrow(
                'SELECT id,code FROM rooms WHERE id=$1 AND "propertyId"=$2 FOR UPDATE',
                room_id,
                prop["id"],
            )
            if not room:
                raise HTTPException(status_code=404, detail="Room not found")
            issued = await issue_room_qr(
                conn,
                property_id=prop["id"],
                room_id=room["id"],
                room_code=room["code"],
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'ISSUE','RoomQr',$4,'PMS_GUEST_OS','SUCCESS',
                  jsonb_build_object('room_id',$5::text,'room_code',$6::text,'raw_token_stored',false),now())
                ''',
                uuid.uuid4(), prop["id"], user["id"], issued["qr_id"], str(room["id"]), room["code"],
            )
    return issued


@admin_router.post("/room-qrs/{room_id}/rotate", status_code=status.HTTP_201_CREATED)
async def rotate_qr(room_id: uuid.UUID, request: Request, user: dict[str, Any] = Depends(admin_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await property_context(conn)
            room = await conn.fetchrow(
                'SELECT id,code FROM rooms WHERE id=$1 AND "propertyId"=$2 FOR UPDATE',
                room_id,
                prop["id"],
            )
            if not room:
                raise HTTPException(status_code=404, detail="Room not found")
            revoked = await conn.fetch(
                '''
                UPDATE room_qrs
                SET status='REVOKED',"revokedAt"=now(),"updatedAt"=now()
                WHERE "roomId"=$1 AND status='ACTIVE'
                RETURNING id
                ''',
                room_id,
            )
            issued = await issue_room_qr(
                conn,
                property_id=prop["id"],
                room_id=room["id"],
                room_code=room["code"],
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'ROTATE','RoomQr',$4,'PMS_GUEST_OS','SUCCESS',
                  jsonb_build_object('room_id',$5::text,'room_code',$6::text,'revoked_count',$7::integer,'raw_token_stored',false),now())
                ''',
                uuid.uuid4(), prop["id"], user["id"], issued["qr_id"], str(room["id"]), room["code"], len(revoked),
            )
    return issued


@admin_router.post("/room-qrs/issue-missing", status_code=status.HTTP_201_CREATED)
async def issue_missing_qrs(
    payload: BatchIssuePayload,
    request: Request,
    user: dict[str, Any] = Depends(admin_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await property_context(conn)
            rooms = await conn.fetch(
                '''
                SELECT room.id,room.code,
                       EXISTS(SELECT 1 FROM room_qrs qr WHERE qr."roomId"=room.id AND qr.status='ACTIVE') AS has_active
                FROM rooms room
                WHERE room."propertyId"=$1
                ORDER BY room.code
                FOR UPDATE OF room
                ''',
                prop["id"],
            )
            issued = []
            existing = []
            for room in rooms:
                if room["has_active"]:
                    if payload.include_existing:
                        existing.append({"room_id": str(room["id"]), "room_code": room["code"]})
                    continue
                issued.append(
                    await issue_room_qr(
                        conn,
                        property_id=prop["id"],
                        room_id=room["id"],
                        room_code=room["code"],
                    )
                )
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'ISSUE_MISSING','RoomQr','PMS_GUEST_OS','SUCCESS',
                  jsonb_build_object('issued_count',$4::integer,'raw_tokens_stored',false),now())
                ''',
                uuid.uuid4(), prop["id"], user["id"], len(issued),
            )
    return {
        "issued": issued,
        "existing": existing,
        "issued_count": len(issued),
        "raw_tokens_display_once": True,
        "warning": "Save/print the returned QR codes now. Plaintext room tokens are never stored and cannot be recovered later.",
    }


@public_router.get("/rooms/{token}")
async def room_context(
    token: str,
    request: Request,
    tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE),
):
    async with request.app.state.db.acquire() as conn:
        qr = await resolve_room_qr(conn, token)
        if not qr:
            raise HTTPException(status_code=404, detail={"code": "ROOM_QR_NOT_FOUND"})
        stay = await current_stay_for_room(conn, qr["roomId"])
        if not stay:
            return generic_room_context(qr, active_stay=False)
        session = await valid_guest_session(conn, tc_guest_session)
        if not session or session["stayId"] != stay["stayId"] or session["guestId"] != stay["guestId"]:
            return generic_room_context(qr, active_stay=True)

        return {
            "qr_valid": True,
            "authenticated": True,
            "verification_required": False,
            "active_stay": True,
            "room": {
                "code": qr["room_code"],
                "name": qr["room_name"],
                "room_type_name": qr["room_type_name"],
                "building_or_zone": qr["buildingOrZone"],
                "floor": qr["floorLabel"],
            },
            "guest": {
                "first_name": stay["firstName"] or "Гость",
            },
            "stay": {
                "check_in": stay["checkIn"],
                "check_out": stay["checkOut"],
            },
            "privacy": "MINIMAL_GUEST_CONTEXT",
        }


@public_router.post("/rooms/{token}/verify")
async def verify_room_pin(
    token: str,
    payload: VerifyPinPayload,
    request: Request,
    response: Response,
):
    client_hash = client_key_hash(request)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            qr = await resolve_room_qr(conn, token, lock=True)
            if not qr:
                raise HTTPException(status_code=404, detail={"code": "ROOM_QR_NOT_FOUND"})
            stay = await current_stay_for_room(conn, qr["roomId"])
            if not stay:
                raise HTTPException(status_code=409, detail={"code": "NO_ACTIVE_STAY"})

            failures = await conn.fetchval(
                '''
                SELECT count(*)::int
                FROM audit_logs
                WHERE "propertyId"=$1 AND resource='RoomQr' AND "resourceId"=$2
                  AND action='VERIFY_PIN' AND source='GUEST_OS' AND result='FAILURE'
                  AND "createdAt" >= now() - ($3::text || ' minutes')::interval
                  AND "afterJson"->>'client_key_hash'=$4
                ''',
                qr["propertyId"],
                str(qr["qr_id"]),
                str(PIN_FAILURE_WINDOW_MINUTES),
                client_hash,
            )
            if failures >= PIN_FAILURE_LIMIT:
                await write_verify_audit(
                    conn,
                    property_id=qr["propertyId"],
                    qr_id=qr["qr_id"],
                    result="BLOCKED",
                    client_hash=client_hash,
                    reason="RATE_LIMIT",
                    stay_id=stay["stayId"],
                )
                raise HTTPException(
                    status_code=429,
                    detail={"code": "PIN_RATE_LIMIT", "retry_after_minutes": PIN_FAILURE_WINDOW_MINUTES},
                    headers={"Retry-After": str(PIN_FAILURE_WINDOW_MINUTES * 60)},
                )

            pin_expires = stay["guestAccessPinExpiresAt"]
            now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
            if not stay["guestAccessPinHash"] or not pin_expires:
                raise HTTPException(status_code=409, detail={"code": "PIN_NOT_ISSUED"})
            if pin_expires <= now_naive:
                raise HTTPException(status_code=409, detail={"code": "PIN_EXPIRED", "action": "ASK_RECEPTION_FOR_NEW_PIN"})

            if not verify_pin_hash(payload.pin, stay["guestAccessPinHash"]):
                await write_verify_audit(
                    conn,
                    property_id=qr["propertyId"],
                    qr_id=qr["qr_id"],
                    result="FAILURE",
                    client_hash=client_hash,
                    reason="WRONG_PIN",
                    stay_id=stay["stayId"],
                )
                if failures + 1 >= PIN_FAILURE_LIMIT:
                    raise HTTPException(
                        status_code=429,
                        detail={"code": "PIN_RATE_LIMIT", "retry_after_minutes": PIN_FAILURE_WINDOW_MINUTES},
                        headers={"Retry-After": str(PIN_FAILURE_WINDOW_MINUTES * 60)},
                    )
                raise HTTPException(status_code=401, detail={"code": "PIN_INVALID", "attempts_remaining": PIN_FAILURE_LIMIT - failures - 1})

            expiry = session_expiry(stay["checkOut"], stay["timezone"])
            if expiry <= now_naive:
                raise HTTPException(status_code=409, detail={"code": "STAY_ACCESS_WINDOW_ENDED"})

            raw_session = secrets.token_urlsafe(48)
            session_id = uuid.uuid4()
            await conn.execute(
                '''
                INSERT INTO guest_sessions (
                  id,"propertyId","stayId","guestId","roomQrId","tokenHash",status,
                  "verificationMethod","verifiedAt","expiresAt","lastSeenAt","createdAt","updatedAt"
                ) VALUES ($1,$2,$3,$4,$5,$6,'ACTIVE','PIN',now(),$7,now(),now(),now())
                ''',
                session_id,
                qr["propertyId"],
                stay["stayId"],
                stay["guestId"],
                qr["qr_id"],
                hash_secret(raw_session),
                expiry,
            )
            await write_verify_audit(
                conn,
                property_id=qr["propertyId"],
                qr_id=qr["qr_id"],
                result="SUCCESS",
                client_hash=client_hash,
                reason="PIN_VERIFIED",
                stay_id=stay["stayId"],
                session_id=session_id,
            )
            await conn.execute(
                '''
                INSERT INTO guest_history_events (
                  id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt"
                ) VALUES ($1,$2,$3,$4,'GUEST_OS_SESSION_VERIFIED','GUEST_OS',
                  jsonb_build_object('room_id',$5::text,'room_qr_id',$6::text,'session_id',$7::text),now(),now())
                ''',
                uuid.uuid4(), qr["propertyId"], stay["guestId"], stay["stayId"],
                str(qr["roomId"]), str(qr["qr_id"]), str(session_id),
            )

    response.set_cookie(
        key=GUEST_COOKIE,
        value=raw_session,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
        expires=expiry.replace(tzinfo=timezone.utc),
    )
    return {
        "verified": True,
        "session_expires_at": expiry,
        "room_code": qr["room_code"],
        "guest": {"first_name": stay["firstName"] or "Гость"},
        "privacy": "MINIMAL_GUEST_CONTEXT",
    }


@public_router.post("/logout")
async def logout_guest(
    request: Request,
    response: Response,
    tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE),
):
    if tc_guest_session:
        async with request.app.state.db.acquire() as conn:
            await conn.execute(
                '''
                UPDATE guest_sessions
                SET status='REVOKED',"revokedAt"=COALESCE("revokedAt",now()),"updatedAt"=now()
                WHERE "tokenHash"=$1 AND status='ACTIVE'
                ''',
                hash_secret(tc_guest_session),
            )
    response.delete_cookie(GUEST_COOKIE, path="/")
    return {"logged_out": True}
