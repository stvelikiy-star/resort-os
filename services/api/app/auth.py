import hashlib
import ipaddress
import os
import secrets
import time
import uuid
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Callable

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, model_validator
from .section_permissions import effective_section_permissions, role_or_section_allowed

SESSION_COOKIE = "resort_session"
PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
# The migration is staged before this flag is enabled. Keeping it fail-closed lets
# the existing single-property deployment continue while the trusted context is
# rolled through staging and verified against every property-scoped query.
MARINA_TENANT_CONTEXT_ENABLED = os.environ.get("MARINA_TENANT_CONTEXT_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
MARINA_SHARED_AUTH_PREVIEW_ENABLED = os.environ.get("MARINA_SHARED_AUTH_PREVIEW_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
_preview_attempts: dict[str, deque[float]] = {}
SESSION_TTL_HOURS = int(os.environ.get("SESSION_TTL_HOURS", "12"))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN") or None
AUTH_TRUST_PROXY_HEADERS = os.environ.get("AUTH_TRUST_PROXY_HEADERS", "false").lower() in {"1", "true", "yes"}
AUTH_LOGIN_WINDOW_SECONDS = max(30, int(os.environ.get("AUTH_LOGIN_WINDOW_SECONDS", "900")))
AUTH_LOGIN_PAIR_MAX_FAILURES = max(2, int(os.environ.get("AUTH_LOGIN_PAIR_MAX_FAILURES", "5")))
AUTH_LOGIN_IP_MAX_FAILURES = max(
    AUTH_LOGIN_PAIR_MAX_FAILURES + 1,
    int(os.environ.get("AUTH_LOGIN_IP_MAX_FAILURES", "30")),
)

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginPayload(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=3, max_length=256)
    tenant_code: str | None = Field(default=None, min_length=3, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    property_code: str | None = Field(default=None, min_length=3, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

    @model_validator(mode="after")
    def enforce_login_length(self):
        demo = os.environ.get("APP_ENV") == "staging" and PROPERTY_CODE == "MARINA_HOTEL01"
        public_demo = (
            os.environ.get("APP_ENV") == "staging"
            and PROPERTY_CODE == "MARINA_DEMO"
            and not MARINA_TENANT_CONTEXT_ENABLED
            and self.username.strip().lower() == "demo"
            and len(self.password) >= 6
        )
        demo = (demo or public_demo) and not MARINA_SHARED_AUTH_PREVIEW_ENABLED
        if not demo and len(self.password) < 8:
            raise ValueError("Password must contain at least 8 characters")
        return self


class AuthUser(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    property_code: str
    property_id: str | None = None
    tenant_id: str | None = None
    module_permissions: list[str] | None = None
    module_permissions_custom: bool = False


def _tenant_context_select_sql() -> str:
    """Return only DB-derived tenant context; never accept it from the client.

    The old database has no properties.tenantId column. The feature flag therefore
    gates the new column reference until migration zz107 is applied in staging.
    """

    if not MARINA_TENANT_CONTEXT_ENABLED:
        return 'p.id AS property_id, NULL::uuid AS tenant_id'
    return 'p.id AS property_id, p."tenantId" AS tenant_id'


def _optional_uuid_text(value: Any) -> str | None:
    return str(value) if value is not None else None


def shared_auth_preview_guard() -> None:
    if MARINA_SHARED_AUTH_PREVIEW_ENABLED and (
        os.environ.get("APP_ENV") != "staging" or not MARINA_TENANT_CONTEXT_ENABLED
    ):
        raise HTTPException(503, detail="Shared authentication preview requires isolated staging and tenant context")
    if MARINA_SHARED_AUTH_PREVIEW_ENABLED and PROPERTY_CODE in {"MARINA_DEMO", "MARINA_HOTEL01"}:
        raise HTTPException(503, detail="Existing synthetic environments cannot host the shared authentication preview")


def _preview_login_limit(client_ip: str) -> None:
    # Coarse per-process protection also covers nonexistent hotel selectors,
    # before any DB lookup. Existing DB-backed throttling remains in force for
    # known workspaces. This preview is not a production-wide rate limiter.
    now = time.monotonic()
    key = _throttle_key("PREVIEW_IP", client_ip)
    for old in [k for k, q in _preview_attempts.items() if not q or now - q[-1] >= 60]:
        del _preview_attempts[old]
    if key not in _preview_attempts:
        if len(_preview_attempts) >= 5000:
            raise _invalid_login()
        _preview_attempts[key] = deque()
    queue = _preview_attempts[key]
    while queue and now - queue[0] >= 60:
        queue.popleft()
    if len(queue) >= 30:
        raise _invalid_login()
    queue.append(now)


def _shared_session_context(token: str) -> tuple[uuid.UUID, uuid.UUID]:
    try:
        prefix, tenant_id, property_id, random_part = token.split(".")
        if prefix != "ms1" or len(random_part) != 64:
            raise ValueError
        return uuid.UUID(tenant_id), uuid.UUID(property_id)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(401, detail="Session expired or invalid") from None


async def trusted_property_id(conn, user: dict[str, Any]) -> uuid.UUID:
    """Resolve the authenticated property from the database-derived context.

    Legacy deployments keep the PROPERTY_CODE boundary. Once the Marina tenant
    flag is enabled, authenticated routes must use the session's property_id and
    active tenant relationship instead of a global environment property.
    """

    if not MARINA_TENANT_CONTEXT_ENABLED:
        value = await conn.fetchval(
            'SELECT id FROM properties WHERE code=$1',
            PROPERTY_CODE,
        )
    else:
        raw_property_id = user.get("property_id")
        raw_tenant_id = user.get("tenant_id")
        try:
            property_uuid = uuid.UUID(str(raw_property_id))
            tenant_uuid = uuid.UUID(str(raw_tenant_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant context") from exc
        value = await conn.fetchval(
            '''
            SELECT p.id
            FROM properties p
            JOIN tenants t ON t.id=p."tenantId"
            WHERE p.id=$1 AND p."tenantId"=$2 AND t.status='ACTIVE'
            ''',
            property_uuid,
            tenant_uuid,
        )

    if not value:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Property not loaded")
    return value


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _invalid_login() -> HTTPException:
    # Keep the same response for an unknown user, bad password and throttled request.
    # Do not expose whether a username exists or whether a throttle threshold was hit.
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")


def _client_ip(request: Request) -> str:
    direct = request.client.host if request.client and request.client.host else "unknown"
    if not AUTH_TRUST_PROXY_HEADERS:
        return direct

    # X-Forwarded-For is trusted only when explicitly enabled for a deployment where
    # Resort Core is reachable exclusively through the controlled reverse proxy.
    forwarded = request.headers.get("x-forwarded-for", "")
    candidate = forwarded.split(",", 1)[0].strip() if forwarded else ""
    if not candidate:
        return direct
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return direct


def _throttle_key(kind: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"{kind}:{digest}"


def _throttle_keys(username: str, client_ip: str, boundary: str | None = None) -> tuple[str, str]:
    scope = PROPERTY_CODE if boundary is None else boundary
    pair_key = _throttle_key("PAIR", scope, username, client_ip)
    ip_key = _throttle_key("IP", scope, client_ip)
    return pair_key, ip_key


async def _release_login_locks(conn, keys: list[str]) -> None:
    for key in reversed(keys):
        await conn.execute("SELECT pg_advisory_unlock(hashtextextended($1, 0))", key)


async def _acquire_login_locks(conn, pair_key: str, ip_key: str) -> list[str]:
    keys = sorted({pair_key, ip_key})
    acquired: list[str] = []
    try:
        for key in keys:
            # Session-level PostgreSQL advisory locks serialize attempts sharing a pair
            # or source IP across all API workers. Explicit cleanup is required because
            # asyncpg connections are pooled and therefore outlive one request.
            await conn.execute("SELECT pg_advisory_lock(hashtextextended($1, 0))", key)
            acquired.append(key)
        return acquired
    except BaseException:
        # Never return a pooled connection carrying a partially-acquired session lock.
        await _release_login_locks(conn, acquired)
        raise


async def _login_is_throttled(conn, property_id: uuid.UUID, pair_key: str, ip_key: str) -> bool:
    window_start = datetime.utcnow() - timedelta(seconds=AUTH_LOGIN_WINDOW_SECONDS)
    pair_reset = await conn.fetchval(
        '''
        SELECT max("createdAt")
        FROM audit_logs
        WHERE "propertyId"=$1
          AND action='LOGIN_THROTTLE_RESET'
          AND resource='AuthThrottle'
          AND "resourceId"=$2
        ''',
        property_id,
        pair_key,
    )
    pair_since = max(window_start, pair_reset) if pair_reset else window_start
    pair_failures = await conn.fetchval(
        '''
        SELECT count(*)::int
        FROM audit_logs
        WHERE "propertyId"=$1
          AND action='LOGIN_FAILED'
          AND resource='AuthThrottle'
          AND "resourceId"=$2
          AND "createdAt">=$3
        ''',
        property_id,
        pair_key,
        pair_since,
    )
    ip_failures = await conn.fetchval(
        '''
        SELECT count(*)::int
        FROM audit_logs
        WHERE "propertyId"=$1
          AND action='LOGIN_FAILED'
          AND resource='AuthThrottle'
          AND "resourceId"=$2
          AND "createdAt">=$3
        ''',
        property_id,
        ip_key,
        window_start,
    )
    return pair_failures >= AUTH_LOGIN_PAIR_MAX_FAILURES or ip_failures >= AUTH_LOGIN_IP_MAX_FAILURES


async def _record_login_failure(conn, property_id: uuid.UUID, pair_key: str, ip_key: str) -> None:
    # Only one-way fingerprints are persisted. Raw usernames, IPs, passwords and tokens
    # are deliberately excluded from throttle evidence.
    await conn.executemany(
        '''
        INSERT INTO audit_logs (
            id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"createdAt"
        ) VALUES ($1,$2,'SYSTEM',NULL,'LOGIN_FAILED','AuthThrottle',$3,'AUTH_THROTTLE','FAILURE',now())
        ''',
        [
            (uuid.uuid4(), property_id, pair_key),
            (uuid.uuid4(), property_id, ip_key),
        ],
    )


async def _record_pair_reset(conn, property_id: uuid.UUID, pair_key: str) -> None:
    await conn.execute(
        '''
        INSERT INTO audit_logs (
            id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"createdAt"
        ) VALUES ($1,$2,'SYSTEM',NULL,'LOGIN_THROTTLE_RESET','AuthThrottle',$3,'AUTH_THROTTLE','SUCCESS',now())
        ''',
        uuid.uuid4(),
        property_id,
        pair_key,
    )


async def resolve_session_user(conn, token: str | None, *, touch: bool = True) -> dict[str, Any]:
    """Use one server-side session boundary for HTTP and WebSocket callers."""
    shared_auth_preview_guard()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    token_hash = hash_session_token(token)
    shared_context = _shared_session_context(token) if MARINA_SHARED_AUTH_PREVIEW_ENABLED else None
    if not MARINA_SHARED_AUTH_PREVIEW_ENABLED and token.startswith("ms1."):
        raise HTTPException(401, detail="Session expired or invalid")
    active_tenant_filter = "" if not MARINA_TENANT_CONTEXT_ENABLED else '''
        AND EXISTS (SELECT 1 FROM tenants t WHERE t.id=p."tenantId" AND t.status='ACTIVE')
    '''
    now = datetime.utcnow()

    row = await conn.fetchrow(
        f'''
        SELECT s.id AS session_id, s."expiresAt", s."revokedAt",
               u.id AS user_id, u.username, u."displayName", u.role::text AS role, u."isActive",
               u."modulePermissions" AS module_permissions, (u."modulePermissions" IS NOT NULL) AS module_permissions_custom,
               p.code AS property_code,
               {_tenant_context_select_sql()}
        FROM auth_sessions s
        JOIN staff_users u ON u.id = s."userId"
        JOIN properties p ON p.id = u."propertyId"
        WHERE s."tokenHash" = $1 {active_tenant_filter}
        ''',
        token_hash,
    )
    if (
        not row
        or row["revokedAt"] is not None
        or row["expiresAt"] <= now
        or not row["isActive"]
        or (not MARINA_SHARED_AUTH_PREVIEW_ENABLED and row["property_code"] != PROPERTY_CODE)
        or (shared_context is not None and (
            _optional_uuid_text(row["tenant_id"]) != str(shared_context[0])
            or _optional_uuid_text(row["property_id"]) != str(shared_context[1])
        ))
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")

    if touch:
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
        "property_id": _optional_uuid_text(row["property_id"]),
        "tenant_id": _optional_uuid_text(row["tenant_id"]),
        "module_permissions": effective_section_permissions(row["role"], row["module_permissions"]),
        "module_permissions_custom": bool(row["module_permissions_custom"]),
    }


async def current_user(request: Request) -> dict[str, Any]:
    shared_auth_preview_guard()
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    async with request.app.state.db.acquire() as conn:
        return await resolve_session_user(conn, token)


def require_roles(*allowed_roles: str, module_grant: bool = True) -> Callable:
    async def dependency(request: Request, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        if not role_or_section_allowed(user, request.url.path, allowed_roles, module_grant=module_grant):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")
        return user

    return dependency


@router.get("/mode")
async def authentication_mode():
    shared_auth_preview_guard()
    return {"mode": "shared_auth_preview" if MARINA_SHARED_AUTH_PREVIEW_ENABLED else "single_property",
            "workspaces_available": False if MARINA_SHARED_AUTH_PREVIEW_ENABLED else None}


@router.post("/login", response_model=AuthUser)
async def login(payload: LoginPayload, request: Request, response: Response):
    shared_auth_preview_guard()
    shared = MARINA_SHARED_AUTH_PREVIEW_ENABLED
    if shared and (not payload.tenant_code or not payload.property_code):
        raise _invalid_login()
    if not shared and (payload.tenant_code is not None or payload.property_code is not None):
        raise HTTPException(422, detail="Shared hotel selection is not enabled")
    username = payload.username.strip().lower()
    client_ip = _client_ip(request)
    if shared:
        _preview_login_limit(client_ip)
    boundary = f"{payload.tenant_code}/{payload.property_code}" if shared else None
    pair_key, ip_key = _throttle_keys(username, client_ip, boundary)

    async with request.app.state.db.acquire() as conn:
        lock_keys = await _acquire_login_locks(conn, pair_key, ip_key)
        try:
            if shared:
                property_id = await conn.fetchval('''
                    SELECT p.id FROM properties p JOIN tenants t ON t.id=p."tenantId"
                    WHERE t.code=$1 AND p.code=$2 AND t.status='ACTIVE'
                ''', payload.tenant_code, payload.property_code)
            else:
                property_id = await conn.fetchval('SELECT id FROM properties WHERE code=$1', PROPERTY_CODE)
            if not property_id:
                if shared:
                    raise _invalid_login()
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Property not loaded")

            if await _login_is_throttled(conn, property_id, pair_key, ip_key):
                raise _invalid_login()

            user_filter = '''p.id = $1 AND EXISTS (
                SELECT 1 FROM tenants t WHERE t.id=p."tenantId" AND t.status='ACTIVE'
            )''' if shared else "p.code = $1"
            row = await conn.fetchrow(
                f'''
                SELECT u.id, u.username, u."displayName", u."passwordHash", u.role::text AS role,
                       u."isActive", u."propertyId", u."modulePermissions" AS module_permissions,
                       (u."modulePermissions" IS NOT NULL) AS module_permissions_custom,
                       p.code AS property_code,
                       {_tenant_context_select_sql()}
                FROM staff_users u
                JOIN properties p ON p.id = u."propertyId"
                WHERE {user_filter} AND lower(u.username) = $2
                ''',
                property_id if shared else PROPERTY_CODE,
                username,
            )

            if not row or not row["isActive"] or (shared and row["propertyId"] != property_id):
                await _record_login_failure(conn, property_id, pair_key, ip_key)
                raise _invalid_login()

            try:
                password_hasher.verify(row["passwordHash"], payload.password)
            except VerificationError:
                await _record_login_failure(conn, property_id, pair_key, ip_key)
                raise _invalid_login()

            if password_hasher.check_needs_rehash(row["passwordHash"]):
                await conn.execute(
                    'UPDATE staff_users SET "passwordHash" = $1, "updatedAt" = now() WHERE id = $2',
                    password_hasher.hash(payload.password),
                    row["id"],
                )

            raw_token = secrets.token_urlsafe(48)
            if shared:
                # The complete contextual token is hashed into auth_sessions.
                # Its IDs are never trusted without a matching DB session and
                # matching current staff/tenant membership in current_user.
                raw_token = f"ms1.{row['tenant_id']}.{row['property_id']}.{raw_token}"
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
            await _record_pair_reset(conn, property_id, pair_key)
        finally:
            await _release_login_locks(conn, lock_keys)

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
        property_id=_optional_uuid_text(row["property_id"]),
        tenant_id=_optional_uuid_text(row["tenant_id"]),
        module_permissions=effective_section_permissions(row["role"], row["module_permissions"]),
        module_permissions_custom=bool(row["module_permissions_custom"]),
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
        property_id=user.get("property_id"),
        tenant_id=user.get("tenant_id"),
        module_permissions=user.get("module_permissions", []),
        module_permissions_custom=bool(user.get("module_permissions_custom")),
    )
