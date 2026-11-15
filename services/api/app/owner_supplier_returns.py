"""OWNER-authorized supplier returns with immutable stock debits and credit-note facts.

Returning goods creates ONE inventory movement and ONE supplier credit adjustment
in the same transaction. No customer payment, no automatic supplier cash refund,
and no claim that the book-value/credit difference is recognized profit.
"""
import uuid
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from .auth import require_roles, trusted_property_id
from .kitchen_inventory_valuation import locked_stock_valuation, debit_cost

router=APIRouter(prefix="/api/v1/admin/finance/owner/supplier-returns",
                 tags=["owner-supplier-returns"])
owner_only=require_roles("OWNER",module_grant=False)
MONEY=Decimal("0.0001")


class ReturnWrite(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    document_line_id: uuid.UUID
    quantity: Decimal = Field(gt=0,max_digits=16,decimal_places=6,allow_inf_nan=False)
    credit_reference: str = Field(min_length=1,max_length=150)
    reason: str = Field(min_length=3,max_length=500)

    @field_validator("credit_reference","reason")
    @classmethod
    def normalize(cls,value:str,info)->str:
        normalized=" ".join(value.split())
        if len(normalized)<(3 if info.field_name=="reason" else 1):
            raise ValueError("Credit reference or reason is too short")
        return normalized


@router.post("",status_code=201)
async def return_to_supplier(body:ReturnWrite,request:Request,user=Depends(owner_only)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            # Same global op ID must never become two movements under concurrency.
            await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
                               "supplier-return:"+str(body.id))
            prior=await conn.fetchrow(
                '''SELECT * FROM kitchen_supplier_returns WHERE id=$1''',body.id)
            if prior:
                if (prior["propertyId"]!=pid or prior["documentId"]!=body.document_id or
                    prior["documentLineId"]!=body.document_line_id or
                    prior["quantity"]!=body.quantity or
                    prior["creditReference"]!=body.credit_reference or
                    prior["reason"]!=body.reason or
                    str(prior["createdById"])!=str(user["id"])):
                    raise HTTPException(409,detail={"code":"SUPPLIER_RETURN_ID_CONFLICT"})
                return {"id":str(body.id),"already_processed":True,
                        "quantity":str(prior["quantity"]),
                        "credit_amount_kgs":str(prior["creditAmountKgs"]),
                        "stock_removed_cost_kgs":str(
                            prior["quantity"]*prior["inventoryUnitCostKgs"]),
                        "payment_created":False,"recognized_profit":False}
            # This lock serializes all supplier settlements and returns for
            # one invoice, preventing payable underflow and duplicate credit.
            document=await conn.fetchrow(
                '''SELECT id FROM kitchen_supplier_documents
                   WHERE "propertyId"=$1 AND id=$2 FOR UPDATE''',pid,body.document_id)
            if not document:
                raise HTTPException(404,detail={"code":"SUPPLIER_DOCUMENT_MISSING"})
            line=await conn.fetchrow(
                '''SELECT id,"stockItemId",quantity,"unitCostKgs"
                   FROM kitchen_supplier_document_lines
                   WHERE id=$1 AND "propertyId"=$2 AND "documentId"=$3''',
                body.document_line_id,pid,body.document_id)
            if not line:
                raise HTTPException(404,detail={"code":"SUPPLIER_DOCUMENT_LINE_MISSING"})
            # Lock stock before invoice line, consistent with procurement
            # receive path, so production, loss, and returns cannot race.
            item=await conn.fetchrow(
                '''SELECT id,"isSample" FROM kitchen_stock_items
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                line["stockItemId"],pid)
            if not item or item["isSample"]:
                raise HTTPException(409,detail={"code":"SUPPLIER_RETURN_ITEM_INVALID"})
            await conn.fetchrow(
                '''SELECT id FROM kitchen_supplier_document_lines
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                body.document_line_id,pid)
            used=await conn.fetchval(
                '''SELECT COALESCE(SUM(quantity),0)
                   FROM kitchen_supplier_receipt_links
                   WHERE "propertyId"=$1 AND "documentLineId"=$2''',
                pid,body.document_line_id)
            returned=await conn.fetchval(
                '''SELECT COALESCE(SUM(quantity),0)
                   FROM kitchen_supplier_returns
                   WHERE "propertyId"=$1 AND "documentLineId"=$2''',
                pid,body.document_line_id)
            if body.quantity>used-returned:
                raise HTTPException(409,detail={"code":"SUPPLIER_RETURN_EXCEEDS_RECEIPTS"})
            # Credit notes adjust payables at *invoice* cost. Stock value
            # comes from the actual moving average of pooled inventory.
            credit=(body.quantity*line["unitCostKgs"]).quantize(
                MONEY,rounding=ROUND_HALF_UP)
            gross=await conn.fetchval(
                '''SELECT ROUND(COALESCE(SUM(quantity*"unitCostKgs"),0),4)
                   FROM kitchen_supplier_document_lines
                   WHERE "propertyId"=$1 AND "documentId"=$2''',
                pid,body.document_id)
            settled=await conn.fetchval(
                '''SELECT COALESCE(SUM("amountKgs"),0)
                   FROM kitchen_supplier_settlements
                   WHERE "propertyId"=$1 AND "documentId"=$2''',
                pid,body.document_id)
            credited=await conn.fetchval(
                '''SELECT COALESCE(SUM("creditAmountKgs"),0)
                   FROM kitchen_supplier_returns
                   WHERE "propertyId"=$1 AND "documentId"=$2''',
                pid,body.document_id)
            if settled+credited+credit>gross:
                raise HTTPException(409,detail={"code":"SUPPLIER_CREDIT_EXCEEDS_UNPAID"})
            duplicate=await conn.fetchval(
                '''SELECT id FROM kitchen_supplier_returns
                   WHERE "propertyId"=$1 AND "documentId"=$2 AND "creditReference"=$3''',
                pid,body.document_id,body.credit_reference)
            if duplicate:
                raise HTTPException(409,detail={"code":"SUPPLIER_CREDIT_REFERENCE_CONFLICT"})
            balance,value=await locked_stock_valuation(conn,pid,item["id"])
            if balance<body.quantity:
                raise HTTPException(409,detail={"code":"SUPPLIER_RETURN_INSUFFICIENT_STOCK"})
            stock_unit=debit_cost(balance,value,body.quantity)
            moved=await conn.fetchval(
                '''INSERT INTO kitchen_stock_movements
                   (id,"propertyId","stockItemId",kind,quantity,"unitCostKgs",
                    "createdById",notes)
                   VALUES ($1,$2,$3,'SUPPLIER_RETURN',$4,$5,$6,$7)
                   ON CONFLICT (id) DO NOTHING RETURNING id''',
                body.id,pid,item["id"],body.quantity,stock_unit,
                uuid.UUID(str(user["id"])),body.reason)
            if not moved:
                raise HTTPException(409,detail={"code":"SUPPLIER_RETURN_ID_CONFLICT"})
            await conn.execute(
                '''INSERT INTO kitchen_supplier_returns
                   (id,"propertyId","documentId","documentLineId","stockItemId",
                    "creditReference",quantity,"invoiceUnitCostKgs",
                    "inventoryUnitCostKgs","creditAmountKgs",reason,"createdById")
                   VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)''',
                body.id,pid,body.document_id,body.document_line_id,item["id"],
                body.credit_reference,body.quantity,line["unitCostKgs"],
                stock_unit,credit,body.reason,uuid.UUID(str(user["id"])))
    return {"id":str(body.id),"already_processed":False,
            "quantity":str(body.quantity),"credit_amount_kgs":str(credit),
            "stock_removed_cost_kgs":str(body.quantity*stock_unit),
            "payment_created":False,"recognized_profit":False}


@router.get("")
async def list_returns(request:Request,user=Depends(owner_only)):
    async with request.app.state.db.acquire() as conn:
        pid=await trusted_property_id(conn,user)
        rows=await conn.fetch(
            '''SELECT id,"documentId","documentLineId","stockItemId",
                      "creditReference",quantity,"creditAmountKgs",
                      "inventoryUnitCostKgs","createdAt"
               FROM kitchen_supplier_returns
               WHERE "propertyId"=$1 ORDER BY "createdAt" DESC,id DESC LIMIT 100''',pid)
    return {"items":[{
        "id":str(r["id"]),"document_id":str(r["documentId"]),
        "document_line_id":str(r["documentLineId"]),"stock_item_id":str(r["stockItemId"]),
        "credit_reference":r["creditReference"],"quantity":str(r["quantity"]),
        "credit_amount_kgs":str(r["creditAmountKgs"]),
        "stock_removed_cost_kgs":str(r["quantity"]*r["inventoryUnitCostKgs"]),
        "created_at":r["createdAt"].isoformat()
      } for r in rows],
      "financial_truth":"SUPPLIER_CREDIT_NOT_CASH_OR_RECOGNIZED_PROFIT",
      "limit":100}
