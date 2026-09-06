import json
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from .auth import password_hasher, require_roles

router = APIRouter(prefix="/api/v1/admin/staff", tags=["admin-staff"])
manager_access = require_roles("OWNER", "MANAGER")
owner_access = require_roles("OWNER")

ManagedRole = Literal[
    "MANAGER",
    "RECEPTION",
    "MAID",
    "TECHNICIAN",
    "STORE_STAFF",
    "DINING_STAFF",
    "CONTENT_MANAGER",
]
MANAGED_ROLES = [
    "MANAGER",
    "RECEPTION",
    "MAID",
    "TECHNICIAN",
    "STORE_STAFF",
    "DINING_STAFF",
    "CONTENT_MANAGER",
]


class StaffCreate(BaseModel):
    username: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    display_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=12, max_length=256)
    role: ManagedRole


class StaffPatch(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    password: str | None = Field(default=None, min_length=12, max_length=256)
    role: ManagedRole | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one staff field must be provided")
        return self


async def _property(conn, property_code: str):
    prop = await conn.fetchrow(
        'SELECT id,timezone FROM properties WHERE code=$1',
        property_code,
    )
    if not prop:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return prop


def _staff_payload(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "username": row["username"],
        "display_name": row["displayName"],
        "role": row["role"],
        "active": bool(row["isActive"]),
        "telegram_linked": row["telegramUserId"] is not None,
        "telegram_username": row["telegramUsername"],
        "telegram_linked_at": row["telegramLinkedAt"],
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
    }


async def _audit(
    conn,
    *,
    property_id: uuid.UUID,
    actor: dict[str, Any],
    action: str,
    target_id: uuid.UUID,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
):
    await conn.execute(
        '''
        INSERT INTO audit_logs (
          id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,
          "beforeJson","afterJson","createdAt"
        ) VALUES ($1,$2,'STAFF',$3,$4,'StaffUser',$5,'STAFF_MANAGEMENT','SUCCESS',$6::jsonb,$7::jsonb,now())
        ''',
        uuid.uuid4(),
        property_id,
        actor["id"],
        action,
        str(target_id),
        json.dumps(before, ensure_ascii=False, default=str) if before is not None else None,
        json.dumps(after, ensure_ascii=False, default=str) if after is not None else None,
    )


@router.get("/overview")
async def staff_overview(
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn, user["property_code"])
        pid = prop["id"]
        today = await conn.fetchval("SELECT (now() AT TIME ZONE $1)::date", prop["timezone"])

        staff = await conn.fetch(
            '''
            WITH task_stats AS (
              SELECT "assignedToId" AS user_id,
                     count(*) FILTER (WHERE status IN ('OPEN','IN_PROGRESS','IN_INSPECTION'))::int AS active_tasks,
                     count(*) FILTER (
                       WHERE "completedAt" IS NOT NULL
                         AND ("completedAt" AT TIME ZONE $2)::date=$3
                     )::int AS completed_today,
                     count(*) FILTER (
                       WHERE type='HOUSEKEEPING' AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
                     )::int AS housekeeping_active,
                     count(*) FILTER (
                       WHERE type='MAINTENANCE' AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
                     )::int AS maintenance_active
              FROM operational_tasks
              WHERE "propertyId"=$1 AND "assignedToId" IS NOT NULL
              GROUP BY "assignedToId"
            ),
            session_stats AS (
              SELECT "userId" AS user_id,MAX("lastSeenAt") AS last_session_seen_at
              FROM auth_sessions
              WHERE "revokedAt" IS NULL
              GROUP BY "userId"
            )
            SELECT u.id,u.username,u."displayName",u.role::text AS role,u."isActive",
                   u."telegramUserId",u."telegramUsername",u."telegramLinkedAt",u."createdAt",u."updatedAt",
                   COALESCE(ts.active_tasks,0)::int AS active_tasks,
                   COALESCE(ts.completed_today,0)::int AS completed_today,
                   COALESCE(ts.housekeeping_active,0)::int AS housekeeping_active,
                   COALESCE(ts.maintenance_active,0)::int AS maintenance_active,
                   ss.last_session_seen_at
            FROM staff_users u
            LEFT JOIN task_stats ts ON ts.user_id=u.id
            LEFT JOIN session_stats ss ON ss.user_id=u.id
            WHERE u."propertyId"=$1
            ORDER BY
              CASE u.role::text
                WHEN 'OWNER' THEN 0 WHEN 'MANAGER' THEN 1 WHEN 'RECEPTION' THEN 2
                WHEN 'MAID' THEN 3 WHEN 'TECHNICIAN' THEN 4 WHEN 'DINING_STAFF' THEN 5
                WHEN 'STORE_STAFF' THEN 6 WHEN 'CONTENT_MANAGER' THEN 7 ELSE 8
              END,
              u."displayName"
            ''',
            pid,
            prop["timezone"],
            today,
        )

        unassigned = await conn.fetchrow(
            '''
            SELECT
              count(*) FILTER (WHERE type='HOUSEKEEPING')::int AS housekeeping,
              count(*) FILTER (WHERE type='MAINTENANCE')::int AS maintenance,
              count(*) FILTER (WHERE type='GUEST_REQUEST')::int AS guest_requests,
              count(*)::int AS total
            FROM operational_tasks
            WHERE "propertyId"=$1
              AND "assignedToId" IS NULL
              AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
            ''',
            pid,
        )

    return {
        "local_date": today,
        "timezone": prop["timezone"],
        "staff": [
            {
                "id": str(row["id"]),
                "username": row["username"],
                "display_name": row["displayName"],
                "role": row["role"],
                "active": row["isActive"],
                "telegram_linked": row["telegramUserId"] is not None,
                "telegram_username": row["telegramUsername"],
                "telegram_linked_at": row["telegramLinkedAt"],
                "active_tasks": row["active_tasks"],
                "completed_today": row["completed_today"],
                "housekeeping_active": row["housekeeping_active"],
                "maintenance_active": row["maintenance_active"],
                "last_session_seen_at": row["last_session_seen_at"],
            }
            for row in staff
        ],
        "unassigned_active_tasks": dict(unassigned),
        "can_manage_access": user["role"] == "OWNER",
        "managed_roles": MANAGED_ROLES,
        "truth": "This is task/session visibility only. It is not an attendance, payroll or employee-performance score.",
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_staff_user(
    payload: StaffCreate,
    request: Request,
    user: dict[str, Any] = Depends(owner_access),
):
    username = payload.username.strip().lower()
    display_name = payload.display_name.strip()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            existing = await conn.fetchval(
                'SELECT id FROM staff_users WHERE "propertyId"=$1 AND username=$2',
                prop["id"],
                username,
            )
            if existing:
                raise HTTPException(status_code=409, detail="Username already exists")

            staff_id = uuid.uuid4()
            row = await conn.fetchrow(
                '''
                INSERT INTO staff_users (
                  id,"propertyId",username,"displayName","passwordHash",role,"isActive","createdAt","updatedAt"
                ) VALUES ($1,$2,$3,$4,$5,$6::"StaffRole",true,now(),now())
                RETURNING id,username,"displayName",role::text AS role,"isActive",
                          "telegramUserId","telegramUsername","telegramLinkedAt","createdAt","updatedAt"
                ''',
                staff_id,
                prop["id"],
                username,
                display_name,
                password_hasher.hash(payload.password),
                payload.role,
            )
            after = _staff_payload(row)
            await _audit(
                conn,
                property_id=prop["id"],
                actor=user,
                action="CREATE_STAFF_USER",
                target_id=staff_id,
                before=None,
                after={**after, "password_rotated": True},
            )
    return after


@router.patch("/{staff_id}")
async def patch_staff_user(
    staff_id: uuid.UUID,
    payload: StaffPatch,
    request: Request,
    user: dict[str, Any] = Depends(owner_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            current = await conn.fetchrow(
                '''
                SELECT id,username,"displayName",role::text AS role,"isActive",
                       "telegramUserId","telegramUsername","telegramLinkedAt","createdAt","updatedAt"
                FROM staff_users
                WHERE id=$1 AND "propertyId"=$2
                FOR UPDATE
                ''',
                staff_id,
                prop["id"],
            )
            if not current:
                raise HTTPException(status_code=404, detail="Staff user not found")
            if current["role"] == "OWNER":
                raise HTTPException(
                    status_code=403,
                    detail="Owner account is protected; use the dedicated owner credential procedure",
                )

            before = _staff_payload(current)
            display_name = payload.display_name.strip() if payload.display_name is not None else current["displayName"]
            role = payload.role if payload.role is not None else current["role"]
            active = payload.active if payload.active is not None else bool(current["isActive"])
            password_hash = password_hasher.hash(payload.password) if payload.password is not None else None

            row = await conn.fetchrow(
                '''
                UPDATE staff_users
                SET "displayName"=$2,
                    role=$3::"StaffRole",
                    "isActive"=$4,
                    "passwordHash"=COALESCE($5,"passwordHash"),
                    "updatedAt"=now()
                WHERE id=$1
                RETURNING id,username,"displayName",role::text AS role,"isActive",
                          "telegramUserId","telegramUsername","telegramLinkedAt","createdAt","updatedAt"
                ''',
                staff_id,
                display_name,
                role,
                active,
                password_hash,
            )
            security_changed = (
                role != current["role"]
                or active != bool(current["isActive"])
                or payload.password is not None
            )
            if security_changed:
                await conn.execute(
                    '''
                    UPDATE auth_sessions
                    SET "revokedAt"=now()
                    WHERE "userId"=$1 AND "revokedAt" IS NULL
                    ''',
                    staff_id,
                )

            after = _staff_payload(row)
            await _audit(
                conn,
                property_id=prop["id"],
                actor=user,
                action="UPDATE_STAFF_ACCESS" if security_changed else "UPDATE_STAFF_PROFILE",
                target_id=staff_id,
                before=before,
                after={**after, "password_rotated": payload.password is not None},
            )
    return after
