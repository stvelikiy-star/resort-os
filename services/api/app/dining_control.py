import json
import uuid
from datetime import date, datetime, time, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, model_validator

from .auth import require_roles
from .dining_coordination import (
    active_session_for_table,
    live_table_status,
    lock_dining_tables,
    reservation_matches_session,
    reservation_window_contains_now,
)

router = APIRouter(prefix="/api/v1/dining", tags=["dining-control"])
dining_access = require_roles("OWNER", "MANAGER", "DINING_STAFF")

MEAL_TYPES = {"BREAKFAST", "LUNCH", "DINNER", "OTHER"}
ACTIVE_ORDER_STATUSES = ("NEW", "ACCEPTED", "COOKING", "READY")
TABLE_RESERVATION_TRANSITIONS: dict[str, set[str]] = {
    "BOOKED": {"SEATED", "CANCELLED", "NO_SHOW"},
    "SEATED": {"COMPLETED", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
    "NO_SHOW": set(),
}


class MenuDayPublish(BaseModel):
    service_date: date
    meal_type: Literal["BREAKFAST", "LUNCH", "DINNER", "OTHER"]
    menu_item_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)


class MenuAvailabilityPatch(BaseModel):
    is_available: bool | None = None
    sold_out: bool | None = None
    notes: str | None = Field(default=None, max_length=500)


class TableReservationCreate(BaseModel):
    table_id: uuid.UUID
    guest_name: str = Field(min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=80)
    party_size: int = Field(ge=1, le=30)
    starts_at: datetime
    ends_at: datetime
    stay_id: uuid.UUID | None = None
    reservation_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_window(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.ends_at - self.starts_at > timedelta(hours=8):
            raise ValueError("table reservation window cannot exceed 8 hours")
        return self


class TableReservationPatch(BaseModel):
    status: Literal["BOOKED", "SEATED", "COMPLETED", "CANCELLED", "NO_SHOW"]


class WaiterAssignmentPatch(BaseModel):
    waiter_id: uuid.UUID | None = None


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


async def property_timezone(conn, pid: uuid.UUID) -> ZoneInfo:
    value = await conn.fetchval('SELECT timezone FROM properties WHERE id=$1', pid)
    try:
        return ZoneInfo(value or "Asia/Bishkek")
    except Exception:
        return ZoneInfo("Asia/Bishkek")


async def hotel_local_date(conn, pid: uuid.UUID) -> date:
    tz = await property_timezone(conn, pid)
    return datetime.now(tz).date()


async def audit(conn, pid: uuid.UUID, user: dict[str, Any], action: str, resource: str, resource_id: str, payload: dict[str, Any]):
    await conn.execute(
        '''INSERT INTO audit_logs (
             id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
           ) VALUES ($1,$2,'STAFF',$3,$4,$5,$6,'DINING_CONTROL','SUCCESS',$7::jsonb,now())''',
        uuid.uuid4(), pid, user["id"], action, resource, resource_id, json.dumps(payload, ensure_ascii=False, default=str),
    )


async def validate_table_reservation_links(
    conn,
    pid: uuid.UUID,
    stay_id: uuid.UUID | None,
    reservation_id: uuid.UUID | None,
) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    resolved_stay = stay_id
    resolved_reservation = reservation_id
    if stay_id is not None:
        stay = await conn.fetchrow(
            '''SELECT id,"reservationId",status::text AS status FROM stays
               WHERE id=$1 AND "propertyId"=$2''', stay_id, pid,
        )
        if not stay:
            raise HTTPException(status_code=422, detail={"code": "DINING_TABLE_RESERVATION_STAY_NOT_FOUND"})
        if reservation_id is not None and reservation_id != stay["reservationId"]:
            raise HTTPException(status_code=422, detail={"code": "DINING_TABLE_RESERVATION_LINK_MISMATCH"})
        resolved_reservation = stay["reservationId"]
    elif reservation_id is not None:
        exists = await conn.fetchval(
            'SELECT id FROM reservations WHERE id=$1 AND "propertyId"=$2', reservation_id, pid,
        )
        if not exists:
            raise HTTPException(status_code=422, detail={"code": "DINING_TABLE_RESERVATION_BOOKING_NOT_FOUND"})
    return resolved_stay, resolved_reservation


@router.get("/menu-day")
async def get_menu_day(
    request: Request,
    service_date: date | None = Query(default=None),
    meal_type: str | None = Query(default=None),
    user: dict[str, Any] = Depends(dining_access),
):
    if meal_type is not None and meal_type not in MEAL_TYPES:
        raise HTTPException(status_code=422, detail="Unknown meal type")
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        day = service_date or await hotel_local_date(conn, pid)
        rows = await conn.fetch(
            '''
            SELECT a.id,a."serviceDate",a."mealType",a."isAvailable",a."soldOut",a.notes,
                   m.id AS menu_item_id,m.code,m.category,m."nameRu",m."nameKg",m."nameEn",m."priceKgs",
                   m."isActive",m."isDraft",m."sortOrder"
            FROM kitchen_menu_availability a
            JOIN kitchen_menu_items m ON m.id=a."menuItemId" AND m."propertyId"=a."propertyId"
            WHERE a."propertyId"=$1 AND a."serviceDate"=$2
              AND ($3::text IS NULL OR a."mealType"=$3)
            ORDER BY a."mealType",m."sortOrder",m.category,m."nameRu"
            ''',
            pid, day, meal_type,
        )
    return {
        "service_date": day,
        "meal_type": meal_type,
        "schedule_configured": bool(rows),
        "items": [
            {
                "availability_id": str(row["id"]),
                "menu_item_id": str(row["menu_item_id"]),
                "meal_type": row["mealType"],
                "code": row["code"],
                "category": row["category"],
                "name_ru": row["nameRu"],
                "name_kg": row["nameKg"],
                "name_en": row["nameEn"],
                "price_kgs": row["priceKgs"],
                "is_active": row["isActive"],
                "is_draft": row["isDraft"],
                "is_available": row["isAvailable"],
                "sold_out": row["soldOut"],
                "notes": row["notes"],
            }
            for row in rows
        ],
    }


@router.post("/menu-day/publish", status_code=status.HTTP_201_CREATED)
async def publish_menu_day(
    payload: MenuDayPublish,
    request: Request,
    user: dict[str, Any] = Depends(dining_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            if payload.menu_item_ids:
                rows = await conn.fetch(
                    '''SELECT id FROM kitchen_menu_items
                       WHERE "propertyId"=$1 AND "isActive"=true AND "isDraft"=false
                         AND id=ANY($2::uuid[]) FOR SHARE''',
                    pid, payload.menu_item_ids,
                )
                found = {row["id"] for row in rows}
                requested = set(payload.menu_item_ids)
                if found != requested:
                    raise HTTPException(
                        status_code=409,
                        detail={"code": "DINING_MENU_PUBLISH_REQUIRES_ACTIVE_APPROVED_ITEMS"},
                    )
                selected = list(requested)
            else:
                selected = list(
                    await conn.fetchval(
                        '''SELECT COALESCE(array_agg(id ORDER BY "sortOrder",category,"nameRu"), ARRAY[]::uuid[])
                           FROM kitchen_menu_items
                           WHERE "propertyId"=$1 AND "isActive"=true AND "isDraft"=false''',
                        pid,
                    )
                    or []
                )

            await conn.execute(
                '''UPDATE kitchen_menu_availability
                   SET "isAvailable"=false,"soldOut"=false,"updatedAt"=now()
                   WHERE "propertyId"=$1 AND "serviceDate"=$2 AND "mealType"=$3''',
                pid, payload.service_date, payload.meal_type,
            )
            for item_id in selected:
                await conn.execute(
                    '''INSERT INTO kitchen_menu_availability (
                         id,"propertyId","menuItemId","serviceDate","mealType","isAvailable","soldOut","createdById","createdAt","updatedAt"
                       ) VALUES ($1,$2,$3,$4,$5,true,false,$6,now(),now())
                       ON CONFLICT ("menuItemId","serviceDate","mealType") DO UPDATE SET
                         "isAvailable"=true,"soldOut"=false,"createdById"=EXCLUDED."createdById","updatedAt"=now()''',
                    uuid.uuid4(), pid, item_id, payload.service_date, payload.meal_type, uuid.UUID(user["id"]),
                )
            await audit(
                conn, pid, user, "PUBLISH_MENU_DAY", "KitchenMenuAvailability",
                f"{payload.service_date}:{payload.meal_type}",
                {"service_date": payload.service_date, "meal_type": payload.meal_type, "item_count": len(selected)},
            )
    return {
        "service_date": payload.service_date,
        "meal_type": payload.meal_type,
        "published_items": len(selected),
        "guest_visibility": "ACTIVE_NON_DRAFT_AND_DAY_PUBLISHED_ONLY",
    }


@router.patch("/menu-day/{availability_id}")
async def patch_menu_availability(
    availability_id: uuid.UUID,
    payload: MenuAvailabilityPatch,
    request: Request,
    user: dict[str, Any] = Depends(dining_access),
):
    if payload.is_available is None and payload.sold_out is None and payload.notes is None:
        raise HTTPException(status_code=422, detail="No change supplied")
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            row = await conn.fetchrow(
                '''UPDATE kitchen_menu_availability SET
                     "isAvailable"=COALESCE($3,"isAvailable"),
                     "soldOut"=COALESCE($4,"soldOut"),
                     notes=COALESCE($5,notes),"updatedAt"=now()
                   WHERE id=$1 AND "propertyId"=$2
                   RETURNING id,"menuItemId","serviceDate","mealType","isAvailable","soldOut",notes''',
                availability_id, pid, payload.is_available, payload.sold_out, payload.notes,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Menu availability not found")
            await audit(conn, pid, user, "PATCH_MENU_DAY_ITEM", "KitchenMenuAvailability", str(availability_id), dict(row))
    return {
        "id": str(row["id"]),
        "menu_item_id": str(row["menuItemId"]),
        "service_date": row["serviceDate"],
        "meal_type": row["mealType"],
        "is_available": row["isAvailable"],
        "sold_out": row["soldOut"],
        "notes": row["notes"],
    }


@router.get("/table-reservations")
async def list_table_reservations(
    request: Request,
    service_date: date | None = Query(default=None),
    user: dict[str, Any] = Depends(dining_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        tz = await property_timezone(conn, pid)
        day = service_date or datetime.now(tz).date()
        start = datetime.combine(day, time.min, tzinfo=tz)
        end = start + timedelta(days=1)
        rows = await conn.fetch(
            '''SELECT tr.id,tr."tableId",tr."stayId",tr."reservationId",tr."guestName",tr.phone,tr."partySize",
                      tr."startsAt",tr."endsAt",tr.status,tr.notes,t.code AS table_code,t.name AS table_name,t.seats
               FROM kitchen_table_reservations tr
               JOIN kitchen_tables t ON t.id=tr."tableId"
               WHERE tr."propertyId"=$1 AND tr."startsAt"<$3 AND tr."endsAt">$2
               ORDER BY tr."startsAt",t.code''',
            pid, start, end,
        )
    return {
        "service_date": day,
        "items": [
            {
                "id": str(row["id"]), "table_id": str(row["tableId"]), "table_code": row["table_code"],
                "table_name": row["table_name"], "seats": row["seats"], "guest_name": row["guestName"],
                "phone": row["phone"], "party_size": row["partySize"], "starts_at": row["startsAt"],
                "ends_at": row["endsAt"], "status": row["status"], "notes": row["notes"],
                "stay_id": str(row["stayId"]) if row["stayId"] else None,
                "reservation_id": str(row["reservationId"]) if row["reservationId"] else None,
            }
            for row in rows
        ],
    }


@router.post("/table-reservations", status_code=status.HTTP_201_CREATED)
async def create_table_reservation(
    payload: TableReservationCreate,
    request: Request,
    user: dict[str, Any] = Depends(dining_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            await lock_dining_tables(conn, payload.table_id)
            table_row = await conn.fetchrow(
                '''SELECT id,code,name,seats,status,"isActive" FROM kitchen_tables
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                payload.table_id, pid,
            )
            if not table_row or not table_row["isActive"]:
                raise HTTPException(status_code=404, detail="Active table not found")
            if payload.party_size > table_row["seats"]:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "DINING_TABLE_TOO_SMALL", "seats": table_row["seats"], "party_size": payload.party_size},
                )

            stay_id, reservation_link_id = await validate_table_reservation_links(
                conn, pid, payload.stay_id, payload.reservation_id,
            )
            conflict = await conn.fetchrow(
                '''SELECT id,"guestName","startsAt","endsAt" FROM kitchen_table_reservations
                   WHERE "tableId"=$1 AND status IN ('BOOKED','SEATED')
                     AND "startsAt"<$3 AND "endsAt">$2
                   LIMIT 1 FOR UPDATE''',
                payload.table_id, payload.starts_at, payload.ends_at,
            )
            if conflict:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "DINING_TABLE_TIME_CONFLICT",
                        "reservation_id": str(conflict["id"]),
                        "guest_name": conflict["guestName"],
                        "starts_at": conflict["startsAt"],
                        "ends_at": conflict["endsAt"],
                    },
                )

            live_session = await active_session_for_table(conn, payload.table_id)
            current_window = await reservation_window_contains_now(conn, payload.starts_at, payload.ends_at)
            if current_window and live_session:
                proposed = {"stayId": stay_id, "reservationId": reservation_link_id}
                if not reservation_matches_session(proposed, live_session):
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "DINING_TABLE_LIVE_SESSION_CONFLICT",
                            "session_id": str(live_session["id"]),
                            "session_status": live_session["status"],
                        },
                    )

            initial_status = "SEATED" if current_window and live_session and live_session["status"] == "SEATED" else "BOOKED"
            reservation_row_id = uuid.uuid4()
            await conn.execute(
                '''INSERT INTO kitchen_table_reservations (
                     id,"propertyId","tableId","stayId","reservationId","guestName",phone,"partySize","startsAt","endsAt",status,notes,"createdById","createdAt","updatedAt"
                   ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,now(),now())''',
                reservation_row_id, pid, payload.table_id, stay_id, reservation_link_id,
                payload.guest_name.strip(), payload.phone, payload.party_size, payload.starts_at, payload.ends_at,
                initial_status, payload.notes, uuid.UUID(user["id"]),
            )
            await audit(conn, pid, user, "CREATE_TABLE_RESERVATION", "KitchenTableReservation", str(reservation_row_id), {
                **payload.model_dump(),
                "resolved_stay_id": str(stay_id) if stay_id else None,
                "resolved_reservation_id": str(reservation_link_id) if reservation_link_id else None,
                "status": initial_status,
                "live_session_id": str(live_session["id"]) if current_window and live_session else None,
            })
    return {"id": str(reservation_row_id), "status": initial_status, "table_code": table_row["code"]}


@router.patch("/table-reservations/{reservation_id}")
async def patch_table_reservation(
    reservation_id: uuid.UUID,
    payload: TableReservationPatch,
    request: Request,
    user: dict[str, Any] = Depends(dining_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            preliminary = await conn.fetchrow(
                '''SELECT id,"tableId" FROM kitchen_table_reservations
                   WHERE id=$1 AND "propertyId"=$2''', reservation_id, pid,
            )
            if not preliminary:
                raise HTTPException(status_code=404, detail="Table reservation not found")
            await lock_dining_tables(conn, preliminary["tableId"])
            row = await conn.fetchrow(
                '''SELECT id,"tableId","stayId","reservationId","startsAt","endsAt",status FROM kitchen_table_reservations
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                reservation_id, pid,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Table reservation not found")

            current_status = row["status"]
            if payload.status == current_status:
                return {"id": str(reservation_id), "status": current_status, "idempotent_replay": True}
            if payload.status not in TABLE_RESERVATION_TRANSITIONS.get(current_status, set()):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "DINING_RESERVATION_INVALID_TRANSITION",
                        "from": current_status,
                        "to": payload.status,
                    },
                )

            live_session = await active_session_for_table(conn, row["tableId"])
            matching_session = bool(live_session and reservation_matches_session(row, live_session))
            if payload.status == "SEATED" and live_session and not matching_session:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "DINING_RESERVATION_LIVE_SESSION_CONFLICT",
                        "session_id": str(live_session["id"]),
                        "session_status": live_session["status"],
                    },
                )
            if matching_session and payload.status != "SEATED":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "DINING_RESERVATION_HAS_ACTIVE_SESSION",
                        "session_id": str(live_session["id"]),
                        "session_status": live_session["status"],
                        "action": "RELEASE_OR_CANCEL_DINING_SESSION_FIRST",
                    },
                )

            await conn.execute(
                'UPDATE kitchen_table_reservations SET status=$2,"updatedAt"=now() WHERE id=$1',
                reservation_id, payload.status,
            )
            if payload.status == "SEATED":
                if matching_session and live_session["status"] == "WAITING":
                    await conn.execute(
                        '''UPDATE dining_table_sessions SET status='SEATED',
                             "seatedAt"=COALESCE("seatedAt",now()),"updatedAt"=now() WHERE id=$1''',
                        live_session["id"],
                    )
                    live_session = {**dict(live_session), "status": "SEATED"}
                await conn.execute(
                    "UPDATE kitchen_tables SET status='OCCUPIED',\"updatedAt\"=now() WHERE id=$1 AND \"propertyId\"=$2",
                    row["tableId"], pid,
                )
            elif payload.status in {"COMPLETED", "CANCELLED", "NO_SHOW"}:
                if live_session:
                    await conn.execute(
                        'UPDATE kitchen_tables SET status=$2,"updatedAt"=now() WHERE id=$1',
                        row["tableId"], live_table_status(live_session),
                    )
                else:
                    active_orders = int(
                        await conn.fetchval(
                            '''SELECT count(*)::int FROM kitchen_orders
                               WHERE "tableId"=$1 AND status=ANY($2::text[])''',
                            row["tableId"], list(ACTIVE_ORDER_STATUSES),
                        )
                        or 0
                    )
                    if active_orders == 0:
                        await conn.execute(
                            "UPDATE kitchen_tables SET status='CLEANING',\"updatedAt\"=now() WHERE id=$1 AND \"propertyId\"=$2",
                            row["tableId"], pid,
                        )
            await audit(
                conn, pid, user, "PATCH_TABLE_RESERVATION", "KitchenTableReservation", str(reservation_id),
                {
                    "from_status": current_status, "status": payload.status,
                    "live_session_id": str(live_session["id"]) if live_session else None,
                    "live_session_match": matching_session,
                },
            )
    return {"id": str(reservation_id), "status": payload.status, "idempotent_replay": False}


@router.patch("/orders/{order_id}/waiter")
async def assign_waiter(
    order_id: uuid.UUID,
    payload: WaiterAssignmentPatch,
    request: Request,
    user: dict[str, Any] = Depends(dining_access),
):
    current_id = uuid.UUID(user["id"])
    if user["role"] == "DINING_STAFF" and payload.waiter_id not in {current_id}:
        raise HTTPException(status_code=403, detail="Dining staff may assign only themselves")
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            order = await conn.fetchrow(
                '''SELECT id,status,"waiterId" FROM kitchen_orders
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                order_id, pid,
            )
            if not order:
                raise HTTPException(status_code=404, detail="Kitchen order not found")
            if order["status"] in {"SERVED", "CANCELLED"}:
                raise HTTPException(status_code=409, detail="Completed order cannot be reassigned")
            if payload.waiter_id is not None:
                waiter = await conn.fetchrow(
                    '''SELECT id,"displayName",role::text AS role FROM staff_users
                       WHERE id=$1 AND "propertyId"=$2 AND "isActive"=true''',
                    payload.waiter_id, pid,
                )
                if not waiter or waiter["role"] != "DINING_STAFF":
                    raise HTTPException(status_code=422, detail="Waiter must be active DINING_STAFF")
            await conn.execute(
                'UPDATE kitchen_orders SET "waiterId"=$2,"updatedAt"=now() WHERE id=$1',
                order_id, payload.waiter_id,
            )
            await audit(
                conn, pid, user, "ASSIGN_WAITER", "KitchenOrder", str(order_id),
                {"waiter_id": str(payload.waiter_id) if payload.waiter_id else None},
            )
    return {"id": str(order_id), "waiter_id": str(payload.waiter_id) if payload.waiter_id else None}


@router.get("/floor")
async def dining_floor(
    request: Request,
    service_date: date | None = Query(default=None),
    user: dict[str, Any] = Depends(dining_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        tz = await property_timezone(conn, pid)
        day = service_date or datetime.now(tz).date()
        start = datetime.combine(day, time.min, tzinfo=tz)
        end = start + timedelta(days=1)
        tables = await conn.fetch(
            '''SELECT id,code,name,seats,status,"isActive",notes FROM kitchen_tables
               WHERE "propertyId"=$1 AND "isActive"=true ORDER BY code''', pid,
        )
        reservations = await conn.fetch(
            '''SELECT tr.id,tr."tableId",tr."stayId",tr."reservationId",tr."guestName",tr.phone,tr."partySize",
                      tr."startsAt",tr."endsAt",tr.status,tr.notes,t.code AS table_code,t.name AS table_name
               FROM kitchen_table_reservations tr
               JOIN kitchen_tables t ON t.id=tr."tableId"
               WHERE tr."propertyId"=$1 AND tr."startsAt"<$3 AND tr."endsAt">$2
                 AND tr.status NOT IN ('CANCELLED','NO_SHOW')
               ORDER BY tr."startsAt",t.code''',
            pid, start, end,
        )
        orders = await conn.fetch(
            '''SELECT o.id,o."orderNumber",o.status,o.source,o."tableId",o."roomId",o."guestCount",o."totalKgs",o."waiterId",o."openedAt",
                      t.code AS table_code,t.name AS table_name,r.code AS room_code,u."displayName" AS waiter_name
               FROM kitchen_orders o
               LEFT JOIN kitchen_tables t ON t.id=o."tableId"
               LEFT JOIN rooms r ON r.id=o."roomId"
               LEFT JOIN staff_users u ON u.id=o."waiterId"
               WHERE o."propertyId"=$1 AND o.status=ANY($2::text[])
               ORDER BY CASE o.status WHEN 'READY' THEN 0 WHEN 'NEW' THEN 1 WHEN 'ACCEPTED' THEN 2 ELSE 3 END,o."openedAt"''',
            pid, list(ACTIVE_ORDER_STATUSES),
        )
    return {
        "service_date": day,
        "current_user_id": user["id"],
        "tables": [
            {"id": str(r["id"]), "code": r["code"], "name": r["name"], "seats": r["seats"], "status": r["status"], "notes": r["notes"]}
            for r in tables
        ],
        "reservations": [
            {"id": str(r["id"]), "table_id": str(r["tableId"]), "table_code": r["table_code"], "table_name": r["table_name"],
             "guest_name": r["guestName"], "phone": r["phone"], "party_size": r["partySize"], "starts_at": r["startsAt"],
             "ends_at": r["endsAt"], "status": r["status"], "notes": r["notes"],
             "stay_id": str(r["stayId"]) if r["stayId"] else None,
             "reservation_id": str(r["reservationId"]) if r["reservationId"] else None}
            for r in reservations
        ],
        "orders": [
            {"id": str(r["id"]), "order_number": r["orderNumber"], "status": r["status"], "source": r["source"],
             "table_id": str(r["tableId"]) if r["tableId"] else None, "table_code": r["table_code"], "table_name": r["table_name"],
             "room_code": r["room_code"], "guest_count": r["guestCount"], "total_kgs": r["totalKgs"],
             "waiter_id": str(r["waiterId"]) if r["waiterId"] else None, "waiter_name": r["waiter_name"], "opened_at": r["openedAt"]}
            for r in orders
        ],
    }
