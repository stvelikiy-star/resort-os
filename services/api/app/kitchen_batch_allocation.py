"""Explicit, tenant-scoped production batch attribution to a served dish.

No automatic COGS posting and no bank movement. The operator is attesting
which batch physically supplied which already-served order item. A batch
has a finite, stock-deducted capacity; rows cannot consume it twice.
"""
import os
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from . import auth
from .auth import require_roles, trusted_property_id

router = APIRouter(prefix="/api/v1/kitchen/orders", tags=["kitchen-served-batches"])
operator_only = require_roles("OWNER", "MANAGER", "COOK", module_grant=False)


class BatchAllocationWrite(BaseModel):
    id: uuid.UUID  # caller-generated idempotency key, retained in ledger
    order_item_id: uuid.UUID
    production_target_id: uuid.UUID
    portions: int = Field(ge=1, le=10000)


def enforce_batch_staging() -> None:
    if not auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED or os.getenv("APP_ENV") != "staging":
        raise HTTPException(503, detail={"code": "BATCH_ALLOCATION_STAGING_ONLY"})
    auth.shared_auth_preview_guard()


@router.post("/{order_id}/batch-allocations", status_code=201)
async def record_served_batch(
    order_id: uuid.UUID, body: BatchAllocationWrite, request: Request,
    user: dict[str, Any] = Depends(operator_only),
):
    enforce_batch_staging()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await trusted_property_id(conn, user)
            order = await conn.fetchrow(
                '''SELECT id,status,"completedAt" FROM kitchen_orders
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''', order_id, pid,
            )
            if not order:
                raise HTTPException(404, detail={"code": "HOTEL_ORDER_NOT_FOUND"})
            if order["status"] != "SERVED" or order["completedAt"] is None:
                raise HTTPException(409, detail={"code": "ORDER_NOT_SERVED"})
            target = await conn.fetchrow(
                '''SELECT t.id,t."menuItemId",t."serviceDate",
                          COALESCE(p."deductedPortions",0) AS deducted_portions
                   FROM kitchen_production_targets t
                   LEFT JOIN kitchen_stock_production_progress p
                     ON p."propertyId"=t."propertyId"
                       AND p."productionTargetId"=t.id
                   WHERE t.id=$1 AND t."propertyId"=$2 FOR UPDATE OF t''',
                body.production_target_id, pid,
            )
            if not target:
                raise HTTPException(404, detail={"code": "HOTEL_BATCH_NOT_FOUND"})
            item = await conn.fetchrow(
                '''SELECT id,"menuItemId",quantity,status FROM kitchen_order_items
                   WHERE id=$1 AND "orderId"=$2 FOR UPDATE''',
                body.order_item_id, order_id,
            )
            if not item:
                raise HTTPException(404, detail={"code": "ORDER_ITEM_NOT_FOUND"})
            if item["status"] != "SERVED" or item["menuItemId"] != target["menuItemId"]:
                raise HTTPException(409, detail={"code": "BATCH_MENU_OR_SERVICE_MISMATCH"})
            local_day = await conn.fetchval(
                '''SELECT ($1::timestamptz AT TIME ZONE p.timezone)::date
                   FROM properties p WHERE p.id=$2''', order["completedAt"], pid,
            )
            if target["serviceDate"] > local_day:
                raise HTTPException(409, detail={"code": "BATCH_AFTER_SERVICE_DATE"})
            existing = await conn.fetchrow(
                '''SELECT id,"propertyId","orderId","orderItemId",
                          "productionTargetId",portions,"totalCostKgs"
                   FROM kitchen_served_batch_allocations WHERE id=$1''', body.id,
            )
            if existing:
                if (existing["propertyId"]==pid and existing["orderId"]==order_id
                        and existing["orderItemId"]==body.order_item_id
                        and existing["productionTargetId"]==body.production_target_id
                        and existing["portions"]==body.portions):
                    return {"allocation_id":str(body.id), "already_processed":True,
                            "cost_kgs":str(existing["totalCostKgs"]),
                            "source":"OPERATOR_ATTESTED","recognized_profit_posted":False}
                raise HTTPException(409, detail={"code": "BATCH_ALLOCATION_ID_REUSED"})
            already_item = await conn.fetchval(
                '''SELECT COALESCE(SUM(portions),0)::int
                   FROM kitchen_served_batch_allocations
                   WHERE "propertyId"=$1 AND "orderItemId"=$2''', pid, item["id"],
            )
            if already_item + body.portions > item["quantity"]:
                raise HTTPException(409, detail={"code": "ORDER_ITEM_PORTIONS_EXCEEDED"})
            already_batch = await conn.fetchval(
                '''SELECT COALESCE(SUM(portions),0)::int
                   FROM kitchen_served_batch_allocations
                   WHERE "propertyId"=$1 AND "productionTargetId"=$2''', pid, target["id"],
            )
            if already_batch + body.portions > target["deducted_portions"]:
                raise HTTPException(409, detail={"code": "STOCK_DEDUCTED_BATCH_CAPACITY_EXCEEDED"})
            costs = await conn.fetchrow(
                '''SELECT COALESCE(SUM(m.quantity*m."unitCostKgs"),0) AS amount,
                          COUNT(*)::int AS movement_count,
                          COUNT(*) FILTER (WHERE i."isSample")::int AS sample_count
                   FROM kitchen_stock_movements m
                   JOIN kitchen_stock_items i
                     ON i.id=m."stockItemId" AND i."propertyId"=m."propertyId"
                   WHERE m."propertyId"=$1 AND m."productionTargetId"=$2
                     AND m.kind='PRODUCTION' ''', pid,target["id"],
            )
            if (not target["deducted_portions"] or not costs["movement_count"]
                    or costs["sample_count"]):
                raise HTTPException(409, detail={"code": "REAL_STOCK_CONSUMPTION_REQUIRED"})
            unit_cost = (Decimal(costs["amount"]) / target["deducted_portions"]).quantize(
                Decimal("0.000001"), rounding=ROUND_HALF_UP)
            total = (Decimal(costs["amount"]) * body.portions / target["deducted_portions"]).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP)
            await conn.execute(
                '''INSERT INTO kitchen_served_batch_allocations
                   (id,"propertyId","orderId","orderItemId","productionTargetId",
                    portions,"unitCostKgs","totalCostKgs","recordedById")
                   VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)''',
                body.id,pid,order_id,item["id"],target["id"],body.portions,
                unit_cost,total,uuid.UUID(user["id"]),
            )
            await conn.execute(
                '''INSERT INTO audit_logs
                   (id,"propertyId","actorType","actorId",action,resource,"resourceId",
                    source,result,"afterJson","createdAt")
                   VALUES($1,$2,'STAFF',$3,'KITCHEN_SERVED_BATCH_ALLOCATION',
                          'KitchenOrderItem',$4,'KITCHEN_BATCH_TRACE','SUCCESS',
                          jsonb_build_object('production_target_id',$5::text,
                            'order_id',$6::text,'portions',$7::int,'cost_kgs',$8::text,
                            'source','OPERATOR_ATTESTED','accounting_posted',false),now())''',
                uuid.uuid4(),pid,user["id"],str(item["id"]),str(target["id"]),
                str(order_id),body.portions,str(total),
            )
            return {"allocation_id":str(body.id),"already_processed":False,
                    "order_item_id":str(item["id"]),
                    "production_target_id":str(target["id"]),
                    "portions":body.portions,"cost_kgs":str(total),
                    "source":"OPERATOR_ATTESTED",
                    "recognized_profit_posted":False}
