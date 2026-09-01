import uuid
from typing import Any, Literal

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from .auth import require_roles
from .guest_os import GUEST_COOKIE
from .guest_requests import authorized_context

admin_router = APIRouter(prefix="/api/v1/kitchen", tags=["kitchen"])
guest_router = APIRouter(prefix="/api/v1/guest-os", tags=["guest-kitchen"])
kitchen_access = require_roles("OWNER", "MANAGER", "DINING_STAFF")

DRAFT_MENU = [
    ("SYRNIKI", "BREAKFAST", "Сырники со сметаной", "Каймак кошулган сырник", "Syrniki with sour cream", 280, 10),
    ("OMELET", "BREAKFAST", "Омлет с овощами", "Жашылча кошулган омлет", "Vegetable omelette", 250, 20),
    ("PORRIDGE", "BREAKFAST", "Овсяная каша с фруктами", "Мөмөлүү сулу боткосу", "Oatmeal with fruit", 190, 30),
    ("SHORPO", "SOUP", "Шорпо", "Шорпо", "Shorpo soup", 340, 100),
    ("LENTIL_SOUP", "SOUP", "Чечевичный крем-суп", "Жасмык крем-шорпосу", "Lentil cream soup", 270, 110),
    ("FRESH_SALAD", "SALAD", "Свежий салат", "Жаңы жашылча салаты", "Fresh vegetable salad", 230, 200),
    ("CAESAR_CHICKEN", "SALAD", "Цезарь с курицей", "Тоок эти менен Цезарь", "Chicken Caesar salad", 390, 210),
    ("PLOV", "MAIN", "Плов", "Палоо", "Plov", 390, 300),
    ("KUURDAK", "MAIN", "Куурдак", "Куурдак", "Kuurdak", 490, 310),
    ("CHICKEN_CUTLET", "MAIN", "Куриная котлета с пюре", "Пюре менен тоок котлети", "Chicken cutlet with mashed potato", 360, 320),
    ("GRILLED_TROUT", "MAIN", "Форель на гриле", "Гриль форель", "Grilled trout", 650, 330),
    ("FRIES", "SIDE", "Картофель фри", "Фри картошка", "French fries", 220, 400),
    ("CHEESECAKE", "DESSERT", "Чизкейк", "Чизкейк", "Cheesecake", 290, 500),
    ("TEA_POT", "DRINK", "Чайник чая", "Чайнек чай", "Pot of tea", 150, 600),
    ("COFFEE", "DRINK", "Кофе", "Кофе", "Coffee", 180, 610),
]

ORDER_TRANSITIONS: dict[str, set[str]] = {
    "NEW": {"ACCEPTED", "CANCELLED"},
    "ACCEPTED": {"COOKING", "CANCELLED"},
    "COOKING": {"READY", "CANCELLED"},
    "READY": {"SERVED", "CANCELLED"},
    "SERVED": set(),
    "CANCELLED": set(),
}


class MenuPatch(BaseModel):
    category: str | None = None
    name_ru: str | None = Field(default=None, min_length=1, max_length=160)
    name_kg: str | None = Field(default=None, min_length=1, max_length=160)
    name_en: str | None = Field(default=None, min_length=1, max_length=160)
    price_kgs: int | None = Field(default=None, ge=0, le=100_000)
    is_active: bool | None = None
    is_draft: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=100_000)


class TableCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    seats: int = Field(ge=1, le=30)
    notes: str | None = Field(default=None, max_length=500)


class TablePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    seats: int | None = Field(default=None, ge=1, le=30)
    status: Literal["AVAILABLE", "RESERVED", "OCCUPIED", "CLEANING", "OUT_OF_SERVICE"] | None = None
    is_active: bool | None = None
    notes: str | None = Field(default=None, max_length=500)


class OrderItemInput(BaseModel):
    menu_item_id: uuid.UUID
    quantity: int = Field(ge=1, le=30)
    notes: str | None = Field(default=None, max_length=300)


class StaffOrderCreate(BaseModel):
    source: Literal["TABLE", "ROOM", "RECEPTION", "MANAGER"] = "TABLE"
    table_id: uuid.UUID | None = None
    stay_id: uuid.UUID | None = None
    room_code: str | None = Field(default=None, max_length=40)
    guest_count: int = Field(default=1, ge=1, le=30)
    meal_type: Literal["BREAKFAST", "LUNCH", "DINNER", "OTHER"] | None = None
    notes: str | None = Field(default=None, max_length=1000)
    items: list[OrderItemInput] = Field(min_length=1, max_length=50)


class GuestOrderCreate(BaseModel):
    guest_count: int = Field(default=1, ge=1, le=20)
    meal_type: Literal["BREAKFAST", "LUNCH", "DINNER", "OTHER"] | None = None
    notes: str | None = Field(default=None, max_length=1000)
    items: list[OrderItemInput] = Field(min_length=1, max_length=30)


class OrderStatusPatch(BaseModel):
    status: Literal["ACCEPTED", "COOKING", "READY", "SERVED", "CANCELLED"]


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


def menu_item(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]), "code": row["code"], "category": row["category"],
        "name_ru": row["nameRu"], "name_kg": row["nameKg"], "name_en": row["nameEn"],
        "price_kgs": row["priceKgs"], "is_active": row["isActive"], "is_draft": row["isDraft"],
        "sort_order": row["sortOrder"],
    }


async def load_menu_for_items(conn, pid: uuid.UUID, inputs: list[OrderItemInput]):
    ids = [item.menu_item_id for item in inputs]
    rows = await conn.fetch(
        '''SELECT id,code,"nameRu","priceKgs","isActive" FROM kitchen_menu_items
           WHERE "propertyId"=$1 AND id=ANY($2::uuid[]) FOR SHARE''',
        pid, ids,
    )
    by_id = {row["id"]: row for row in rows}
    if len(by_id) != len(set(ids)):
        raise HTTPException(status_code=422, detail={"code": "KITCHEN_MENU_ITEM_NOT_FOUND"})
    inactive = [str(item_id) for item_id, row in by_id.items() if not row["isActive"]]
    if inactive:
        raise HTTPException(status_code=409, detail={"code": "KITCHEN_MENU_ITEM_INACTIVE", "item_ids": inactive})
    return by_id


async def insert_order(
    conn,
    *,
    pid: uuid.UUID,
    source: str,
    table_id: uuid.UUID | None,
    stay_id: uuid.UUID | None,
    reservation_id: uuid.UUID | None,
    room_id: uuid.UUID | None,
    guest_task_id: uuid.UUID | None,
    guest_count: int,
    meal_type: str | None,
    notes: str | None,
    opened_by_id: uuid.UUID | None,
    items: list[OrderItemInput],
):
    menu = await load_menu_for_items(conn, pid, items)
    order_id = uuid.uuid4()
    order_number = f"K-{order_id.hex[:8].upper()}"
    total = sum(menu[item.menu_item_id]["priceKgs"] * item.quantity for item in items)
    await conn.execute(
        '''INSERT INTO kitchen_orders (
             id,"propertyId","orderNumber",status,source,"tableId","stayId","reservationId","roomId","guestTaskId",
             "guestCount","mealType",notes,"totalKgs","openedById","openedAt","createdAt","updatedAt"
           ) VALUES ($1,$2,$3,'NEW',$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,now(),now(),now())''',
        order_id, pid, order_number, source, table_id, stay_id, reservation_id, room_id, guest_task_id,
        guest_count, meal_type, notes, total, opened_by_id,
    )
    for item in items:
        row = menu[item.menu_item_id]
        await conn.execute(
            '''INSERT INTO kitchen_order_items (
                 id,"orderId","menuItemId",quantity,"unitPriceKgs","lineTotalKgs",status,notes,"createdAt","updatedAt"
               ) VALUES ($1,$2,$3,$4,$5,$6,'NEW',$7,now(),now())''',
            uuid.uuid4(), order_id, item.menu_item_id, item.quantity, row["priceKgs"],
            row["priceKgs"] * item.quantity, item.notes,
        )
    if table_id:
        await conn.execute(
            '''UPDATE kitchen_tables SET status='OCCUPIED',"updatedAt"=now()
               WHERE id=$1 AND "propertyId"=$2 AND "isActive"=true''', table_id, pid,
        )
    return order_id, order_number, total


async def audit(conn, pid, actor_type: str, actor_id: str | None, action: str, resource_id: str, payload: dict[str, Any]):
    await conn.execute(
        '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
           VALUES ($1,$2,$3,$4,$5,'KitchenOrder',$6,'KITCHEN','SUCCESS',$7::jsonb,now())''',
        uuid.uuid4(), pid, actor_type, actor_id, action, resource_id,
        __import__("json").dumps({**payload, "financial_effect": "NONE_AUTOMATIC", "reservation_total_effect": "NONE"}),
    )


@admin_router.post("/menu/bootstrap-draft")
async def bootstrap_draft_menu(request: Request, user: dict[str, Any] = Depends(kitchen_access)):
    created = 0
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            for code, category, ru, kg, en, price, sort_order in DRAFT_MENU:
                result = await conn.execute(
                    '''INSERT INTO kitchen_menu_items (
                         id,"propertyId",code,category,"nameRu","nameKg","nameEn","priceKgs","isActive","isDraft","sortOrder","createdAt","updatedAt"
                       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,true,true,$9,now(),now())
                       ON CONFLICT ("propertyId",code) DO NOTHING''',
                    uuid.uuid4(), pid, code, category, ru, kg, en, price, sort_order,
                )
                created += int(result.endswith("1"))
    return {"created": created, "draft": True, "truth": "Draft menu is replaceable from Kitchen Admin."}


@admin_router.get("/menu")
async def list_menu(request: Request, user: dict[str, Any] = Depends(kitchen_access)):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        rows = await conn.fetch(
            '''SELECT id,code,category,"nameRu","nameKg","nameEn","priceKgs","isActive","isDraft","sortOrder"
               FROM kitchen_menu_items WHERE "propertyId"=$1 ORDER BY "sortOrder",category,"nameRu"''', pid,
        )
    return {"items": [menu_item(row) for row in rows]}


@admin_router.patch("/menu/{item_id}")
async def patch_menu(item_id: uuid.UUID, payload: MenuPatch, request: Request, user: dict[str, Any] = Depends(kitchen_access)):
    allowed_categories = {"BREAKFAST", "SOUP", "SALAD", "MAIN", "SIDE", "DESSERT", "DRINK"}
    if payload.category is not None and payload.category not in allowed_categories:
        raise HTTPException(status_code=422, detail="Unknown menu category")
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            row = await conn.fetchrow(
                '''UPDATE kitchen_menu_items SET
                     category=COALESCE($3,category),"nameRu"=COALESCE($4,"nameRu"),"nameKg"=COALESCE($5,"nameKg"),
                     "nameEn"=COALESCE($6,"nameEn"),"priceKgs"=COALESCE($7,"priceKgs"),"isActive"=COALESCE($8,"isActive"),
                     "isDraft"=COALESCE($9,"isDraft"),"sortOrder"=COALESCE($10,"sortOrder"),"updatedAt"=now()
                   WHERE id=$1 AND "propertyId"=$2
                   RETURNING id,code,category,"nameRu","nameKg","nameEn","priceKgs","isActive","isDraft","sortOrder"''',
                item_id, pid, payload.category, payload.name_ru, payload.name_kg, payload.name_en,
                payload.price_kgs, payload.is_active, payload.is_draft, payload.sort_order,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Menu item not found")
    return menu_item(row)


@admin_router.get("/tables")
async def list_tables(request: Request, user: dict[str, Any] = Depends(kitchen_access)):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        rows = await conn.fetch(
            '''SELECT id,code,name,seats,status,"isActive",notes FROM kitchen_tables
               WHERE "propertyId"=$1 ORDER BY code''', pid,
        )
    return {"items": [{"id": str(r["id"]), "code": r["code"], "name": r["name"], "seats": r["seats"], "status": r["status"], "is_active": r["isActive"], "notes": r["notes"]} for r in rows]}


@admin_router.post("/tables", status_code=status.HTTP_201_CREATED)
async def create_table(payload: TableCreate, request: Request, user: dict[str, Any] = Depends(kitchen_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            try:
                row = await conn.fetchrow(
                    '''INSERT INTO kitchen_tables (id,"propertyId",code,name,seats,status,"isActive",notes,"createdAt","updatedAt")
                       VALUES ($1,$2,$3,$4,$5,'AVAILABLE',true,$6,now(),now())
                       RETURNING id,code,name,seats,status,"isActive",notes''',
                    uuid.uuid4(), pid, payload.code.strip().upper(), payload.name.strip(), payload.seats, payload.notes,
                )
            except Exception as exc:
                if "unique" in str(exc).lower():
                    raise HTTPException(status_code=409, detail="Table code already exists") from exc
                raise
    return {"id": str(row["id"]), "code": row["code"], "name": row["name"], "seats": row["seats"], "status": row["status"]}


@admin_router.patch("/tables/{table_id}")
async def patch_table(table_id: uuid.UUID, payload: TablePatch, request: Request, user: dict[str, Any] = Depends(kitchen_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            row = await conn.fetchrow(
                '''UPDATE kitchen_tables SET name=COALESCE($3,name),seats=COALESCE($4,seats),status=COALESCE($5,status),
                     "isActive"=COALESCE($6,"isActive"),notes=COALESCE($7,notes),"updatedAt"=now()
                   WHERE id=$1 AND "propertyId"=$2 RETURNING id,code,name,seats,status,"isActive",notes''',
                table_id, pid, payload.name, payload.seats, payload.status, payload.is_active, payload.notes,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Table not found")
    return {"id": str(row["id"]), "code": row["code"], "name": row["name"], "seats": row["seats"], "status": row["status"], "is_active": row["isActive"]}


ORDER_SELECT = '''
SELECT o.id,o."orderNumber",o.status,o.source,o."guestCount",o."mealType",o.notes,o."totalKgs",o."openedAt",o."completedAt",
       t.code AS table_code,t.name AS table_name,r.code AS room_code,
       COALESCE(jsonb_agg(jsonb_build_object(
         'id',i.id::text,'menu_item_id',m.id::text,'name_ru',m."nameRu",'name_kg',m."nameKg",'name_en',m."nameEn",
         'quantity',i.quantity,'unit_price_kgs',i."unitPriceKgs",'line_total_kgs',i."lineTotalKgs",'status',i.status,'notes',i.notes
       ) ORDER BY i."createdAt") FILTER (WHERE i.id IS NOT NULL),'[]'::jsonb) AS items
FROM kitchen_orders o
LEFT JOIN kitchen_tables t ON t.id=o."tableId"
LEFT JOIN rooms r ON r.id=o."roomId"
LEFT JOIN kitchen_order_items i ON i."orderId"=o.id
LEFT JOIN kitchen_menu_items m ON m.id=i."menuItemId"
'''


def order_json(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]), "order_number": row["orderNumber"], "status": row["status"], "source": row["source"],
        "guest_count": row["guestCount"], "meal_type": row["mealType"], "notes": row["notes"], "total_kgs": row["totalKgs"],
        "table_code": row["table_code"], "table_name": row["table_name"], "room_code": row["room_code"],
        "opened_at": row["openedAt"], "completed_at": row["completedAt"], "items": row["items"],
        "financial_posting": "NONE_AUTOMATIC",
    }


@admin_router.get("/orders")
async def list_orders(request: Request, order_status: str = Query(default="ACTIVE", alias="status"), user: dict[str, Any] = Depends(kitchen_access)):
    if order_status not in {"ACTIVE", "ALL", "NEW", "ACCEPTED", "COOKING", "READY", "SERVED", "CANCELLED"}:
        raise HTTPException(status_code=422, detail="Unknown order status")
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        rows = await conn.fetch(
            ORDER_SELECT + ''' WHERE o."propertyId"=$1 AND ($2='ALL' OR ($2='ACTIVE' AND o.status IN ('NEW','ACCEPTED','COOKING','READY')) OR o.status=$2)
              GROUP BY o.id,t.code,t.name,r.code ORDER BY o."openedAt" ASC LIMIT 300''', pid, order_status,
        )
    return {"items": [order_json(row) for row in rows]}


@admin_router.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_staff_order(payload: StaffOrderCreate, request: Request, user: dict[str, Any] = Depends(kitchen_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            table_id = payload.table_id
            if table_id:
                exists = await conn.fetchval('SELECT 1 FROM kitchen_tables WHERE id=$1 AND "propertyId"=$2 AND "isActive"=true', table_id, pid)
                if not exists:
                    raise HTTPException(status_code=422, detail="Active table not found")
            stay_id = payload.stay_id
            reservation_id = None
            room_id = None
            if stay_id:
                stay = await conn.fetchrow('SELECT id,"reservationId" FROM stays WHERE id=$1 AND "propertyId"=$2 AND status=\'ACTIVE\'', stay_id, pid)
                if not stay:
                    raise HTTPException(status_code=422, detail="Active stay not found")
                reservation_id = stay["reservationId"]
                room_id = await conn.fetchval('SELECT "roomId" FROM room_assignments WHERE "stayId"=$1 AND "endedAt" IS NULL ORDER BY "startedAt" DESC LIMIT 1', stay_id)
            elif payload.room_code:
                room_id = await conn.fetchval('SELECT id FROM rooms WHERE "propertyId"=$1 AND code=$2', pid, payload.room_code.strip())
                if not room_id:
                    raise HTTPException(status_code=422, detail="Room not found")
            order_id, order_number, total = await insert_order(
                conn, pid=pid, source=payload.source, table_id=table_id, stay_id=stay_id, reservation_id=reservation_id,
                room_id=room_id, guest_task_id=None, guest_count=payload.guest_count, meal_type=payload.meal_type,
                notes=payload.notes, opened_by_id=uuid.UUID(user["id"]), items=payload.items,
            )
            await audit(conn, pid, "STAFF", user["id"], "CREATE_KITCHEN_ORDER", str(order_id), {"order_number": order_number, "total_kgs": total, "source": payload.source})
    return {"id": str(order_id), "order_number": order_number, "status": "NEW", "total_kgs": total, "financial_posting": "NONE_AUTOMATIC"}


@admin_router.patch("/orders/{order_id}/status")
async def patch_order_status(order_id: uuid.UUID, payload: OrderStatusPatch, request: Request, user: dict[str, Any] = Depends(kitchen_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            row = await conn.fetchrow('SELECT id,status,"tableId","guestTaskId","orderNumber" FROM kitchen_orders WHERE id=$1 AND "propertyId"=$2 FOR UPDATE', order_id, pid)
            if not row:
                raise HTTPException(status_code=404, detail="Kitchen order not found")
            if payload.status not in ORDER_TRANSITIONS[row["status"]]:
                raise HTTPException(status_code=409, detail={"code": "KITCHEN_ORDER_INVALID_TRANSITION", "from": row["status"], "to": payload.status})
            await conn.execute(
                '''UPDATE kitchen_orders SET status=$2,"acceptedAt"=CASE WHEN $2='ACCEPTED' THEN COALESCE("acceptedAt",now()) ELSE "acceptedAt" END,
                     "readyAt"=CASE WHEN $2='READY' THEN COALESCE("readyAt",now()) ELSE "readyAt" END,
                     "completedAt"=CASE WHEN $2 IN ('SERVED','CANCELLED') THEN now() ELSE "completedAt" END,"updatedAt"=now() WHERE id=$1''',
                order_id, payload.status,
            )
            item_status = {"ACCEPTED": "NEW", "COOKING": "COOKING", "READY": "READY", "SERVED": "SERVED", "CANCELLED": "CANCELLED"}[payload.status]
            await conn.execute('UPDATE kitchen_order_items SET status=$2,"updatedAt"=now() WHERE "orderId"=$1 AND status<>\'CANCELLED\'', order_id, item_status)
            if row["guestTaskId"]:
                task_status = "DONE" if payload.status == "SERVED" else "CANCELLED" if payload.status == "CANCELLED" else "IN_PROGRESS"
                await conn.execute(
                    '''UPDATE operational_tasks SET status=$2::"OperationalTaskStatus","completedAt"=CASE WHEN $2 IN ('DONE','CANCELLED') THEN now() ELSE NULL END,"updatedAt"=now() WHERE id=$1''',
                    row["guestTaskId"], task_status,
                )
            if row["tableId"] and payload.status in {"SERVED", "CANCELLED"}:
                other = await conn.fetchval(
                    '''SELECT 1 FROM kitchen_orders WHERE "tableId"=$1 AND id<>$2 AND status IN ('NEW','ACCEPTED','COOKING','READY') LIMIT 1''', row["tableId"], order_id,
                )
                if not other:
                    await conn.execute('UPDATE kitchen_tables SET status=\'AVAILABLE\',"updatedAt"=now() WHERE id=$1', row["tableId"])
            await audit(conn, pid, "STAFF", user["id"], "UPDATE_KITCHEN_ORDER_STATUS", str(order_id), {"order_number": row["orderNumber"], "from": row["status"], "to": payload.status})
    return {"id": str(order_id), "status": payload.status}


@guest_router.get("/rooms/{token}/kitchen/menu")
async def guest_menu(token: str, request: Request, tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE)):
    async with request.app.state.db.acquire() as conn:
        qr, _, _ = await authorized_context(conn, token, tc_guest_session)
        rows = await conn.fetch(
            '''SELECT id,code,category,"nameRu","nameKg","nameEn","priceKgs","isActive","isDraft","sortOrder"
               FROM kitchen_menu_items WHERE "propertyId"=$1 AND "isActive"=true ORDER BY "sortOrder",category,"nameRu"''', qr["propertyId"],
        )
    return {"items": [menu_item(row) for row in rows], "currency": "KGS"}


@guest_router.post("/rooms/{token}/kitchen/orders", status_code=status.HTTP_201_CREATED)
async def create_guest_order(token: str, payload: GuestOrderCreate, request: Request, tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            qr, stay, session = await authorized_context(conn, token, tc_guest_session)
            task_id = uuid.uuid4()
            title = f"Заказ питания · №{qr['room_code']}"
            await conn.execute(
                '''INSERT INTO operational_tasks (
                     id,"propertyId","roomId","reservationId","stayId",type,status,priority,title,description,"serviceCode",
                     "createdByType","createdById",source,"createdAt","updatedAt"
                   ) VALUES ($1,$2,$3,$4,$5,'GUEST_REQUEST','OPEN','NORMAL',$6,$7,'MEALS','GUEST',$8,'GUEST_OS_MEALS',now(),now())''',
                task_id, qr["propertyId"], qr["roomId"], stay["reservation_id"], stay["stayId"], title,
                payload.notes, str(stay["guestId"]),
            )
            order_id, order_number, total = await insert_order(
                conn, pid=qr["propertyId"], source="GUEST_OS", table_id=None, stay_id=stay["stayId"],
                reservation_id=stay["reservation_id"], room_id=qr["roomId"], guest_task_id=task_id,
                guest_count=payload.guest_count, meal_type=payload.meal_type, notes=payload.notes,
                opened_by_id=None, items=payload.items,
            )
            await conn.execute('UPDATE operational_tasks SET description=$2 WHERE id=$1', task_id, f"{order_number} · {len(payload.items)} позиций · {total} KGS")
            await audit(conn, qr["propertyId"], "GUEST", str(stay["guestId"]), "CREATE_KITCHEN_ORDER", str(order_id), {"order_number": order_number, "total_kgs": total, "guest_session_id": str(session["id"])})
            await conn.execute(
                '''INSERT INTO guest_history_events (id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt")
                   VALUES ($1,$2,$3,$4,'KITCHEN_ORDER_CREATED','GUEST_OS',jsonb_build_object('order_id',$5::text,'order_number',$6::text,'task_id',$7::text,'total_kgs',$8::int),now(),now())''',
                uuid.uuid4(), qr["propertyId"], stay["guestId"], stay["stayId"], str(order_id), order_number, str(task_id), total,
            )
    return {"id": str(order_id), "order_number": order_number, "task_id": str(task_id), "status": "NEW", "total_kgs": total, "financial_posting": "NONE_AUTOMATIC"}
