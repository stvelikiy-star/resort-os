"""Controlled append-only OWNER accounting postings; isolated staging feature.

A posting mirrors one independently approved, source-verified proposal. A
reversal contains the exact opposite lines. Never mutates payments or stock.
General P&L remains NOT_READY until all income/cost/tax evidence is reconciled.
"""
import os
import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from .auth import require_roles, trusted_property_id
from .owner_revenue_source_journal import lock_keys

router = APIRouter(prefix="/api/v1/admin/finance/owner/accounting-journal",
                   tags=["owner-posted-accounting"])
owner_only = require_roles("OWNER",module_grant=False)


class PostAccounting(BaseModel):
    id: uuid.UUID
    action: Literal["POST", "REVERSE"]
    reason: str = Field(min_length=8,max_length=500)

    @field_validator("reason")
    @classmethod
    def nonblank(cls,v):
        value=" ".join(v.split())
        if len(value)<8:
            raise ValueError("Reason must contain at least eight characters")
        return value


def guard():
    if (os.getenv("APP_ENV")!="staging"
        or os.getenv("MARINA_SHARED_AUTH_PREVIEW_ENABLED","false").lower()=="true"
        or os.getenv("MARINA_ACCOUNTING_DECISION_EVIDENCE_ENABLED","false").lower()!="true"
        or os.getenv("MARINA_ACCOUNTING_POSTING_ENABLED","false").lower()!="true"):
        raise HTTPException(503,detail={"code":"ACCOUNTING_POSTING_DISABLED"})


def posting_view(row,lines,replay=False):
    return {
        "id":str(row["id"]),"proposal_id":str(row["proposalId"]),
        "action":row["action"],"reverses_id":str(row["reversesId"]) if row["reversesId"] else None,
        "accounting_date":row["accountingDate"].isoformat(),
        "already_processed":replay,
        "lines":[{"line_no":x["lineNo"],"account_code":x["accountCode"],
                  "side":x["side"],"amount_kgs":str(x["amountKgs"])} for x in lines],
        "accounting_posted":True,
        "recognized_profit_kgs":None,
        "completeness_verified":False,
    }


@router.post("/proposals/{proposal_id}/postings",status_code=201)
async def post_accounting(proposal_id:uuid.UUID,body:PostAccounting,request:Request,
                          user=Depends(owner_only)):
    guard()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            actor=uuid.UUID(str(user["id"]))
            await lock_keys(conn,"owner-posting:"+str(pid)+":"+str(proposal_id))
            proposal=await conn.fetchrow(
                'SELECT * FROM owner_accounting_journal_proposals WHERE id=$1 AND "propertyId"=$2',
                proposal_id,pid)
            if not proposal:
                raise HTTPException(404,detail={"code":"ACCOUNTING_PROPOSAL_NOT_FOUND"})
            old=await conn.fetchrow(
                '''SELECT * FROM owner_accounting_postings
                   WHERE "propertyId"=$1 AND "proposalId"=$2 AND action=$3''',
                pid,proposal_id,body.action)
            if old:
                if old["id"]!=body.id or old["postedById"]!=actor or old["reason"]!=body.reason:
                    raise HTTPException(409,detail={"code":"ACCOUNTING_POSTING_CONFLICT"})
                lines=await conn.fetch(
                    'SELECT * FROM owner_accounting_posting_lines WHERE "propertyId"=$1 AND "postingId"=$2 ORDER BY "lineNo"',
                    pid,old["id"])
                return posting_view(old,lines,True)
            if actor==proposal["createdById"]:
                raise HTTPException(403,detail={"code":"ACCOUNTING_POSTER_MUST_BE_INDEPENDENT"})
            approval=await conn.fetchrow(
                '''SELECT * FROM owner_accounting_journal_decisions
                   WHERE "propertyId"=$1 AND "proposalId"=$2 AND action='APPROVE' ''',
                pid,proposal_id)
            if not approval:
                raise HTTPException(409,detail={"code":"ACCOUNTING_APPROVAL_REQUIRED"})
            if body.action=="POST":
                if await conn.fetchval(
                    '''SELECT 1 FROM owner_accounting_journal_decisions
                       WHERE "propertyId"=$1 AND "proposalId"=$2 AND action='REVERSE' ''',
                    pid,proposal_id):
                    raise HTTPException(409,detail={"code":"ACCOUNTING_APPROVAL_REVERSED"})
                original_id=None
                lines=await conn.fetch(
                    '''SELECT * FROM owner_accounting_journal_proposal_lines
                       WHERE "propertyId"=$1 AND "proposalId"=$2 ORDER BY "lineNo"''',
                    pid,proposal_id)
            else:
                original=await conn.fetchrow(
                    '''SELECT * FROM owner_accounting_postings
                       WHERE "propertyId"=$1 AND "proposalId"=$2 AND action='POST' ''',
                    pid,proposal_id)
                if not original:
                    raise HTTPException(409,detail={"code":"ACCOUNTING_POSTING_REQUIRED"})
                original_id=original["id"]
                lines=await conn.fetch(
                    '''SELECT * FROM owner_accounting_posting_lines
                       WHERE "propertyId"=$1 AND "postingId"=$2 ORDER BY "lineNo"''',
                    pid,original_id)
            row=await conn.fetchrow(
                '''INSERT INTO owner_accounting_postings
                   (id,"propertyId","proposalId","decisionId",action,"reversesId",
                    "postedById",reason,"accountingDate","policyVersion")
                   VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING *''',
                body.id,pid,proposal_id,approval["id"],body.action,original_id,
                actor,body.reason,proposal["accountingDate"],proposal["policyVersion"])
            for line in lines:
                side=(line["side"] if body.action=="POST" else
                      "CREDIT" if line["side"]=="DEBIT" else "DEBIT")
                await conn.execute(
                    '''INSERT INTO owner_accounting_posting_lines
                       ("postingId","propertyId","lineNo","accountCode",side,"amountKgs",memo)
                       VALUES($1,$2,$3,$4,$5,$6,$7)''',
                    body.id,pid,line["lineNo"],line["accountCode"],side,
                    line["amountKgs"],line["memo"])
            await conn.execute(
                '''INSERT INTO audit_logs
                   (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"createdAt")
                   VALUES($1,$2,'STAFF',$3,$4,'AccountingPosting',$5,'WEB_ADMIN','SUCCESS',now())''',
                uuid.uuid4(),pid,str(actor),"ACCOUNTING_"+body.action,str(body.id))
            posted=await conn.fetch(
                '''SELECT * FROM owner_accounting_posting_lines
                   WHERE "propertyId"=$1 AND "postingId"=$2 ORDER BY "lineNo"''',pid,body.id)
            return posting_view(row,posted)


@router.get("/proposals/{proposal_id}/postings")
async def list_postings(proposal_id:uuid.UUID,request:Request,user=Depends(owner_only)):
    guard()
    async with request.app.state.db.acquire() as conn:
        pid=await trusted_property_id(conn,user)
        if not await conn.fetchval(
            'SELECT 1 FROM owner_accounting_journal_proposals WHERE id=$1 AND "propertyId"=$2',
            proposal_id,pid):
            raise HTTPException(404,detail={"code":"ACCOUNTING_PROPOSAL_NOT_FOUND"})
        rows=await conn.fetch(
            '''SELECT * FROM owner_accounting_postings
               WHERE "propertyId"=$1 AND "proposalId"=$2 ORDER BY "createdAt",id''',
            pid,proposal_id)
        out=[]
        for row in rows:
            lines=await conn.fetch(
                '''SELECT * FROM owner_accounting_posting_lines
                   WHERE "propertyId"=$1 AND "postingId"=$2 ORDER BY "lineNo"''',
                pid,row["id"])
            out.append(posting_view(row,lines))
        return {"items":out,"recognized_profit_kgs":None,
                "completeness_verified":False}


@router.get("/posted-subtotals")
async def posted_subtotals(request:Request,from_date:date=Query(),to_date:date=Query(),
                           user=Depends(owner_only)):
    guard()
    if from_date>to_date or (to_date-from_date).days>366:
        raise HTTPException(422,detail={"code":"ACCOUNTING_PERIOD_INVALID"})
    async with request.app.state.db.acquire() as conn:
        pid=await trusted_property_id(conn,user)
        rows=await conn.fetch(
            '''SELECT l."accountCode",
                      COALESCE(SUM(CASE WHEN l.side='CREDIT' THEN l."amountKgs"
                                        ELSE -l."amountKgs" END),0) AS credit_net
               FROM owner_accounting_postings p
               JOIN owner_accounting_posting_lines l
                 ON l."postingId"=p.id AND l."propertyId"=p."propertyId"
               WHERE p."propertyId"=$1 AND p."accountingDate" BETWEEN $2 AND $3
               GROUP BY l."accountCode" ORDER BY l."accountCode"''',
            pid,from_date,to_date)
        entries={r["accountCode"]:Decimal(r["credit_net"]) for r in rows}
        revenue=sum((entries.get(k,Decimal(0)) for k in ("4000","4100")),Decimal(0))
        costs=-sum((entries.get(k,Decimal(0)) for k in ("5000","6000")),Decimal(0))
        return {
            "scope":"POSTED_LEDGER_SUBTOTALS_NOT_FULL_PROFIT",
            "posted_revenue_subtotal_kgs":str(revenue.quantize(Decimal("0.0001"))),
            "posted_cost_subtotal_kgs":str(costs.quantize(Decimal("0.0001"))),
            "posted_contribution_subtotal_kgs":str((revenue-costs).quantize(Decimal("0.0001"))),
            "recognized_profit_kgs":None,
            "completeness_verified":False,
            "blockers":["TAXES_REFUNDS_ACCOMMODATION_EXPENSES_COGS_PERIOD_CLOSE_REQUIRED"],
        }
