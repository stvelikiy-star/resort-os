from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .auth import require_roles
from .folio import ensure_kitchen_order_charge

router = APIRouter(prefix="/api/v1/dining", tags=["dining-folio"])
access = require_roles("OWNER", "MANAGER", "RECEPTION", "DINING_STAFF")
MANAGEMENT_ROLES = {"OWNER", "MANAGER", "RECEPTION"}


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


def item(row: Any) -> dict[str, Any]:
    stay_active = row["stay_status"] == "ACTIVE"
    return {
        "id": str(row["id"]),
        "order_number": row["orderNumber"],
        "status": row["status"],
        "source": row["source"],
        "table_code": row["table_code"],
        "room_code": row["room_code"],
        "waiter_id": str(row["waiterId"]) if row["waiterId"] else None,
        "waiter_name": row["waiter_name"],
        "stay_id": str(row["stayId"]) if row["stayId"] else None,
        "reservation_id": str(row["reservationId"]) if row["reservationId"] else None,
        "stay_status": row["stay_status"],
        "guest_name": row["guest_name"],
        "total_kgs": int(row["totalKgs"]),
        "folio_charge_id": str(row["folioChargeId"]) if row["folioChargeId"] else None,
        "eligible_to_post": bool(
            row["stayId"]
            and row["reservationId"]
            and stay_active
            and row["status"] != "CANCELLED"
        ),
        "financial_truth": "FOLIO_CHARGE_NOT_PAYMENT" if row["folioChargeId"] else "NOT_POSTED",
    }


ORDER_SELECT = '''
SELECT o.id,o."orderNumber",o.status,o.source,o."tableId",o."roomId",o."waiterId",o."stayId",o."reservationId",
       o."totalKgs",o."folioChargeId",o."openedAt",t.code AS table_code,r.code AS room_code,
       u."displayName" AS waiter_name,s.status::text AS stay_status,
       trim(concat_ws(' ',g."firstName",g."lastName")) AS guest_name
FROM kitchen_orders o
LEFT JOIN kitchen_tables t ON t.id=o."tableId"
LEFT JOIN rooms r ON r.id=o."roomId"
LEFT JOIN staff_users u ON u.id=o."waiterId"
LEFT JOIN stays s ON s.id=o."stayId"
LEFT JOIN guests g ON g.id=s."guestId"
'''


@router.get("/folio-orders")
async def folio_orders(
    request: Request,
    user: dict[str, Any] = Depends(access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        rows = await conn.fetch(
            ORDER_SELECT
            + ''' WHERE o."propertyId"=$1
                  AND o."stayId" IS NOT NULL AND o."reservationId" IS NOT NULL
                  AND o.status<>'CANCELLED'
                  AND ($2::boolean OR o."waiterId"=$3)
                  ORDER BY CASE WHEN o."folioChargeId" IS NULL THEN 0 ELSE 1 END,o."openedAt" DESC
                  LIMIT 100''',
            pid,
            user["role"] in MANAGEMENT_ROLES,
            uuid.UUID(user["id"]),
        )
    return {
        "items": [item(row) for row in rows],
        "truth": "Posting a restaurant order to a room creates an OPEN folio charge only. It never creates or confirms a Payment.",
    }


@router.post("/orders/{order_id}/folio", status_code=status.HTTP_201_CREATED)
async def post_order_to_folio(
    order_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            order = await conn.fetchrow(
                '''SELECT o.id,o.status,o."waiterId",o."stayId",o."reservationId",o."folioChargeId",
                          s.status::text AS stay_status
                   FROM kitchen_orders o
                   LEFT JOIN stays s ON s.id=o."stayId"
                   WHERE o.id=$1 AND o."propertyId"=$2 FOR UPDATE OF o''',
                order_id,
                pid,
            )
            if not order:
                raise HTTPException(status_code=404, detail="Kitchen order not found")
            if user["role"] == "DINING_STAFF" and order["waiterId"] != uuid.UUID(user["id"]):
                raise HTTPException(
                    status_code=403,
                    detail={"code": "DINING_FOLIO_ORDER_NOT_ASSIGNED_TO_WAITER"},
                )
            if order["status"] == "CANCELLED":
                raise HTTPException(status_code=409, detail={"code": "DINING_FOLIO_CANCELLED_ORDER"})
            if not order["stayId"] or not order["reservationId"]:
                raise HTTPException(status_code=409, detail={"code": "KITCHEN_ORDER_NOT_LINKED_TO_RESERVATION"})
            if order["stay_status"] != "ACTIVE":
                raise HTTPException(
                    status_code=409,
                    detail={"code": "DINING_FOLIO_STAY_NOT_ACTIVE", "stay_status": order["stay_status"]},
                )

            existing = order["folioChargeId"]
            charge_id = await ensure_kitchen_order_charge(
                conn,
                order_id,
                actor_type="STAFF",
                actor_id=user["id"],
            )
            if not charge_id:
                raise HTTPException(status_code=409, detail={"code": "KITCHEN_ORDER_NOT_LINKED_TO_RESERVATION"})

    return {
        "order_id": str(order_id),
        "charge_id": str(charge_id),
        "idempotent_replay": existing is not None,
        "payment_created": False,
        "financial_truth": "OPEN_FOLIO_CHARGE_NOT_PAYMENT",
    }
