"""Owner-only reconciliation of observed cash records, not income, profit or bank balance.

Customer payments have a RECEIVED fact; owner expenses have a separately entered
manual settlement fact. The difference is not statutory cash flow or P&L.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from .auth import require_roles, trusted_property_id

router = APIRouter(prefix="/api/v1/admin/finance/owner", tags=["owner-cash-reconciliation"])
owner_only = require_roles("OWNER", module_grant=False)


@router.get("/recorded-cash-movements")
async def recorded_cash_movements(
    request: Request, from_date: date = Query(), to_date: date = Query(),
    user=Depends(owner_only),
):
    if to_date < from_date or (to_date-from_date).days > 366:
        raise HTTPException(422, detail={"code": "OWNER_CASH_RECONCILIATION_RANGE"})
    async with request.app.state.db.acquire() as conn:
        pid=await trusted_property_id(conn,user)
        prop=await conn.fetchrow('SELECT timezone,currency FROM properties WHERE id=$1',pid)
        if not prop:
            raise HTTPException(503, detail={"code":"PROPERTY_UNAVAILABLE"})
        end=to_date+timedelta(days=1)
        bounds=await conn.fetchrow(
            "SELECT (($1::date::timestamp AT TIME ZONE $3) AT TIME ZONE 'UTC') AS start_ts, "
            "(($2::date::timestamp AT TIME ZONE $3) AT TIME ZONE 'UTC') AS end_ts",
            from_date,end,prop["timezone"])
        income=await conn.fetchrow(
            '''SELECT COALESCE(SUM(p."amountKgs"),0)::bigint AS received_kgs,
                      COUNT(*)::int AS received_count
               FROM payments p
               LEFT JOIN reservation_requests rr ON rr.id=p."requestId"
               LEFT JOIN reservations r ON r.id=p."reservationId"
               WHERE COALESCE(rr."propertyId",r."propertyId")=$1
                 AND p.status='RECEIVED'
                 AND COALESCE(p."paidAt",p."createdAt") >= $2
                 AND COALESCE(p."paidAt",p."createdAt") < $3''',
            pid,bounds["start_ts"],bounds["end_ts"])
        paid=await conn.fetchrow(
            '''SELECT COALESCE(SUM(s."amountKgs"),0)::bigint AS paid_kgs,
                      COUNT(*)::int AS settlement_count
               FROM owner_expense_settlements s JOIN owner_expenses e
                 ON e."propertyId"=s."propertyId" AND e.id=s."expenseId"
               WHERE s."propertyId"=$1 AND e.status='POSTED'
                 AND s."paidOn">=$2 AND s."paidOn"<$3''',
            pid,from_date,end)
        obligation=await conn.fetchrow(
            '''SELECT COALESCE(SUM(e."amountKgs"),0)::bigint AS posted_kgs,
                      COUNT(*)::int AS expense_count
               FROM owner_expenses e WHERE e."propertyId"=$1 AND e.status='POSTED'
                 AND e."expenseDate">=$2 AND e."expenseDate"<$3''',
            pid,from_date,end)
        outstanding=await conn.fetchval(
            '''SELECT COALESCE(SUM(e."amountKgs" - COALESCE(
                        (SELECT SUM(s."amountKgs") FROM owner_expense_settlements s
                         WHERE s."propertyId"=e."propertyId" AND s."expenseId"=e.id),0)),0)::bigint
               FROM owner_expenses e WHERE e."propertyId"=$1 AND e.status='POSTED' ''',pid)
    observed_difference=income["received_kgs"]-paid["paid_kgs"]
    return {
        "scope":"OWNER_ONLY_PROPERTY_SCOPED",
        "period":{"from":from_date.isoformat(),"to":to_date.isoformat(),
                  "currency":prop["currency"],"timezone":prop["timezone"]},
        "customer_payments_received_kgs":income["received_kgs"],
        "customer_payments_received_count":income["received_count"],
        "owner_expense_manual_settlements_kgs":paid["paid_kgs"],
        "owner_expense_manual_settlements_count":paid["settlement_count"],
        "observed_recorded_difference_kgs":observed_difference,
        "owner_expenses_posted_for_period_kgs":obligation["posted_kgs"],
        "owner_expenses_posted_count":obligation["expense_count"],
        "all_time_unsettled_expenses_kgs":outstanding,
        "truth":{
            "report_type":"OBSERVED_CASH_RECORDS_NOT_RECOGNIZED_PROFIT",
            "recognized_profit_kgs":None,
            "verified_bank_balance_kgs":None,
            "refunds_reconciled":False,
            "completeness_verified":False,
            "payment_created":False,
            "reason":"Received customer Payments minus manually recorded expense settlements excludes refunds, unrecorded payments, other cash movements, recognition timing and inventory accounting. Not profit, bank balance or full cash flow.",
        },
    }
