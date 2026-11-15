"""Kitchen purchasing: dated demand -> explicit request -> approval -> receipt.

No planning, request, or approval deducts inventory or creates financial payments.
"""
from datetime import date
from decimal import Decimal
from typing import Literal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from .auth import require_roles, trusted_property_id
from .kitchen_recipes import read_recipe

router = APIRouter(prefix="/api/v1/kitchen/procurement", tags=["kitchen-procurement"])
read_access = require_roles("OWNER", "MANAGER", "COOK", "STORE_STAFF")
request_access = require_roles("OWNER", "MANAGER", "COOK", "STORE_STAFF")
approve_access = require_roles("OWNER", "MANAGER")
receive_access = require_roles("OWNER", "MANAGER", "STORE_STAFF")


class RequestWrite(BaseModel):
    request_id: uuid.UUID
    stock_item_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=16, decimal_places=6, allow_inf_nan=False)
    service_date: date | None = None
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None):
        return " ".join(value.split()) if value else None


class ReceiptWrite(BaseModel):
    receipt_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=16, decimal_places=6, allow_inf_nan=False)


def serialize_request(row):
    return {
        "id":str(row["id"]), "stock_item_id":str(row["stockItemId"]),
        "stock_name":row["name"], "unit":row["unit"], "is_sample":row["isSample"],
        "quantity":str(row["requestedQuantity"]),
        "received_quantity":str(row["receivedQuantity"]),
        "status":row["status"], "service_date":row["serviceDate"].isoformat() if row["serviceDate"] else None,
        "notes":row["notes"],
        "requested_by_id":str(row["createdById"]) if row["createdById"] else None,
        "approved_by_id":str(row["approvedById"]) if row["approvedById"] else None,
        "created_at":row["createdAt"].isoformat(),
    }


@router.get("/needs")
async def procurement_needs(service_date: date, request: Request, user=Depends(read_access)):
    async with request.app.state.db.acquire() as conn:
        pid=await trusted_property_id(conn,user)
        rows=await conn.fetch(
            '''SELECT t.id,t."menuItemId",t."plannedQuantity",t."preparedQuantity",
                      m."nameRu",m.recipe
               FROM kitchen_production_targets t
               JOIN kitchen_menu_items m ON m.id=t."menuItemId" AND m."propertyId"=t."propertyId"
               WHERE t."propertyId"=$1 AND t."serviceDate"=$2
               ORDER BY t.id''',pid,service_date)
        requirements={}
        missing=[]
        sample_targets=0
        for row in rows:
            remaining=row["plannedQuantity"]-row["preparedQuantity"]
            if remaining<=0:continue
            recipe=read_recipe(row["recipe"])
            if not recipe or recipe["status"]!="APPROVED":
                missing.append({"menu_item_id":str(row["menuItemId"]),"name_ru":row["nameRu"]})
                continue
            if recipe["is_sample"]:
                sample_targets+=1
                continue
            for ingredient in recipe["ingredients"]:
                key=(ingredient["name"].casefold(),ingredient["unit"])
                entry=requirements.setdefault(key,{"name":ingredient["name"],"unit":ingredient["unit"],"required":Decimal(0)})
                entry["required"]+=Decimal(ingredient["quantity_per_portion"])*remaining
        stock=await conn.fetch(
            '''SELECT i.id,i.name,i."nameKey",i.unit,i."costPerUnitKgs",
                      COALESCE(SUM(CASE WHEN m.kind='RECEIPT' THEN m.quantity ELSE -m.quantity END),0) AS balance
               FROM kitchen_stock_items i
               LEFT JOIN kitchen_stock_movements m ON m."propertyId"=i."propertyId" AND m."stockItemId"=i.id
               WHERE i."propertyId"=$1 AND i."isSample"=false
               GROUP BY i.id''',pid)
        stock_lookup={(r["nameKey"],r["unit"]):r for r in stock}
        pipeline=await conn.fetch(
            '''SELECT i."nameKey",i.unit,
                      COALESCE(SUM(p."requestedQuantity"-p."receivedQuantity"),0) AS pending,
                      COALESCE(SUM(CASE WHEN p.status IN ('APPROVED','PARTIAL')
                             THEN p."requestedQuantity"-p."receivedQuantity" ELSE 0 END),0) AS approved_inbound
               FROM kitchen_procurement_requests p JOIN kitchen_stock_items i
                 ON i.id=p."stockItemId" AND i."propertyId"=p."propertyId"
               WHERE p."propertyId"=$1 AND i."isSample"=false AND p.status IN ('REQUESTED','APPROVED','PARTIAL')
               GROUP BY i."nameKey",i.unit''',pid)
        pending={(r["nameKey"],r["unit"]):r["pending"] for r in pipeline}
        approved_inbound={(r["nameKey"],r["unit"]):r["approved_inbound"] for r in pipeline}
    items=[]
    for key,entry in sorted(requirements.items()):
        item=stock_lookup.get(key)
        balance=item["balance"] if item else Decimal(0)
        already=pending.get(key,Decimal(0))
        approved=approved_inbound.get(key,Decimal(0))
        required=entry["required"]
        items.append({
            "stock_item_id":str(item["id"]) if item else None,
            "name":entry["name"],"unit":entry["unit"],
            "remaining_needed":str(required),"balance":str(balance),
            "shortage":str(max(Decimal(0),required-balance)),
            "pending_requests":str(already),
            "approved_inbound":str(approved),
            # Unapproved requests are not a guaranteed delivery.
            "shortage_after_pipeline":str(max(Decimal(0),required-balance-approved)),
            "estimated_unit_cost_kgs":str(item["costPerUnitKgs"]) if item else None,
        })
    return {"service_date":service_date.isoformat(),"basis":"APPROVED_NON_SAMPLE_REMAINING_PRODUCTION",
            "is_complete":not missing and sample_targets==0,
            "missing_recipes":missing,"excluded_sample_targets":sample_targets,
            "inventory_deducted":False,"payment_created":False,"items":items}


@router.get("/requests")
async def list_requests(request: Request, user=Depends(read_access)):
    async with request.app.state.db.acquire() as conn:
        pid=await trusted_property_id(conn,user)
        rows=await conn.fetch(
            '''SELECT p.*,i.name,i.unit,i."isSample" FROM kitchen_procurement_requests p
               JOIN kitchen_stock_items i ON i.id=p."stockItemId" AND i."propertyId"=p."propertyId"
               WHERE p."propertyId"=$1 ORDER BY p."createdAt" DESC,p.id DESC LIMIT 100''',pid)
    return {"items":[serialize_request(r) for r in rows],"payment_created":False,
            "new_request_id":str(uuid.uuid4()),"new_receipt_id":str(uuid.uuid4())}


@router.post("/requests",status_code=201)
async def create_request(body: RequestWrite, request: Request, user=Depends(request_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            item=await conn.fetchrow(
                '''SELECT id FROM kitchen_stock_items WHERE id=$1 AND "propertyId"=$2
                   AND "isSample"=false FOR UPDATE''',
                body.stock_item_id,pid)
            if not item:raise HTTPException(404,detail={"code":"KITCHEN_PROC_ITEM_MISSING"})
            prior=await conn.fetchrow(
                '''SELECT id,"propertyId","stockItemId","requestedQuantity","serviceDate",notes
                   FROM kitchen_procurement_requests WHERE id=$1''',body.request_id)
            if prior:
                if (prior["propertyId"]!=pid or prior["stockItemId"]!=body.stock_item_id
                    or prior["requestedQuantity"]!=body.quantity or prior["serviceDate"]!=body.service_date
                    or prior["notes"]!=body.notes):
                    raise HTTPException(409,detail={"code":"KITCHEN_PROC_REQUEST_ID_CONFLICT"})
                return {"id":str(body.request_id),"status":"EXISTS","payment_created":False}
            await conn.execute(
                '''INSERT INTO kitchen_procurement_requests
                   (id,"propertyId","stockItemId","requestedQuantity","serviceDate",notes,"createdById")
                   VALUES ($1,$2,$3,$4,$5,$6,$7)''',
                body.request_id,pid,body.stock_item_id,body.quantity,body.service_date,
                body.notes,uuid.UUID(user["id"]))
    return {"id":str(body.request_id),"status":"REQUESTED","payment_created":False}


@router.post("/requests/{request_id}/approve")
async def approve_request(request_id: uuid.UUID, request: Request, user=Depends(approve_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            row=await conn.fetchrow(
                '''SELECT status FROM kitchen_procurement_requests
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',request_id,pid)
            if not row:raise HTTPException(404,detail={"code":"KITCHEN_PROC_REQUEST_MISSING"})
            if row["status"]!="REQUESTED":
                return {"id":str(request_id),"status":row["status"],
                        "already_processed":True,"payment_created":False}
            await conn.execute(
                '''UPDATE kitchen_procurement_requests
                   SET status='APPROVED',"approvedById"=$3,"approvedAt"=now(),"updatedAt"=now()
                   WHERE id=$1 AND "propertyId"=$2''',
                request_id,pid,uuid.UUID(user["id"]))
    return {"id":str(request_id),"status":"APPROVED",
            "already_processed":False,"payment_created":False}


@router.post("/requests/{request_id}/receive",status_code=201)
async def receive_request(request_id: uuid.UUID, body: ReceiptWrite, request: Request,
                          user=Depends(receive_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            preliminary=await conn.fetchrow(
                '''SELECT "stockItemId" FROM kitchen_procurement_requests
                   WHERE id=$1 AND "propertyId"=$2''',request_id,pid)
            if not preliminary:raise HTTPException(404,detail={"code":"KITCHEN_PROC_REQUEST_MISSING"})
            # Item first, then request: serialize with regular receipts, loss and production debits.
            item=await conn.fetchrow(
                '''SELECT id,"costPerUnitKgs" FROM kitchen_stock_items
                   WHERE id=$1 AND "propertyId"=$2 AND "isSample"=false FOR UPDATE''',
                preliminary["stockItemId"],pid)
            row=await conn.fetchrow(
                '''SELECT "stockItemId","requestedQuantity","receivedQuantity",status
                   FROM kitchen_procurement_requests WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                request_id,pid)
            if not item or not row or row["stockItemId"]!=item["id"]:
                raise HTTPException(409,detail={"code":"KITCHEN_PROC_STOCK_CHANGED"})
            prior=await conn.fetchrow(
                '''SELECT "propertyId","requestId",quantity FROM kitchen_procurement_receipts
                   WHERE id=$1''',body.receipt_id)
            if prior:
                if (prior["propertyId"]!=pid or prior["requestId"]!=request_id
                    or prior["quantity"]!=body.quantity):
                    raise HTTPException(409,detail={"code":"KITCHEN_PROC_RECEIPT_ID_CONFLICT"})
                return {"id":str(body.receipt_id),"request_id":str(request_id),
                        "already_processed":True,"status":row["status"],"payment_created":False}
            if row["status"] not in ("APPROVED","PARTIAL"):
                raise HTTPException(409,detail={"code":"KITCHEN_PROC_NOT_APPROVED"})
            accumulated=row["receivedQuantity"]+body.quantity
            if accumulated>row["requestedQuantity"]:
                raise HTTPException(409,detail={"code":"KITCHEN_PROC_OVER_RECEIPT"})
            await conn.execute(
                '''INSERT INTO kitchen_stock_movements
                   (id,"propertyId","stockItemId",kind,quantity,"unitCostKgs","createdById",notes)
                   VALUES ($1,$2,$3,'RECEIPT',$4,$5,$6,$7)''',
                body.receipt_id,pid,item["id"],body.quantity,item["costPerUnitKgs"],
                uuid.UUID(user["id"]),f"Procurement receipt for {request_id}")
            await conn.execute(
                '''INSERT INTO kitchen_procurement_receipts
                   (id,"propertyId","requestId",quantity,"createdById")
                   VALUES ($1,$2,$3,$4,$5)''',
                body.receipt_id,pid,request_id,body.quantity,uuid.UUID(user["id"]))
            final="RECEIVED" if accumulated==row["requestedQuantity"] else "PARTIAL"
            await conn.execute(
                '''UPDATE kitchen_procurement_requests
                   SET "receivedQuantity"=$3,status=$4,"updatedAt"=now()
                   WHERE id=$1 AND "propertyId"=$2''',request_id,pid,accumulated,final)
    return {"id":str(body.receipt_id),"request_id":str(request_id),
            "quantity":str(body.quantity),"status":final,"already_processed":False,
            "cost_kgs":str(body.quantity*item["costPerUnitKgs"]),"payment_created":False}
