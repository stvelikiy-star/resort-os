"""Property-scoped supplier source documents and manual settlement facts.

A supplier document is an obligation, not an owner operating expense, customer
Payment, cash transfer, recognized COGS, or proven stock receipt.
"""
from datetime import date
from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from .auth import require_roles, trusted_property_id

router = APIRouter(prefix="/api/v1/admin/finance/owner/supplier-documents",
                   tags=["owner-supplier-documents"])
owner_only = require_roles("OWNER", module_grant=False)


class SupplierLine(BaseModel):
    id: uuid.UUID
    stock_item_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=16, decimal_places=6,
                              allow_inf_nan=False)
    unit_cost_kgs: Decimal = Field(ge=0, max_digits=16, decimal_places=4,
                                   allow_inf_nan=False)


class SupplierDocumentWrite(BaseModel):
    id: uuid.UUID
    supplier_name: str = Field(min_length=1, max_length=150)
    document_reference: str = Field(min_length=1, max_length=150)
    document_date: date
    lines: list[SupplierLine] = Field(min_length=1, max_length=100)

    @field_validator("supplier_name", "document_reference")
    @classmethod
    def strip_nonempty(cls, value: str):
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Supplier and reference must not be blank")
        return normalized


class SupplierSettlementWrite(BaseModel):
    id: uuid.UUID
    amount_kgs: Decimal = Field(gt=0, max_digits=20, decimal_places=4,
                                 allow_inf_nan=False)
    paid_on: date
    method: str = Field(pattern="^(CASH|BANK_TRANSFER|CARD|OTHER)$")
    reference: str | None = Field(None, min_length=1, max_length=150)


def total_value(lines):
    return sum((line["quantity"] * line["unitCostKgs"] for line in lines), Decimal(0))


def line_key(line):
    return (line["id"], line["stockItemId"], line["quantity"], line["unitCostKgs"])


@router.post("", status_code=201)
async def register_document(body: SupplierDocumentWrite, request: Request,
                            user=Depends(owner_only)):
    if len({line.id for line in body.lines}) != len(body.lines):
        raise HTTPException(422, detail={"code": "SUPPLIER_DUPLICATE_LINE_IDS"})
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await trusted_property_id(conn, user)
            # Lock both keys before checking to prevent races on repeated invoice references.
            keys = sorted(("supplier-document-id:" + str(body.id),
                           "supplier-reference:" + str(pid) + ":" +
                           body.supplier_name + ":" + body.document_reference))
            for key in keys:
                await conn.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended($1,0))", key)
            previous = await conn.fetchrow(
                'SELECT * FROM kitchen_supplier_documents WHERE id=$1', body.id)
            if previous:
                if (previous["propertyId"] != pid or
                    previous["supplierName"] != body.supplier_name or
                    previous["documentReference"] != body.document_reference or
                    previous["documentDate"] != body.document_date or
                    str(previous["createdById"]) != str(user["id"])):
                    raise HTTPException(409, detail={"code": "SUPPLIER_DOCUMENT_ID_CONFLICT"})
                existing = await conn.fetch(
                    'SELECT * FROM kitchen_supplier_document_lines '
                    'WHERE "propertyId"=$1 AND "documentId"=$2', pid, body.id)
                expected = {(line.id, line.stock_item_id, line.quantity,
                             line.unit_cost_kgs) for line in body.lines}
                if {line_key(line) for line in existing} != expected:
                    raise HTTPException(409, detail={"code": "SUPPLIER_DOCUMENT_ID_CONFLICT"})
                return {"id": str(body.id), "already_processed": True,
                        "amount_kgs": str(total_value(existing)),
                        "payment_created": False, "recognized_profit": False}
            duplicate = await conn.fetchval(
                'SELECT id FROM kitchen_supplier_documents WHERE "propertyId"=$1 '
                'AND "supplierName"=$2 AND "documentReference"=$3',
                pid, body.supplier_name, body.document_reference)
            if duplicate:
                raise HTTPException(409, detail={"code": "SUPPLIER_REFERENCE_CONFLICT"})
            item_ids = [line.stock_item_id for line in body.lines]
            found = await conn.fetch(
                'SELECT id FROM kitchen_stock_items '
                'WHERE "propertyId"=$1 AND id=ANY($2::uuid[]) AND "isSample"=false',
                pid, item_ids)
            if {row["id"] for row in found} != set(item_ids):
                raise HTTPException(404, detail={"code": "SUPPLIER_STOCK_ITEM_MISSING"})
            await conn.execute(
                'INSERT INTO kitchen_supplier_documents '
                '(id,"propertyId","supplierName","documentReference",'
                '"documentDate","createdById") VALUES ($1,$2,$3,$4,$5,$6)',
                body.id, pid, body.supplier_name, body.document_reference,
                body.document_date, uuid.UUID(str(user["id"])))
            for line in body.lines:
                await conn.execute(
                    'INSERT INTO kitchen_supplier_document_lines '
                    '(id,"propertyId","documentId","stockItemId",quantity,"unitCostKgs") '
                    'VALUES($1,$2,$3,$4,$5,$6)',
                    line.id, pid, body.id, line.stock_item_id, line.quantity,
                    line.unit_cost_kgs)
    value = sum((line.quantity * line.unit_cost_kgs for line in body.lines),
                Decimal(0))
    return {"id": str(body.id), "already_processed": False,
            "amount_kgs": str(value), "payment_created": False,
            "recognized_profit": False}


@router.get("")
async def list_documents(request: Request, user=Depends(owner_only)):
    async with request.app.state.db.acquire() as conn:
        pid = await trusted_property_id(conn, user)
        rows = await conn.fetch(
            '''SELECT d.id,d."supplierName",d."documentReference",d."documentDate",
                COALESCE((SELECT SUM(l.quantity*l."unitCostKgs")
                  FROM kitchen_supplier_document_lines l
                  WHERE l."propertyId"=d."propertyId" AND l."documentId"=d.id),0)
                   AS total,
                COALESCE((SELECT SUM(s."amountKgs") FROM kitchen_supplier_settlements s
                  WHERE s."propertyId"=d."propertyId" AND s."documentId"=d.id),0)
                   AS settled
               FROM kitchen_supplier_documents d WHERE d."propertyId"=$1
               ORDER BY d."documentDate" DESC,d.id DESC LIMIT 100''', pid)
        return {"items": [
            {"id": str(row["id"]), "supplier_name": row["supplierName"],
             "document_reference": row["documentReference"],
             "document_date": row["documentDate"].isoformat(),
             "amount_kgs": str(row["total"]),
             "settled_kgs": str(row["settled"]),
             "outstanding_kgs": str(row["total"] - row["settled"])}
            for row in rows],
            "limit": 100, "payment_created": False,
            "recognized_profit": False, "scope": "OWNER_ONLY_PROPERTY_SCOPED"}


@router.post("/{document_id}/settlements", status_code=201)
async def settle_document(document_id: uuid.UUID, body: SupplierSettlementWrite,
                          request: Request, user=Depends(owner_only)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await trusted_property_id(conn, user)
            document = await conn.fetchrow(
                'SELECT id FROM kitchen_supplier_documents '
                'WHERE id=$1 AND "propertyId"=$2 FOR UPDATE', document_id, pid)
            if not document:
                raise HTTPException(404, detail={"code": "SUPPLIER_DOCUMENT_MISSING"})
            prior = await conn.fetchrow(
                'SELECT * FROM kitchen_supplier_settlements WHERE id=$1', body.id)
            if prior:
                if (prior["propertyId"] != pid or prior["documentId"] != document_id or
                    prior["amountKgs"] != body.amount_kgs or
                    prior["paidOn"] != body.paid_on or
                    prior["method"] != body.method or
                    prior["reference"] != body.reference or
                    str(prior["recordedById"]) != str(user["id"])):
                    raise HTTPException(409, detail={"code": "SUPPLIER_SETTLEMENT_ID_CONFLICT"})
                return {"id": str(body.id), "already_processed": True,
                        "customer_payment_created": False}
            total = await conn.fetchval(
                'SELECT COALESCE(SUM(quantity*"unitCostKgs"),0) '
                'FROM kitchen_supplier_document_lines '
                'WHERE "propertyId"=$1 AND "documentId"=$2', pid, document_id)
            settled = await conn.fetchval(
                'SELECT COALESCE(SUM("amountKgs"),0) '
                'FROM kitchen_supplier_settlements '
                'WHERE "propertyId"=$1 AND "documentId"=$2', pid, document_id)
            if settled + body.amount_kgs > total:
                raise HTTPException(409, detail={"code": "SUPPLIER_OVER_SETTLEMENT"})
            await conn.execute(
                'INSERT INTO kitchen_supplier_settlements '
                '(id,"propertyId","documentId","amountKgs","paidOn",'
                'method,reference,"recordedById") '
                'VALUES ($1,$2,$3,$4,$5,$6,$7,$8)',
                body.id, pid, document_id, body.amount_kgs, body.paid_on,
                body.method, body.reference, uuid.UUID(str(user["id"])))
    return {"id": str(body.id), "already_processed": False,
            "customer_payment_created": False, "recognized_profit": False}
