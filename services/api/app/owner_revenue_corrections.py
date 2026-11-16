"""Append-only documented revenue-source corrections for OWNER.

This is financial *evidence* rather than statutory accounting. The document
fingerprint and its storage reference are declared by OWNER; the server cannot
attest that bytes were actually uploaded or independently authenticated.
No customer Payment, recognized revenue/expenses/profit, or tax payment is made.
"""
import hashlib
import json
import re
import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from .auth import require_roles, trusted_property_id
from .owner_revenue_source_journal import lock_keys

router = APIRouter(prefix="/api/v1/admin/finance/owner/revenue-corrections",
                   tags=["owner-revenue-correction-evidence"])
owner_only = require_roles("OWNER",module_grant=False)
MONEY=Decimal("0.0001")
REDUCERS=("DISCOUNT","CANCELLATION")
CLASSIFIERS=("PACKAGE_SPLIT","TAX_COMPONENT")
ALL_KINDS=(*REDUCERS,"REFUND",*CLASSIFIERS)


class CorrectionWrite(BaseModel):
    id: uuid.UUID
    approval_id: uuid.UUID
    kind: Literal["DISCOUNT","PACKAGE_SPLIT","CANCELLATION","REFUND","TAX_COMPONENT"]
    component: Literal["LODGING","DINING","OTHER","UNALLOCATED"]
    amount_kgs: Decimal = Field(gt=0,max_digits=20,decimal_places=4,
                                allow_inf_nan=False)
    document_reference: str = Field(min_length=4,max_length=150)
    document_date: date
    document_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_document_id: uuid.UUID
    evidence_reference: str = Field(min_length=8,max_length=300)
    reason: str = Field(min_length=8,max_length=500)

    @field_validator("document_reference","evidence_reference","reason")
    @classmethod
    def normalize_reference(cls,v,info):
        x=" ".join(v.split())
        minimum=4 if info.field_name=="document_reference" else 8
        if len(x)<minimum:
            raise ValueError("Document reference, evidence or reason is blank")
        return x


class CorrectionReversal(BaseModel):
    id: uuid.UUID
    reason: str = Field(min_length=8,max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls,value):
        normalized=" ".join(value.split())
        if len(normalized)<8:
            raise ValueError("Reversal reason must contain at least 8 nonblank characters")
        return normalized


def validate_correction(kind,component,amount,face,totals):
    """Validate aggregate *candidate* amounts, never treat cash as earned income.

    Refund is only a reported cash-related claim and is deliberately excluded
    from net-revenue candidate arithmetic to avoid counting cancellation twice.
    """
    if kind not in ALL_KINDS or amount<=0 or face<0:
        raise ValueError("Invalid source adjustment")
    if kind in CLASSIFIERS and component=="UNALLOCATED":
        raise ValueError("Classification requires component")
    if kind=="PACKAGE_SPLIT" and totals["PACKAGE_SPLIT"]+amount>face:
        raise ValueError("Package allocation exceeds source")
    if kind=="TAX_COMPONENT" and totals["TAX_COMPONENT"]+amount>face:
        raise ValueError("Tax component exceeds source")
    if kind in REDUCERS and totals["DISCOUNT"]+totals["CANCELLATION"]+amount>face:
        raise ValueError("Discount and cancellation exceed source face value")
    if kind=="REFUND" and totals["REFUND"]+amount>face:
        raise ValueError("Referenced refunds exceed source face value")
    if kind=="PACKAGE_SPLIT" and totals["DISCOUNT"]+totals["CANCELLATION"]+totals["PACKAGE_SPLIT"]+amount>face:
        raise ValueError("Package allocation exceeds remaining face value")
    if kind in REDUCERS and totals["PACKAGE_SPLIT"]+totals["DISCOUNT"]+totals["CANCELLATION"]+amount>face:
        raise ValueError("Remaining face cannot cover classified package")
    if kind in REDUCERS and totals["TAX_COMPONENT"]+totals["DISCOUNT"]+totals["CANCELLATION"]+amount>face:
        raise ValueError("Remaining face cannot cover classified tax component")
    if kind=="TAX_COMPONENT" and totals["DISCOUNT"]+totals["CANCELLATION"]+totals["TAX_COMPONENT"]+amount>face:
        raise ValueError("Tax component exceeds remaining face value")
    return True


def view(row,repeated=False):
    return {
        "id":str(row["id"]),
        "approval_id":str(row["approvalId"]),
        "action":row["action"],
        "kind":row["kind"],
        "component":row["component"],
        "amount_kgs":str(row["amountKgs"]),
        "document_reference":row["documentReference"],
        "document_date":row["documentDate"].isoformat(),
        "document_sha256":row["documentSha256"],
        "evidence_document_id":str(row["evidenceDocumentId"]) if row["evidenceDocumentId"] else None,
        "bytes_sha256_verified_by_server":row["evidenceDocumentId"] is not None,
        "evidence_reference":row["evidenceReference"],
        "reason":row["reason"],
        "reverses_id":str(row["reversesId"]) if row["reversesId"] else None,
        "already_processed":repeated,
        "document_authenticity_verified":False,
        "accounting_posted":False,
        "payment_created":False,
        "recognized_net_revenue_kgs":None,
        "recognized_profit_kgs":None,
    }


async def totals_for_approval(conn,pid,approval_id):
    rows=await conn.fetch(
        '''SELECT e.kind,COALESCE(SUM(e."amountKgs"),0) AS amount
           FROM owner_revenue_correction_events e
           WHERE e."propertyId"=$1 AND e."approvalId"=$2 AND e.action='RECORD'
             AND NOT EXISTS(SELECT 1 FROM owner_revenue_correction_events r
                  WHERE r."propertyId"=e."propertyId" AND r."reversesId"=e.id)
           GROUP BY e.kind''',pid,approval_id)
    out={kind:Decimal("0") for kind in ALL_KINDS}
    for row in rows:out[row["kind"]]=Decimal(row["amount"])
    return out


@router.post("",status_code=201)
async def record_correction(body:CorrectionWrite,request:Request,user=Depends(owner_only)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            owner_id=uuid.UUID(str(user["id"]))
            await lock_keys(conn,
                "revenue-correction-event:"+str(body.id),
                "revenue-approval:"+str(pid)+":"+str(body.approval_id))
            old=await conn.fetchrow(
                'SELECT * FROM owner_revenue_correction_events WHERE id=$1',body.id)
            if old:
                if (old["propertyId"]!=pid or old["approvalId"]!=body.approval_id or
                    old["action"]!="RECORD" or old["kind"]!=body.kind or
                    old["component"]!=body.component or
                    old["amountKgs"]!=body.amount_kgs or
                    old["documentReference"]!=body.document_reference or
                    old["documentDate"]!=body.document_date or
                    old["documentSha256"]!=body.document_sha256 or
                    old["evidenceDocumentId"]!=body.evidence_document_id or
                    old["evidenceReference"]!=body.evidence_reference or
                    old["reason"]!=body.reason or old["createdById"]!=owner_id):
                    raise HTTPException(409,detail={"code":"REVENUE_CORRECTION_ID_CONFLICT"})
                return view(old,True)
            source=await conn.fetchrow(
                '''SELECT * FROM owner_revenue_source_events
                   WHERE "propertyId"=$1 AND id=$2 AND action='APPROVE_SOURCE' ''',
                pid,body.approval_id)
            if not source:
                raise HTTPException(404,detail={"code":"REVENUE_APPROVED_SOURCE_MISSING"})
            reversed_=await conn.fetchval(
                'SELECT id FROM owner_revenue_source_events WHERE "propertyId"=$1 '
                'AND "reversesId"=$2 AND action=\'REVERSE_SOURCE\'',
                pid,body.approval_id)
            if reversed_:
                raise HTTPException(409,detail={"code":"REVENUE_SOURCE_REVERSED"})
            duplicate=await conn.fetchval(
                '''SELECT id FROM owner_revenue_correction_events
                   WHERE "propertyId"=$1 AND "approvalId"=$2 AND kind=$3
                     AND component=$4 AND
                     ("documentReference"=$5 OR "documentSha256"=$6)
                     AND action='RECORD' ''',
                pid,body.approval_id,body.kind,body.component,
                body.document_reference,body.document_sha256)
            if duplicate:
                raise HTTPException(409,detail={"code":"REVENUE_CORRECTION_DOCUMENT_ALREADY_USED"})
            evidence=await conn.fetchrow(
                '''SELECT * FROM owner_revenue_evidence_documents
                   WHERE "propertyId"=$1 AND id=$2''',pid,body.evidence_document_id)
            if not evidence:
                raise HTTPException(404,detail={"code":"REVENUE_EVIDENCE_DOCUMENT_NOT_FOUND"})
            if (evidence["documentReference"]!=body.document_reference or
                evidence["documentDate"]!=body.document_date or
                evidence["sha256"]!=body.document_sha256 or
                hashlib.sha256(bytes(evidence["content"])).hexdigest()!=body.document_sha256):
                raise HTTPException(409,detail={"code":"REVENUE_EVIDENCE_MISMATCH"})
            totals=await totals_for_approval(conn,pid,body.approval_id)
            try:
                validate_correction(body.kind,body.component,body.amount_kgs,
                                    Decimal(source["faceValueKgs"]),totals)
            except ValueError as exc:
                raise HTTPException(409,detail={"code":"REVENUE_CORRECTION_TOTAL_CONFLICT",
                                                "reason":str(exc)}) from exc
            snapshot={"source_type":source["sourceType"],
                      "source_id":str(source["sourceId"]),
                      "service_date":source["serviceDate"].isoformat(),
                      "approved_face_value_kgs":str(source["faceValueKgs"]),
                      "document_verification":"BYTE_HASH_SERVER_VERIFIED_AUTHENTICITY_UNREVIEWED",
                      "evidence_document_id":str(body.evidence_document_id),
                      "recognized_revenue":False}
            row=await conn.fetchrow(
                '''INSERT INTO owner_revenue_correction_events
                   (id,"propertyId","approvalId",action,kind,component,"amountKgs",
                    "documentReference","documentDate","documentSha256",
                    "evidenceReference",reason,"sourceSnapshot","createdById","evidenceDocumentId")
                   VALUES ($1,$2,$3,'RECORD',$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb,$13,$14)
                   RETURNING *''',
                body.id,pid,body.approval_id,body.kind,body.component,
                body.amount_kgs,body.document_reference,body.document_date,
                body.document_sha256,body.evidence_reference,body.reason,
                json.dumps(snapshot,separators=(",",":")),owner_id,
                body.evidence_document_id)
            return view(row)


@router.post("/{correction_id}/reverse",status_code=201)
async def reverse_correction(correction_id:uuid.UUID,body:CorrectionReversal,
                             request:Request,user=Depends(owner_only)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            owner_id=uuid.UUID(str(user["id"]))
            row_for_lock=await conn.fetchrow(
                'SELECT "approvalId" FROM owner_revenue_correction_events '
                'WHERE "propertyId"=$1 AND id=$2 AND action=\'RECORD\'',
                pid,correction_id)
            if not row_for_lock:
                raise HTTPException(404,detail={"code":"REVENUE_CORRECTION_NOT_FOUND"})
            await lock_keys(conn,
                "revenue-approval:"+str(pid)+":"+str(row_for_lock["approvalId"]),
                "revenue-correction-event:"+str(body.id))
            prior=await conn.fetchrow(
                'SELECT * FROM owner_revenue_correction_events WHERE id=$1',body.id)
            if prior:
                if (prior["propertyId"]!=pid or prior["reversesId"]!=correction_id
                    or prior["action"]!="REVERSE" or prior["reason"]!=body.reason
                    or prior["createdById"]!=owner_id):
                    raise HTTPException(409,detail={"code":"REVENUE_CORRECTION_REVERSAL_ID_CONFLICT"})
                return view(prior,True)
            original=await conn.fetchrow(
                'SELECT * FROM owner_revenue_correction_events '
                'WHERE "propertyId"=$1 AND id=$2 AND action=\'RECORD\'',
                pid,correction_id)
            dup=await conn.fetchval(
                'SELECT id FROM owner_revenue_correction_events '
                'WHERE "propertyId"=$1 AND "reversesId"=$2 AND action=\'REVERSE\'',
                pid,correction_id)
            if dup:
                raise HTTPException(409,detail={"code":"REVENUE_CORRECTION_ALREADY_REVERSED"})
            source_snapshot=original["sourceSnapshot"]
            if not isinstance(source_snapshot,str):
                source_snapshot=json.dumps(source_snapshot,separators=(",",":"))
            inserted=await conn.fetchrow(
                '''INSERT INTO owner_revenue_correction_events
                   (id,"propertyId","approvalId",action,kind,component,"amountKgs",
                    "documentReference","documentDate","documentSha256",
                    "evidenceReference",reason,"reversesId","sourceSnapshot","createdById","evidenceDocumentId")
                   VALUES ($1,$2,$3,'REVERSE',$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,$14,$15)
                   RETURNING *''',
                body.id,pid,original["approvalId"],original["kind"],
                original["component"],original["amountKgs"],
                original["documentReference"],original["documentDate"],
                original["documentSha256"],original["evidenceReference"],
                body.reason,correction_id,source_snapshot,owner_id,
                original["evidenceDocumentId"])
            return view(inserted)


async def correction_snapshot(conn,pid,from_date,to_date):
    rows=await conn.fetch(
        '''SELECT e.kind,e."amountKgs",e."documentSha256",e.action,e.id,
                  EXISTS (SELECT 1 FROM owner_revenue_correction_events r
                    WHERE r."propertyId"=e."propertyId"
                      AND r."reversesId"=e.id) AS reversed_
           FROM owner_revenue_correction_events e
           JOIN owner_revenue_source_events s ON s.id=e."approvalId"
                AND s."propertyId"=e."propertyId"
           WHERE e."propertyId"=$1 AND s."serviceDate">=$2
                 AND s."serviceDate"<=$3''',pid,from_date,to_date)
    summary={kind:Decimal("0") for kind in ALL_KINDS}
    entries=0;reversals=0
    for r in rows:
        if r["action"]=="REVERSE":
            reversals+=1
        else:
            entries+=1
            if not r["reversed_"]:
                summary[r["kind"]]+=Decimal(r["amountKgs"])
    return {"recorded_corrections_count":entries,
            "reversed_corrections_count":reversals,
            "active_by_kind_kgs":{k:str(v.quantize(MONEY)) for k,v in summary.items()},
            "metadata_only_documents_not_independently_verified":True,
            "refunds_are_cash_evidence_not_recognized_revenue":True,
            "tax_and_packages_are_classifications_not_expenses":True,
            "recognized_revenue_kgs":None,
            "recognized_profit_kgs":None,
            "status":"SOURCE_CORRECTIONS_NOT_ACCOUNTING_POSTINGS"}


@router.get("")
async def list_corrections(request:Request,from_date:date=Query(),to_date:date=Query(),
                           user=Depends(owner_only)):
    if from_date>to_date or (to_date-from_date).days>366:
        raise HTTPException(422,detail={"code":"REVENUE_CORRECTION_DATE_RANGE"})
    async with request.app.state.db.acquire() as conn:
        pid=await trusted_property_id(conn,user)
        rows=await conn.fetch(
            '''SELECT e.* FROM owner_revenue_correction_events e
               JOIN owner_revenue_source_events s ON s.id=e."approvalId"
                 AND s."propertyId"=e."propertyId"
               WHERE e."propertyId"=$1 AND s."serviceDate">=$2
                 AND s."serviceDate"<=$3
               ORDER BY e."createdAt" DESC,e.id DESC LIMIT 200''',
            pid,from_date,to_date)
        return {"scope":"OWNER_ONLY_PROPERTY_SCOPED",
                "items":[view(r) for r in rows],"limit":200,
                "document_authenticity_verified":False,
                "history_append_only":True,
                "recognized_profit_kgs":None,
                "accounting_policy_status":"CORRECTION_EVIDENCE_REQUIRES_REVIEW"}
