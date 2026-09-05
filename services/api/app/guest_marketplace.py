import uuid
from typing import Any

from fastapi import APIRouter, Cookie, HTTPException, Request, status

from .guest_os import GUEST_COOKIE
from .guest_requests import authorized_context
from .kitchen import GuestOrderCreate, audit, insert_order

router = APIRouter(prefix="/api/v1/guest-os", tags=["guest-marketplace"])


async def _published_menu_rows(conn, property_id: uuid.UUID):
    return await conn.fetch(
        '''SELECT id,code,category,"nameRu","nameKg","nameEn","priceKgs","isActive","isDraft","sortOrder"
           FROM kitchen_menu_items
           WHERE "propertyId"=$1 AND "isActive"=true AND "isDraft"=false
           ORDER BY "sortOrder",category,"nameRu"''',
        property_id,
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
    }


@router.get("/rooms/{token}/kitchen/menu")
async def guest_marketplace_menu(
    token: str,
    request: Request,
    tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE),
):
    async with request.app.state.db.acquire() as conn:
        qr, _, _ = await authorized_context(conn, token, tc_guest_session)
        rows = await _published_menu_rows(conn, qr["propertyId"])
    return {
        "items": [_menu_item(row) for row in rows],
        "currency": "KGS",
        "truth": "Only active non-draft Kitchen menu items are guest-visible.",
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

            requested_ids = {item.menu_item_id for item in payload.items}
            published_rows = await conn.fetch(
                '''SELECT id FROM kitchen_menu_items
                   WHERE "propertyId"=$1 AND "isActive"=true AND "isDraft"=false
                     AND id=ANY($2::uuid[])''',
                qr["propertyId"], list(requested_ids),
            )
            published_ids = {row["id"] for row in published_rows}
            if requested_ids != published_ids:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "GUEST_MARKETPLACE_ITEM_NOT_PUBLISHED",
                        "message": "One or more menu items are draft, inactive or unavailable to guests.",
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
                f"{order_number} · {len(payload.items)} позиций · {total} KGS",
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
                    "published_menu_only": True,
                },
            )
            await conn.execute(
                '''INSERT INTO guest_history_events (
                     id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt"
                   ) VALUES ($1,$2,$3,$4,'KITCHEN_ORDER_CREATED','GUEST_MARKETPLACE',
                     jsonb_build_object('order_id',$5::text,'order_number',$6::text,'task_id',$7::text,'total_kgs',$8::int),now(),now())''',
                uuid.uuid4(),
                qr["propertyId"],
                stay["guestId"],
                stay["stayId"],
                str(order_id),
                order_number,
                str(task_id),
                total,
            )

    return {
        "id": str(order_id),
        "order_number": order_number,
        "task_id": str(task_id),
        "status": "NEW",
        "total_kgs": total,
        "financial_posting": "NONE_AUTOMATIC",
        "published_menu_only": True,
    }
