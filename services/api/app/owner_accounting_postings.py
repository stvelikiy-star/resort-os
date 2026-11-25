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


def posting_enabled():
    return (os.getenv("APP_ENV")=="staging"
            and os.getenv("MARINA_SHARED_AUTH_PREVIEW_ENABLED","false").lower()!="true"
            and os.getenv("MARINA_ACCOUNTING_POSTING_ENABLED","false").lower()=="true")


def posting_guard():
    if not posting_enabled():
        raise HTTPException(503,detail={"code":"OWNER_ACCOUNTING_POSTING_DISABLED"})


class RevenueSourceCertification(BaseModel):
    id: uuid.UUID
    source_event_id: uuid.UUID
    evidence_document_id: uuid.UUID
    tax_amount_kgs: Decimal=Field(ge=0,max_digits=20,decimal_places=4,allow_inf_nan=False)
    reduction_amount_kgs: Decimal=Field(default=Decimal(0),ge=0,max_digits=20,decimal_places=4,allow_inf_nan=False)
    reduction_basis: str|None=None
    correction_event_ids: list[uuid.UUID]|None=Field(default=None,max_length=128)
    policy_version: str=Field(min_length=3,max_length=80)
    reason: str=Field(min_length=8,max_length=500)

    @field_validator("reason","policy_version")
    @classmethod
    def normalize_text(cls,value):
        value=" ".join(value.split())
        if len(value)<3:
            raise ValueError("Policy / explanation is required")
        return value


@router.post("/revenue-certifications",status_code=201)
async def certify_revenue_source(body:RevenueSourceCertification,request:Request,
                                 user=Depends(owner_only)):
    """Independent review of stored source document; not final period close."""
    posting_guard()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            actor=uuid.UUID(str(user["id"]))
            await lock_keys(conn,"owner-revenue-certification:"+str(pid)+":"+
                            str(body.source_event_id))
            prior=await conn.fetchrow(
                """SELECT * FROM owner_revenue_accounting_certifications
                   WHERE "propertyId"=$1 AND "sourceEventId"=$2""",
                pid,body.source_event_id)
            if prior:
                if (prior["id"]!=body.id
                    or prior["reviewedById"]!=actor
                    or prior["evidenceDocumentId"]!=body.evidence_document_id
                    or prior["taxAmountKgs"]!=body.tax_amount_kgs
                    or prior["reductionAmountKgs"]!=body.reduction_amount_kgs
                    or prior["reductionBasis"]!=body.reduction_basis
                    or (body.correction_event_ids is not None and
                        list(prior["correctionEventIds"] or ([prior["taxCorrectionEventId"]]
                             if prior["taxCorrectionEventId"] else []))!=sorted(body.correction_event_ids))
                    or prior["policyVersion"]!=body.policy_version
                    or prior["reason"]!=body.reason):
                    raise HTTPException(409,detail={"code":"REVENUE_SOURCE_CERTIFICATION_CONFLICT"})
                return {"id":str(prior["id"]),"already_processed":True,
                        "accounting_posted":False,"recognized_profit_kgs":None}
            ev=await conn.fetchrow(
                """SELECT e."faceValueKgs",e."createdById",e."sourceType",e."sourceId",
                          e."serviceDate"
                   FROM owner_revenue_source_events e
                   WHERE e.id=$1 AND e."propertyId"=$2 AND e.action='APPROVE_SOURCE'
                   AND NOT EXISTS(SELECT 1 FROM owner_revenue_source_events r
                     WHERE r."propertyId"=$2 AND r."reversesId"=e.id)""",
                body.source_event_id,pid)
            doc=await conn.fetchrow(
                """SELECT "uploadedById","documentDate" FROM owner_revenue_evidence_documents
                   WHERE id=$1 AND "propertyId"=$2""",body.evidence_document_id,pid)
            if (not ev or not doc or ev["sourceType"] not in ("ROOM_NIGHT","DINING_ORDER","OTHER_SERVICE")
                or ev["createdById"]==actor or doc["uploadedById"]==actor
                or doc["documentDate"]>date.today()):
                raise HTTPException(409,detail={"code":"REVENUE_INDEPENDENT_DOCUMENT_REVIEW_REQUIRED"})
            await conn.execute("SELECT owner_lock_revenue_posting($1,$2)",pid,body.source_event_id)
            if ((body.reduction_amount_kgs>0 and
                 (body.reduction_basis!="ADDITIONAL_TO_APPROVED_FACE" or body.correction_event_ids is None))
                or (body.reduction_amount_kgs==0 and body.reduction_basis is not None)):
                raise HTTPException(409,detail={"code":"REVENUE_REDUCTION_REVIEW_REQUIRED"})
            ids=await conn.fetchval("SELECT owner_active_revenue_correction_ids($1,$2)",pid,body.source_event_id)
            if body.correction_event_ids is None:
                if len(ids)>1:
                    raise HTTPException(409,detail={"code":"REVENUE_CORRECTION_SET_REVIEW_REQUIRED"})
            elif sorted(body.correction_event_ids)!=list(ids):
                raise HTTPException(409,detail={"code":"REVENUE_CORRECTION_SET_CHANGED"})
            if not await conn.fetchval(
                "SELECT owner_revenue_corrections_match_snapshot($1,$2,$3,$4,$5,$6,$7)",
                pid,body.source_event_id,body.evidence_document_id,actor,
                body.tax_amount_kgs,body.reduction_amount_kgs,ids):
                raise HTTPException(409,detail={"code":"REVENUE_CORRECTIONS_UNRECONCILED"})
            if ev["sourceType"]=="OTHER_SERVICE" and await conn.fetchval(
                "SELECT owner_guest_service_revenue_proof($1,$2,$3)",pid,ev["sourceId"],ev["serviceDate"])!=ev["faceValueKgs"]:
                raise HTTPException(409,detail={"code":"REVENUE_GUEST_SERVICE_NOT_QUALIFIED"})
            gross=Decimal(ev["faceValueKgs"])
            net=gross-body.tax_amount_kgs-body.reduction_amount_kgs
            if net<0 or (net==0 and body.tax_amount_kgs!=0):
                raise HTTPException(409,detail={"code":"REVENUE_TAX_COMPONENT_INVALID"})
            if net==0 and not await conn.fetchval(
                "SELECT owner_full_cancellation_proof($1,$2,$3,$4)",
                pid,body.source_event_id,gross,ids):
                raise HTTPException(409,detail={"code":"OWNER_FULL_CANCELLATION_PROOF_REQUIRED"})
            row=await conn.fetchrow(
                """INSERT INTO owner_revenue_accounting_certifications
                   (id,"propertyId","sourceEventId","evidenceDocumentId",
                    "reviewedById","grossAmountKgs","taxAmountKgs",
                    "netRevenueKgs","policyVersion",reason,
                    "reductionAmountKgs","reductionBasis","correctionEventIds")
                   VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13) RETURNING id""",
                body.id,pid,body.source_event_id,body.evidence_document_id,
                actor,gross,body.tax_amount_kgs,net,body.policy_version,body.reason,
                body.reduction_amount_kgs,body.reduction_basis,ids)
            await conn.execute(
                """INSERT INTO audit_logs
                   (id,"propertyId","actorType","actorId",action,resource,
                    "resourceId",source,result,"createdAt")
                   VALUES($1,$2,'STAFF',$3,'ACCOUNTING_REVENUE_CERTIFIED',
                          'OwnerRevenueSource',$4,'WEB_ADMIN','SUCCESS',now())""",
                uuid.uuid4(),pid,str(actor),str(body.source_event_id))
            return {"id":str(row["id"]),"already_processed":False,
                    "accounting_posted":False,"recognized_profit_kgs":None}


async def qualified_posting_source(conn,pid,proposal):
    """Only unmodified, verified delivered-source evidence; never client amounts."""
    if proposal["sourceType"]=="STOCK_CONSUMPTION":
        cost=await conn.fetchval(
            """SELECT owner_accounting_served_cogs_proof(
                  $1::uuid,$2::uuid,$3::date)""",
            pid,proposal["sourceId"],proposal["accountingDate"])
        if cost is None:
            raise HTTPException(409,detail={"code":"ACCOUNTING_SERVED_COGS_INCOMPLETE_OR_FOLIO_MISSING"})
        return {"faceValueKgs":cost,"sourceType":"STOCK_CONSUMPTION"}
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
    await conn.execute("SELECT owner_lock_revenue_posting($1,$2)",pid,proposal["sourceId"])
    row=await conn.fetchrow(
        """SELECT e."faceValueKgs",e."sourceType",e."sourceSnapshot",e."serviceDate",e."sourceId"
           FROM owner_revenue_source_events e
           WHERE e.id=$1 AND e."propertyId"=$2 AND e.action='APPROVE_SOURCE'
             AND NOT EXISTS(SELECT 1 FROM owner_revenue_source_events rev
               WHERE rev."propertyId"=$2 AND rev."reversesId"=e.id)""",
        proposal["sourceId"],pid)
    if not row:
        raise HTTPException(409,detail={"code":"ACCOUNTING_SOURCE_UNVERIFIED_OR_REVERSED"})
    if row["serviceDate"]!=proposal["accountingDate"]:
        raise HTTPException(409,detail={"code":"ACCOUNTING_REVENUE_SERVICE_DATE_MISMATCH"})
    if row["sourceType"]=="OTHER_SERVICE" and await conn.fetchval(
        "SELECT owner_guest_service_revenue_proof($1,$2,$3)",pid,row["sourceId"],row["serviceDate"])!=row["faceValueKgs"]:
        raise HTTPException(409,detail={"code":"REVENUE_GUEST_SERVICE_NOT_QUALIFIED"})
    cert=await conn.fetchrow(
        """SELECT "grossAmountKgs","taxAmountKgs","netRevenueKgs",
                  "evidenceDocumentId","reviewedById","taxCorrectionEventId",
                  "reductionAmountKgs",owner_revenue_certificate_current(c) AS current
           FROM owner_revenue_accounting_certifications c
           WHERE "propertyId"=$1 AND "sourceEventId"=$2
             AND "policyVersion"=$3""",
        pid,proposal["sourceId"],proposal["policyVersion"])
    if not cert or cert["grossAmountKgs"]!=row["faceValueKgs"]:
        raise HTTPException(409,detail={"code":"ACCOUNTING_CERTIFIED_SOURCE_DOCUMENT_REQUIRED"})
    if not cert["current"]:
        raise HTTPException(409,detail={"code":"ACCOUNTING_CORRECTIONS_NOT_RECONCILED"})
    return {**dict(row),**dict(cert)}


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
                                 source_amount=source["faceValueKgs"]-source.get("reductionAmountKgs",Decimal(0)),
                                 revenue_service_type=source["sourceType"])
                if proposal["sourceType"]=="REVENUE_SOURCE":
                    rev_code={"ROOM_NIGHT":"4100","DINING_ORDER":"4200","OTHER_SERVICE":"4300"}[source["sourceType"]]
                    sums=lambda code,side:sum(
                        (Decimal(r["amount_kgs"]) for r in lines
                          if r["account_code"]==code and r["side"]==side),
                        Decimal(0))
                    if (sums("1100","DEBIT")!=source["grossAmountKgs"]-source["reductionAmountKgs"]
                        or sums(rev_code,"CREDIT")!=source["netRevenueKgs"]
                        or sums("2100","CREDIT")!=source["taxAmountKgs"]):
                        raise ValueError("REVENUE_DOCUMENT_SPLIT_MISMATCH")
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


@router.get("/proposals/{proposal_id}/postings")
async def list_postings(proposal_id:uuid.UUID,request:Request,user=Depends(owner_only)):
    """Read back append-only POST + REVERSE events without declaring profit."""
    posting_guard()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction(isolation="repeatable_read",readonly=True):
            pid=await trusted_property_id(conn,user)
            exists=await conn.fetchval(
                'SELECT EXISTS(SELECT 1 FROM owner_accounting_journal_proposals '
                'WHERE id=$1 AND "propertyId"=$2)',proposal_id,pid)
            if not exists:
                raise HTTPException(404,detail={"code":"ACCOUNTING_PROPOSAL_NOT_FOUND"})
            headers=await conn.fetch(
                """SELECT * FROM owner_accounting_postings
                   WHERE "propertyId"=$1 AND "proposalId"=$2
                   ORDER BY "createdAt",id""",pid,proposal_id)
            out=[]
            for row in headers:
                lines=await conn.fetch(
                    """SELECT "lineNo","accountCode",side,"amountKgs"
                       FROM owner_accounting_posting_lines
                       WHERE "propertyId"=$1 AND "postingId"=$2
                       ORDER BY "lineNo" """,pid,row["id"])
                out.append({**posting_view(row),
                    "reverses_id":str(row["reversesId"]) if row["reversesId"] else None,
                    "lines":[{"line_no":l["lineNo"],"account_code":l["accountCode"],
                              "side":l["side"],"amount_kgs":str(l["amountKgs"])}
                             for l in lines]})
            return {"items":out,"recognized_profit_kgs":None,
                    "period_completeness_verified":False}


@router.get("/posted-subtotals")
async def posted_subtotals(request:Request,from_date:date=Query(),to_date:date=Query(),
                           user=Depends(owner_only)):
    """Operational ledger subtotals, expressly not closed-period P&L."""
    posting_guard()
    if from_date>to_date or (to_date-from_date).days>366:
        raise HTTPException(422,detail={"code":"ACCOUNTING_PERIOD_INVALID"})
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction(isolation="repeatable_read",readonly=True):
            pid=await trusted_property_id(conn,user)
            rows=await conn.fetch(
                """SELECT l."accountCode" AS account_code,
                          SUM(CASE WHEN l.side='CREDIT' THEN l."amountKgs"
                                   ELSE -l."amountKgs" END) AS net_credit
                   FROM owner_accounting_postings p
                   JOIN owner_accounting_posting_lines l
                     ON p.id=l."postingId" AND p."propertyId"=l."propertyId"
                   WHERE p."propertyId"=$1 AND p."accountingDate" BETWEEN $2 AND $3
                   GROUP BY l."accountCode" ORDER BY l."accountCode" """,
                pid,from_date,to_date)
            entries={r["account_code"]:Decimal(r["net_credit"]) for r in rows}
            revenue=sum((entries.get(c,Decimal(0)) for c in ("4100","4200","4300")),Decimal(0))
            expenses=-sum((entries.get(c,Decimal(0)) for c in ("5100","5200")),Decimal(0))
            return {
                "scope":"POSTED_LEDGER_SUBTOTALS_NOT_FULL_PROFIT",
                "posted_revenue_subtotal_kgs":str(revenue.quantize(Decimal("0.0001"))),
                "posted_expense_cogs_subtotal_kgs":str(expenses.quantize(Decimal("0.0001"))),
                "posted_contribution_subtotal_kgs":str((revenue-expenses).quantize(Decimal("0.0001"))),
                "recognized_profit_kgs":None,"period_completeness_verified":False,
                "blockers":["SERVICE_TAX_REFUND_EXPENSE_COGS_PERIOD_CLOSE_UNVERIFIED"],
            }


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

async def period_coverage(conn,pid,from_date,to_date,tz):
    """Read-only source-to-ledger coverage. A diagnostic, never a close approval."""
    from .owner_delivered_revenue import delivered_sources
    # Match each operational source by identity and service date, not totals.
    # Active POST means a POST without its exact REVERSE.
    rows=await conn.fetch(
        """WITH active_post AS (
             SELECT p.*,q."sourceType",q."sourceId"
             FROM owner_accounting_postings p
             JOIN owner_accounting_journal_proposals q
               ON q."propertyId"=p."propertyId" AND q.id=p."proposalId"
             WHERE p."propertyId"=$1 AND p.action='POST'
               AND NOT EXISTS(SELECT 1 FROM owner_accounting_postings r
                 WHERE r."propertyId"=$1 AND r."reversesId"=p.id AND r.action='REVERSE')
           ), sources AS (
             SELECT e.id,e."sourceType",e."sourceId",e."serviceDate",e."faceValueKgs"
             FROM owner_revenue_source_events e
             WHERE e."propertyId"=$1 AND e.action='APPROVE_SOURCE'
               AND e."serviceDate" BETWEEN $2 AND $3
               AND NOT EXISTS(SELECT 1 FROM owner_revenue_source_events r
                 WHERE r."propertyId"=$1 AND r."reversesId"=e.id AND r.action='REVERSE_SOURCE')
           )
           SELECT e.id,e."sourceType",e."sourceId",e."serviceDate",e."faceValueKgs",
                  p.id AS posting_id,
                  p."accountingDate" AS posting_date,
                  c.id AS certification_id,
                  c."grossAmountKgs" AS certified_gross,
                  owner_revenue_certificate_current(c) AS certificate_current,
                  owner_zero_revenue_certificate_current(c) AS zero_current
           FROM sources e
           LEFT JOIN active_post p ON p."sourceType"='REVENUE_SOURCE' AND p."sourceId"=e.id
           LEFT JOIN owner_revenue_accounting_certifications c
             ON c."propertyId"=$1 AND c."sourceEventId"=e.id
             AND (c."policyVersion"=p."policyVersion" OR
                  (p.id IS NULL AND c."netRevenueKgs"=0))
           ORDER BY e.id""",pid,from_date,to_date)
    by_key={(r["sourceType"],str(r["sourceId"]),r["serviceDate"].isoformat()):r for r in rows}
    matched=set()
    counts={"lodging_verified":0,"dining_verified":0}
    def match(kind,identifier,day,gross):
        key=(kind,str(identifier),str(day))
        row=by_key.get(key)
        if row is None:
            return False
        matched.add(key)
        return (row["certification_id"] is not None
                and row["certificate_current"] is True
                and row["certified_gross"]==row["faceValueKgs"]==Decimal(str(gross))
                and ((row["posting_id"] is not None and row["posting_date"]==row["serviceDate"])
                     or (row["posting_id"] is None and row["zero_current"] is True)))
    def observe_night(reservation_id,service_date,gross):
        if match("ROOM_NIGHT",reservation_id,service_date,gross):
            counts["lodging_verified"]+=1
    delivery=await delivered_sources(conn,pid,from_date,to_date,tz,on_night=observe_night)
    lodging=delivery["accommodation"]
    dining=delivery["dining"]
    counts["lodging_expected"]=lodging["delivered_booked_nights_count"]
    counts["dining_expected"]=dining["served_orders_count"]
    orders=await conn.fetch(
        """SELECT o.id,o.status,o."totalKgs",
                  (o."completedAt" AT TIME ZONE $4)::date AS served_local_date,
                  f.id AS folio_id,f.status AS folio_status,
                  f."sourceType" AS source_type,f."sourceId" AS source_id,
                  f."amountKgs" AS folio_amount,f."serviceDate" AS service_date
           FROM kitchen_orders o LEFT JOIN guest_folio_charges f
             ON f.id=o."folioChargeId" AND f."propertyId"=o."propertyId"
           WHERE o."propertyId"=$1 AND o.status='SERVED'
             AND (o."completedAt" AT TIME ZONE $4)::date BETWEEN $2 AND $3""",
        pid,from_date,to_date,tz)
    from .owner_delivered_revenue import classify_served_order
    for order in orders:
        if classify_served_order(order) is None and match(
            "DINING_ORDER",order["id"],order["served_local_date"],order["totalKgs"]):
            counts["dining_verified"]+=1
    other=await conn.fetch(
        """SELECT f."sourceType",f."sourceId",f."serviceDate",f."amountKgs",
                  CASE WHEN f."sourceType"='GUEST_SERVICE' THEN
                    owner_guest_service_revenue_proof($1,f."sourceId",f."serviceDate")
                  END AS qualified_amount
           FROM guest_folio_charges f WHERE f."propertyId"=$1
             AND f."sourceType"<>'KITCHEN_ORDER' AND f.status IN ('OPEN','PAID')
             AND f."serviceDate" BETWEEN $2 AND $3""",pid,from_date,to_date)
    counts["other_service_expected"]=len(other)
    counts["other_service_verified"]=sum(
        1 for item in other if item["qualified_amount"] is not None and match(
            "OTHER_SERVICE",item["sourceId"],item["serviceDate"],item["qualified_amount"]))
    coverage=await conn.fetchrow(
        """WITH active_post AS (
             SELECT q."sourceType",q."sourceId",p."accountingDate",p.id
             FROM owner_accounting_postings p JOIN owner_accounting_journal_proposals q
               ON q."propertyId"=p."propertyId" AND q.id=p."proposalId"
             WHERE p."propertyId"=$1 AND p.action='POST'
               AND NOT EXISTS(SELECT 1 FROM owner_accounting_postings r
                 WHERE r."propertyId"=$1 AND r."reversesId"=p.id AND r.action='REVERSE')
           )
           SELECT
             (SELECT count(*) FROM owner_expenses e WHERE e."propertyId"=$1
               AND e.status='POSTED' AND e."expenseDate" BETWEEN $2 AND $3) AS expense_expected,
             (SELECT count(*) FROM owner_expenses e JOIN active_post p
               ON p."sourceType"='OPERATING_EXPENSE' AND p."sourceId"=e.id
               AND p."accountingDate"=e."expenseDate"
               WHERE e."propertyId"=$1 AND e.status='POSTED'
                 AND e."expenseDate" BETWEEN $2 AND $3
                 AND e.category IN ('UTILITIES','PAYROLL','MAINTENANCE','RENT','MARKETING')
                 AND e."supplierName" IS NOT NULL AND e."documentReference" IS NOT NULL
                 AND NOT EXISTS(SELECT 1 FROM kitchen_supplier_documents d
                   WHERE d."propertyId"=$1 AND d."supplierName"=e."supplierName"
                     AND d."documentReference"=e."documentReference")
                 AND e."amountKgs"=(SELECT COALESCE(sum(l."amountKgs"),0)
                   FROM owner_accounting_posting_lines l WHERE l."propertyId"=$1
                     AND l."postingId"=p.id AND l."accountCode"='5200' AND l.side='DEBIT')
             ) AS expense_verified,
             (SELECT count(*) FROM kitchen_orders o JOIN active_post p
               ON p."sourceType"='STOCK_CONSUMPTION' AND p."sourceId"=o.id
               AND p."accountingDate"=(o."completedAt" AT TIME ZONE $4)::date
               WHERE o."propertyId"=$1 AND o.status='SERVED'
                 AND p."accountingDate" BETWEEN $2 AND $3
                 AND owner_accounting_served_cogs_proof($1,o.id,p."accountingDate")=
                   (SELECT COALESCE(sum(l."amountKgs"),0) FROM owner_accounting_posting_lines l
                     WHERE l."propertyId"=$1 AND l."postingId"=p.id
                       AND l."accountCode"='5100' AND l.side='DEBIT')
             ) AS cogs_verified,
             (SELECT count(*) FROM owner_revenue_correction_events c
               JOIN owner_revenue_source_events e ON e."propertyId"=c."propertyId" AND e.id=c."approvalId"
               WHERE c."propertyId"=$1 AND c.action='RECORD'
                 AND (c."documentDate" BETWEEN $2 AND $3 OR e."serviceDate" BETWEEN $2 AND $3)
                 AND NOT EXISTS(SELECT 1 FROM owner_revenue_correction_events r
                   WHERE r."propertyId"=$1 AND r."reversesId"=c.id AND r.action='REVERSE')
                 AND NOT EXISTS(SELECT 1 FROM owner_revenue_accounting_certifications cert
                   LEFT JOIN active_post p ON p."sourceType"='REVENUE_SOURCE'
                     AND p."sourceId"=cert."sourceEventId"
                     AND p."accountingDate"=e."serviceDate"
                   WHERE cert."propertyId"=$1 AND cert."sourceEventId"=e.id
                     AND (c.id=ANY(cert."correctionEventIds") OR
                       (cert."correctionEventIds" IS NULL AND cert."taxCorrectionEventId"=c.id))
                     AND owner_revenue_certificate_current(cert)
                     AND (p.id IS NOT NULL OR owner_zero_revenue_certificate_current(cert)))
             ) AS active_corrections""",pid,from_date,to_date,tz)
    counts.update(dict(coverage))
    # Entitlements are rights to meals, not proof of delivered paid value.
    # Do not let a period with unallocated package rights appear complete.
    package=await conn.fetchrow(
        """SELECT count(*)::int AS package_entitlement_count,
                  COALESCE(sum(e."adultPortions"+e."childPortions"),0)::bigint AS package_portions_count
           FROM dining_entitlements e
           WHERE e."propertyId"=$1 AND e.status='ACTIVE'
             AND e."serviceDate" BETWEEN $2 AND $3""",pid,from_date,to_date)
    counts.update(dict(package))
    # The canonical refund audit date is distinct from the service date.
    # Missing audit dates are explicit unresolved facts, not estimated refunds.
    refunds=await conn.fetchrow(
        """WITH candidates AS (
             SELECT pay.id,pay."amountKgs",
               EXISTS(SELECT 1 FROM audit_logs a WHERE a."propertyId"=$1
                 AND a."resourceId"=pay.id::text AND a.action='CONFIRM_MANUAL_FULL_REFUND'
                 AND a.resource='Payment' AND a.source='PMS_MANUAL_REFUND' AND a.result='SUCCESS'
                 AND ((a."createdAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date BETWEEN $2 AND $3
               ) AS in_period,
               EXISTS(SELECT 1 FROM audit_logs a WHERE a."propertyId"=$1
                 AND a."resourceId"=pay.id::text AND a.action='CONFIRM_MANUAL_FULL_REFUND'
                 AND a.resource='Payment' AND a.source='PMS_MANUAL_REFUND' AND a.result='SUCCESS'
               ) AS dated
             FROM payments pay JOIN reservations r ON r.id=pay."reservationId"
             WHERE r."propertyId"=$1 AND pay.status='REFUNDED'
           ), evidence AS (
             SELECT x.*,EXISTS(SELECT 1 FROM owner_revenue_refund_bindings b
                JOIN owner_revenue_accounting_certifications c
                  ON c."propertyId"=b."propertyId" AND c.id=b."certificateId"
                WHERE b."propertyId"=$1 AND b."paymentId"=x.id
                  AND owner_revenue_certificate_current(c)
                  AND owner_revenue_has_active_posting(c."propertyId",c."sourceEventId")) AS verified
             FROM candidates x
           )
           SELECT count(*) FILTER(WHERE in_period)::int AS refund_payment_expected,
                  count(*) FILTER(WHERE in_period AND verified)::int AS refund_payment_verified,
                  count(*) FILTER(WHERE NOT dated)::int AS refund_undated_count
           FROM evidence""",pid,from_date,to_date,tz)
    counts.update(dict(refunds))
    amounts=await conn.fetchrow(
        """SELECT count(*)::int AS posting_line_count,
                  COALESCE(sum(CASE WHEN l.side='CREDIT' THEN l."amountKgs" ELSE -l."amountKgs" END)
                   FILTER(WHERE l."accountCode" IN ('4100','4200','4300')),0) AS revenue,
                  COALESCE(sum(CASE WHEN l.side='DEBIT' THEN l."amountKgs" ELSE -l."amountKgs" END)
                   FILTER(WHERE l."accountCode" IN ('5100','5200')),0) AS expenses
           FROM owner_accounting_postings p JOIN owner_accounting_posting_lines l
             ON l."propertyId"=p."propertyId" AND l."postingId"=p.id
           WHERE p."propertyId"=$1 AND p."accountingDate" BETWEEN $2 AND $3""",
        pid,from_date,to_date)
    counts["cogs_expected"]=len(orders)
    counts["unmatched_approved_sources"]=len(set(by_key)-matched)
    blockers=[]
    for category in ("lodging","dining","other_service","expense","cogs"):
        if counts[category+"_expected"]!=counts[category+"_verified"]:
            blockers.append(category.upper()+"_SOURCE_COVERAGE_INCOMPLETE")
    if lodging["excluded_reservations_count"] or dining["excluded_orders_count"]:
        blockers.append("DELIVERED_SOURCE_QUALIFICATION_INCOMPLETE")
    if counts["unmatched_approved_sources"]:
        blockers.append("APPROVED_SOURCE_NOT_MATCHED_TO_DELIVERY")
    if counts["active_corrections"]:
        blockers.append("ACTIVE_CORRECTIONS_REQUIRE_ACCOUNTING_POLICY")
    if counts["other_service_expected"]!=counts["other_service_verified"] or dining["non_dining_undated_folio_count"]:
        blockers.append("OTHER_SERVICE_REVENUE_NOT_RECONCILED")
    if counts["package_entitlement_count"]:
        blockers.append("PACKAGE_DELIVERY_AND_VALUE_ALLOCATION_UNVERIFIED")
    if counts["refund_payment_expected"]!=counts["refund_payment_verified"] or counts["refund_undated_count"]:
        blockers.append("CASH_REFUND_RECONCILIATION_INCOMPLETE")
    # Even a perfect match of these supported source categories does not prove
    # legal document contents, completeness of all operations, or a sealed period.
    blockers.extend(["INDEPENDENT_DOCUMENT_CONTENT_REVIEW_REQUIRED",
                     "FULL_PERIOD_POLICY_AND_CLOSE_NOT_VERIFIED"])
    return {"scope":"PROPERTY_SCOPED_READ_ONLY_PERIOD_DIAGNOSTIC",
            "counts":counts,"blockers":blockers,
            "period":{"from":from_date.isoformat(),"to":to_date.isoformat()},
            "posted_ledger_subtotals":{
                "posting_line_count":amounts["posting_line_count"],
                "revenue_kgs":str(amounts["revenue"].quantize(Decimal("0.0001"))),
                "expense_cogs_kgs":str(amounts["expenses"].quantize(Decimal("0.0001"))),
                "contribution_kgs":str((amounts["revenue"]-amounts["expenses"]).quantize(Decimal("0.0001"))),
            },
            "period_completeness_verified":False,"recognized_profit_kgs":None,
            "currency":"KGS"}


@router.get("/period-coverage")
async def period_coverage_view(request:Request,from_date:date=Query(),to_date:date=Query(),
                               user=Depends(owner_only)):
    posting_guard()
    if from_date>to_date or (to_date-from_date).days>366:
        raise HTTPException(422,detail={"code":"ACCOUNTING_PERIOD_INVALID"})
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction(isolation="repeatable_read",readonly=True):
            pid=await trusted_property_id(conn,user)
            tz=await conn.fetchval('SELECT timezone FROM properties WHERE id=$1',pid)
            if not tz:
                raise HTTPException(503,detail={"code":"PROPERTY_TIMEZONE_UNAVAILABLE"})
            return await period_coverage(conn,pid,from_date,to_date,tz)

