"""Separate read-only MARINA FLEX agent/investor portal and admin overview.

DB role scopes are resolved from signed JWT subject + independent DB membership,
never from request parameters. All entries are QA_ONLY, no payout confirmation.
Not mounted in the existing hotel PMS or production FLEX API.
"""
from __future__ import annotations

import uuid
from calendar import monthrange
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Query, Request

from .flex_control_plane import (
    lifespan as core_lifespan,
    qa_password_reads,
    resolve_platform_principal,
)
from .flex_foundation import PlatformPrincipal

TZ = ZoneInfo("Asia/Bishkek")
READERS = frozenset({
    "flex_agent_statement_reader",
    "flex_investor_statement_reader",
    "flex_platform_statement_reader",
})


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with core_lifespan(app):
        async with app.state.flex_pool.acquire() as conn:
            for role in READERS:
                member = await conn.fetchval(
                    "SELECT pg_has_role(current_user,$1,'MEMBER')", role
                )
                inherited = await conn.fetchval(
                    "SELECT pg_has_role(current_user,$1,'USAGE')", role
                )
                if not member or inherited:
                    raise RuntimeError("FLEX partner reader must be a NOINHERIT membership: "+role)
        yield


app = FastAPI(
    title="MARINA FLEX Partner Earnings QA",
    version="0.1.0", lifespan=lifespan,
    docs_url=None, redoc_url=None, openapi_url=None,
)


def _window(period: str) -> tuple[datetime, datetime]:
    now = datetime.now(TZ)
    today = now.date()
    if period == "day":
        start_day = today
    elif period == "week":
        start_day = today - timedelta(days=today.weekday())
    elif period == "month":
        start_day = today.replace(day=1)
    else:
        raise ValueError("Unsupported reporting period")
    begin = datetime.combine(start_day, time.min, tzinfo=TZ).astimezone(timezone.utc)
    return begin, now.astimezone(timezone.utc)


async def _switch(conn, role: str, scope: str, value: str) -> None:
    if role not in READERS:
        raise RuntimeError("Unexpected partner reader")
    await conn.execute("SELECT set_config($1,$2,true)", scope, value)
    await conn.execute("SET LOCAL ROLE " + role)


@app.get("/health")
async def health():
    return {"status": "ok", "commercial_data": "QA_ONLY", "payouts_enabled": False}


@app.get("/v1/partner/me/earnings")
async def own_earnings(
    request: Request,
    period: str = Query("month", pattern="^(day|week|month)$"),
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    if principal.role == "SALES_AGENT" and principal.agent_id:
        role = "flex_agent_statement_reader"
        scope, party_id = "flex.authorized_agent_id", principal.agent_id
        column = "agent_id"
    elif principal.role == "INVESTOR" and principal.investor_id:
        if not (principal.mfa_verified or qa_password_reads()):
            raise HTTPException(403, detail="Investor MFA required")
        role = "flex_investor_statement_reader"
        scope, party_id = "flex.authorized_investor_id", principal.investor_id
        column = "investor_id"
    else:
        raise HTTPException(403, detail="Only verified agent or investor")
    start, end = _window(period)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(isolation="repeatable_read",readonly=True):
            await _switch(conn, role, scope, party_id)
            row = await conn.fetchrow(
                "SELECT "
                "coalesce(sum(amount) FILTER (WHERE entry_type='ACCRUAL'),0) AS gross,"
                "coalesce(sum(amount) FILTER (WHERE entry_type='REVERSAL'),0) AS refunded,"
                "count(*) AS events "
                "FROM flex_partner_earnings_entries "
                f"WHERE {column}=$1 AND recognized_at>=$2 AND recognized_at<=$3",
                __import__("uuid").UUID(party_id), start, end,
            )
            party_uuid=uuid.UUID(party_id)
            history=await conn.fetch(
                f"""SELECT e.id,e.entry_type,e.amount,e.recognized_at,r.hotel_id,r.sku
                    FROM flex_partner_earnings_entries e
                    JOIN flex_partner_rule_versions r ON r.id=e.rule_version_id
                    WHERE e.{column}=$1 AND e.recognized_at>=$2 AND e.recognized_at<=$3
                    ORDER BY e.recognized_at DESC,e.id DESC LIMIT 100""",
                party_uuid,start,end)
            if principal.role=="SALES_AGENT":
                details=await conn.fetch("""SELECT h.id AS hotel_id,h.display_name,h.status,
                    min(a.attributed_at) AS attributed_at,count(DISTINCT a.sku) AS attributed_modules
                    FROM flex_agent_attributions a JOIN flex_hotels h ON h.id=a.hotel_id
                    WHERE a.agent_id=$1 GROUP BY h.id,h.display_name,h.status ORDER BY h.display_name,h.id""",party_uuid)
                contracts=[]
            else:
                details=[]
                contracts=await conn.fetch("""SELECT id,contract_key,version,principal,share_bps,effective_from
                    FROM flex_investor_contract_versions WHERE investor_id=$1
                    ORDER BY contract_key,version DESC""",party_uuid)
            gross, refunded = row["gross"], row["refunded"]
            return {
                "role":principal.role,
                "period":period, "currency":"KGS",
                "accrued_gross_kg":f"{gross:.2f}",
                "reversed_kg":f"{refunded:.2f}",
                "net_accrued_kg":f"{gross-refunded:.2f}",
                "actual_paid_kg":None,
                "payout_status":"NOT_IMPLEMENTED",
                "events":row["events"],
                "history_truncated":row["events"]>len(history),
                "history":[{**dict(h),"amount":f"{h['amount']:.2f}"} for h in history],
                "assigned_hotels":[dict(h) for h in details],
                "contracts":[{**dict(c),"principal":f"{c['principal']:.2f}"} for c in contracts],
                "outstanding_payable_kg":None,
                "data_provenance":"QA_ONLY_NOT_BANK_RECONCILED",
            }


@app.get("/v1/platform/partner-earnings-summary")
async def admin_earnings_summary(
    request: Request,
    period: str = Query("month", pattern="^(day|week|month)$"),
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    if principal.role != "SUPER_ADMIN" or not (principal.mfa_verified or qa_password_reads()):
        raise HTTPException(403, detail="Platform SUPER_ADMIN with MFA required")
    start, end = _window(period)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await _switch(conn,"flex_platform_statement_reader","flex.admin_audit","1")
            rows = await conn.fetch(
                "SELECT CASE WHEN agent_id IS NOT NULL THEN 'SALES_AGENT' ELSE 'INVESTOR' END party,"
                "coalesce(sum(amount) FILTER (WHERE entry_type='ACCRUAL'),0) AS gross,"
                "coalesce(sum(amount) FILTER (WHERE entry_type='REVERSAL'),0) AS refunded,"
                "count(*) AS events "
                "FROM flex_partner_earnings_entries "
                "WHERE recognized_at>=$1 AND recognized_at<$2 "
                "GROUP BY 1 ORDER BY 1",
                start,end,
            )
            return {
                "period": period,"currency":"KGS",
                "data_provenance":"QA_ONLY_NOT_BANK_RECONCILED",
                "payouts_enabled":False,
                "groups":[{
                    "role":r["party"],
                    "accrued_gross_kg":f"{r['gross']:.2f}",
                    "reversed_kg":f"{r['refunded']:.2f}",
                    "net_accrued_kg":f"{r['gross']-r['refunded']:.2f}",
                    "events":r["events"],
                } for r in rows],
            }
