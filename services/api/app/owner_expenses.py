"""Owner-only manual expense obligations and separately recorded settlement facts.

Posting an expense is NOT a payment. Manual settlement never creates a customer
Payment, initiates acquiring, or implies recognized income/profit.
"""
from datetime import date
from typing import Literal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from .auth import require_roles, trusted_property_id

router = APIRouter(prefix="/api/v1/admin/finance/owner/expenses", tags=["owner-expenses"])
owner= require_roles("OWNER")

class ExpensePost(BaseModel):
    id: uuid.UUID
    expense_date: date
    category: Literal["SUPPLIES","UTILITIES","PAYROLL","MAINTENANCE","RENT","MARKETING","OTHER"]
    title: str=Field(min_length=1,max_length=150)
    amount_kgs: int=Field(gt=0,le=2_000_000_000)
    supplier_name: str|None=Field(None,min_length=1,max_length=150)
    document_reference: str|None=Field(None,min_length=1,max_length=150)
    notes: str|None=Field(None,max_length=500)

    @field_validator("title")
    @classmethod
    def name_not_blank(cls,value):
        cleaned=" ".join(value.split())
        if not cleaned:
            raise ValueError("Expense title required")
        return cleaned

class SettlementPost(BaseModel):
    id: uuid.UUID
    amount_kgs: int=Field(gt=0,le=2_000_000_000)
    paid_on: date
    method: Literal["CASH","BANK_TRANSFER","CARD","OTHER"]
    reference: str|None=Field(None,min_length=1,max_length=150)

class VoidPost(BaseModel):
    reason: str=Field(min_length=5,max_length=500)

def view(row):
    return {"id":str(row["id"]),"expense_date":row["expenseDate"].isoformat(),
        "category":row["category"],"title":row["title"],"amount_kgs":row["amountKgs"],
        "settled_kgs":int(row["settled_kgs"]),"outstanding_kgs":row["amountKgs"]-int(row["settled_kgs"]),
        "status":row["status"],"supplier_name":row["supplierName"],
        "document_reference":row["documentReference"],"notes":row["notes"],
        "created_by_id":str(row["createdById"]) if row["createdById"] else None,
        "void_reason":row["voidReason"],
        "created_at":row["createdAt"].isoformat()}

def expense_query():
    return '''SELECT e.*,COALESCE((SELECT SUM(s."amountKgs")
                 FROM owner_expense_settlements s WHERE s."propertyId"=e."propertyId"
                   AND s."expenseId"=e.id),0)::bigint AS settled_kgs
              FROM owner_expenses e'''

@router.get("")
async def list_expenses(request:Request,from_date:date=Query(),to_date:date=Query(),
                        user=Depends(owner)):
    if to_date<from_date or (to_date-from_date).days>366:
        raise HTTPException(422,detail={"code":"OWNER_EXPENSE_RANGE_INVALID"})
    async with request.app.state.db.acquire() as conn:
        pid=await trusted_property_id(conn,user)
        rows=await conn.fetch(expense_query()+'''
            WHERE e."propertyId"=$1 AND e."expenseDate">=$2 AND e."expenseDate"<=$3
            ORDER BY e."expenseDate" DESC,e."createdAt" DESC,e.id DESC LIMIT 500''',
            pid,from_date,to_date)
        totals=await conn.fetchrow('''WITH expenses AS (
            SELECT e.id,e.status,e."amountKgs",
              COALESCE((SELECT SUM(s."amountKgs") FROM owner_expense_settlements s
                 WHERE s."propertyId"=e."propertyId" AND s."expenseId"=e.id),0)::bigint AS settled
            FROM owner_expenses e WHERE e."propertyId"=$1
              AND e."expenseDate">=$2 AND e."expenseDate"<=$3
          ) SELECT COUNT(*) FILTER(WHERE status='POSTED')::int AS count,
             COALESCE(SUM("amountKgs") FILTER(WHERE status='POSTED'),0)::bigint AS posted,
             COALESCE(SUM(settled) FILTER(WHERE status='POSTED'),0)::bigint AS settled,
             COALESCE(SUM("amountKgs"-settled) FILTER(WHERE status='POSTED'),0)::bigint AS outstanding
            FROM expenses''',pid,from_date,to_date)
    return {"items":[view(x) for x in rows],"preview_limit":500,
        "new_expense_id":str(uuid.uuid4()),"new_settlement_id":str(uuid.uuid4()),
        "preview_truncated":totals["count"]>500,
        "totals":{"posted_expenses_kgs":totals["posted"],
                  "settled_against_period_expenses_kgs":totals["settled"],
                  "outstanding_kgs":totals["outstanding"],"posted_count":totals["count"]},
        "scope":"OWNER_ONLY_PROPERTY_SCOPED","payment_created":False,
        "truth":"POSTED_OBLIGATION_NOT_AUTOMATIC_PAYMENT_OR_PROFIT"}

@router.post("",status_code=201)
async def post_expense(payload:ExpensePost,request:Request,user=Depends(owner)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            row=await conn.fetchrow('SELECT * FROM owner_expenses WHERE id=$1 FOR UPDATE',payload.id)
            if row:
                same=(row["propertyId"]==pid and row["expenseDate"]==payload.expense_date
                    and row["category"]==payload.category and row["title"]==payload.title
                    and row["amountKgs"]==payload.amount_kgs
                    and row["supplierName"]==payload.supplier_name
                    and row["documentReference"]==payload.document_reference
                    and row["notes"]==payload.notes)
                if not same:raise HTTPException(409,detail={"code":"OWNER_EXPENSE_ID_CONFLICT"})
                return {"id":str(payload.id),"already_processed":True,
                        "status":row["status"],"payment_created":False}
            await conn.execute('''INSERT INTO owner_expenses
              (id,"propertyId","expenseDate",category,title,"amountKgs","supplierName",
               "documentReference",notes,"createdById")
              VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)''',
              payload.id,pid,payload.expense_date,payload.category,payload.title,
              payload.amount_kgs,payload.supplier_name,payload.document_reference,
              payload.notes,uuid.UUID(str(user["id"])))
    return {"id":str(payload.id),"already_processed":False,
            "status":"POSTED","payment_created":False}

@router.post("/{expense_id}/settlements",status_code=201)
async def record_settlement(expense_id:uuid.UUID,payload:SettlementPost,
                            request:Request,user=Depends(owner)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            expense=await conn.fetchrow('''SELECT "amountKgs",status
                FROM owner_expenses WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',expense_id,pid)
            if not expense:raise HTTPException(404,detail={"code":"OWNER_EXPENSE_MISSING"})
            prior=await conn.fetchrow('SELECT * FROM owner_expense_settlements WHERE id=$1',payload.id)
            if prior:
                if (prior["propertyId"]!=pid or prior["expenseId"]!=expense_id or
                    prior["amountKgs"]!=payload.amount_kgs or
                    prior["paidOn"]!=payload.paid_on or prior["method"]!=payload.method or
                    prior["reference"]!=payload.reference):
                    raise HTTPException(409,detail={"code":"OWNER_SETTLEMENT_ID_CONFLICT"})
                return {"id":str(payload.id),"already_processed":True,
                        "expense_id":str(expense_id),"payment_created":False,
                        "source":"MANUAL_EXPENSE_SETTLEMENT_FACT"}
            if expense["status"]!="POSTED":
                raise HTTPException(409,detail={"code":"OWNER_EXPENSE_VOID"})
            received=await conn.fetchval('''SELECT COALESCE(SUM("amountKgs"),0)::bigint
                FROM owner_expense_settlements WHERE "propertyId"=$1 AND "expenseId"=$2''',
                pid,expense_id)
            if received+payload.amount_kgs>expense["amountKgs"]:
                raise HTTPException(409,detail={"code":"OWNER_EXPENSE_OVER_SETTLEMENT"})
            await conn.execute('''INSERT INTO owner_expense_settlements
                (id,"propertyId","expenseId","amountKgs","paidOn",method,reference,"recordedById")
                VALUES($1,$2,$3,$4,$5,$6,$7,$8)''',
                payload.id,pid,expense_id,payload.amount_kgs,payload.paid_on,
                payload.method,payload.reference,uuid.UUID(str(user["id"])))
    return {"id":str(payload.id),"expense_id":str(expense_id),
            "already_processed":False,"payment_created":False,
            "source":"MANUAL_EXPENSE_SETTLEMENT_FACT"}

@router.post("/{expense_id}/void")
async def void_expense(expense_id:uuid.UUID,payload:VoidPost,
                       request:Request,user=Depends(owner)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            row=await conn.fetchrow('''SELECT status,"voidReason" FROM owner_expenses
               WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',expense_id,pid)
            if not row:raise HTTPException(404,detail={"code":"OWNER_EXPENSE_MISSING"})
            if row["status"]=="VOID":
                if row["voidReason"]!=payload.reason:
                    raise HTTPException(409,detail={"code":"OWNER_EXPENSE_ALREADY_VOID"})
                return {"id":str(expense_id),"status":"VOID","already_processed":True}
            settled=await conn.fetchval('''SELECT COUNT(*)::int FROM owner_expense_settlements
              WHERE "propertyId"=$1 AND "expenseId"=$2''',pid,expense_id)
            if settled:raise HTTPException(409,detail={"code":"OWNER_EXPENSE_PAID_CANNOT_VOID"})
            await conn.execute('''UPDATE owner_expenses SET status='VOID',
               "voidReason"=$3,"voidedById"=$4,"voidedAt"=now()
               WHERE id=$1 AND "propertyId"=$2''',expense_id,pid,
               payload.reason,uuid.UUID(str(user["id"])))
    return {"id":str(expense_id),"status":"VOID","already_processed":False}
