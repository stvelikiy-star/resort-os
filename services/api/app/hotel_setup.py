import json
import os
import uuid
from datetime import date
from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/hotel-setup", tags=["hotel-setup"])
manager_access = require_roles("OWNER", "MANAGER")
module_read_access = require_roles("OWNER", "MANAGER", "RECEPTION", "MAID", "TECHNICIAN")
RATE_PLAN_CODE = os.environ.get("RATE_PLAN_CODE", "MARINA_DIRECT")
DEMO_LAYOUT_ENABLED = os.environ.get("MARINA_ALLOW_DEMO_RESET", "false").strip().lower() in {"1", "true", "yes", "on"}
OPTIONAL_MODULES = {
    "GROUPS", "AGENTS", "MARKETING", "DINING", "OFFERS",
    "GROWTH", "CONTENT", "ROOM_QR", "POINT_QR", "INBOX",
}
DEFAULT_MODULES = ["AGENTS", "DINING", "ROOM_QR"]

RoomState = Literal["UNKNOWN", "CLEAN", "DIRTY", "IN_INSPECTION", "TECH_BLOCK"]


class PropertyPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    timezone: str | None = Field(default=None, min_length=2, max_length=80)
    currency: str | None = Field(default=None, pattern=r"^[A-Za-z]{3}$")
    check_in_time: str | None = Field(default=None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    check_out_time: str | None = Field(default=None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    hotel_logo_url: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one property field is required")
        return self


class RoomTypeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=160)
    capacity_adults: int = Field(ge=1, le=20)
    capacity_children: int | None = Field(default=0, ge=0, le=20)
    area_label: str | None = Field(default=None, max_length=80)


class RoomTypePatch(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=60, pattern=r"^[A-Za-z0-9_-]+$")
    name: str | None = Field(default=None, min_length=2, max_length=160)
    capacity_adults: int | None = Field(default=None, ge=1, le=20)
    capacity_children: int | None = Field(default=None, ge=0, le=20)
    area_label: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def validate_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one room type field is required")
        return self


class RoomCreate(BaseModel):
    room_type_id: uuid.UUID
    code: str = Field(min_length=1, max_length=60)
    name: str | None = Field(default=None, max_length=160)
    building_or_zone: str | None = Field(default=None, max_length=120)
    floor_label: str | None = Field(default=None, max_length=80)
    bed_configuration: str | None = Field(default=None, max_length=180)
    area_label: str | None = Field(default=None, max_length=80)
    operational_state: RoomState = "CLEAN"
    notes: str | None = Field(default=None, max_length=2000)


class RoomPatch(BaseModel):
    room_type_id: uuid.UUID | None = None
    code: str | None = Field(default=None, min_length=1, max_length=60)
    name: str | None = Field(default=None, max_length=160)
    building_or_zone: str | None = Field(default=None, max_length=120)
    floor_label: str | None = Field(default=None, max_length=80)
    bed_configuration: str | None = Field(default=None, max_length=180)
    area_label: str | None = Field(default=None, max_length=80)
    operational_state: RoomState | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one room field is required")
        return self


class BulkRoomsCreate(BaseModel):
    room_type_id: uuid.UUID
    start_number: int = Field(ge=1, le=99999)
    end_number: int = Field(ge=1, le=99999)
    pad_width: int = Field(default=3, ge=1, le=6)
    prefix: str = Field(default="", max_length=12, pattern=r"^[A-Za-z0-9_-]*$")
    building_or_zone: str | None = Field(default=None, max_length=120)
    floor_label: str | None = Field(default=None, max_length=80)
    bed_configuration: str | None = Field(default=None, max_length=180)
    area_label: str | None = Field(default=None, max_length=80)
    operational_state: RoomState = "CLEAN"

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_number < self.start_number:
            raise ValueError("end_number must be >= start_number")
        if self.end_number - self.start_number + 1 > 200:
            raise ValueError("A single bulk operation is limited to 200 rooms")
        return self


class DemoLayoutRequest(BaseModel):
    confirmation: Literal["CREATE_COMPACT_DEMO"]


class ModulesPatch(BaseModel):
    enabled_modules: list[str]

    @model_validator(mode="after")
    def validate_modules(self):
        normalized = []
        for value in self.enabled_modules:
            module = value.strip().upper()
            if module not in OPTIONAL_MODULES:
                raise ValueError(f"Unknown module: {module}")
            if module not in normalized:
                normalized.append(module)
        self.enabled_modules = normalized
        return self


async def _ensure_product_settings(conn, property_id: uuid.UUID):
    await conn.execute(
        '''INSERT INTO property_product_settings (
             id,"propertyId","checkInTime","checkOutTime","enabledModules","createdAt","updatedAt"
           ) VALUES ($1,$2,TIME '14:00',TIME '12:00',$3::jsonb,now(),now())
           ON CONFLICT ("propertyId") DO NOTHING''',
        uuid.uuid4(), property_id, json.dumps(DEFAULT_MODULES),
    )
    row = await conn.fetchrow(
        '''SELECT id,
                  to_char("checkInTime",'HH24:MI') AS check_in_time,
                  to_char("checkOutTime",'HH24:MI') AS check_out_time,
                  "enabledModules","hotelLogoUrl"
           FROM property_product_settings WHERE "propertyId"=$1''',
        property_id,
    )
    modules_raw = row["enabledModules"]
    modules = json.loads(modules_raw) if isinstance(modules_raw, str) else list(modules_raw or [])
    modules = [str(value) for value in modules if str(value) in OPTIONAL_MODULES]
    return {
        "id": row["id"],
        "check_in_time": row["check_in_time"],
        "check_out_time": row["check_out_time"],
        "enabled_modules": modules,
        "hotel_logo_url": row["hotelLogoUrl"],
    }


async def _property(conn, property_code: str):
    row = await conn.fetchrow(
        'SELECT id,code,name,timezone,currency,"updatedAt" FROM properties WHERE code=$1',
        property_code,
    )
    if not row:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return row


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _room_type_payload(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "code": row["code"],
        "name": row["name"],
        "capacity_adults": int(row["capacityAdults"]),
        "capacity_children": row["capacityChildren"],
        "area_label": row["areaLabel"],
        "room_count": int(row.get("room_count", 0)),
        "rate_count": int(row.get("rate_count", 0)),
    }


def _room_payload(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "room_type_id": str(row["roomTypeId"]),
        "room_type_code": row["room_type_code"],
        "room_type_name": row["room_type_name"],
        "code": row["code"],
        "name": row["name"],
        "building_or_zone": row["buildingOrZone"],
        "floor_label": row["floorLabel"],
        "bed_configuration": row["bedConfiguration"],
        "area_label": row["areaLabel"],
        "operational_state": row["operational_state"],
        "notes": row["notes"],
        "updated_at": row["updatedAt"],
    }


async def _audit(conn, *, property_id: uuid.UUID, user: dict[str, Any], action: str, resource: str,
                 resource_id: str, before: dict[str, Any] | None, after: dict[str, Any] | None):
    await conn.execute(
        '''
        INSERT INTO audit_logs (
          id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,
          "beforeJson","afterJson","createdAt"
        ) VALUES ($1,$2,'STAFF',$3,$4,$5,$6,'HOTEL_SETUP','SUCCESS',$7::jsonb,$8::jsonb,now())
        ''',
        uuid.uuid4(), property_id, user["id"], action, resource, resource_id,
        json.dumps(before, ensure_ascii=False, default=str) if before is not None else None,
        json.dumps(after, ensure_ascii=False, default=str) if after is not None else None,
    )


async def _room_type(conn, property_id: uuid.UUID, room_type_id: uuid.UUID, *, lock: bool = False):
    suffix = " FOR UPDATE" if lock else ""
    row = await conn.fetchrow(
        f'''SELECT id,code,name,"capacityAdults","capacityChildren","areaLabel"
            FROM room_types WHERE id=$1 AND "propertyId"=$2{suffix}''',
        room_type_id, property_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Room type not found")
    return row


async def _room(conn, property_id: uuid.UUID, room_id: uuid.UUID, *, lock: bool = False):
    suffix = " FOR UPDATE OF r" if lock else ""
    row = await conn.fetchrow(
        f'''
        SELECT r.id,r."roomTypeId",r.code,r.name,r."buildingOrZone",r."floorLabel",
               r."bedConfiguration",r."areaLabel",r."operationalState"::text AS operational_state,
               r.notes,r."updatedAt",rt.code AS room_type_code,rt.name AS room_type_name
        FROM rooms r JOIN room_types rt ON rt.id=r."roomTypeId"
        WHERE r.id=$1 AND r."propertyId"=$2{suffix}
        ''',
        room_id, property_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Room not found")
    return row


async def _ensure_unique_room_type(conn, property_id, code: str, name: str, exclude_id=None):
    found = await conn.fetchrow(
        '''SELECT id,code,name FROM room_types
           WHERE "propertyId"=$1 AND (lower(code)=lower($2) OR lower(name)=lower($3))
             AND ($4::uuid IS NULL OR id<>$4)
           LIMIT 1''',
        property_id, code, name, exclude_id,
    )
    if found:
        raise HTTPException(status_code=409, detail="Room type code or name already exists")


async def _ensure_unique_room_code(conn, property_id, code: str, exclude_id=None):
    found = await conn.fetchval(
        '''SELECT id FROM rooms WHERE "propertyId"=$1 AND lower(code)=lower($2)
           AND ($3::uuid IS NULL OR id<>$3) LIMIT 1''',
        property_id, code, exclude_id,
    )
    if found:
        raise HTTPException(status_code=409, detail="Room code already exists")


@router.get("")
async def overview(request: Request, user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn, user["property_code"])
        room_types = await conn.fetch(
            '''
            SELECT rt.id,rt.code,rt.name,rt."capacityAdults",rt."capacityChildren",rt."areaLabel",
                   count(DISTINCT r.id)::int AS room_count,
                   count(DISTINCT rp.id)::int AS rate_count
            FROM room_types rt
            LEFT JOIN rooms r ON r."roomTypeId"=rt.id
            LEFT JOIN rate_periods rp ON rp."roomTypeId"=rt.id
            WHERE rt."propertyId"=$1
            GROUP BY rt.id
            ORDER BY rt.name
            ''',
            prop["id"],
        )
        rooms = await conn.fetch(
            '''
            SELECT r.id,r."roomTypeId",r.code,r.name,r."buildingOrZone",r."floorLabel",
                   r."bedConfiguration",r."areaLabel",r."operationalState"::text AS operational_state,
                   r.notes,r."updatedAt",rt.code AS room_type_code,rt.name AS room_type_name
            FROM rooms r JOIN room_types rt ON rt.id=r."roomTypeId"
            WHERE r."propertyId"=$1
            ORDER BY COALESCE(r."buildingOrZone",''),COALESCE(r."floorLabel",''),r.code
            ''',
            prop["id"],
        )
        product_settings = await _ensure_product_settings(conn, prop["id"])
        readiness = await conn.fetchrow(
            '''SELECT
                 (SELECT count(*)::int FROM rate_periods rp
                    JOIN rate_plans plan ON plan.id=rp."ratePlanId"
                    WHERE plan."propertyId"=$1) AS rate_periods,
                 (SELECT count(*)::int FROM staff_users su
                    WHERE su."propertyId"=$1 AND su."isActive"=true) AS active_staff''',
            prop["id"],
        )
    room_count = len(rooms)
    room_type_count = len(room_types)
    setup_steps = {
        "property": bool(prop["name"] and prop["timezone"] and prop["currency"]),
        "room_types": room_type_count > 0,
        "rooms": room_count > 0,
        "rates": int(readiness["rate_periods"] or 0) > 0,
        "staff": int(readiness["active_staff"] or 0) > 0,
    }
    return {
        "property": {
            "id": str(prop["id"]), "code": prop["code"], "name": prop["name"],
            "timezone": prop["timezone"], "currency": prop["currency"], "updated_at": prop["updatedAt"],
        },
        "product_settings": {
            "check_in_time": product_settings["check_in_time"],
            "check_out_time": product_settings["check_out_time"],
            "enabled_modules": product_settings["enabled_modules"],
            "available_modules": sorted(OPTIONAL_MODULES),
            "hotel_logo_url": product_settings["hotel_logo_url"],
        },
        "summary": {
            "room_types": room_type_count,
            "rooms": room_count,
            "ready": sum(1 for row in rooms if row["operational_state"] == "CLEAN"),
            "blocked": sum(1 for row in rooms if row["operational_state"] == "TECH_BLOCK"),
        },
        "onboarding": {
            "ready": all(setup_steps.values()),
            "completed": sum(1 for value in setup_steps.values() if value),
            "total": len(setup_steps),
            "steps": setup_steps,
            "rate_periods": int(readiness["rate_periods"] or 0),
            "active_staff": int(readiness["active_staff"] or 0),
        },
        "room_types": [_room_type_payload(row) for row in room_types],
        "rooms": [_room_payload(row) for row in rooms],
        "rules": {
            "delete_room_only_without_history": True,
            "delete_room_type_only_when_unused": True,
            "tech_block_means_temporarily_not_sellable": True,
            "bulk_create_limit": 200,
            "demo_layout_enabled": DEMO_LAYOUT_ENABLED,
        },
    }


@router.patch("/property")
async def patch_property(payload: PropertyPatch, request: Request, user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            product = await _ensure_product_settings(conn, prop["id"])
            before = {"name": prop["name"], "timezone": prop["timezone"], "currency": prop["currency"], "hotel_logo_url": product["hotel_logo_url"]}
            supplied = payload.model_fields_set
            name = payload.name.strip() if "name" in supplied and payload.name is not None else prop["name"]
            timezone = payload.timezone.strip() if "timezone" in supplied and payload.timezone is not None else prop["timezone"]
            currency = payload.currency.upper() if "currency" in supplied and payload.currency is not None else prop["currency"]
            if "timezone" in supplied:
                timezone_exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_timezone_names WHERE name=$1)", timezone)
                if not timezone_exists:
                    raise HTTPException(status_code=422, detail="Unknown timezone")
            check_in_time = payload.check_in_time if "check_in_time" in supplied and payload.check_in_time is not None else product["check_in_time"]
            check_out_time = payload.check_out_time if "check_out_time" in supplied and payload.check_out_time is not None else product["check_out_time"]
            if check_in_time == check_out_time:
                raise HTTPException(status_code=422, detail="Check-in and check-out time must differ")
            row = await conn.fetchrow(
                '''UPDATE properties SET name=$2,timezone=$3,currency=$4,"updatedAt"=now()
                   WHERE id=$1 RETURNING id,code,name,timezone,currency,"updatedAt"''',
                prop["id"], name, timezone, currency,
            )
            hotel_logo_url = _clean(payload.hotel_logo_url) if "hotel_logo_url" in supplied else product["hotel_logo_url"]
            await conn.execute(
                '''UPDATE property_product_settings
                   SET "checkInTime"=$2::text::time,"checkOutTime"=$3::text::time,"hotelLogoUrl"=$4,"updatedAt"=now()
                   WHERE "propertyId"=$1''',
                prop["id"], check_in_time, check_out_time, hotel_logo_url,
            )
            after = {
                "name": row["name"], "timezone": row["timezone"], "currency": row["currency"],
                "check_in_time": check_in_time, "check_out_time": check_out_time,
                "hotel_logo_url": hotel_logo_url,
            }
            await _audit(conn, property_id=prop["id"], user=user, action="UPDATE_PROPERTY",
                         resource="Property", resource_id=str(prop["id"]), before=before, after=after)
    return {**after, "id": str(row["id"]), "code": row["code"], "updated_at": row["updatedAt"]}


@router.get("/modules")
async def get_modules(request: Request, user: dict[str, Any] = Depends(module_read_access)):
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn, user["property_code"])
        settings = await _ensure_product_settings(conn, prop["id"])
    return {
        "enabled_modules": settings["enabled_modules"],
        "available_modules": sorted(OPTIONAL_MODULES),
        "hotel_logo_url": settings["hotel_logo_url"],
        "property_name": prop["name"],
    }


@router.patch("/modules")
async def patch_modules(payload: ModulesPatch, request: Request, user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            settings = await _ensure_product_settings(conn, prop["id"])
            before = {"enabled_modules": settings["enabled_modules"]}
            await conn.execute(
                '''UPDATE property_product_settings SET "enabledModules"=$2::jsonb,"updatedAt"=now()
                   WHERE "propertyId"=$1''',
                prop["id"], json.dumps(payload.enabled_modules),
            )
            after = {"enabled_modules": payload.enabled_modules}
            await _audit(conn, property_id=prop["id"], user=user, action="UPDATE_ENABLED_MODULES",
                         resource="PropertyProductSettings", resource_id=str(settings["id"]),
                         before=before, after=after)
    return {
        "enabled_modules": payload.enabled_modules,
        "available_modules": sorted(OPTIONAL_MODULES),
    }


@router.post("/room-types", status_code=status.HTTP_201_CREATED)
async def create_room_type(payload: RoomTypeCreate, request: Request, user: dict[str, Any] = Depends(manager_access)):
    code = payload.code.strip().upper()
    name = payload.name.strip()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            await _ensure_unique_room_type(conn, prop["id"], code, name)
            room_type_id = uuid.uuid4()
            row = await conn.fetchrow(
                '''INSERT INTO room_types (
                     id,"propertyId",code,name,"capacityAdults","capacityChildren","areaLabel","createdAt","updatedAt"
                   ) VALUES ($1,$2,$3,$4,$5,$6,$7,now(),now())
                   RETURNING id,code,name,"capacityAdults","capacityChildren","areaLabel"''',
                room_type_id, prop["id"], code, name, payload.capacity_adults,
                payload.capacity_children, _clean(payload.area_label),
            )
            after = _room_type_payload(row)
            await _audit(conn, property_id=prop["id"], user=user, action="CREATE_ROOM_TYPE",
                         resource="RoomType", resource_id=str(room_type_id), before=None, after=after)
    return after


@router.patch("/room-types/{room_type_id}")
async def patch_room_type(room_type_id: uuid.UUID, payload: RoomTypePatch, request: Request,
                          user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            current = await _room_type(conn, prop["id"], room_type_id, lock=True)
            before = _room_type_payload(current)
            supplied = payload.model_fields_set
            code = payload.code.strip().upper() if "code" in supplied and payload.code is not None else current["code"]
            name = payload.name.strip() if "name" in supplied and payload.name is not None else current["name"]
            capacity_adults = payload.capacity_adults if "capacity_adults" in supplied else current["capacityAdults"]
            capacity_children = payload.capacity_children if "capacity_children" in supplied else current["capacityChildren"]
            area_label = _clean(payload.area_label) if "area_label" in supplied else current["areaLabel"]
            await _ensure_unique_room_type(conn, prop["id"], code, name, room_type_id)
            row = await conn.fetchrow(
                '''UPDATE room_types SET code=$2,name=$3,"capacityAdults"=$4,"capacityChildren"=$5,
                     "areaLabel"=$6,"updatedAt"=now() WHERE id=$1
                   RETURNING id,code,name,"capacityAdults","capacityChildren","areaLabel"''',
                room_type_id, code, name, capacity_adults, capacity_children, area_label,
            )
            after = _room_type_payload(row)
            await _audit(conn, property_id=prop["id"], user=user, action="UPDATE_ROOM_TYPE",
                         resource="RoomType", resource_id=str(room_type_id), before=before, after=after)
    return after


@router.delete("/room-types/{room_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room_type(room_type_id: uuid.UUID, request: Request, user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            current = await _room_type(conn, prop["id"], room_type_id, lock=True)
            usage = await conn.fetchrow(
                '''SELECT
                     (SELECT count(*) FROM rooms WHERE "roomTypeId"=$1)::int AS rooms,
                     (SELECT count(*) FROM rate_periods WHERE "roomTypeId"=$1)::int AS rates,
                     (SELECT count(*) FROM reservation_requests WHERE "desiredRoomTypeId"=$1)::int AS requests''',
                room_type_id,
            )
            if usage["rooms"] or usage["rates"] or usage["requests"]:
                raise HTTPException(status_code=409, detail={
                    "code": "ROOM_TYPE_IN_USE", "rooms": usage["rooms"],
                    "rates": usage["rates"], "requests": usage["requests"],
                })
            before = _room_type_payload(current)
            await conn.execute('DELETE FROM room_types WHERE id=$1', room_type_id)
            await _audit(conn, property_id=prop["id"], user=user, action="DELETE_ROOM_TYPE",
                         resource="RoomType", resource_id=str(room_type_id), before=before, after=None)


@router.post("/rooms", status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreate, request: Request, user: dict[str, Any] = Depends(manager_access)):
    code = payload.code.strip()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            rt = await _room_type(conn, prop["id"], payload.room_type_id)
            await _ensure_unique_room_code(conn, prop["id"], code)
            room_id = uuid.uuid4()
            await conn.execute(
                '''INSERT INTO rooms (
                     id,"propertyId","roomTypeId",code,name,"buildingOrZone","floorLabel",
                     "bedConfiguration","areaLabel","operationalState",notes,"createdAt","updatedAt"
                   ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::"RoomOperationalState",$11,now(),now())''',
                room_id, prop["id"], payload.room_type_id, code, _clean(payload.name) or f"Номер {code}",
                _clean(payload.building_or_zone), _clean(payload.floor_label),
                _clean(payload.bed_configuration), _clean(payload.area_label),
                payload.operational_state, _clean(payload.notes),
            )
            row = await _room(conn, prop["id"], room_id)
            after = _room_payload(row)
            await _audit(conn, property_id=prop["id"], user=user, action="CREATE_ROOM",
                         resource="Room", resource_id=str(room_id), before=None, after=after)
    return after


@router.patch("/rooms/{room_id}")
async def patch_room(room_id: uuid.UUID, payload: RoomPatch, request: Request,
                     user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            current = await _room(conn, prop["id"], room_id, lock=True)
            before = _room_payload(current)
            supplied = payload.model_fields_set
            room_type_id = payload.room_type_id if "room_type_id" in supplied and payload.room_type_id is not None else current["roomTypeId"]
            await _room_type(conn, prop["id"], room_type_id)
            code = payload.code.strip() if "code" in supplied and payload.code is not None else current["code"]
            await _ensure_unique_room_code(conn, prop["id"], code, room_id)

            def chosen(field: str, db_key: str):
                if field not in supplied:
                    return current[db_key]
                return _clean(getattr(payload, field))

            state_value = payload.operational_state if "operational_state" in supplied else current["operational_state"]
            name_value = chosen("name", "name") or f"Номер {code}"
            await conn.execute(
                '''UPDATE rooms SET "roomTypeId"=$2,code=$3,name=$4,"buildingOrZone"=$5,"floorLabel"=$6,
                     "bedConfiguration"=$7,"areaLabel"=$8,"operationalState"=$9::"RoomOperationalState",
                     notes=$10,"updatedAt"=now() WHERE id=$1''',
                room_id, room_type_id, code, name_value,
                chosen("building_or_zone", "buildingOrZone"), chosen("floor_label", "floorLabel"),
                chosen("bed_configuration", "bedConfiguration"), chosen("area_label", "areaLabel"),
                state_value, chosen("notes", "notes"),
            )
            row = await _room(conn, prop["id"], room_id)
            after = _room_payload(row)
            await _audit(conn, property_id=prop["id"], user=user, action="UPDATE_ROOM",
                         resource="Room", resource_id=str(room_id), before=before, after=after)
    return after


@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(room_id: uuid.UUID, request: Request, user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            current = await _room(conn, prop["id"], room_id, lock=True)
            usage = await conn.fetchrow(
                '''SELECT
                   (SELECT count(*) FROM inventory_blocks WHERE "roomId"=$1)::int AS inventory_blocks,
                   (SELECT count(*) FROM room_assignments WHERE "roomId"=$1)::int AS assignments,
                   (SELECT count(*) FROM room_qrs WHERE "roomId"=$1)::int AS room_qrs,
                   (SELECT count(*) FROM operational_tasks WHERE "roomId"=$1)::int AS tasks,
                   (SELECT count(*) FROM kitchen_orders WHERE "roomId"=$1)::int AS kitchen_orders,
                   (SELECT count(*) FROM booking_group_members WHERE "roomId"=$1)::int AS group_members''',
                room_id,
            )
            total = sum(int(value or 0) for value in usage.values())
            if total:
                raise HTTPException(status_code=409, detail={"code": "ROOM_HAS_HISTORY", **dict(usage)})
            before = _room_payload(current)
            await conn.execute('DELETE FROM rooms WHERE id=$1', room_id)
            await _audit(conn, property_id=prop["id"], user=user, action="DELETE_ROOM",
                         resource="Room", resource_id=str(room_id), before=before, after=None)


@router.post("/rooms/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_create_rooms(payload: BulkRoomsCreate, request: Request,
                            user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            await _room_type(conn, prop["id"], payload.room_type_id)
            codes = [f"{payload.prefix}{number:0{payload.pad_width}d}" for number in range(payload.start_number, payload.end_number + 1)]
            existing = await conn.fetch(
                'SELECT code FROM rooms WHERE "propertyId"=$1 AND code=ANY($2::text[])',
                prop["id"], codes,
            )
            if existing:
                raise HTTPException(status_code=409, detail={
                    "code": "ROOM_CODES_ALREADY_EXIST", "rooms": [row["code"] for row in existing],
                })
            created = []
            for code in codes:
                room_id = uuid.uuid4()
                await conn.execute(
                    '''INSERT INTO rooms (
                       id,"propertyId","roomTypeId",code,name,"buildingOrZone","floorLabel",
                       "bedConfiguration","areaLabel","operationalState","createdAt","updatedAt"
                     ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::"RoomOperationalState",now(),now())''',
                    room_id, prop["id"], payload.room_type_id, code, f"Номер {code}",
                    _clean(payload.building_or_zone), _clean(payload.floor_label),
                    _clean(payload.bed_configuration), _clean(payload.area_label), payload.operational_state,
                )
                created.append(code)
            await _audit(conn, property_id=prop["id"], user=user, action="BULK_CREATE_ROOMS",
                         resource="Room", resource_id=str(prop["id"]), before=None,
                         after={"count": len(created), "codes": created})
    return {"created": len(created), "codes": created}


@router.post("/compact-demo")
async def compact_demo_layout(payload: DemoLayoutRequest, request: Request,
                              user: dict[str, Any] = Depends(manager_access)):
    if not DEMO_LAYOUT_ENABLED:
        raise HTTPException(status_code=403, detail={"code": "DEMO_LAYOUT_DISABLED"})
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            activity = await conn.fetchrow(
                '''SELECT
                  (SELECT count(*) FROM reservations WHERE "propertyId"=$1)::int AS reservations,
                  (SELECT count(*) FROM stays WHERE "propertyId"=$1)::int AS stays,
                  (SELECT count(*) FROM reservation_requests WHERE "propertyId"=$1)::int AS requests,
                  (SELECT count(*) FROM payments p
                     LEFT JOIN reservation_requests rr ON rr.id=p."requestId"
                     LEFT JOIN reservations r ON r.id=p."reservationId"
                     WHERE rr."propertyId"=$1 OR r."propertyId"=$1)::int AS payments,
                  (SELECT count(*) FROM kitchen_orders WHERE "propertyId"=$1)::int AS kitchen_orders''',
                prop["id"],
            )
            if any(int(value or 0) for value in activity.values()):
                raise HTTPException(status_code=409, detail={
                    "code": "DEMO_RESET_BLOCKED_BY_ACTIVITY", **dict(activity),
                })

            before_counts = await conn.fetchrow(
                '''SELECT
                  (SELECT count(*) FROM rooms WHERE "propertyId"=$1)::int AS rooms,
                  (SELECT count(*) FROM room_types WHERE "propertyId"=$1)::int AS room_types''',
                prop["id"],
            )

            await conn.execute('DELETE FROM operational_tasks WHERE "propertyId"=$1', prop["id"])
            await conn.execute('DELETE FROM room_qrs WHERE "propertyId"=$1', prop["id"])
            await conn.execute('DELETE FROM rooms WHERE "propertyId"=$1', prop["id"])

            # Rate periods reference room types. Remove only this property's rate
            # periods before replacing the catalogue; keep the rate plan itself so
            # its identity remains stable for the rest of the system.
            await conn.execute(
                '''DELETE FROM rate_periods rp
                   USING rate_plans plan
                   WHERE rp."ratePlanId"=plan.id AND plan."propertyId"=$1''',
                prop["id"],
            )
            await conn.execute('DELETE FROM room_types WHERE "propertyId"=$1', prop["id"])

            plan = await conn.fetchrow(
                'SELECT id FROM rate_plans WHERE "propertyId"=$1 AND code=$2',
                prop["id"], RATE_PLAN_CODE,
            )
            if not plan:
                plan_id = uuid.uuid4()
                await conn.execute(
                    '''INSERT INTO rate_plans (id,"propertyId",code,name,currency,"createdAt","updatedAt")
                       VALUES ($1,$2,$3,'MARINA SMART Demo Rate','KGS',now(),now())''',
                    plan_id, prop["id"], RATE_PLAN_CODE,
                )
            else:
                plan_id = plan["id"]

            today = date.today()
            valid_from = date(today.year, 1, 1)
            valid_to = date(today.year + 1, 12, 31)
            categories = [
                ("STANDARD", "Стандарт", 2, 1, "18–24 м²", 3000, 100),
                ("COMFORT", "Комфорт", 2, 2, "24–32 м²", 4500, 200),
                ("SUITE", "Люкс", 4, 2, "35–50 м²", 7000, 300),
            ]
            room_codes = []
            for type_code, type_name, adults, children, area, price, base in categories:
                rt_id = uuid.uuid4()
                await conn.execute(
                    '''INSERT INTO room_types (
                       id,"propertyId",code,name,"capacityAdults","capacityChildren","areaLabel","createdAt","updatedAt"
                     ) VALUES ($1,$2,$3,$4,$5,$6,$7,now(),now())''',
                    rt_id, prop["id"], type_code, type_name, adults, children, area,
                )
                await conn.execute(
                    '''INSERT INTO rate_periods (
                       id,"ratePlanId","roomTypeId",label,"validFrom","validTo","priceKgs",
                       "mealIncluded","saleStatus","createdAt","updatedAt"
                     ) VALUES ($1,$2,$3,'Базовый тестовый тариф',$4,$5,$6,'NONE','OPEN',now(),now())''',
                    uuid.uuid4(), plan_id, rt_id, valid_from, valid_to, price,
                )
                for offset in range(1, 5):
                    code = str(base + offset)
                    room_codes.append(code)
                    await conn.execute(
                        '''INSERT INTO rooms (
                           id,"propertyId","roomTypeId",code,name,"floorLabel","bedConfiguration",
                           "areaLabel","operationalState","createdAt","updatedAt"
                         ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'CLEAN',now(),now())''',
                        uuid.uuid4(), prop["id"], rt_id, code, f"Номер {code}",
                        str(base // 100), "1 двуспальная / трансформируемая", area,
                    )
            await conn.execute(
                'UPDATE properties SET name=$2,"updatedAt"=now() WHERE id=$1',
                prop["id"], "MARINA SMART TEST HOTEL",
            )
            await _audit(conn, property_id=prop["id"], user=user, action="CREATE_COMPACT_DEMO_LAYOUT",
                         resource="Property", resource_id=str(prop["id"]),
                         before=dict(before_counts), after={"rooms": 12, "room_types": 3, "codes": room_codes})
    return {"ok": True, "rooms": 12, "room_types": 3, "codes": room_codes}
