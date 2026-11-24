"""Guarded immutable accounting posting and exact reversal for existing OWNER journal.

Only staging and independently reviewed complete sources. This is not a
period-close process: P&L stays NULL until complete-period reconciliation.
"""
import os
import json
import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from .auth import require_roles, trusted_property_id
from .owner_revenue_source_journal import lock_keys
from .owner_ledger_policy import validate_posting, posted_totals

router=APIRouter(prefix="/api/v1/admin/finance/owner/accounting-journal",
                 tags=["owner-accounting-postings"])
owner_only=require_roles("OWNER",module_grant=False)


class PostingAction(BaseModel):
    id: uuid.UUID
    reason: str=Field(min_length=8,max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_trim(cls,v):
        x=" ".join(v.split())
        if len(x)<8:
            raise ValueError("Detailed accounting justification is required")
        return x


def posting_guard():
    if (os.getenv("APP_ENV")!="staging"
            or os.getenv("MARINA_SHARED_AUTH_PREVIEW_ENABLED","false").lower()=="true"
            or os.getenv("MARINA_ACCOUNTING_POSTING_ENABLED","false").lower()!="true"):
        raise HTTPException(503,detail={"code":"OWNER_ACCOUNTING_POSTING_DISABLED"})


async def qualified_posting_source(conn,pid,proposal):
    """Only unmodified, verified delivered-source evidence; never client amounts."""
    if proposal["sourceType"]=="OPERATING_EXPENSE":
        row=await conn.fetchrow(
            """SELECT e."amountKgs" AS "faceValueKgs",
                      'OPERATING_EXPENSE'::text AS "sourceType"
               FROM owner_expenses e
               WHERE e.id=$1 AND e."propertyId"=$2
                 AND e.status='POSTED' AND e."expenseDate"=$3
                 AND e.category IN
                   ('UTILITIES','PAYROLL','MAINTENANCE','RENT','MARKETING')
                 AND e."supplierName" IS NOT NULL
                 AND e."documentReference" IS NOT NULL
                 AND NOT EXISTS (SELECT 1 FROM kitchen_supplier_documents d
                   WHERE d."propertyId"=e."propertyId"
                     AND d."supplierName"=e."supplierName"
                     AND d."documentReference"=e."documentReference")""",
            proposal["sourceId"],pid,proposal["accountingDate"])
        if not row:
            raise HTTPException(409,detail={"code":"ACCOUNTING_EXPENSE_UNVERIFIED_OR_STOCK_OVERLAP"})
        return row
    if proposal["sourceType"]!="REVENUE_SOURCE":
        raise HTTPException(409,detail={"code":"ACCOUNTING_POSTING_SOURCE_TYPE_NOT_SUPPORTED"})
    row=await conn.fetchrow(
        """SELECT e."faceValueKgs",e."sourceType",e."sourceSnapshot"
           FROM owner_revenue_source_events e
           WHERE e.id=$1 AND e."propertyId"=$2 AND e.action='APPROVE_SOURCE'
             AND NOT EXISTS(SELECT 1 FROM owner_revenue_source_events rev
               WHERE rev."propertyId"=$2 AND rev."reversesId"=e.id)""",
        proposal["sourceId"],pid)
    if not row:
        raise HTTPException(409,detail={"code":"ACCOUNTING_SOURCE_UNVERIFIED_OR_REVERSED"})
    # Immutable qualification snapshot is written only by the original
    # verified source API, never by this posting request.
    proof=(json.loads(row["sourceSnapshot"])
           if isinstance(row["sourceSnapshot"],str) else row["sourceSnapshot"])
    if not isinstance(proof,dict):
        raise HTTPException(409,detail={"code":"ACCOUNTING_SOURCE_SNAPSHOT_INVALID"})
    key=("rate_and_tax_accounting_approved" if row["sourceType"]=="ROOM_NIGHT"
         else "tax_discount_refund_accounting_approved")
    if proof.get(key) is not True:
        raise HTTPException(409,detail={"code":"ACCOUNTING_SOURCE_TAX_DISCOUNT_PROOF_MISSING"})
    corrections=await conn.fetchval(
        """SELECT COUNT(*) FROM owner_revenue_correction_events c
           WHERE c."propertyId"=$1 AND c."approvalId"=$2 AND c.action='RECORD'
             AND NOT EXISTS(SELECT 1 FROM owner_revenue_correction_events rev
               WHERE rev."propertyId"=$1 AND rev."reversesId"=c.id)""",
        pid,proposal["sourceId"])
    if corrections:
        raise HTTPException(409,detail={"code":"ACCOUNTING_CORRECTIONS_NOT_RECONCILED"})
    return row


def posting_view(row,replay=False):
    return {"id":str(row["id"]),"proposal_id":str(row["proposalId"]),
            "action":row["action"],"already_processed":replay,
            "accounting_posted":True,"period_completeness_verified":False,
            "recognized_profit_kgs":None}


@router.post("/proposals/{proposal_id}/post",status_code=201)
async def post_approved_proposal(proposal_id:uuid.UUID,body:PostingAction,
                                 request:Request,user=Depends(owner_only)):
    posting_guard()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            actor=uuid.UUID(str(user["id"]))
            await lock_keys(conn,"owner-ledger-post:"+str(pid)+":"+str(proposal_id))
            proposal=await conn.fetchrow(
                'SELECT * FROM owner_accounting_journal_proposals WHERE id=$1 AND "propertyId"=$2',
                proposal_id,pid)
            if not proposal:
                raise HTTPException(404,detail={"code":"ACCOUNTING_PROPOSAL_NOT_FOUND"})
            prior=await conn.fetchrow(
                """SELECT * FROM owner_accounting_postings WHERE "propertyId"=$1
                   AND "proposalId"=$2 AND action='POST'""",pid,proposal_id)
            if prior:
                if prior["id"]!=body.id or prior["postedById"]!=actor or prior["reason"]!=body.reason:
                    raise HTTPException(409,detail={"code":"ACCOUNTING_POSTING_ID_CONFLICT"})
                return posting_view(prior,True)
            approval=await conn.fetchrow(
                """SELECT * FROM owner_accounting_journal_decisions WHERE "propertyId"=$1
                   AND "proposalId"=$2 AND action='APPROVE'""",pid,proposal_id)
            if not approval or approval["actorId"]!=actor or proposal["createdById"]==actor:
                raise HTTPException(403,detail={"code":"ACCOUNTING_INDEPENDENT_APPROVAL_REQUIRED"})
            if await conn.fetchval(
                """SELECT EXISTS(SELECT 1 FROM owner_accounting_journal_decisions
                   WHERE "propertyId"=$1 AND "proposalId"=$2 AND action='REVERSE')""",
                pid,proposal_id):
                raise HTTPException(409,detail={"code":"ACCOUNTING_APPROVAL_REVERSED"})
            source=await qualified_posting_source(conn,pid,proposal)
            original=await conn.fetch(
                """SELECT "lineNo","accountCode",side,"amountKgs"
                   FROM owner_accounting_journal_proposal_lines
                   WHERE "propertyId"=$1 AND "proposalId"=$2 ORDER BY "lineNo" """,
                pid,proposal_id)
            lines=[{"account_code":r["accountCode"],"side":r["side"],
                    "amount_kgs":r["amountKgs"]} for r in original]
            try:
                validate_posting(lines,source_type=proposal["sourceType"],
                                 evidence_complete=True,
                                 source_amount=source["faceValueKgs"],
                                 revenue_service_type=source["sourceType"])
            except ValueError as exc:
                raise HTTPException(409,detail={"code":"ACCOUNTING_POSTING_POLICY_REJECTED",
                                                "reason":str(exc)}) from exc
            row=await conn.fetchrow(
                """INSERT INTO owner_accounting_postings(
                   id,"propertyId","proposalId","decisionId",action,
                   "accountingDate","policyVersion","postedById",
                   "sourceCompletenessAttested",reason)
                   VALUES($1,$2,$3,$4,'POST',$5,$6,$7,true,$8) RETURNING *""",
                body.id,pid,proposal_id,approval["id"],proposal["accountingDate"],
                proposal["policyVersion"],actor,body.reason)
            for r in original:
                await conn.execute(
                    """INSERT INTO owner_accounting_posting_lines
                       ("postingId","propertyId","lineNo","accountCode",side,"amountKgs")
                       VALUES($1,$2,$3,$4,$5,$6)""",
                    body.id,pid,r["lineNo"],r["accountCode"],r["side"],r["amountKgs"])
            await conn.execute(
                """INSERT INTO audit_logs
                   (id,"propertyId","actorType","actorId",action,resource,"resourceId",
                    source,result,"createdAt")
                   VALUES($1,$2,'STAFF',$3,'ACCOUNTING_LEDGER_POST',
                          'OwnerAccountingPosting',$4,'WEB_ADMIN','SUCCESS',now())""",
                uuid.uuid4(),pid,str(actor),str(body.id))
            return posting_view(row)


@router.post("/postings/{posting_id}/reverse",status_code=201)
async def reverse_posting(posting_id:uuid.UUID,body:PostingAction,request:Request,
                          user=Depends(owner_only)):
    posting_guard()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            actor=uuid.UUID(str(user["id"]))
            await lock_keys(conn,"owner-ledger-reverse:"+str(pid)+":"+str(posting_id))
            original=await conn.fetchrow(
                """SELECT * FROM owner_accounting_postings
                   WHERE id=$1 AND "propertyId"=$2 AND action='POST'""",posting_id,pid)
            if not original:
                raise HTTPException(404,detail={"code":"ACCOUNTING_POSTING_NOT_FOUND"})
            prior=await conn.fetchrow(
                """SELECT * FROM owner_accounting_postings
                   WHERE "propertyId"=$1 AND "reversesId"=$2 AND action='REVERSE'""",
                pid,posting_id)
            if prior:
                if prior["id"]!=body.id or prior["postedById"]!=actor or prior["reason"]!=body.reason:
                    raise HTTPException(409,detail={"code":"ACCOUNTING_REVERSAL_ID_CONFLICT"})
                return posting_view(prior,True)
            decision=await conn.fetchrow(
                """SELECT * FROM owner_accounting_journal_decisions
                   WHERE "propertyId"=$1 AND "proposalId"=$2 AND action='REVERSE'""",
                pid,original["proposalId"])
            if not decision:
                raise HTTPException(409,detail={"code":"ACCOUNTING_REVERSAL_DECISION_REQUIRED"})
            row=await conn.fetchrow(
                """INSERT INTO owner_accounting_postings
                   (id,"propertyId","proposalId","decisionId",action,"reversesId",
                    "accountingDate","policyVersion","postedById",
                    "sourceCompletenessAttested",reason)
                   VALUES($1,$2,$3,$4,'REVERSE',$5,$6,$7,$8,true,$9) RETURNING *""",
                body.id,pid,original["proposalId"],decision["id"],posting_id,
                original["accountingDate"],original["policyVersion"],actor,body.reason)
            lines=await conn.fetch(
                """SELECT * FROM owner_accounting_posting_lines WHERE "propertyId"=$1
                   AND "postingId"=$2 ORDER BY "lineNo" """,pid,posting_id)
            for line in lines:
                opposite="CREDIT" if line["side"]=="DEBIT" else "DEBIT"
                await conn.execute(
                    """INSERT INTO owner_accounting_posting_lines(
                       "postingId","propertyId","lineNo","accountCode",side,"amountKgs")
                       VALUES($1,$2,$3,$4,$5,$6)""",
                    body.id,pid,line["lineNo"],line["accountCode"],opposite,line["amountKgs"])
            await conn.execute(
                """INSERT INTO audit_logs
                   (id,"propertyId","actorType","actorId",action,resource,"resourceId",
                    source,result,"createdAt")
                   VALUES($1,$2,'STAFF',$3,'ACCOUNTING_LEDGER_REVERSE',
                          'OwnerAccountingPosting',$4,'WEB_ADMIN','SUCCESS',now())""",
                uuid.uuid4(),pid,str(actor),str(body.id))
            return posting_view(row)


@router.get("/posted-profit")
async def posted_profit(request:Request,from_date:date=Query(),to_date:date=Query(),
                        user=Depends(owner_only)):
    posting_guard()
    if from_date>to_date or (to_date-from_date).days>366:
        raise HTTPException(422,detail={"code":"ACCOUNTING_PERIOD_INVALID"})
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction(isolation="repeatable_read",readonly=True):
            pid=await trusted_property_id(conn,user)
            rows=await conn.fetch(
                """SELECT l."accountCode" AS account_code,l.side,
                          l."amountKgs" AS amount_kgs
                   FROM owner_accounting_posting_lines l
                   JOIN owner_accounting_postings p
                     ON p.id=l."postingId" AND p."propertyId"=l."propertyId"
                   WHERE p."propertyId"=$1 AND p."accountingDate" BETWEEN $2 AND $3
                   ORDER BY p."createdAt",p.id,l."lineNo" """,pid,from_date,to_date)
            result=posted_totals(rows,completeness_verified=False)
            return {**result,"posting_line_count":len(rows),
                    "accounting_postings_exist":bool(rows),
                    "period_completeness_verified":False,
                    "blockers":["PERIOD_SOURCE_COVERAGE_NOT_VERIFIED",
                                "TAX_REFUNDS_STOCK_AND_EXPENSE_CLOSE_NOT_VERIFIED"],
                    "currency":"KGS"}
