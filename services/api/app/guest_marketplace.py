import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Cookie, HTTPException, Request, status

from .guest_os import GUEST_COOKIE
from .guest_requests import authorized_context
from .kitchen import GuestOrderCreate, audit, insert_order

router = APIRouter(prefix="/api/v1/guest-os", tags=["guest-marketplace"])


async def _hotel_local_date(conn, property_id: uuid.UUID):
    timezone_name = await conn.fetchval('SELECT timezone FROM properties WHERE id=$1', property_id)
    try:
        tz = ZoneInfo(timezone_name or "Asia/Bishkek")
    except Exception:
        tz = ZoneInfo("Asia/Bishkek")
    return datetime.now(tz).date()


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


@router.get("/rooms/{token}/kitchen/menu")
async def guest_marketplace_menu(
    token: str,
    request: Request,
    tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE),
):
    async with request.app.state.db.acquire() as conn:
        qr, _, _ = await authorized_context(conn, token, tc_guest_session)
        service_date = await _hotel_local_date(conn, qr["propertyId"])
        configured = int(
            await conn.fetchval(
                '''SELECT count(*)::int FROM kitchen_menu_availability
                   WHERE "propertyId"=$1 AND "serviceDate"=$2''',
                qr["propertyId"], service_date,
            )
            or 0
        ) > 0
        rows = await _published_menu_rows(conn, qr["propertyId"], service_date)
    return {
        "service_date": service_date,
        "schedule_configured": configured,
        "items": [_menu_item(row) for row in rows],
        "currency": "KGS",
        "truth": "Guest menu is hotel-local-day specific: active + non-draft + explicitly published + available + not sold out.",
    }


@router.post("/rooms/{token}/kitchen/orders", status_code=status.HTTP_201_CREATED)
async def create_guest_marketplace_order(
    token: str,
    payload: GuestOrderCreate,
    request: Request,
    tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            qr, stay, session = await authorized_context(conn, token, tc_guest_session)
            service_date = await _hotel_local_date(conn, qr["propertyId"])

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
                     AND ($4::text IS NULL OR a."mealType"=$4)
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
                        "message": "One or more menu items are not published, are sold out or are unavailable for this service day.",
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

            order_id, order_number, total = await insert_order(
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
            await conn.execute(
                'UPDATE operational_tasks SET description=$2 WHERE id=$1',
                task_id,
                f"{order_number} · {len(payload.items)} позиций · {total} KGS · меню {service_date}",
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
                    "total_kgs": total,
                    "guest_session_id": str(session["id"]),
                    "service_date": str(service_date),
                    "day_published_menu_only": True,
                },
            )
            await conn.execute(
                '''INSERT INTO guest_history_events (
                     id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt"
                   ) VALUES ($1,$2,$3,$4,'KITCHEN_ORDER_CREATED','GUEST_MARKETPLACE',
                     jsonb_build_object('order_id',$5::text,'order_number',$6::text,'task_id',$7::text,'total_kgs',$8::int,'service_date',$9::text),now(),now())''',
                uuid.uuid4(),
                qr["propertyId"],
                stay["guestId"],
                stay["stayId"],
                str(order_id),
                order_number,
                str(task_id),
                total,
                str(service_date),
            )

    return {
        "id": str(order_id),
        "order_number": order_number,
        "task_id": str(task_id),
        "status": "NEW",
        "service_date": service_date,
        "total_kgs": total,
        "financial_posting": "NONE_AUTOMATIC",
        "day_published_menu_only": True,
    }
