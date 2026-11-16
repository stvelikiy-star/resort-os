"""OWNER accrual-readiness: source-backed candidate flows, NOT recognized profit.

Cash receipts, obligations, stock movements, supplier credit notes and served
orders are separate facts. No accounting journal automatically recognizes
revenue from a reservation, payment, restaurant order or folio receivable.
This read-only report deliberately exposes NULL recognized totals.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from .auth import require_roles, trusted_property_id
from .owner_kitchen_reconciliation import owner_inventory_reconciliation

router = APIRouter(prefix="/api/v1/admin/finance/owner",
                 tags=["owner-accrual-readiness"])
owner_only=require_roles("OWNER", module_grant=False)
MONEY=Decimal("0.0001")
NON_STOCK_CATEGORIES=("UTILITIES","PAYROLL","MAINTENANCE","RENT","MARKETING")
STOCK_AMBIGUOUS_CATEGORIES=("SUPPLIES","OTHER")


def amount(value):
    """Keep monetary outputs exact; never float or silently fabricate a zero."""
    return str(Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP))


def expense_breakdown(rows):
    by_category={category:Decimal(0) for category in
                 (*NON_STOCK_CATEGORIES,*STOCK_AMBIGUOUS_CATEGORIES)}
    count=0
    for row in rows:
        category=row["category"]
        value=Decimal(row["cost"])
        if category not in by_category or value<0:
            raise ValueError("Expense category or amount is not recognizable")
        by_category[category]+=value
        count+=int(row["movement_count"])
    non_stock=sum((by_category[k] for k in NON_STOCK_CATEGORIES),Decimal(0))
    ambiguous=sum((by_category[k] for k in STOCK_AMBIGUOUS_CATEGORIES),Decimal(0))
    return {"posted_total_kgs":amount(non_stock+ambiguous),
            "non_stock_obligations_candidate_kgs":amount(non_stock),
            "stock_overlap_review_kgs":amount(ambiguous),
            "posted_count":count,
            "categories_kgs":{key:amount(value) for key,value in by_category.items()},
            "status":"CLASSIFICATION_REQUIRED" if ambiguous else "POSTED_NOT_RECOGNIZED"}


async def accrual_source_snapshot(conn,pid,from_date:date,to_date:date,tz:str):
    """Caller holds a repeatable-read transaction and has already authorized OWNER."""
    end=to_date+timedelta(days=1)
    bounds=await conn.fetchrow(
        "SELECT ($1::date::timestamp AT TIME ZONE $3) AS start_at,"
        " ($2::date::timestamp AT TIME ZONE $3) AS end_at",
        from_date,end,tz)
    expenses=await conn.fetch(
        '''SELECT category,COUNT(*)::int AS movement_count,
                  COALESCE(SUM("amountKgs"),0) AS cost
           FROM owner_expenses
           WHERE "propertyId"=$1 AND status='POSTED'
             AND "expenseDate">=$2 AND "expenseDate"<$3
           GROUP BY category''',pid,from_date,end)
    expense=expense_breakdown(expenses)
    # Match explicitly referenced supplier documents as duplication warnings,
    # not automatic adjustments. NULL references cannot prove non-duplication.
    supplier_overlap=await conn.fetchrow(
        '''SELECT COUNT(*)::int AS linked_count,
                  COALESCE(SUM(e."amountKgs"),0) AS linked_amount
           FROM owner_expenses e
           JOIN kitchen_supplier_documents d
             ON d."propertyId"=e."propertyId"
             AND d."supplierName"=e."supplierName"
             AND d."documentReference"=e."documentReference"
           WHERE e."propertyId"=$1 AND e.status='POSTED'
             AND e."expenseDate">=$2 AND e."expenseDate"<$3''',
        pid,from_date,end)
    movements=await conn.fetch(
        '''SELECT m.kind,i."isSample" AS is_sample,
                  COUNT(*)::int AS movement_count,
                  ROUND(COALESCE(SUM(m.quantity*m."unitCostKgs"),0),4) AS cost
           FROM kitchen_stock_movements m
           JOIN kitchen_stock_items i ON i."propertyId"=m."propertyId"
              AND i.id=m."stockItemId"
           WHERE m."propertyId"=$1 AND m."createdAt">=$2 AND m."createdAt"<$3
           GROUP BY m.kind,i."isSample"''',
        pid,bounds["start_at"],bounds["end_at"])
    def movements_cost(kinds,include_sample=False):
        return sum((Decimal(r["cost"]) for r in movements if r["kind"] in kinds
                    and (include_sample or not r["is_sample"])), Decimal(0))
    production=movements_cost(("PRODUCTION",))
    loss=movements_cost(("WASTE","SPOILAGE"))
    returned=movements_cost(("SUPPLIER_RETURN",))
    received=movements_cost(("RECEIPT",))
    samples=movements_cost(("RECEIPT","PRODUCTION","WASTE","SPOILAGE","SUPPLIER_RETURN"),True)-(
        received+production+loss+returned)
    # A served order is an *operational candidate*. Even a charge marked OPEN
    # is not earned revenue without confirmed source/recognition policy.
    dining=await conn.fetchrow(
        '''SELECT
             COUNT(*)::int AS served_count,
             COALESCE(SUM(o."totalKgs"),0) AS served_face_value,
             COUNT(*) FILTER (WHERE f.id IS NULL)::int AS without_folio_count,
             COALESCE(SUM(o."totalKgs") FILTER (WHERE f.id IS NULL),0)
               AS without_folio_face_value,
             COUNT(*) FILTER (WHERE f.id IS NOT NULL
                 AND f.status IN ('OPEN','PAID'))::int AS active_folio_count,
             COALESCE(SUM(o."totalKgs") FILTER (WHERE f.id IS NOT NULL
                 AND f.status IN ('OPEN','PAID')),0) AS active_folio_face_value,
             COUNT(*) FILTER (WHERE f.id IS NOT NULL AND (
                 f.status NOT IN ('OPEN','PAID')
                 OR f."amountKgs"<>o."totalKgs"))::int
                 AS disputed_folio_count
           FROM kitchen_orders o
           LEFT JOIN guest_folio_charges f ON f.id=o."folioChargeId"
             AND f."propertyId"=o."propertyId"
             AND f."sourceType"='KITCHEN_ORDER' AND f."sourceId"=o.id
           WHERE o."propertyId"=$1 AND o.status='SERVED'
             AND o."completedAt">=$2 AND o."completedAt"<$3''',
        pid,bounds["start_at"],bounds["end_at"])
    manual_folio=await conn.fetchrow(
        '''SELECT COUNT(*)::int AS charge_count,
                  COALESCE(SUM("amountKgs"),0) AS face_value
           FROM guest_folio_charges
           WHERE "propertyId"=$1 AND "sourceType"='MANUAL'
             AND status IN ('OPEN','PAID')
             AND "serviceDate">=$2 AND "serviceDate"<$3''',
        pid,from_date,end)
    no_date=await conn.fetchval(
        '''SELECT COUNT(*)::int FROM guest_folio_charges
           WHERE "propertyId"=$1 AND "sourceType"='MANUAL'
             AND status IN ('OPEN','PAID') AND "serviceDate" IS NULL''',pid)
    lodging=await conn.fetchrow(
        '''SELECT COUNT(*)::int AS checked_out_count,
                  COALESCE(SUM("totalKgs"),0) AS booked_total
           FROM reservations WHERE "propertyId"=$1
             AND status='CHECKED_OUT' AND "checkOut">=$2 AND "checkOut"<$3''',
        pid,from_date,end)
    # The carried value and outstanding payable from the same read snapshot
    # are warnings; neither supplier settlement nor invoice is kitchen COGS.
    reconciliation=await owner_inventory_reconciliation(conn,pid)
    stock=reconciliation["inventory"]
    supplier=reconciliation["supplier_documents"]
    blockers=[
        "RECOGNIZED_REVENUE_LEDGER_NOT_APPROVED",
        "ACCOMMODATION_NIGHTLY_RECOGNITION_NOT_RECONCILED",
        "FOLIO_AND_REFUND_RECOGNITION_NOT_RECONCILED",
        "PRODUCTION_COST_TO_SERVED_ORDERS_NOT_ALLOCATED",
        "TAX_PAYROLL_DEPRECIATION_AND_ADJUSTMENTS_NOT_RECONCILED",
    ]
    if Decimal(expense["stock_overlap_review_kgs"]):
        blockers.append("OWNER_SUPPLIES_OR_OTHER_EXPENSE_CLASSIFICATION_REQUIRED")
    if supplier_overlap["linked_count"]:
        blockers.append("OWNER_EXPENSE_SUPPLIER_INVOICE_POSSIBLE_DUPLICATE")
    if stock["valuation_status"]!="MOVEMENT_BASED":
        blockers.append("STOCK_CARRYING_VALUE_RECONCILIATION_REQUIRED")
    if stock["linked_source"]["source_mismatch_count"]:
        blockers.append("LEGACY_RECEIPT_VS_INVOICE_COST_DIFFERENCE")
    if Decimal(supplier["return_credit_minus_stock_cost_kgs"]):
        blockers.append("SUPPLIER_RETURN_DIFFERENCE_NOT_RECOGNIZED")
    if dining["without_folio_count"] or dining["disputed_folio_count"]:
        blockers.append("DINING_FOLIO_SOURCE_INCOMPLETE")
    if no_date:
        blockers.append("MANUAL_FOLIO_SERVICE_DATE_MISSING")
    return {
        "scope":"OWNER_ONLY_PROPERTY_SCOPED",
        "period":{"from":from_date.isoformat(),"to":to_date.isoformat(),
                  "timezone":tz,"currency":"KGS"},
        "posted_owner_obligations":expense | {
            "matching_supplier_invoice_count":supplier_overlap["linked_count"],
            "matching_supplier_invoice_kgs":amount(supplier_overlap["linked_amount"]),
        },
        "kitchen_cost_movements":{
            "production_cost_candidate_kgs":amount(production),
            "loss_cost_candidate_kgs":amount(loss),
            "receipt_inventory_inflow_kgs":amount(received),
            "supplier_return_inventory_debit_kgs":amount(returned),
            "sample_movement_gross_kgs":amount(samples),
            "costs_are_reconciled_to_revenue":False,
        },
        "revenue_source_candidates":{
            "served_dining_orders_count":dining["served_count"],
            "served_dining_face_value_kgs":amount(dining["served_face_value"]),
            "served_without_linked_folio_count":dining["without_folio_count"],
            "served_without_linked_folio_kgs":amount(dining["without_folio_face_value"]),
            "served_with_active_folio_count":dining["active_folio_count"],
            "served_with_active_folio_kgs":amount(dining["active_folio_face_value"]),
            "disputed_dining_folio_count":dining["disputed_folio_count"],
            "manual_folio_active_count":manual_folio["charge_count"],
            "manual_folio_face_value_kgs":amount(manual_folio["face_value"]),
            "manual_folio_without_service_date_count":no_date,
            "checked_out_reservations_count":lodging["checked_out_count"],
            "checked_out_booked_total_kgs":amount(lodging["booked_total"]),
            "amounts_are_not_additive_or_recognized":True,
        },
        "source_valuation":{
            "inventory_valuation_status":stock["valuation_status"],
            "source_mismatch_count":stock["linked_source"]["source_mismatch_count"],
            "supplier_return_credit_minus_stock_cost_kgs":
                supplier["return_credit_minus_stock_cost_kgs"],
            "supplier_payables_outstanding_kgs":supplier["outstanding_payables_kgs"],
        },
        "recognition":{
            "status":"REQUIRES_APPROVED_RECOGNITION_LEDGER",
            "blockers":blockers,
            "recognized_revenue_kgs":None,
            "recognized_expenses_kgs":None,
            "recognized_profit_kgs":None,
            "completeness_verified":False,
            "customer_payments_are_revenue":False,
            "supplier_settlements_are_expenses":False,
            "receipts_are_expenses":False,
            "source_candidates_are_recognized":False,
        },
    }


@router.get("/accrual-readiness")
async def accrual_readiness(request:Request,from_date:date=Query(),
                            to_date:date=Query(),user=Depends(owner_only)):
    if to_date<from_date or (to_date-from_date).days>366:
        raise HTTPException(422,detail={"code":"OWNER_ACCRUAL_DATE_RANGE_INVALID"})
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction(isolation="repeatable_read",readonly=True):
            pid=await trusted_property_id(conn,user)
            tz=await conn.fetchval('SELECT timezone FROM properties WHERE id=$1',pid)
            if not tz:
                raise HTTPException(503,detail={"code":"PROPERTY_TIMEZONE_UNAVAILABLE"})
            return await accrual_source_snapshot(conn,pid,from_date,to_date,tz)
