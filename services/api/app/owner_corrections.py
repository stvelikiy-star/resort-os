import json
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Literal

from asyncpg.exceptions import ExclusionViolationError
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field, model_validator

from .auth import password_hasher, require_roles


router = APIRouter(prefix="/api/v1/admin/owner-corrections", tags=["owner-corrections"])
commercial_access = require_roles("OWNER", "MANAGER", "RECEPTION")
manager_access = require_roles("OWNER", "MANAGER")
owner_access = require_roles("OWNER")


async def _property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


async def _audit(
    conn,
    *,
    property_id: uuid.UUID,
    user: dict[str, Any],
    action: str,
    resource: str,
    resource_id: str,
    after: dict[str, Any],
):
    await conn.execute(
        '''
        INSERT INTO audit_logs (
          id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
        ) VALUES ($1,$2,'STAFF',$3,$4,$5,$6,'OWNER_CORRECTIONS','SUCCESS',$7::jsonb,now())
        ''',
        uuid.uuid4(),
        property_id,
        user["id"],
        action,
        resource,
        resource_id,
        json.dumps(after, ensure_ascii=False),
    )


class AgentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    contact_name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=50)
    whatsapp: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    notes: str | None = Field(default=None, max_length=4000)
    access_username: str | None = Field(default=None, min_length=2, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    access_password: str | None = Field(default=None, min_length=12, max_length=256)

    @model_validator(mode="after")
    def validate_access_pair(self):
        if (self.access_username is None) != (self.access_password is None):
            raise ValueError("access_username and access_password must be provided together")
        return self


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    contact_name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=50)
    whatsapp: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    notes: str | None = Field(default=None, max_length=4000)
    active: bool | None = None


class AgentInteractionCreate(BaseModel):
    kind: Literal["CALL", "WHATSAPP", "MESSAGE", "MEETING", "NOTE", "TASK"] = "NOTE"
    note: str = Field(min_length=1, max_length=4000)
    next_contact_at: datetime | None = None


class AgentAccessPatch(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    password: str | None = Field(default=None, min_length=12, max_length=256)
    active: bool | None = None

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one access field must be provided")
        return self


@router.get("/agents")
async def list_agents(
    request: Request,
    search: str = Query(default="", max_length=160),
    include_inactive: bool = False,
    from_date: date | None = None,
    to_date: date | None = None,
    user: dict[str, Any] = Depends(commercial_access),
):
    if from_date and to_date and to_date < from_date:
        raise HTTPException(status_code=422, detail="to_date must be on or after from_date")
    async with request.app.state.db.acquire() as conn:
        property_id = await _property_id(conn, user["property_code"])
        rows = await conn.fetch(
            '''
            SELECT a.id,a.name,a."contactName",a.phone,a.whatsapp,a.email,a.notes,a.status,a."createdAt",a."updatedAt",
                   count(r.id)::int AS reservations,
                   coalesce(sum(CASE WHEN r.status NOT IN ('CANCELLED','NO_SHOW') THEN r."totalKgs" ELSE 0 END),0)::bigint AS booked_kgs,
                   coalesce(sum(pay.received_kgs),0)::bigint AS received_kgs,
                   coalesce(sum(CASE WHEN r.status NOT IN ('CANCELLED','NO_SHOW') THEN (r."checkOut"-r."checkIn") ELSE 0 END),0)::int AS room_nights,
                   max(r."checkIn") AS last_check_in,
                   access.username AS access_username,
                   access."isActive" AS access_active
            FROM booking_agents a
            LEFT JOIN reservations r ON r."agentId"=a.id
              AND ($4::date IS NULL OR r."checkIn">=$4::date)
              AND ($5::date IS NULL OR r."checkIn"<=$5::date)
            LEFT JOIN LATERAL (
              SELECT coalesce(sum(p."amountKgs") FILTER (WHERE p.status='RECEIVED'),0)::bigint AS received_kgs
              FROM payments p WHERE p."reservationId"=r.id
            ) pay ON true
            LEFT JOIN LATERAL (
              SELECT su.username,su."isActive"
              FROM staff_users su
              WHERE su."propertyId"=a."propertyId"
                AND su."bookingAgentId"=a.id
                AND su.role='AGENT'
              ORDER BY su."createdAt" ASC
              LIMIT 1
            ) access ON true
            WHERE a."propertyId"=$1
              AND ($2::boolean OR a.status='ACTIVE')
              AND ($3='' OR lower(a.name) LIKE '%'||lower($3)||'%' OR lower(coalesce(a."contactName",'')) LIKE '%'||lower($3)||'%'
                   OR coalesce(a.phone,'') LIKE '%'||$3||'%' OR coalesce(a.whatsapp,'') LIKE '%'||$3||'%')
            GROUP BY a.id,access.username,access."isActive"
            ORDER BY a.status,a.name
            ''',
            property_id,
            include_inactive,
            search.strip(),
            from_date,
            to_date,
        )
        return {
            "items": [
                {
                    "id": str(row["id"]),
                    "name": row["name"],
                    "contact_name": row["contactName"],
                    "phone": row["phone"],
                    "whatsapp": row["whatsapp"],
                    "email": row["email"],
                    "notes": row["notes"],
                    "status": row["status"],
                    "reservations": row["reservations"],
                    "booked_kgs": int(row["booked_kgs"] or 0),
                    "received_kgs": int(row["received_kgs"] or 0),
                    "room_nights": row["room_nights"],
                    "last_check_in": row["last_check_in"].isoformat() if row["last_check_in"] else None,
                    "access_username": row["access_username"],
                    "access_active": bool(row["access_active"]) if row["access_active"] is not None else None,
                }
                for row in rows
            ]
        }


@router.post("/agents", status_code=status.HTTP_201_CREATED)
async def create_agent(payload: AgentCreate, request: Request, user: dict[str, Any] = Depends(manager_access)):
    if payload.access_username and user["role"] != "OWNER":
        raise HTTPException(status_code=403, detail="Only OWNER can create agent login credentials")
    agent_id = uuid.uuid4()
    async with request.app.state.db.acquire() as conn:
        property_id = await _property_id(conn, user["property_code"])
        try:
            async with conn.transaction():
                await conn.execute(
                    '''INSERT INTO booking_agents (id,"propertyId",name,"contactName",phone,whatsapp,email,notes,status,"createdAt","updatedAt")
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'ACTIVE',now(),now())''',
                    agent_id,
                    property_id,
                    payload.name.strip(),
                    payload.contact_name,
                    payload.phone,
                    payload.whatsapp,
                    str(payload.email) if payload.email else None,
                    payload.notes,
                )
                access_username = None
                if payload.access_username and payload.access_password:
                    access_username = payload.access_username.strip().lower()
                    await conn.execute(
                        '''INSERT INTO staff_users (
                          id,"propertyId",username,"displayName","passwordHash",role,"bookingAgentId","isActive","createdAt","updatedAt"
                        ) VALUES ($1,$2,$3,$4,$5,'AGENT',$6,true,now(),now())''',
                        uuid.uuid4(),
                        property_id,
                        access_username,
                        payload.contact_name or payload.name.strip(),
                        password_hasher.hash(payload.access_password),
                        agent_id,
                    )
                await _audit(
                    conn,
                    property_id=property_id,
                    user=user,
                    action="AGENT_CREATE",
                    resource="BookingAgent",
                    resource_id=str(agent_id),
                    after={
                        **payload.model_dump(mode="json", exclude={"access_password"}),
                        "access_username": access_username,
                        "access_created": access_username is not None,
                    },
                )
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(status_code=409, detail="Название агента или логин уже заняты") from exc
            raise
    return {"id": str(agent_id), "status": "ACTIVE", "access_username": access_username}


@router.patch("/agents/{agent_id}")
async def update_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdate,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    values = payload.model_dump(exclude_unset=True)
    if not values:
        raise HTTPException(status_code=422, detail="No changes")
    async with request.app.state.db.acquire() as conn:
        property_id = await _property_id(conn, user["property_code"])
        current = await conn.fetchrow('SELECT * FROM booking_agents WHERE id=$1 AND "propertyId"=$2', agent_id, property_id)
        if not current:
            raise HTTPException(status_code=404, detail="Agent not found")
        name = values.get("name", current["name"])
        contact_name = values.get("contact_name", current["contactName"])
        phone = values.get("phone", current["phone"])
        whatsapp = values.get("whatsapp", current["whatsapp"])
        email = values.get("email", current["email"])
        notes = values.get("notes", current["notes"])
        status_value = ("ACTIVE" if values["active"] else "INACTIVE") if "active" in values else current["status"]
        await conn.execute(
            '''UPDATE booking_agents SET name=$3,"contactName"=$4,phone=$5,whatsapp=$6,email=$7,notes=$8,status=$9,"updatedAt"=now()
               WHERE id=$1 AND "propertyId"=$2''',
            agent_id,
            property_id,
            name,
            contact_name,
            phone,
            whatsapp,
            str(email) if email else None,
            notes,
            status_value,
        )
        await _audit(
            conn,
            property_id=property_id,
            user=user,
            action="AGENT_UPDATE",
            resource="BookingAgent",
            resource_id=str(agent_id),
            after={**values, "status": status_value},
        )
    return {"id": str(agent_id), "status": status_value}


@router.post("/agents/{agent_id}/interactions", status_code=status.HTTP_201_CREATED)
async def create_agent_interaction(
    agent_id: uuid.UUID,
    payload: AgentInteractionCreate,
    request: Request,
    user: dict[str, Any] = Depends(commercial_access),
):
    interaction_id = uuid.uuid4()
    async with request.app.state.db.acquire() as conn:
        property_id = await _property_id(conn, user["property_code"])
        exists = await conn.fetchval('SELECT 1 FROM booking_agents WHERE id=$1 AND "propertyId"=$2', agent_id, property_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Agent not found")
        await conn.execute(
            '''INSERT INTO booking_agent_interactions (id,"propertyId","agentId",kind,note,"nextContactAt","createdBy","createdAt")
               VALUES ($1,$2,$3,$4,$5,$6,$7,now())''',
            interaction_id,
            property_id,
            agent_id,
            payload.kind,
            payload.note.strip(),
            payload.next_contact_at,
            user["id"],
        )
        await _audit(
            conn,
            property_id=property_id,
            user=user,
            action="AGENT_INTERACTION_CREATE",
            resource="BookingAgentInteraction",
            resource_id=str(interaction_id),
            after=payload.model_dump(mode="json"),
        )
    return {"id": str(interaction_id)}


@router.patch("/agents/{agent_id}/access")
async def patch_agent_access(
    agent_id: uuid.UUID,
    payload: AgentAccessPatch,
    request: Request,
    user: dict[str, Any] = Depends(owner_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            property_id = await _property_id(conn, user["property_code"])
            agent = await conn.fetchrow(
                'SELECT id,name,"contactName",status FROM booking_agents WHERE id=$1 AND "propertyId"=$2 FOR UPDATE',
                agent_id,
                property_id,
            )
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            current = await conn.fetchrow(
                '''SELECT id,username,"displayName","isActive"
                   FROM staff_users
                   WHERE "propertyId"=$1 AND "bookingAgentId"=$2 AND role='AGENT'
                   ORDER BY "createdAt" ASC LIMIT 1 FOR UPDATE''',
                property_id,
                agent_id,
            )
            if current is None:
                if not payload.username or not payload.password:
                    raise HTTPException(status_code=422, detail="username and password are required to create agent access")
                staff_id = uuid.uuid4()
                username = payload.username.strip().lower()
                active = True if payload.active is None else payload.active
                try:
                    row = await conn.fetchrow(
                        '''INSERT INTO staff_users (
                          id,"propertyId",username,"displayName","passwordHash",role,"bookingAgentId","isActive","createdAt","updatedAt"
                        ) VALUES ($1,$2,$3,$4,$5,'AGENT',$6,$7,now(),now())
                        RETURNING id,username,"isActive"''',
                        staff_id,
                        property_id,
                        username,
                        agent["contactName"] or agent["name"],
                        password_hasher.hash(payload.password),
                        agent_id,
                        active,
                    )
                except Exception as exc:
                    if "unique" in str(exc).lower():
                        raise HTTPException(status_code=409, detail="Username already exists") from exc
                    raise
                action = "AGENT_ACCESS_CREATE"
            else:
                staff_id = current["id"]
                username = payload.username.strip().lower() if payload.username is not None else current["username"]
                active = payload.active if payload.active is not None else bool(current["isActive"])
                password_hash = password_hasher.hash(payload.password) if payload.password is not None else None
                try:
                    row = await conn.fetchrow(
                        '''UPDATE staff_users
                           SET username=$2,
                               "passwordHash"=COALESCE($3,"passwordHash"),
                               "isActive"=$4,
                               "updatedAt"=now()
                           WHERE id=$1
                           RETURNING id,username,"isActive"''',
                        staff_id,
                        username,
                        password_hash,
                        active,
                    )
                except Exception as exc:
                    if "unique" in str(exc).lower():
                        raise HTTPException(status_code=409, detail="Username already exists") from exc
                    raise
                if payload.username is not None or payload.password is not None or payload.active is not None:
                    await conn.execute(
                        'UPDATE auth_sessions SET "revokedAt"=now() WHERE "userId"=$1 AND "revokedAt" IS NULL',
                        staff_id,
                    )
                action = "AGENT_ACCESS_UPDATE"
            await _audit(
                conn,
                property_id=property_id,
                user=user,
                action=action,
                resource="StaffUser",
                resource_id=str(staff_id),
                after={
                    "agent_id": str(agent_id),
                    "username": row["username"],
                    "active": bool(row["isActive"]),
                    "password_rotated": payload.password is not None,
                },
            )
    return {
        "agent_id": str(agent_id),
        "username": row["username"],
        "active": bool(row["isActive"]),
        "password_rotated": payload.password is not None,
    }


@router.get("/agents/{agent_id}/report")
async def agent_report(
    agent_id: uuid.UUID,
    request: Request,
    from_date: date | None = None,
    to_date: date | None = None,
    user: dict[str, Any] = Depends(commercial_access),
):
    if from_date and to_date and to_date < from_date:
        raise HTTPException(status_code=422, detail="to_date must be on or after from_date")
    async with request.app.state.db.acquire() as conn:
        property_id = await _property_id(conn, user["property_code"])
        agent = await conn.fetchrow('SELECT * FROM booking_agents WHERE id=$1 AND "propertyId"=$2', agent_id, property_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        reservations = await conn.fetch(
            '''
            SELECT r.id,r."bookingNumber",r.status::text AS status,r."checkIn",r."checkOut",r.adults,r.children,r."totalKgs",
                   r."discountPercent",r."discountReason",r."extraBedCount",r."extraBedUnitKgs",
                   trim(concat_ws(' ',g."firstName",g."lastName")) AS guest_name,g.phone,
                   string_agg(DISTINCT room.code,', ' ORDER BY room.code) AS rooms,
                   coalesce(pay.received_kgs,0)::bigint AS received_kgs
            FROM reservations r
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            LEFT JOIN inventory_blocks ib ON ib."reservationId"=r.id AND ib.active=true AND ib."blockType"='RESERVATION'
            LEFT JOIN rooms room ON room.id=ib."roomId"
            LEFT JOIN LATERAL (
              SELECT coalesce(sum(p."amountKgs") FILTER (WHERE p.status='RECEIVED'),0)::bigint AS received_kgs
              FROM payments p WHERE p."reservationId"=r.id
            ) pay ON true
            WHERE r."propertyId"=$1 AND r."agentId"=$2
              AND ($3::date IS NULL OR r."checkIn">=$3::date)
              AND ($4::date IS NULL OR r."checkIn"<=$4::date)
            GROUP BY r.id,g.id,pay.received_kgs
            ORDER BY r."checkIn" DESC,r."createdAt" DESC
            ''',
            property_id,
            agent_id,
            from_date,
            to_date,
        )
        access = await conn.fetchrow(
            '''SELECT username,"isActive" FROM staff_users
               WHERE "propertyId"=$1 AND "bookingAgentId"=$2 AND role='AGENT'
               ORDER BY "createdAt" ASC LIMIT 1''',
            property_id,
            agent_id,
        )
        interactions = await conn.fetch(
            '''SELECT id,kind,note,"nextContactAt","createdAt" FROM booking_agent_interactions
               WHERE "propertyId"=$1 AND "agentId"=$2 ORDER BY "createdAt" DESC LIMIT 200''',
            property_id,
            agent_id,
        )
        effective = [row for row in reservations if row["status"] not in {"CANCELLED", "NO_SHOW"}]
        booked_kgs = sum(int(row["totalKgs"] or 0) for row in effective)
        received_kgs = sum(int(row["received_kgs"] or 0) for row in reservations)
        nights = sum((row["checkOut"] - row["checkIn"]).days for row in effective)
        return {
            "agent": {
                "id": str(agent["id"]),
                "name": agent["name"],
                "contact_name": agent["contactName"],
                "phone": agent["phone"],
                "whatsapp": agent["whatsapp"],
                "email": agent["email"],
                "notes": agent["notes"],
                "status": agent["status"],
                "access_username": access["username"] if access else None,
                "access_active": bool(access["isActive"]) if access else None,
            },
            "period": {
                "from": from_date.isoformat() if from_date else None,
                "to": to_date.isoformat() if to_date else None,
            },
            "summary": {
                "reservations": len(reservations),
                "effective_reservations": len(effective),
                "booked_kgs": booked_kgs,
                "received_kgs": received_kgs,
                "room_nights": nights,
                "average_booking_kgs": round(booked_kgs / len(effective)) if effective else 0,
                "cancelled_or_no_show": len(reservations) - len(effective),
            },
            "reservations": [
                {
                    "id": str(row["id"]),
                    "booking_number": row["bookingNumber"],
                    "status": row["status"],
                    "check_in": row["checkIn"].isoformat(),
                    "check_out": row["checkOut"].isoformat(),
                    "adults": row["adults"],
                    "children": row["children"],
                    "total_kgs": row["totalKgs"],
                    "received_kgs": int(row["received_kgs"] or 0),
                    "discount_percent": row["discountPercent"],
                    "discount_reason": row["discountReason"],
                    "extra_bed_count": row["extraBedCount"],
                    "extra_bed_unit_kgs": row["extraBedUnitKgs"],
                    "guest_name": row["guest_name"] or None,
                    "guest_phone": row["phone"],
                    "rooms": row["rooms"],
                }
                for row in reservations
            ],
            "interactions": [
                {
                    "id": str(row["id"]),
                    "kind": row["kind"],
                    "note": row["note"],
                    "next_contact_at": row["nextContactAt"].isoformat() if row["nextContactAt"] else None,
                    "created_at": row["createdAt"].isoformat(),
                }
                for row in interactions
            ],
        }


class RoomBlockCreate(BaseModel):
    room_id: uuid.UUID
    block_type: Literal["MAINTENANCE", "MANUAL"]
    start_date: date
    end_date: date
    usage_category: Literal["OWNER", "STAFF", "GUEST_HOLD", "SERVICE", "OTHER"] | None = None
    usage_label: str | None = Field(default=None, max_length=200)
    reason: str = Field(min_length=2, max_length=1000)

    @model_validator(mode="after")
    def validate_period(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        if (self.end_date - self.start_date).days > 370:
            raise ValueError("block cannot exceed 370 days")
        if self.block_type == "MANUAL" and not self.usage_category:
            raise ValueError("usage_category is required for MANUAL block")
        return self


@router.get("/room-blocks/context")
async def room_blocks_context(
    request: Request,
    from_date: date | None = None,
    to_date: date | None = None,
    block_type: Literal["ALL", "MAINTENANCE", "MANUAL"] = "ALL",
    user: dict[str, Any] = Depends(commercial_access),
):
    today = date.today()
    start = from_date or today
    end = to_date or (today + timedelta(days=31))
    if end <= start:
        raise HTTPException(status_code=422, detail="to_date must be after from_date")
    async with request.app.state.db.acquire() as conn:
        property_id = await _property_id(conn, user["property_code"])
        rooms = await conn.fetch(
            '''SELECT room.id,room.code,rt.name AS room_type_name,room."operationalState"::text AS operational_state
               FROM rooms room JOIN room_types rt ON rt.id=room."roomTypeId"
               WHERE room."propertyId"=$1 ORDER BY room.code''',
            property_id,
        )
        blocks = await conn.fetch(
            '''
            SELECT ib.id,ib."roomId",room.code AS room_code,ib."blockType"::text AS block_type,
                   ib."startDate",ib."endDate",ib.reason,ib."usageCategory",ib."usageLabel",ib.active
            FROM inventory_blocks ib JOIN rooms room ON room.id=ib."roomId"
            WHERE room."propertyId"=$1 AND ib.active=true AND ib."blockType" IN ('MAINTENANCE','MANUAL')
              AND ($2='ALL' OR ib."blockType"::text=$2)
              AND daterange(ib."startDate",ib."endDate",'[)') && daterange($3::date,$4::date,'[)')
            ORDER BY ib."startDate",room.code
            ''',
            property_id,
            block_type,
            start,
            end,
        )
        return {
            "from_date": start,
            "to_date": end,
            "rooms": [
                {
                    "id": str(row["id"]),
                    "code": row["code"],
                    "room_type_name": row["room_type_name"],
                    "operational_state": row["operational_state"],
                }
                for row in rooms
            ],
            "blocks": [
                {
                    "id": str(row["id"]),
                    "room_id": str(row["roomId"]),
                    "room_code": row["room_code"],
                    "block_type": row["block_type"],
                    "start_date": row["startDate"].isoformat(),
                    "end_date": row["endDate"].isoformat(),
                    "reason": row["reason"],
                    "usage_category": row["usageCategory"],
                    "usage_label": row["usageLabel"],
                }
                for row in blocks
            ],
        }


@router.post("/room-blocks", status_code=status.HTTP_201_CREATED)
async def create_room_block(
    payload: RoomBlockCreate,
    request: Request,
    user: dict[str, Any] = Depends(commercial_access),
):
    block_id = uuid.uuid4()
    async with request.app.state.db.acquire() as conn:
        try:
            async with conn.transaction():
                property_id = await _property_id(conn, user["property_code"])
                room = await conn.fetchrow(
                    'SELECT id,code FROM rooms WHERE id=$1 AND "propertyId"=$2 FOR UPDATE',
                    payload.room_id,
                    property_id,
                )
                if not room:
                    raise HTTPException(status_code=404, detail="Room not found")
                conflicts = await conn.fetch(
                    '''SELECT ib.id,ib."blockType"::text AS block_type,ib."startDate",ib."endDate",ib.reason,r."bookingNumber"
                       FROM inventory_blocks ib LEFT JOIN reservations r ON r.id=ib."reservationId"
                       WHERE ib."roomId"=$1 AND ib.active=true
                         AND daterange(ib."startDate",ib."endDate",'[)') && daterange($2::date,$3::date,'[)')''',
                    payload.room_id,
                    payload.start_date,
                    payload.end_date,
                )
                if conflicts:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "ROOM_BLOCK_CONFLICT",
                            "room_code": room["code"],
                            "conflicts": [
                                {
                                    "id": str(row["id"]),
                                    "block_type": row["block_type"],
                                    "start": row["startDate"].isoformat(),
                                    "end": row["endDate"].isoformat(),
                                    "reason": row["reason"],
                                    "booking_number": row["bookingNumber"],
                                }
                                for row in conflicts
                            ],
                        },
                    )
                await conn.execute(
                    '''INSERT INTO inventory_blocks (id,"roomId","blockType","startDate","endDate",active,reason,"usageCategory","usageLabel","createdAt","updatedAt")
                       VALUES ($1,$2,$3::"InventoryBlockType",$4,$5,true,$6,$7,$8,now(),now())''',
                    block_id,
                    payload.room_id,
                    payload.block_type,
                    payload.start_date,
                    payload.end_date,
                    payload.reason.strip(),
                    payload.usage_category,
                    payload.usage_label,
                )
                await _audit(
                    conn,
                    property_id=property_id,
                    user=user,
                    action="ROOM_PERIOD_BLOCK_CREATE",
                    resource="InventoryBlock",
                    resource_id=str(block_id),
                    after={**payload.model_dump(mode="json"), "room_code": room["code"]},
                )
        except ExclusionViolationError as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "ROOM_BLOCK_CONFLICT_RACE", "message": "Room availability changed before commit."},
            ) from exc
    return {"id": str(block_id), "room_code": room["code"], "status": "ACTIVE"}


@router.delete("/room-blocks/{block_id}")
async def deactivate_room_block(
    block_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(commercial_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            property_id = await _property_id(conn, user["property_code"])
            row = await conn.fetchrow(
                '''SELECT ib.id,ib."blockType"::text AS block_type,room.code FROM inventory_blocks ib
                   JOIN rooms room ON room.id=ib."roomId"
                   WHERE ib.id=$1 AND room."propertyId"=$2 AND ib.active=true AND ib."blockType" IN ('MAINTENANCE','MANUAL') FOR UPDATE''',
                block_id,
                property_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Active room block not found")
            await conn.execute('UPDATE inventory_blocks SET active=false,"updatedAt"=now() WHERE id=$1', block_id)
            await _audit(
                conn,
                property_id=property_id,
                user=user,
                action="ROOM_PERIOD_BLOCK_DEACTIVATE",
                resource="InventoryBlock",
                resource_id=str(block_id),
                after={"room_code": row["code"], "block_type": row["block_type"], "active": False},
            )
    return {"id": str(block_id), "status": "INACTIVE"}


@router.get("/guest-status")
async def guest_status(phone: str, request: Request, user: dict[str, Any] = Depends(commercial_access)):
    normalized = "".join(ch for ch in phone if ch.isdigit())
    if len(normalized) < 5:
        return {"returning_guest": False, "discount_percent": 0, "previous_stays": 0}
    async with request.app.state.db.acquire() as conn:
        property_id = await _property_id(conn, user["property_code"])
        rows = await conn.fetch(
            '''SELECT g.id FROM guests g WHERE g."propertyId"=$1 AND regexp_replace(coalesce(g.phone,''),'\\D','','g')=$2''',
            property_id,
            normalized,
        )
        if not rows:
            return {"returning_guest": False, "discount_percent": 0, "previous_stays": 0}
        guest_ids = [row["id"] for row in rows]
        previous = await conn.fetchval(
            '''SELECT count(*)::int FROM reservations r WHERE r."propertyId"=$1 AND r."primaryGuestId"=ANY($2::uuid[]) AND r.status='CHECKED_OUT' ''',
            property_id,
            guest_ids,
        ) or 0
        return {
            "returning_guest": previous > 0,
            "discount_percent": 10 if previous > 0 else 0,
            "previous_stays": previous,
        }
