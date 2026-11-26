"""Separate read-only MARINA FLEX agent/investor portal and admin overview.

DB role scopes are resolved from signed JWT subject + independent DB membership,
never from request parameters. All entries are QA_ONLY, no payout confirmation.
Not mounted in the existing hotel PMS or production FLEX API.
"""
from __future__ import annotations

import uuid
from calendar import monthrange
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
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
                qa_assignments=await conn.fetch("""SELECT h.id AS hotel_id,h.display_name,h.status,q.created_at AS assigned_at
                    FROM (SELECT DISTINCT ON(hotel_id) hotel_id,action,created_at
                        FROM flex_qa_agent_assignments WHERE agent_id=$1 ORDER BY hotel_id,revision DESC) q
                    JOIN flex_hotels h ON h.id=q.hotel_id WHERE q.action='ASSIGN' ORDER BY h.display_name,h.id""",party_uuid)
                employment=await conn.fetchrow("SELECT action,created_at FROM flex_qa_agent_employment_events WHERE agent_id=$1 ORDER BY revision DESC LIMIT 1",party_uuid)
                month_start,_=_window("month")
                planned_connections=await conn.fetchval("""SELECT count(*) FROM
                    (SELECT hotel_id,min(created_at) AS first_assignment FROM flex_qa_agent_assignments
                     WHERE agent_id=$1 AND action='ASSIGN' GROUP BY hotel_id) a
                    WHERE first_assignment>=$2 AND first_assignment<=$3""",party_uuid,month_start,end)
                contracts=[]
                investment_plans=[]
            else:
                details=[]
                qa_assignments=[]
                employment=None
                planned_connections=None
                contracts=await conn.fetch("""SELECT id,contract_key,version,principal,share_bps,effective_from
                    FROM flex_investor_contract_versions WHERE investor_id=$1
                    ORDER BY contract_key,version DESC""",party_uuid)
                drafts=await conn.fetch("""SELECT id,investor_id,revision,principal,share_bps,bonus_months,revenue_basis,state,created_at
                    FROM flex_qa_investor_plans WHERE investor_id=$1 ORDER BY revision DESC""",party_uuid)
                links=await conn.fetch("SELECT plan_id,hotel_id,hotel_name_snapshot FROM flex_qa_investor_plan_hotels WHERE investor_id=$1 ORDER BY plan_id,hotel_id",party_uuid)
                by_plan={}
                for h in links:
                    by_plan.setdefault(h["plan_id"],[]).append(dict(h))
                investment_plans=[{**dict(p),"principal":str(p["principal"]),"hotels":by_plan.get(p["id"],[]),
                    "principal_received_kg":None,"principal_repaid_kg":None,"bonus_end":None} for p in drafts]
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
                "qa_assignments":[dict(h) for h in qa_assignments],
                "agent_terms":({"currency":"KGS","connection_fee":"7000.00","monthly_addon_fee":"500.00",
                    "monthly_salary":"10000.00","monthly_target":7,"employment_required":True,
                    "employment_state":("WORKING" if employment["action"]=="START" else "STOPPED") if employment else "UNRECORDED",
                    "employment_since":employment["created_at"] if employment else None,
                    "qa_new_assignments_this_month":planned_connections,
                    "paid_connections":None,"payable_amount":None} if principal.role=="SALES_AGENT" else None),
                "contracts":[{**dict(c),"principal":f"{c['principal']:.2f}"} for c in contracts],
                "investment_plans":investment_plans,
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


def investment_projection(principal: Decimal, share_bps: int, bonus_months: int,
                          monthly_revenue: Decimal, start_month: date, elapsed_months: int):
    """Hypothetical constant-revenue scenario; never evidence of actual cash."""
    if (principal,share_bps) not in {(Decimal("150000"),2500),(Decimal("250000"),3500),(Decimal("400000"),5000)} or bonus_months!=3:
        raise ValueError("Unsupported investment plan")
    if (not monthly_revenue.is_finite() or monthly_revenue<0 or monthly_revenue>Decimal("999999999999")
        or monthly_revenue!=monthly_revenue.quantize(Decimal("0.01")) or start_month.day!=1
        or not 2000<=start_month.year<=2090 or not 0<=elapsed_months<=120):
        raise ValueError("Invalid forecast scenario")
    share=(monthly_revenue*Decimal(share_bps)/Decimal(10000)).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
    def month_at(offset):
        year,month=divmod(start_month.year*12+start_month.month-1+offset,12)
        return date(year,month+1,1)
    def money(v): return f"{v:.2f}"
    zero=Decimal("0.00")
    months_to_return=int((principal+share-Decimal("0.01"))//share) if share else None
    repaid=min(principal,share*elapsed_months)
    remaining=principal-repaid
    bonus_paid=zero
    bonus_start=bonus_end=repayment_date=None
    final_principal_payment=None
    if months_to_return is not None and months_to_return<=120:
        bonus_start=month_at(months_to_return)
        repayment_date=bonus_start-timedelta(days=1)
        bonus_end=month_at(months_to_return+bonus_months)
        final_principal_payment=principal-share*(months_to_return-1)
        bonus_paid=share*min(bonus_months,max(0,elapsed_months-months_to_return))
    stage=("RETURN" if remaining>0 else "BONUS" if elapsed_months<months_to_return+bonus_months else "ENDED")
    return {"mode":"FORECAST_ONLY","currency":"KGS","stage":stage,
        "monthly_share":money(share),"projected_principal_repaid":money(repaid),
        "projected_principal_remaining":money(remaining),"projected_bonus_paid":money(bonus_paid),
        "projected_total_received":money(repaid+bonus_paid),
        "final_principal_payment":money(final_principal_payment) if final_principal_payment is not None else None,
        "months_to_return":months_to_return if months_to_return is not None and months_to_return<=120 else None,
        "projected_repayment_date":repayment_date,"bonus_start":bonus_start,"bonus_end_exclusive":bonus_end,
        "payouts_enabled":False,"actual_principal_repaid":None}


@app.get("/v1/partner/me/investment-projection")
async def own_investment_projection(request: Request,plan_id: uuid.UUID=Query(...),
    monthly_revenue: str=Query(...,pattern=r"^(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,2})?$"),
    start_month: date=Query(...),elapsed_months: int=Query(...,ge=0,le=120),
    principal: PlatformPrincipal=Depends(resolve_platform_principal)):
    if principal.role!="INVESTOR" or not principal.investor_id or not (principal.mfa_verified or qa_password_reads()):
        raise HTTPException(403,detail="Verified investor required")
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await _switch(conn,"flex_investor_statement_reader","flex.authorized_investor_id",principal.investor_id)
            row=await conn.fetchrow("SELECT principal,share_bps,bonus_months FROM flex_qa_investor_plans WHERE id=$1 AND investor_id=$2",plan_id,uuid.UUID(principal.investor_id))
            if row is None:
                raise HTTPException(404,detail="Investment proposal unavailable")
            try:
                return {"plan_id":str(plan_id),**investment_projection(row["principal"],row["share_bps"],row["bonus_months"],Decimal(monthly_revenue),start_month,elapsed_months)}
            except (ValueError,ArithmeticError):
                raise HTTPException(422,detail="Invalid forecast scenario") from None


@app.get("/v1/partner/me/proposals")
async def own_partner_proposals(request: Request,principal: PlatformPrincipal=Depends(resolve_platform_principal)):
    if principal.role!="PARTNER":
        raise HTTPException(403,detail="Partner membership required")
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await conn.execute("SELECT set_config('flex.authorized_subject_id',$1,true)",principal.subject_id)
            await conn.execute("SET LOCAL ROLE flex_identity_reader")
            rows=await conn.fetch("""SELECT id,partner_subject_id,hotel_id,revision,hotel_name_snapshot,title,terms_text,state,created_at
                FROM flex_qa_partner_proposals WHERE partner_subject_id=$1 ORDER BY hotel_id,revision DESC""",principal.subject_id)
            return {"role":"PARTNER","proposals":[dict(p) for p in rows],"payouts_enabled":False,
                "actual_paid_kg":None,"outstanding_payable_kg":None}
