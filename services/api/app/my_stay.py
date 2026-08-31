import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, model_validator

from .auth import require_roles

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
GUEST_COOKIE = "resort_guest_session"
GUEST_SESSION_HOURS = int(os.environ.get("GUEST_SESSION_HOURS", "24"))
GUEST_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
GUEST_HOST = os.environ.get("GUEST_HOST", "guest.3korony.com")

router = APIRouter(tags=["my-stay"])
manager_access = require_roles("OWNER", "ADMIN", "MANAGER", "RECEPTION")
dining_access = require_roles("OWNER", "ADMIN", "MANAGER", "DINING")
finance_access = require_roles("OWNER", "ADMIN", "MANAGER", "RECEPTION")

MEAL_TYPES = {"BREAKFAST", "LUNCH", "DINNER"}
DINING_STATUSES = {"NEW", "ACCEPTED", "PREPARING", "READY", "DELIVERED", "CANCELLED"}
SERVICE_CODES = {"TRANSFER", "EXCURSIONS"}


def _secret() -> bytes:
    value = os.environ.get("GUEST_SESSION_SECRET", "")
    if len(value) < 32:
        raise HTTPException(status_code=503, detail="MY STAY security secret is not configured")
    return value.encode("utf-8")


def _digest(kind: str, value: str) -> str:
    return hmac.new(_secret(), f"{kind}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()


def _pin() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _token() -> str:
    return secrets.token_urlsafe(32)


async def _property(conn, code: str = PROPERTY_CODE):
    row = await conn.fetchrow('SELECT id,code,timezone,currency FROM properties WHERE code=$1', code)
    if not row:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return row


async def _guest_context(request: Request, raw_session: str | None) -> dict[str, Any]:
    if not raw_session:
        raise HTTPException(status_code=401, detail="Guest session required")
    token_hash = _digest("session", raw_session)
    async with request.app.state.db.acquire() as conn:
        row = await conn.fetchrow(
            '''
            SELECT gs.id AS session_id, gs."expiresAt" AS session_expires, gs."revokedAt",
                   gac.id AS credential_id,gac."isActive",gac."expiresAt" AS credential_expires,
                   r.id AS reservation_id,r."bookingNumber",r.status::text AS reservation_status,
                   r."checkIn",r."checkOut",r.adults,r.children,r."primaryGuestId",
                   p.id AS property_id,p.code AS property_code,p.timezone,p.currency,
                   g."firstName",g."lastName"
            FROM guest_sessions gs
            JOIN guest_access_credentials gac ON gac.id=gs."credentialId"
            JOIN reservations r ON r.id=gac."reservationId" AND r."propertyId"=gac."propertyId"
            JOIN properties p ON p.id=gac."propertyId"
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            WHERE gs."tokenHash"=$1
            ''',
            token_hash,
        )
        now = datetime.utcnow()
        if (
            not row
            or row["revokedAt"] is not None
            or row["session_expires"].replace(tzinfo=None) <= now
            or not row["isActive"]
            or row["credential_expires"].replace(tzinfo=None) <= now
            or row["reservation_status"] != "CHECKED_IN"
        ):
            raise HTTPException(status_code=401, detail="Guest session expired or stay is not active")
        room = await conn.fetchrow(
            '''
            SELECT rm.id,rm.code,rt.name AS room_type
            FROM inventory_blocks ib
            JOIN rooms rm ON rm.id=ib."roomId"
            JOIN room_types rt ON rt.id=rm."roomTypeId"
            WHERE ib."reservationId"=$1 AND ib.active=true AND ib."blockType"='RESERVATION'
              AND (now() AT TIME ZONE $2)::date >= ib."startDate"
              AND (now() AT TIME ZONE $2)::date < ib."endDate"
            ORDER BY ib."startDate" DESC LIMIT 1
            ''',
            row["reservation_id"], row["timezone"],
        )
        await conn.execute('UPDATE guest_sessions SET "lastSeenAt"=now() WHERE id=$1', row["session_id"])
    return {
        "session_id": row["session_id"],
        "credential_id": row["credential_id"],
        "property_id": row["property_id"],
        "property_code": row["property_code"],
        "timezone": row["timezone"],
        "currency": row["currency"],
        "reservation_id": row["reservation_id"],
        "booking_number": row["bookingNumber"],
        "check_in": row["checkIn"],
        "check_out": row["checkOut"],
        "guest_name": " ".join(filter(None, [row["firstName"], row["lastName"]])).strip() or "Гость",
        "room_id": room["id"] if room else None,
        "room_code": room["code"] if room else None,
        "room_type": room["room_type"] if room else None,
    }


class GuestActivation(BaseModel):
    activation_token: str = Field(min_length=20, max_length=200)
    pin: str = Field(pattern=r"^\d{6}$")


class MealPlanPatch(BaseModel):
    service_date: str
    meal_type: Literal["BREAKFAST", "LUNCH", "DINNER"]
    included: bool


class MenuItemCreate(BaseModel):
    service_date: str
    meal_type: Literal["BREAKFAST", "LUNCH", "DINNER"]
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    price_kgs: int = Field(default=0, ge=0, le=100000)
    available_qty: int | None = Field(default=None, ge=0, le=10000)
    included_in_meal_plan: bool = False
    sort_order: int = Field(default=0, ge=-1000, le=1000)


class MenuItemPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    price_kgs: int | None = Field(default=None, ge=0, le=100000)
    available_qty: int | None = Field(default=None, ge=0, le=10000)
    included_in_meal_plan: bool | None = None
    active: bool | None = None
    sort_order: int | None = Field(default=None, ge=-1000, le=1000)


class DiningOrderLine(BaseModel):
    menu_item_id: uuid.UUID
    quantity: int = Field(ge=1, le=20)


class DiningOrderCreate(BaseModel):
    service_date: str
    meal_type: Literal["BREAKFAST", "LUNCH", "DINNER"]
    items: list[DiningOrderLine] = Field(min_length=1, max_length=30)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def no_duplicate_items(self):
        ids = [item.menu_item_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate menu_item_id")
        return self


class GuestRequestCreate(BaseModel):
    kind: Literal["HOUSEKEEPING", "MAINTENANCE", "TRANSFER", "EXCURSIONS"]
    description: str = Field(min_length=2, max_length=2000)
    priority: Literal["NORMAL", "HIGH", "URGENT"] = "NORMAL"
    service_date: str | None = None
    service_time: str | None = Field(default=None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")


class DiningStatusPatch(BaseModel):
    status: Literal["ACCEPTED", "PREPARING", "READY", "DELIVERED", "CANCELLED"]


class ChargePaymentPatch(BaseModel):
    payment_id: uuid.UUID


@router.post("/api/v1/admin/my-stay/reservations/{reservation_id}/issue")
async def issue_guest_access(reservation_id: uuid.UUID, request: Request, user=Depends(manager_access)):
    pin = _pin()
    activation = _token()
    now = datetime.utcnow()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            reservation = await conn.fetchrow(
                '''SELECT id,"bookingNumber",status::text AS status,"checkOut" FROM reservations
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''', reservation_id, prop["id"]
            )
            if not reservation:
                raise HTTPException(status_code=404, detail="Reservation not found")
            if reservation["status"] not in {"GUARANTEED", "CHECKED_IN"}:
                raise HTTPException(status_code=409, detail="Guest access is only issued for active/upcoming stays")
            expires = max(now + timedelta(hours=2), datetime.combine(reservation["checkOut"], datetime.min.time()) + timedelta(hours=4))
            credential_id = uuid.uuid4()
            existing = await conn.fetchrow('SELECT id FROM guest_access_credentials WHERE "reservationId"=$1 FOR UPDATE', reservation_id)
            if existing:
                credential_id = existing["id"]
                await conn.execute(
                    '''UPDATE guest_access_credentials SET "pinHash"=$2,"activationTokenHash"=$3,"isActive"=true,
                       "expiresAt"=$4,"updatedAt"=now() WHERE id=$1''',
                    credential_id, _digest("pin", pin), _digest("activation", activation), expires,
                )
                await conn.execute(
                    '''UPDATE guest_sessions SET "revokedAt"=now() WHERE "credentialId"=$1 AND "revokedAt" IS NULL''', credential_id
                )
            else:
                await conn.execute(
                    '''INSERT INTO guest_access_credentials
                       (id,"propertyId","reservationId","pinHash","activationTokenHash","isActive","expiresAt","issuedAt","updatedAt")
                       VALUES ($1,$2,$3,$4,$5,true,$6,now(),now())''',
                    credential_id, prop["id"], reservation_id, _digest("pin", pin), _digest("activation", activation), expires,
                )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"createdAt")
                   VALUES ($1,$2,'STAFF',$3,'ISSUE_GUEST_ACCESS','Reservation',$4,'PMS_MY_STAY','SUCCESS',now())''',
                uuid.uuid4(), prop["id"], user["id"], str(reservation_id),
            )
    return {
        "reservation_id": str(reservation_id),
        "booking_number": reservation["bookingNumber"],
        "pin": pin,
        "activation_token": activation,
        "guest_url": f"https://{GUEST_HOST}/my-stay#activate={activation}",
        "expires_at": expires,
    }


@router.post("/api/v1/admin/my-stay/reservations/{reservation_id}/revoke", status_code=204)
async def revoke_guest_access(reservation_id: uuid.UUID, request: Request, user=Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn, user["property_code"])
        credential = await conn.fetchval(
            '''UPDATE guest_access_credentials SET "isActive"=false,"updatedAt"=now()
               WHERE "reservationId"=$1 AND "propertyId"=$2 RETURNING id''', reservation_id, prop["id"]
        )
        if credential:
            await conn.execute('UPDATE guest_sessions SET "revokedAt"=now() WHERE "credentialId"=$1 AND "revokedAt" IS NULL', credential)
    return Response(status_code=204)


@router.post("/api/v1/guest/activate")
async def activate_guest(payload: GuestActivation, request: Request, response: Response):
    activation_hash = _digest("activation", payload.activation_token)
    pin_hash = _digest("pin", payload.pin)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                '''
                SELECT gac.id,gac."pinHash",gac."isActive",gac."expiresAt",r.status::text AS reservation_status
                FROM guest_access_credentials gac
                JOIN reservations r ON r.id=gac."reservationId"
                WHERE gac."activationTokenHash"=$1
                FOR UPDATE OF gac
                ''', activation_hash,
            )
            now = datetime.utcnow()
            valid = row and row["isActive"] and row["expiresAt"].replace(tzinfo=None) > now and row["reservation_status"] == "CHECKED_IN"
            if not valid or not hmac.compare_digest(row["pinHash"] if row else "", pin_hash):
                raise HTTPException(status_code=401, detail="Invalid activation code or PIN")
            raw_session = _token()
            session_id = uuid.uuid4()
            expires = min(row["expiresAt"].replace(tzinfo=None), now + timedelta(hours=GUEST_SESSION_HOURS))
            await conn.execute(
                '''INSERT INTO guest_sessions (id,"credentialId","tokenHash","expiresAt","lastSeenAt","createdAt")
                   VALUES ($1,$2,$3,$4,now(),now())''', session_id, row["id"], _digest("session", raw_session), expires
            )
            await conn.execute('UPDATE guest_access_credentials SET "activationTokenHash"=NULL,"updatedAt"=now() WHERE id=$1', row["id"])
    response.set_cookie(
        GUEST_COOKIE, raw_session, httponly=True, secure=GUEST_COOKIE_SECURE,
        samesite="lax", path="/", max_age=max(60, int((expires - datetime.utcnow()).total_seconds())),
    )
    return {"ok": True, "expires_at": expires}


@router.post("/api/v1/guest/logout", status_code=204)
async def guest_logout(request: Request, response: Response, resort_guest_session: str | None = Cookie(default=None)):
    if resort_guest_session:
        try:
            token_hash = _digest("session", resort_guest_session)
            async with request.app.state.db.acquire() as conn:
                await conn.execute('UPDATE guest_sessions SET "revokedAt"=now() WHERE "tokenHash"=$1 AND "revokedAt" IS NULL', token_hash)
        except HTTPException:
            pass
    response.delete_cookie(GUEST_COOKIE, path="/")
    return Response(status_code=204)


@router.get("/api/v1/guest/me")
async def guest_me(request: Request, resort_guest_session: str | None = Cookie(default=None)):
    ctx = await _guest_context(request, resort_guest_session)
    return {
        "guest_name": ctx["guest_name"], "booking_number": ctx["booking_number"],
        "check_in": ctx["check_in"], "check_out": ctx["check_out"],
        "room_code": ctx["room_code"], "room_type": ctx["room_type"], "currency": ctx["currency"],
    }


@router.get("/api/v1/guest/menu")
async def guest_menu(request: Request, service_date: str, meal_type: Literal["BREAKFAST", "LUNCH", "DINNER"], resort_guest_session: str | None = Cookie(default=None)):
    ctx = await _guest_context(request, resort_guest_session)
    async with request.app.state.db.acquire() as conn:
        included = bool(await conn.fetchval(
            '''SELECT included FROM reservation_meal_plans WHERE "reservationId"=$1 AND "serviceDate"=$2::date AND "mealType"=$3''',
            ctx["reservation_id"], service_date, meal_type,
        ) or False)
        rows = await conn.fetch(
            '''SELECT id,name,description,"priceKgs","availableQty","includedInMealPlan"
               FROM dining_menu_items WHERE "propertyId"=$1 AND "serviceDate"=$2::date AND "mealType"=$3 AND active=true
               AND ("availableQty" IS NULL OR "availableQty">0) ORDER BY "sortOrder",name''',
            ctx["property_id"], service_date, meal_type,
        )
    return {"meal_plan_included": included, "items": [dict(row) for row in rows]}


@router.post("/api/v1/guest/dining/orders", status_code=status.HTTP_201_CREATED)
async def guest_create_dining_order(payload: DiningOrderCreate, request: Request, resort_guest_session: str | None = Cookie(default=None)):
    ctx = await _guest_context(request, resort_guest_session)
    order_id = uuid.uuid4()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            plan_included = bool(await conn.fetchval(
                '''SELECT included FROM reservation_meal_plans WHERE "reservationId"=$1 AND "serviceDate"=$2::date AND "mealType"=$3''',
                ctx["reservation_id"], payload.service_date, payload.meal_type,
            ) or False)
            total = 0
            resolved = []
            for line in payload.items:
                item = await conn.fetchrow(
                    '''SELECT id,name,"priceKgs","availableQty","includedInMealPlan",active
                       FROM dining_menu_items WHERE id=$1 AND "propertyId"=$2 AND "serviceDate"=$3::date AND "mealType"=$4 FOR UPDATE''',
                    line.menu_item_id, ctx["property_id"], payload.service_date, payload.meal_type,
                )
                if not item or not item["active"]:
                    raise HTTPException(status_code=409, detail={"code": "MENU_ITEM_UNAVAILABLE", "item_id": str(line.menu_item_id)})
                if item["availableQty"] is not None and item["availableQty"] < line.quantity:
                    raise HTTPException(status_code=409, detail={"code": "NOT_ENOUGH_PORTIONS", "item_id": str(line.menu_item_id), "available": item["availableQty"]})
                included_line = plan_included and item["includedInMealPlan"]
                unit = 0 if included_line else item["priceKgs"]
                line_total = unit * line.quantity
                total += line_total
                resolved.append((item, line.quantity, unit, line_total, included_line))
                if item["availableQty"] is not None:
                    await conn.execute('UPDATE dining_menu_items SET "availableQty"="availableQty"-$2,"updatedAt"=now() WHERE id=$1', item["id"], line.quantity)
            payment_mode = "INCLUDED" if total == 0 else "ROOM_FOLIO"
            await conn.execute(
                '''INSERT INTO dining_orders (id,"propertyId","reservationId","serviceDate","mealType",status,"paymentMode","totalKgs",notes,"createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4::date,$5,'NEW',$6,$7,$8,now(),now())''',
                order_id, ctx["property_id"], ctx["reservation_id"], payload.service_date, payload.meal_type, payment_mode, total, payload.notes,
            )
            for item, qty, unit, line_total, included_line in resolved:
                await conn.execute(
                    '''INSERT INTO dining_order_items (id,"orderId","menuItemId",name,quantity,"unitPriceKgs","lineTotalKgs","includedByPlan","createdAt")
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,now())''',
                    uuid.uuid4(), order_id, item["id"], item["name"], qty, unit, line_total, included_line,
                )
            if total > 0:
                await conn.execute(
                    '''INSERT INTO reservation_charges (id,"propertyId","reservationId","sourceType","sourceId",description,"amountKgs",status,"createdAt","updatedAt")
                       VALUES ($1,$2,$3,'DINING_ORDER',$4,$5,$6,'OPEN',now(),now())''',
                    uuid.uuid4(), ctx["property_id"], ctx["reservation_id"], order_id, f"Питание · {payload.meal_type}", total,
                )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'GUEST',$3,'CREATE_DINING_ORDER','DiningOrder',$4,'MY_STAY','SUCCESS',jsonb_build_object('total_kgs',$5::int),now())''',
                uuid.uuid4(), ctx["property_id"], str(ctx["session_id"]), str(order_id), total,
            )
    return {"id": str(order_id), "status": "NEW", "total_kgs": total, "payment_mode": payment_mode}


@router.get("/api/v1/guest/orders")
async def guest_orders(request: Request, resort_guest_session: str | None = Cookie(default=None)):
    ctx = await _guest_context(request, resort_guest_session)
    async with request.app.state.db.acquire() as conn:
        orders = await conn.fetch(
            '''SELECT id,"serviceDate","mealType",status,"paymentMode","totalKgs",notes,"createdAt","updatedAt"
               FROM dining_orders WHERE "reservationId"=$1 ORDER BY "createdAt" DESC LIMIT 100''', ctx["reservation_id"]
        )
        requests = await conn.fetch(
            '''SELECT id,type::text AS type,status::text AS status,"serviceCode",title,description,"createdAt","updatedAt"
               FROM operational_tasks WHERE "reservationId"=$1 AND source LIKE 'GUEST_PORTAL%' ORDER BY "createdAt" DESC LIMIT 100''', ctx["reservation_id"]
        )
        charges = await conn.fetch(
            '''SELECT id,description,"amountKgs",status,"paymentId","createdAt" FROM reservation_charges
               WHERE "reservationId"=$1 ORDER BY "createdAt" DESC LIMIT 100''', ctx["reservation_id"]
        )
    return {"dining_orders": [dict(row) for row in orders], "service_requests": [dict(row) for row in requests], "charges": [dict(row) for row in charges]}


@router.post("/api/v1/guest/requests", status_code=status.HTTP_201_CREATED)
async def guest_create_request(payload: GuestRequestCreate, request: Request, resort_guest_session: str | None = Cookie(default=None)):
    ctx = await _guest_context(request, resort_guest_session)
    if payload.kind in {"HOUSEKEEPING", "MAINTENANCE"} and not ctx["room_id"]:
        raise HTTPException(status_code=409, detail="Current room is not resolved")
    task_type = payload.kind if payload.kind in {"HOUSEKEEPING", "MAINTENANCE"} else "GUEST_REQUEST"
    service_code = payload.kind if payload.kind in SERVICE_CODES else None
    task_id = uuid.uuid4()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            duplicate = await conn.fetchval(
                '''SELECT id FROM operational_tasks WHERE "propertyId"=$1 AND "reservationId"=$2
                   AND type::text=$3 AND COALESCE("serviceCode",'')=COALESCE($4,'')
                   AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION') LIMIT 1 FOR UPDATE''',
                ctx["property_id"], ctx["reservation_id"], task_type, service_code,
            )
            if duplicate:
                raise HTTPException(status_code=409, detail={"code": "ACTIVE_REQUEST_EXISTS", "task_id": str(duplicate)})
            title_map = {"HOUSEKEEPING": "Уборка по просьбе гостя", "MAINTENANCE": "Ремонт по просьбе гостя", "TRANSFER": "Трансфер", "EXCURSIONS": "Экскурсия / тур"}
            await conn.execute(
                '''INSERT INTO operational_tasks
                   (id,"propertyId","roomId","reservationId","serviceCode","serviceDate","serviceTime",type,status,priority,title,description,
                    "createdByType","createdById",source,"createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,$5,$6::date,$7,$8::"OperationalTaskType",'OPEN',$9::"OperationalTaskPriority",$10,$11,
                           'GUEST',$12,'GUEST_PORTAL_IN_STAY',now(),now())''',
                task_id, ctx["property_id"], ctx["room_id"] if task_type != "GUEST_REQUEST" else None, ctx["reservation_id"], service_code,
                payload.service_date, payload.service_time, task_type, payload.priority, title_map[payload.kind], payload.description, str(ctx["session_id"]),
            )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"createdAt")
                   VALUES ($1,$2,'GUEST',$3,'CREATE_SERVICE_REQUEST','OperationalTask',$4,'MY_STAY','SUCCESS',now())''',
                uuid.uuid4(), ctx["property_id"], str(ctx["session_id"]), str(task_id),
            )
    return {"id": str(task_id), "status": "OPEN", "kind": payload.kind}


@router.put("/api/v1/admin/my-stay/reservations/{reservation_id}/meal-plan")
async def set_meal_plan(reservation_id: uuid.UUID, payload: MealPlanPatch, request: Request, user=Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn, user["property_code"])
        exists = await conn.fetchval('SELECT 1 FROM reservations WHERE id=$1 AND "propertyId"=$2', reservation_id, prop["id"])
        if not exists:
            raise HTTPException(status_code=404, detail="Reservation not found")
        await conn.execute(
            '''INSERT INTO reservation_meal_plans (id,"propertyId","reservationId","serviceDate","mealType",included,"createdAt","updatedAt")
               VALUES ($1,$2,$3,$4::date,$5,$6,now(),now())
               ON CONFLICT ("reservationId","serviceDate","mealType") DO UPDATE SET included=EXCLUDED.included,"updatedAt"=now()''',
            uuid.uuid4(), prop["id"], reservation_id, payload.service_date, payload.meal_type, payload.included,
        )
    return {"ok": True}


@router.get("/api/v1/dining/menu")
async def dining_menu(request: Request, service_date: str, meal_type: Literal["BREAKFAST", "LUNCH", "DINNER"], user=Depends(dining_access)):
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn, user["property_code"])
        rows = await conn.fetch(
            '''SELECT id,"serviceDate","mealType",name,description,"priceKgs","availableQty","includedInMealPlan",active,"sortOrder"
               FROM dining_menu_items WHERE "propertyId"=$1 AND "serviceDate"=$2::date AND "mealType"=$3 ORDER BY "sortOrder",name''',
            prop["id"], service_date, meal_type,
        )
    return {"items": [dict(row) for row in rows]}


@router.post("/api/v1/dining/menu", status_code=status.HTTP_201_CREATED)
async def dining_create_menu_item(payload: MenuItemCreate, request: Request, user=Depends(dining_access)):
    item_id = uuid.uuid4()
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn, user["property_code"])
        await conn.execute(
            '''INSERT INTO dining_menu_items
               (id,"propertyId","serviceDate","mealType",name,description,"priceKgs","availableQty","includedInMealPlan",active,"sortOrder","createdById","createdAt","updatedAt")
               VALUES ($1,$2,$3::date,$4,$5,$6,$7,$8,$9,true,$10,$11,now(),now())''',
            item_id, prop["id"], payload.service_date, payload.meal_type, payload.name.strip(), payload.description,
            payload.price_kgs, payload.available_qty, payload.included_in_meal_plan, payload.sort_order, uuid.UUID(user["id"]),
        )
    return {"id": str(item_id), "active": True}


@router.patch("/api/v1/dining/menu/{item_id}")
async def dining_patch_menu_item(item_id: uuid.UUID, payload: MenuItemPatch, request: Request, user=Depends(dining_access)):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return {"ok": True}
    column_map = {
        "name": 'name', "description": 'description', "price_kgs": '"priceKgs"', "available_qty": '"availableQty"',
        "included_in_meal_plan": '"includedInMealPlan"', "active": 'active', "sort_order": '"sortOrder"',
    }
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn, user["property_code"])
        sets, values = [], []
        for key, value in changes.items():
            values.append(value)
            sets.append(f"{column_map[key]}=${len(values)+2}")
        result = await conn.execute(
            f'''UPDATE dining_menu_items SET {', '.join(sets)},"updatedAt"=now() WHERE id=$1 AND "propertyId"=$2''',
            item_id, prop["id"], *values,
        )
        if result.endswith("0"):
            raise HTTPException(status_code=404, detail="Menu item not found")
    return {"ok": True}


@router.get("/api/v1/dining/orders")
async def dining_list_orders(request: Request, user=Depends(dining_access)):
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn, user["property_code"])
        rows = await conn.fetch(
            '''SELECT o.id,o."serviceDate",o."mealType",o.status,o."paymentMode",o."totalKgs",o.notes,o."createdAt",
                      r."bookingNumber",g."firstName",rm.code AS room_code
               FROM dining_orders o JOIN reservations r ON r.id=o."reservationId"
               LEFT JOIN guests g ON g.id=r."primaryGuestId"
               LEFT JOIN LATERAL (
                   SELECT room.code FROM inventory_blocks ib JOIN rooms room ON room.id=ib."roomId"
                   WHERE ib."reservationId"=r.id AND ib.active=true AND ib."blockType"='RESERVATION'
                   ORDER BY ib."startDate" DESC LIMIT 1
               ) rm ON true
               WHERE o."propertyId"=$1 AND o.status NOT IN ('DELIVERED','CANCELLED')
               ORDER BY o."createdAt"''', prop["id"]
        )
    return {"items": [dict(row) for row in rows]}


@router.patch("/api/v1/dining/orders/{order_id}/status")
async def dining_order_status(order_id: uuid.UUID, payload: DiningStatusPatch, request: Request, user=Depends(dining_access)):
    allowed = {
        "NEW": {"ACCEPTED", "CANCELLED"}, "ACCEPTED": {"PREPARING", "CANCELLED"}, "PREPARING": {"READY"},
        "READY": {"DELIVERED"}, "DELIVERED": set(), "CANCELLED": set(),
    }
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            row = await conn.fetchrow('SELECT status FROM dining_orders WHERE id=$1 AND "propertyId"=$2 FOR UPDATE', order_id, prop["id"])
            if not row:
                raise HTTPException(status_code=404, detail="Dining order not found")
            if payload.status not in allowed[row["status"]]:
                raise HTTPException(status_code=409, detail={"code": "INVALID_DINING_TRANSITION", "from": row["status"], "to": payload.status})
            if payload.status == "CANCELLED":
                lines = await conn.fetch('SELECT "menuItemId",quantity FROM dining_order_items WHERE "orderId"=$1', order_id)
                for line in lines:
                    await conn.execute(
                        '''UPDATE dining_menu_items SET "availableQty"=CASE WHEN "availableQty" IS NULL THEN NULL ELSE "availableQty"+$2 END,"updatedAt"=now() WHERE id=$1''',
                        line["menuItemId"], line["quantity"],
                    )
                await conn.execute('UPDATE reservation_charges SET status=\'VOID\',"updatedAt"=now() WHERE "sourceType"=\'DINING_ORDER\' AND "sourceId"=$1 AND status=\'OPEN\'', order_id)
            await conn.execute(
                '''UPDATE dining_orders SET status=$2,"completedAt"=CASE WHEN $2 IN ('DELIVERED','CANCELLED') THEN now() ELSE NULL END,"updatedAt"=now() WHERE id=$1''',
                order_id, payload.status,
            )
    return {"ok": True, "status": payload.status}


@router.patch("/api/v1/admin/my-stay/charges/{charge_id}/payment")
async def link_charge_payment(charge_id: uuid.UUID, payload: ChargePaymentPatch, request: Request, user=Depends(finance_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await _property(conn, user["property_code"])
            charge = await conn.fetchrow(
                '''SELECT id,"reservationId","amountKgs",status FROM reservation_charges WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                charge_id, prop["id"],
            )
            if not charge:
                raise HTTPException(status_code=404, detail="Charge not found")
            if charge["status"] != "OPEN":
                raise HTTPException(status_code=409, detail="Charge is not open")
            payment = await conn.fetchrow(
                '''SELECT id,"reservationId","amountKgs",status::text AS status FROM payments WHERE id=$1 FOR UPDATE''', payload.payment_id
            )
            if not payment or payment["status"] != "RECEIVED" or payment["reservationId"] != charge["reservationId"]:
                raise HTTPException(status_code=409, detail="Payment must be RECEIVED and belong to the same reservation")
            already_used = await conn.fetchval('SELECT 1 FROM reservation_charges WHERE "paymentId"=$1 AND status=\'PAID\' AND id<>$2', payload.payment_id, charge_id)
            if already_used:
                raise HTTPException(status_code=409, detail="Payment is already linked to another ancillary charge")
            if payment["amountKgs"] < charge["amountKgs"]:
                raise HTTPException(status_code=409, detail="Payment amount is lower than charge amount")
            await conn.execute(
                '''UPDATE reservation_charges SET status='PAID',"paymentId"=$2,"paidAt"=now(),"updatedAt"=now() WHERE id=$1''', charge_id, payload.payment_id
            )
    return {"ok": True, "status": "PAID"}
