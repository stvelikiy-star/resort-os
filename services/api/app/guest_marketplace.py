import uuid
from datetime import datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Cookie, HTTPException, Request, status
from pydantic import BaseModel, Field

from .guest_os import GUEST_COOKIE
from .guest_requests import authorized_context
from .guest_service_settings import load_settings
from .kitchen import OrderItemInput, audit, insert_order

router = APIRouter(prefix="/api/v1/guest-os", tags=["guest-marketplace"])


class GuestMarketplaceOrderCreate(BaseModel):
    guest_count: int = Field(default=1, ge=1, le=20)
    meal_type: Literal["BREAKFAST", "LUNCH", "DINNER", "OTHER"]
    delivery_to_room: bool = True
    notes: str | None = Field(default=None, max_length=1000)
    items: list[OrderItemInput] = Field(min_length=1, max_length=30)


async def _hotel_timezone(conn, property_id: uuid.UUID) -> ZoneInfo:
    timezone_name = await conn.fetchval('SELECT timezone FROM properties WHERE id=$1', property_id)
    try:
        return ZoneInfo(timezone_name or "Asia/Bishkek")
    except Exception:
        return ZoneInfo("Asia/Bishkek")


async def _hotel_local_date(conn, property_id: uuid.UUID):
    return datetime.now(await _hotel_timezone(conn, property_id)).date()


async def _published_menu_rows(conn, property_id: uuid.UUID, service_date):
    return await conn.fetch(
        '''SELECT m.id,m.code,m.category,m."nameRu",m."nameKg",m."nameEn",m."priceKgs",m."isActive",m."isDraft",m."sortOrder",
                  array_agg(DISTINCT a."mealType" ORDER BY a."mealType") AS meal_types
           FROM kitchen_menu_items m
           JOIN kitchen_menu_availability a ON a."menuItemId"=m.id AND a."propertyId"=m."propertyId"
           WHERE m."propertyId"=$1 AND m."isActive"=true AND m."isDraft"=false
             AND a."serviceDate"=$2 AND a."isAvailable"=true AND a."soldOut"=false
           GROUP BY m.id
           ORDER BY m."sortOrder",m.category,m."nameRu"''',
        property_id, service_date,
    )


def _menu_item(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "code": row["code"],
        "category": row["category"],
        "name_ru": row["nameRu"],
        "name_kg": row["nameKg"],
        "name_en": row["nameEn"],
        "price_kgs": row["priceKgs"],
        "is_active": row["isActive"],
        "is_draft": row["isDraft"],
        "sort_order": row["sortOrder"],
        "meal_types": list(row["meal_types"] or []),
    }


def _meal_window(now: datetime, service_date, meal_type: str, settings: dict[str, Any], tz: ZoneInfo) -> dict[str, Any]:
    if meal_type == "OTHER":
        return {
            "configured": True,
            "open": True,
            "start": None,
            "cutoff_at": None,
            "cutoff_minutes": settings["meal_order_cutoff_minutes"],
        }
    key = {
        "BREAKFAST": "breakfast_start",
        "LUNCH": "lunch_start",
        "DINNER": "dinner_start",
    }[meal_type]
    start = settings[key]
    if start is None:
        return {
            "configured": False,
            "open": False,
            "start": None,
            "cutoff_at": None,
            "cutoff_minutes": settings["meal_order_cutoff_minutes"],
        }
    meal_at = datetime.combine(service_date, start, tzinfo=tz)
    cutoff_at = meal_at - timedelta(minutes=settings["meal_order_cutoff_minutes"])
    return {
        "configured": True,
        "open": now <= cutoff_at,
        "start": start.strftime("%H:%M"),
        "cutoff_at": cutoff_at.isoformat(),
        "cutoff_minutes": settings["meal_order_cutoff_minutes"],
    }


@router.get("/rooms/{token}/kitchen/menu")
async def guest_marketplace_menu(
    token: str,
    request: Request,
    tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE),
):
    async with request.app.state.db.acquire() as conn:
        qr, _, _ = await authorized_context(conn, token, tc_guest_session)
        tz = await _hotel_timezone(conn, qr["propertyId"])
        now = datetime.now(tz)
        service_date = now.date()
        configured = int(
            await conn.fetchval(
                '''SELECT count(*)::int FROM kitchen_menu_availability
                   WHERE "propertyId"=$1 AND "serviceDate"=$2''',
                qr["propertyId"], service_date,
            )
            or 0
        ) > 0
        rows = await _published_menu_rows(conn, qr["propertyId"], service_date)
        settings = await load_settings(conn, qr["propertyId"])

    meal_ordering = {
        meal: _meal_window(now, service_date, meal, settings, tz)
        for meal in ("BREAKFAST", "LUNCH", "DINNER", "OTHER")
    }
    return {
        "service_date": service_date,
        "schedule_configured": configured,
        "items": [_menu_item(row) for row in rows],
        "currency": "KGS",
        "meal_ordering": meal_ordering,
        "delivery": {
            "enabled": settings["room_delivery_enabled"],
            "fee_kgs": settings["room_delivery_fee_kgs"],
        },
        "truth": "Guest menu is hotel-local-day specific. Breakfast/lunch/dinner orders close at the owner-configured meal start minus the configured cutoff (60 minutes by owner rule).",
    }


@router.post("/rooms/{token}/kitchen/orders", status_code=status.HTTP_201_CREATED)
async def create_guest_marketplace_order(
    token: str,
    payload: GuestMarketplaceOrderCreate,
    request: Request,
    tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            qr, stay, session = await authorized_context(conn, token, tc_guest_session)
            tz = await _hotel_timezone(conn, qr["propertyId"])
            now = datetime.now(tz)
            service_date = now.date()
            settings = await load_settings(conn, qr["propertyId"])
            meal_window = _meal_window(now, service_date, payload.meal_type, settings, tz)

            if payload.meal_type in {"BREAKFAST", "LUNCH", "DINNER"} and not meal_window["configured"]:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "GUEST_MEAL_TIME_NOT_CONFIGURED",
                        "meal_type": payload.meal_type,
                        "message": "Management must configure the meal start time before Guest OS can accept this meal order.",
                    },
                )
            if not meal_window["open"]:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "GUEST_MEAL_ORDER_CLOSED",
                        "meal_type": payload.meal_type,
                        "meal_start": meal_window["start"],
                        "cutoff_at": meal_window["cutoff_at"],
                        "cutoff_minutes": meal_window["cutoff_minutes"],
                        "message": "Guest meal orders close one hour before the configured meal start.",
                    },
                )
            if payload.delivery_to_room and not settings["room_delivery_enabled"]:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "ROOM_DELIVERY_DISABLED", "message": "Room delivery is currently disabled by management."},
                )

            schedule_count = int(
                await conn.fetchval(
                    '''SELECT count(*)::int FROM kitchen_menu_availability
                       WHERE "propertyId"=$1 AND "serviceDate"=$2''',
                    qr["propertyId"], service_date,
                )
                or 0
            )
            if schedule_count == 0:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "GUEST_MARKETPLACE_MENU_NOT_PUBLISHED_TODAY",
                        "service_date": str(service_date),
                        "message": "The hotel has not published today's guest menu yet.",
                    },
                )

            requested_ids = {item.menu_item_id for item in payload.items}
            published_rows = await conn.fetch(
                '''SELECT m.id,a."mealType"
                   FROM kitchen_menu_items m
                   JOIN kitchen_menu_availability a ON a."menuItemId"=m.id AND a."propertyId"=m."propertyId"
                   WHERE m."propertyId"=$1 AND m."isActive"=true AND m."isDraft"=false
                     AND a."serviceDate"=$2 AND a."isAvailable"=true AND a."soldOut"=false
                     AND m.id=ANY($3::uuid[])
                     AND a."mealType"=$4
                   FOR SHARE OF m,a''',
                qr["propertyId"], service_date, list(requested_ids), payload.meal_type,
            )
            published_ids = {row["id"] for row in published_rows}
            if requested_ids != published_ids:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "GUEST_MARKETPLACE_ITEM_NOT_AVAILABLE_TODAY",
                        "service_date": str(service_date),
                        "meal_type": payload.meal_type,
                        "message": "One or more menu items are not published, are sold out or are unavailable for this meal.",
                    },
                )

            task_id = uuid.uuid4()
            title = f"Заказ питания · №{qr['room_code']}"
            await conn.execute(
                '''INSERT INTO operational_tasks (
                     id,"propertyId","roomId","reservationId","stayId",type,status,priority,title,description,"serviceCode",
                     "createdByType","createdById",source,"createdAt","updatedAt"
                   ) VALUES ($1,$2,$3,$4,$5,'GUEST_REQUEST','OPEN','NORMAL',$6,$7,'MEALS','GUEST',$8,'GUEST_MARKETPLACE',now(),now())''',
                task_id,
                qr["propertyId"],
                qr["roomId"],
                stay["reservation_id"],
                stay["stayId"],
                title,
                payload.notes,
                str(stay["guestId"]),
            )

            order_id, order_number, subtotal = await insert_order(
                conn,
                pid=qr["propertyId"],
                source="GUEST_OS",
                table_id=None,
                stay_id=stay["stayId"],
                reservation_id=stay["reservation_id"],
                room_id=qr["roomId"],
                guest_task_id=task_id,
                guest_count=payload.guest_count,
                meal_type=payload.meal_type,
                notes=payload.notes,
                opened_by_id=None,
                items=payload.items,
            )
            delivery_fee = settings["room_delivery_fee_kgs"] if payload.delivery_to_room else 0
            total = subtotal + delivery_fee
            await conn.execute(
                '''UPDATE kitchen_orders SET "subtotalKgs"=$2,"deliveryFeeKgs"=$3,"deliveryToRoom"=$4,
                     "totalKgs"=$5,"updatedAt"=now() WHERE id=$1''',
                order_id, subtotal, delivery_fee, payload.delivery_to_room, total,
            )
            delivery_label = f"доставка в номер +{delivery_fee} KGS" if payload.delivery_to_room else "без доставки"
            await conn.execute(
                'UPDATE operational_tasks SET description=$2 WHERE id=$1',
                task_id,
                f"{order_number} · {payload.meal_type} · {len(payload.items)} позиций · {subtotal} KGS + {delivery_label} · итог {total} KGS · меню {service_date}",
            )
            await audit(
                conn,
                qr["propertyId"],
                "GUEST",
                str(stay["guestId"]),
                "CREATE_GUEST_MARKETPLACE_ORDER",
                str(order_id),
                {
                    "order_number": order_number,
                    "subtotal_kgs": subtotal,
                    "delivery_fee_kgs": delivery_fee,
                    "delivery_to_room": payload.delivery_to_room,
                    "total_kgs": total,
                    "guest_session_id": str(session["id"]),
                    "service_date": str(service_date),
                    "meal_type": payload.meal_type,
                    "cutoff_at": meal_window["cutoff_at"],
                    "day_published_menu_only": True,
                },
            )
            await conn.execute(
                '''INSERT INTO guest_history_events (
                     id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt"
                   ) VALUES ($1,$2,$3,$4,'KITCHEN_ORDER_CREATED','GUEST_MARKETPLACE',
                     jsonb_build_object('order_id',$5::text,'order_number',$6::text,'task_id',$7::text,
                       'subtotal_kgs',$8::int,'delivery_fee_kgs',$9::int,'total_kgs',$10::int,
                       'delivery_to_room',$11::boolean,'service_date',$12::text,'meal_type',$13::text),now(),now())''',
                uuid.uuid4(),
                qr["propertyId"],
                stay["guestId"],
                stay["stayId"],
                str(order_id),
                order_number,
                str(task_id),
                subtotal,
                delivery_fee,
                total,
                payload.delivery_to_room,
                str(service_date),
                payload.meal_type,
            )

    return {
        "id": str(order_id),
        "order_number": order_number,
        "task_id": str(task_id),
        "status": "NEW",
        "service_date": service_date,
        "meal_type": payload.meal_type,
        "subtotal_kgs": subtotal,
        "delivery_to_room": payload.delivery_to_room,
        "delivery_fee_kgs": delivery_fee,
        "total_kgs": total,
        "financial_posting": "KITCHEN_ORDER_ONLY_NOT_RESERVATION_PAYMENT",
        "day_published_menu_only": True,
        "meal_order_cutoff": meal_window,
    }
