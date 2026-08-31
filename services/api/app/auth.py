import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

SESSION_COOKIE = "resort_session"
PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
SESSION_TTL_HOURS = int(os.environ.get("SESSION_TTL_HOURS", "12"))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN") or None

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginPayload(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8, max_length=256)


class AuthUser(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    property_code: str


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def current_user(request: Request) -> dict[str, Any]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    token_hash = hash_session_token(token)
    now = datetime.utcnow()

    async with request.app.state.db.acquire() as conn:
        row = await conn.fetchrow(
            '''
            SELECT s.id AS session_id, s."expiresAt", s."revokedAt",
                   u.id AS user_id, u.username, u."displayName", u.role::text AS role, u."isActive",
                   p.code AS property_code
            FROM auth_sessions s
            JOIN staff_users u ON u.id = s."userId"
            JOIN properties p ON p.id = u."propertyId"
            WHERE s."tokenHash" = $1
            ''',
            token_hash,
        )
        if (
            not row
            or row["revokedAt"] is not None
            or row["expiresAt"] <= now
            or not row["isActive"]
            or row["property_code"] != PROPERTY_CODE
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")

        await conn.execute(
            'UPDATE auth_sessions SET "lastSeenAt" = now() WHERE id = $1',
            row["session_id"],
        )

    return {
        "id": str(row["user_id"]),
        "session_id": str(row["session_id"]),
        "username": row["username"],
        "display_name": row["displayName"],
        "role": row["role"],
        "property_code": row["property_code"],
    }


def require_roles(*allowed_roles: str) -> Callable:
    """Server-side RBAC dependency.

    ADMIN intentionally inherits MANAGER-authorized endpoints, but never OWNER-only
    endpoints. Narrow roles such as RECEPTION/DINING do not inherit permissions and
    must be named explicitly by each domain router.
    """
    allowed = set(allowed_roles)

    async def dependency(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        role = user["role"]
        permitted = role in allowed or (role == "ADMIN" and "MANAGER" in allowed)
        if not permitted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")
        return user

    return dependency


@router.post("/login", response_model=AuthUser)
async def login(payload: LoginPayload, request: Request, response: Response):
    username = payload.username.strip().lower()
    async with request.app.state.db.acquire() as conn:
        row = await conn.fetchrow(
            '''
            SELECT u.id, u.username, u."displayName", u."passwordHash", u.role::text AS role,
                   u."isActive", u."propertyId", p.code AS property_code
            FROM staff_users u
            JOIN properties p ON p.id = u."propertyId"
            WHERE p.code = $1 AND lower(u.username) = $2
            ''',
            PROPERTY_CODE,
            username,
        )

        if not row or not row["isActive"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

        try:
            password_hasher.verify(row["passwordHash"], payload.password)
        except VerificationError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

        if password_hasher.check_needs_rehash(row["passwordHash"]):
            await conn.execute(
                'UPDATE staff_users SET "passwordHash" = $1, "updatedAt" = now() WHERE id = $2',
                password_hasher.hash(payload.password),
                row["id"],
            )

        raw_token = secrets.token_urlsafe(48)
        token_hash = hash_session_token(raw_token)
        expires_at = datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)
        session_id = uuid.uuid4()

        await conn.execute(
            '''
            INSERT INTO auth_sessions (id, "userId", "tokenHash", "expiresAt", "lastSeenAt", "createdAt")
            VALUES ($1, $2, $3, $4, now(), now())
            ''',
            session_id,
            row["id"],
            token_hash,
            expires_at,
        )
        await conn.execute(
            '''
            INSERT INTO audit_logs (
                id, "propertyId", "actorType", "actorId", action, resource, "resourceId", source, result, "createdAt"
            ) VALUES ($1, $2, 'STAFF', $3, 'LOGIN', 'AuthSession', $4, 'WEB_ADMIN', 'SUCCESS', now())
            ''',
            uuid.uuid4(),
            row["propertyId"],
            str(row["id"]),
            str(session_id),
        )

    response.set_cookie(
        SESSION_COOKIE,
        raw_token,
        max_age=SESSION_TTL_HOURS * 3600,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
        domain=COOKIE_DOMAIN,
    )
    return AuthUser(
        id=str(row["id"]),
        username=row["username"],
        display_name=row["displayName"],
        role=row["role"],
        property_code=row["property_code"],
    )


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        async with request.app.state.db.acquire() as conn:
            await conn.execute(
                'UPDATE auth_sessions SET "revokedAt" = now() WHERE "tokenHash" = $1 AND "revokedAt" IS NULL',
                hash_session_token(token),
            )
    response.delete_cookie(SESSION_COOKIE, path="/", domain=COOKIE_DOMAIN)


@router.get("/me", response_model=AuthUser)
async def me(user: dict[str, Any] = Depends(current_user)):
    return AuthUser(
        id=user["id"],
        username=user["username"],
        display_name=user["display_name"],
        role=user["role"],
        property_code=user["property_code"],
    )
