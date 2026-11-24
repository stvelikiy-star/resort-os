"""Immutable proposed double-entry entries. No accounting recognition is enabled.

This P0 foundation is explicitly PENDING_ACCOUNTANT_APPROVAL and never feeds P&L.
Source evidence is checked against the tenant's immutable revenue evidence ledger.
"""
import hashlib
import json
import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from .auth import require_roles, trusted_property_id
from .owner_revenue_source_journal import lock_keys

router = APIRouter(prefix="/api/v1/admin/finance/owner/accounting-journal",
                   tags=["owner-accounting-journal"])
owner_only = require_roles("OWNER", module_grant=False)


class JournalLine(BaseModel):
    account_code: str = Field(pattern=r"^[A-Za-z0-9._-]{2,32}$")
    side: Literal["DEBIT", "CREDIT"]
    amount_kgs: Decimal = Field(gt=0, max_digits=20, decimal_places=4,
                                allow_inf_nan=False)
    memo: str = Field(default="", max_length=300)


class JournalProposal(BaseModel):
    id: uuid.UUID
    source_type: Literal["REVENUE_SOURCE", "REVENUE_CORRECTION"]
    source_id: uuid.UUID
    accounting_date: date
    policy_version: str = Field(min_length=3, max_length=80)
    reason: str = Field(min_length=8, max_length=500)
    lines: list[JournalLine] = Field(min_length=2, max_length=128)

    @field_validator("reason", "policy_version")
    @classmethod
    def nonblank(cls, value, info):
        v = " ".join(value.split())
        minimum = 8 if info.field_name == "reason" else 3
        if len(v) < minimum:
            raise ValueError("Policy or reason is too short after whitespace normalization")
        return v


def fingerprint(body: JournalProposal) -> str:
    payload = body.model_dump(mode="json", exclude={"id"})
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def validate_balanced(lines: list[JournalLine]):
    debit = sum((line.amount_kgs for line in lines if line.side == "DEBIT"), Decimal(0))
    credit = sum((line.amount_kgs for line in lines if line.side == "CREDIT"), Decimal(0))
    if debit != credit or debit <= 0:
        raise ValueError("Debits and credits must balance exactly")
    return debit


async def validate_source(conn, pid, body: JournalProposal):
    if body.source_type == "REVENUE_SOURCE":
        source = await conn.fetchrow(
            '''SELECT id FROM owner_revenue_source_events
               WHERE "propertyId"=$1 AND id=$2 AND action='APPROVE_SOURCE'
                 AND NOT EXISTS (SELECT 1 FROM owner_revenue_source_events rev
                    WHERE rev."propertyId"=$1 AND rev."reversesId"=$2)''',
            pid, body.source_id)
    else:
        source = await conn.fetchrow(
            '''SELECT c.id FROM owner_revenue_correction_events c
               JOIN owner_revenue_evidence_documents d
                 ON d.id=c."evidenceDocumentId" AND d."propertyId"=c."propertyId"
               WHERE c."propertyId"=$1 AND c.id=$2 AND c.action='RECORD'
                 AND NOT EXISTS (SELECT 1 FROM owner_revenue_correction_events rev
                    WHERE rev."propertyId"=$1 AND rev."reversesId"=$2)''',
            pid, body.source_id)
    if not source:
        raise HTTPException(409, detail={"code": "ACCOUNTING_SOURCE_UNVERIFIED_OR_REVERSED"})


def representation(row, lines, replay=False):
    return {
        "id": str(row["id"]),
        "source_type": row["sourceType"],
        "source_id": str(row["sourceId"]),
        "accounting_date": row["accountingDate"].isoformat(),
        "currency": row["currency"],
        "status": row["status"],
        "policy_version": row["policyVersion"],
        "reason": row["reason"],
        "created_at": row["createdAt"].isoformat(),
        "already_processed": replay,
        "lines": [{
            "line_no": r["lineNo"], "account_code": r["accountCode"],
            "side": r["side"], "amount_kgs": str(r["amountKgs"]),
            "memo": r["memo"]
        } for r in lines],
        "accounting_posted": False,
        "accountant_approved": False,
        "recognized_revenue_kgs": None,
        "recognized_expense_kgs": None,
        "recognized_profit_kgs": None,
    }


@router.post("/proposals", status_code=201)
async def propose(body: JournalProposal, request: Request, user=Depends(owner_only)):
    try:
        validate_balanced(body.lines)
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "ACCOUNTING_LINES_UNBALANCED"}) from exc
    digest = fingerprint(body)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await trusted_property_id(conn, user)
            actor = uuid.UUID(str(user["id"]))
            await lock_keys(conn, "accounting-journal-id:" + str(body.id),
                            "accounting-journal-source:" + str(pid) + ":" +
                            body.source_type + ":" + str(body.source_id))
            old = await conn.fetchrow(
                'SELECT * FROM owner_accounting_journal_proposals WHERE id=$1', body.id)
            if old:
                if old["propertyId"] != pid or old["payloadHash"] != digest or old["createdById"] != actor:
                    raise HTTPException(409, detail={"code": "ACCOUNTING_OPERATION_ID_CONFLICT"})
                old_lines = await conn.fetch(
                    'SELECT * FROM owner_accounting_journal_proposal_lines WHERE "proposalId"=$1 ORDER BY "lineNo"', body.id)
                return representation(old, old_lines, True)
            await validate_source(conn, pid, body)
            duplicate = await conn.fetchval(
                'SELECT id FROM owner_accounting_journal_proposals WHERE "propertyId"=$1 AND "sourceType"=$2 AND "sourceId"=$3',
                pid, body.source_type, body.source_id)
            if duplicate:
                raise HTTPException(409, detail={"code": "ACCOUNTING_SOURCE_ALREADY_PROPOSED"})
            row = await conn.fetchrow(
                '''INSERT INTO owner_accounting_journal_proposals
                   (id,"propertyId","sourceType","sourceId","accountingDate",
                    "policyVersion",reason,"payloadHash","createdById")
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING *''',
                body.id, pid, body.source_type, body.source_id, body.accounting_date,
                body.policy_version, body.reason, digest, actor)
            for index, line in enumerate(body.lines, start=1):
                await conn.execute(
                    '''INSERT INTO owner_accounting_journal_proposal_lines
                       ("proposalId","propertyId","lineNo","accountCode","side","amountKgs",memo)
                       VALUES($1,$2,$3,$4,$5,$6,$7)''',
                    body.id, pid, index, line.account_code, line.side,
                    line.amount_kgs, line.memo)
            lines = await conn.fetch(
                'SELECT * FROM owner_accounting_journal_proposal_lines WHERE "proposalId"=$1 ORDER BY "lineNo"', body.id)
            return representation(row, lines)


@router.get("/proposals")
async def list_proposals(request: Request, from_date: date = Query(),
                         to_date: date = Query(), user=Depends(owner_only)):
    if from_date > to_date or (to_date - from_date).days > 366:
        raise HTTPException(422, detail={"code": "ACCOUNTING_PERIOD_INVALID"})
    async with request.app.state.db.acquire() as conn:
        pid = await trusted_property_id(conn, user)
        rows = await conn.fetch(
            '''SELECT * FROM owner_accounting_journal_proposals
               WHERE "propertyId"=$1 AND "accountingDate" BETWEEN $2 AND $3
               ORDER BY "accountingDate" DESC, "createdAt" DESC LIMIT 500''',
            pid, from_date, to_date)
        results = []
        for row in rows:
            lines = await conn.fetch(
                'SELECT * FROM owner_accounting_journal_proposal_lines WHERE "propertyId"=$1 AND "proposalId"=$2 ORDER BY "lineNo"',
                pid, row["id"])
            results.append(representation(row, lines))
        return {"items": results, "status": "PROPOSED_ONLY",
                "recognized_profit_kgs": None, "accounting_posted": False}


# Evidence-only approval workflow. It never posts a ledger or supplies
# recognized P&L; the accounting policy and completeness release gates remain
# deliberately separate. Disabled by default and forbidden in shared preview.
class JournalDecision(BaseModel):
    id: uuid.UUID
    action: Literal["APPROVE", "REVERSE"]
    reason: str = Field(min_length=8, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_decision_reason(cls, value):
        result = " ".join(value.split())
        if len(result) < 8:
            raise ValueError("Reason must explain the decision")
        return result


def _decision_preview_guard():
    import os
    if (os.getenv("APP_ENV") != "staging"
            or os.getenv("MARINA_SHARED_AUTH_PREVIEW_ENABLED", "false").lower() == "true"
            or os.getenv("MARINA_ACCOUNTING_DECISION_EVIDENCE_ENABLED", "false").lower() != "true"):
        raise HTTPException(503, detail={"code": "ACCOUNTING_DECISIONS_DISABLED"})


async def _source_still_verified(conn, pid, proposal):
    if proposal["sourceType"] == "REVENUE_SOURCE":
        return await conn.fetchval(
            """SELECT EXISTS(
                 SELECT 1 FROM owner_revenue_source_events e
                 WHERE e.id=$2 AND e."propertyId"=$1 AND e.action='APPROVE_SOURCE'
                   AND NOT EXISTS(
                     SELECT 1 FROM owner_revenue_source_events rev
                     WHERE rev."propertyId"=$1 AND rev."reversesId"=e.id))""",
            pid, proposal["sourceId"])
    if proposal["sourceType"] == "REVENUE_CORRECTION":
        return await conn.fetchval(
            """SELECT EXISTS(
                 SELECT 1 FROM owner_revenue_correction_events e
                 JOIN owner_revenue_evidence_documents d
                   ON d.id=e."evidenceDocumentId" AND d."propertyId"=e."propertyId"
                 WHERE e.id=$2 AND e."propertyId"=$1 AND e.action='RECORD'
                   AND NOT EXISTS(
                     SELECT 1 FROM owner_revenue_correction_events rev
                     WHERE rev."propertyId"=$1 AND rev."reversesId"=e.id))""",
            pid, proposal["sourceId"])
    return False


@router.post("/proposals/{proposal_id}/decisions", status_code=201)
async def record_decision(proposal_id: uuid.UUID, body: JournalDecision,
                          request: Request, user=Depends(owner_only)):
    _decision_preview_guard()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await trusted_property_id(conn, user)
            actor = uuid.UUID(str(user["id"]))
            await lock_keys(conn, "accounting-journal-decision:" + str(pid) + ":" + str(proposal_id))
            proposal = await conn.fetchrow(
                'SELECT * FROM owner_accounting_journal_proposals WHERE id=$1 AND "propertyId"=$2',
                proposal_id, pid)
            if not proposal:
                raise HTTPException(404, detail={"code": "ACCOUNTING_PROPOSAL_NOT_FOUND"})
            if proposal["createdById"] == actor:
                raise HTTPException(403, detail={"code": "ACCOUNTING_SELF_APPROVAL_FORBIDDEN"})
            old = await conn.fetchrow(
                """SELECT * FROM owner_accounting_journal_decisions
                   WHERE "propertyId"=$1 AND "proposalId"=$2 AND action=$3""",
                pid, proposal_id, body.action)
            if old:
                if old["id"] != body.id or old["actorId"] != actor or old["reason"] != body.reason:
                    raise HTTPException(409, detail={"code": "ACCOUNTING_DECISION_CONFLICT"})
                return {"id": str(old["id"]), "action": old["action"], "already_processed": True,
                        "accounting_posted": False, "recognized_profit_kgs": None}
            approval_id = None
            if body.action == "APPROVE":
                if not await _source_still_verified(conn, pid, proposal):
                    raise HTTPException(409, detail={"code": "ACCOUNTING_SOURCE_UNVERIFIED_OR_REVERSED"})
            else:
                approval_id = await conn.fetchval(
                    """SELECT id FROM owner_accounting_journal_decisions
                       WHERE "propertyId"=$1 AND "proposalId"=$2 AND action='APPROVE'""",
                    pid, proposal_id)
                if approval_id is None:
                    raise HTTPException(409, detail={"code": "ACCOUNTING_APPROVAL_REQUIRED"})
            await conn.execute(
                """INSERT INTO owner_accounting_journal_decisions
                   (id,"propertyId","proposalId",action,"approvalId","actorId",reason)
                   VALUES($1,$2,$3,$4,$5,$6,$7)""",
                body.id, pid, proposal_id, body.action, approval_id, actor, body.reason)
            await conn.execute(
                """INSERT INTO audit_logs
                   (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"createdAt")
                   VALUES($1,$2,'STAFF',$3,$4,'AccountingJournalProposal',$5,'WEB_ADMIN','SUCCESS',now())""",
                uuid.uuid4(), pid, str(actor), "ACCOUNTING_EVIDENCE_" + body.action,
                str(proposal_id))
            return {"id": str(body.id), "action": body.action, "already_processed": False,
                    "accounting_posted": False, "recognized_profit_kgs": None}


@router.get("/proposals/{proposal_id}/decisions")
async def list_decisions(proposal_id: uuid.UUID, request: Request, user=Depends(owner_only)):
    _decision_preview_guard()
    async with request.app.state.db.acquire() as conn:
        pid = await trusted_property_id(conn, user)
        exists = await conn.fetchval(
            'SELECT 1 FROM owner_accounting_journal_proposals WHERE id=$1 AND "propertyId"=$2',
            proposal_id, pid)
        if not exists:
            raise HTTPException(404, detail={"code": "ACCOUNTING_PROPOSAL_NOT_FOUND"})
        rows = await conn.fetch(
            """SELECT id,action,"actorId",reason,"createdAt","approvalId"
               FROM owner_accounting_journal_decisions
               WHERE "propertyId"=$1 AND "proposalId"=$2 ORDER BY "createdAt",id""",
            pid, proposal_id)
        actions = {r["action"] for r in rows}
        state = ("EVIDENCE_REVERSED" if "REVERSE" in actions else
                 "EVIDENCE_APPROVED" if "APPROVE" in actions else
                 "PENDING_ACCOUNTANT_APPROVAL")
        return {
            "proposal_id": str(proposal_id), "evidence_status": state,
            "decisions": [
                {"id": str(row["id"]), "action": row["action"],
                 "actor_id": str(row["actorId"]), "reason": row["reason"],
                 "approval_id": str(row["approvalId"]) if row["approvalId"] else None,
                 "created_at": row["createdAt"].isoformat()}
                for row in rows],
            "accounting_posted": False, "recognized_profit_kgs": None,
        }
