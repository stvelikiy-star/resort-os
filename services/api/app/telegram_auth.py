import hashlib
import hmac
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from .auth import COOKIE_SECURE, SESSION_COOKIE, SESSION_TTL_HOURS, current_user, hash_session_token

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_INITDATA_MAX_AGE_SECONDS = int(os.environ.get("TELEGRAM_INITDATA_MAX_AGE_SECONDS", "600"))

router = APIRouter(prefix="/api/v1/auth/telegram", tags=["telegram-auth"])


class TelegramInitPayload(BaseModel):
    init_data: str = Field(min_length=20, max_length=12000)


def validate_init_data(init_data: str) -> dict[str, Any]:
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Telegram Mini App authentication is not configured")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received_hash = pairs.pop("hash", None)
    pairs.pop("signature", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Telegram initData has no hash")

    data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", TELEGRAM_BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(status_code=401, detail="Telegram initData signature is invalid")

    auth_date_raw = pairs.get("auth_date")
    try:
        auth_date = datetime.fromtimestamp(int(auth_date_raw or "0"), tz=timezone.utc)
    except (ValueError, OverflowError):
        raise HTTPException(status_code=401, detail="Telegram auth_date is invalid")

    now = datetime.now(timezone.utc)
    if auth_date > now + timedelta(seconds=60):
        raise HTTPException(status_code=401, detail="Telegram auth_date is in the future")
    if now - auth_date > timedelta(seconds=TELEGRAM_INITDATA_MAX_AGE_SECONDS):
        raise HTTPException(status_code=401, detail="Telegram initData has expired")

    try:
        telegram_user = json.loads(pairs.get("user", "{}"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=401, detail="Telegram user payload is invalid")
    telegram_id = telegram_user.get("id")
    if telegram_id is None:
        raise HTTPException(status_code=401, detail="Telegram user id is missing")

    return {
        "telegram_user_id": str(telegram_id),
        "telegram_username": telegram_user.get("username"),
        "first_name": telegram_user.get("first_name"),
        "last_name": telegram_user.get("last_name"),
        "auth_date": auth_date,
    }


async def set_staff_session(response: Response, conn, user_row) -> dict[str, Any]:
    raw_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)
    session_id = uuid.uuid4()
    await conn.execute(
        '''
        INSERT INTO auth_sessions (id,"userId","tokenHash","expiresAt","lastSeenAt","createdAt")
        VALUES ($1,$2,$3,$4,now(),now())
        ''',
        session_id,
        user_row["id"],
        hash_session_token(raw_token),
        expires_at,
    )
    response.set_cookie(
        SESSION_COOKIE,
        raw_token,
        max_age=SESSION_TTL_HOURS * 3600,
        expires=expires_at,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return {
        "id": str(user_row["id"]),
        "username": user_row["username"],
        "display_name": user_row["displayName"],
        "role": user_row["role"],
        "property_code": user_row["property_code"],
    }


@router.post("/login")
async def telegram_login(payload: TelegramInitPayload, request: Request, response: Response):
    telegram = validate_init_data(payload.init_data)
    async with request.app.state.db.acquire() as conn:
        row = await conn.fetchrow(
            '''
            SELECT u.id,u.username,u."displayName",u.role::text AS role,p.code AS property_code,u."propertyId"
            FROM staff_users u JOIN properties p ON p.id=u."propertyId"
            WHERE p.code=$1 AND u."telegramUserId"=$2 AND u."isActive"=true
            ''',
            PROPERTY_CODE,
            telegram["telegram_user_id"],
        )
        if not row:
            raise HTTPException(status_code=403, detail="Telegram account is not linked to an active staff user")
        result = await set_staff_session(response, conn, row)
        await conn.execute(
            '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"createdAt")
               VALUES ($1,$2,'STAFF',$3,'TELEGRAM_LOGIN','StaffUser',$3,'TELEGRAM_MINI_APP','SUCCESS',now())''',
            uuid.uuid4(), row["propertyId"], str(row["id"]),
        )
    return result


@router.post("/link")
async def link_telegram_account(
    payload: TelegramInitPayload,
    request: Request,
    user: dict[str, Any] = Depends(current_user),
):
    telegram = validate_init_data(payload.init_data)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            property_id = await conn.fetchval("SELECT id FROM properties WHERE code=$1", user["property_code"])
            conflict = await conn.fetchrow(
                '''SELECT id,username FROM staff_users WHERE "propertyId"=$1 AND "telegramUserId"=$2 AND id<>$3''',
                property_id,
                telegram["telegram_user_id"],
                uuid.UUID(user["id"]),
            )
            if conflict:
                raise HTTPException(status_code=409, detail="This Telegram account is already linked to another staff user")
            await conn.execute(
                '''
                UPDATE staff_users SET "telegramUserId"=$1,"telegramUsername"=$2,"telegramLinkedAt"=now(),"updatedAt"=now()
                WHERE id=$3 AND "propertyId"=$4
                ''',
                telegram["telegram_user_id"],
                telegram["telegram_username"],
                uuid.UUID(user["id"]),
                property_id,
            )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'LINK_TELEGRAM','StaffUser',$3,'TELEGRAM_MINI_APP','SUCCESS',
                     jsonb_build_object('telegram_user_id',$4::text,'telegram_username',$5::text),now())''',
                uuid.uuid4(), property_id, user["id"], telegram["telegram_user_id"], telegram["telegram_username"],
            )
    return {
        "linked": True,
        "telegram_user_id": telegram["telegram_user_id"],
        "telegram_username": telegram["telegram_username"],
    }
