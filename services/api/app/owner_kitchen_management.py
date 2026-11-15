"""OWNER-only kitchen management cost and procurement exposure report.

Management estimates are inventory movements, not Payments, bills, statutory
expenses, recognized revenue or profit. Every query is property-scoped.
"""
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from .auth import require_roles, trusted_property_id

router = APIRouter(prefix="/api/v1/admin/finance/owner", tags=["owner-kitchen-management"])
owner_only = require_roles("OWNER")


@router.get("/kitchen-operations")
async def owner_kitchen_operations(
    request: Request,
    from_date: date = Query(),
    to_date: date = Query(),
    user=Depends(owner_only),
):
    if to_date < from_date or (to_date - from_date).days > 366:
        raise HTTPException(422, detail={"code": "INVALID_KITCHEN_REPORT_RANGE"})
    async with request.app.state.db.acquire() as conn:
        pid = await trusted_property_id(conn, user)
        tz = await conn.fetchval('SELECT timezone FROM properties WHERE id=$1', pid)
        if not tz:
            raise HTTPException(503, detail={"code": "PROPERTY_TIMEZONE_UNAVAILABLE"})
        # kitchen_* timestamps are TIMESTAMPTZ; convert property dates to absolute instants.
        bounds = await conn.fetchrow(
            "SELECT ($1::date::timestamp AT TIME ZONE $3) AS start_at, "
            "($2::date::timestamp AT TIME ZONE $3) AS end_at",
            from_date, to_date + timedelta(days=1), tz,
        )
        movements = await conn.fetch(
            '''SELECT m.kind, i."isSample" AS is_sample,
                      COUNT(*)::int AS movement_count,
                      COALESCE(SUM(m.quantity*m."unitCostKgs"),0) AS cost
               FROM kitchen_stock_movements m
               JOIN kitchen_stock_items i ON i."propertyId"=m."propertyId"
                   AND i.id=m."stockItemId"
               WHERE m."propertyId"=$1 AND m."createdAt">=$2 AND m."createdAt"<$3
               GROUP BY m.kind, i."isSample"''',
            pid, bounds["start_at"], bounds["end_at"],
        )
        valuation = await conn.fetchrow(
            '''WITH item_balances AS (
                 SELECT i.id, i."isSample", i."costPerUnitKgs",
                        COALESCE(SUM(CASE WHEN m.kind='RECEIPT' THEN m.quantity
                                          ELSE -m.quantity END),0) AS balance
                 FROM kitchen_stock_items i
                 LEFT JOIN kitchen_stock_movements m ON m."propertyId"=i."propertyId"
                     AND m."stockItemId"=i.id
                 WHERE i."propertyId"=$1
                 GROUP BY i.id
               )
               SELECT COALESCE(SUM(balance*"costPerUnitKgs") FILTER (WHERE NOT "isSample"),0)
                        AS real_inventory_value,
                      COALESCE(SUM(balance*"costPerUnitKgs") FILTER (WHERE "isSample"),0)
                        AS sample_inventory_value,
                      COUNT(*) FILTER (WHERE balance<0)::int AS negative_balance_items,
                      COUNT(*)::int AS item_count
               FROM item_balances''', pid,
        )
        commitments = await conn.fetchrow(
            '''SELECT COALESCE(SUM(
                 (p."requestedQuantity"-p."receivedQuantity")*i."costPerUnitKgs")
                   FILTER (WHERE p.status IN ('APPROVED','PARTIAL')
                          AND NOT i."isSample"),0) AS approved_unreceived_estimate,
                     COALESCE(SUM(
                 (p."requestedQuantity"-p."receivedQuantity")*i."costPerUnitKgs")
                   FILTER (WHERE p.status='REQUESTED' AND NOT i."isSample"),0)
                          AS unapproved_estimate,
                     COUNT(*) FILTER (WHERE p.status IN ('APPROVED','PARTIAL')
                          AND NOT i."isSample")::int AS approved_open_request_count,
                     COUNT(*) FILTER (WHERE p.status='REQUESTED'
                          AND NOT i."isSample")::int AS pending_approval_count
               FROM kitchen_procurement_requests p
               JOIN kitchen_stock_items i ON i.id=p."stockItemId"
                   AND i."propertyId"=p."propertyId"
               WHERE p."propertyId"=$1''', pid,
        )
    def segment(is_sample):
        return {
            kind: {
                "cost_kgs": str(next((row["cost"] for row in movements
                                      if row["kind"]==kind and row["is_sample"]==is_sample), Decimal(0))),
                "movement_count": sum(row["movement_count"] for row in movements
                                      if row["kind"]==kind and row["is_sample"]==is_sample),
            } for kind in ("RECEIPT", "PRODUCTION", "WASTE", "SPOILAGE")
        }
    real, sample = segment(False), segment(True)
    production_cost = Decimal(real["PRODUCTION"]["cost_kgs"])
    loss_cost = Decimal(real["WASTE"]["cost_kgs"]) + Decimal(real["SPOILAGE"]["cost_kgs"])
    return {
        "scope": "OWNER_ONLY_PROPERTY_SCOPED",
        "period": {"from": from_date.isoformat(), "to": to_date.isoformat(),
                   "timezone": tz},
        "real_inventory_movements": real,
        "sample_inventory_movements": sample,
        "real_production_cost_kgs": str(production_cost),
        "real_loss_cost_kgs": str(loss_cost),
        "real_total_consumption_and_loss_cost_kgs": str(production_cost+loss_cost),
        "current_stock": {
            "real_value_at_current_item_cost_kgs": str(valuation["real_inventory_value"]),
            "sample_value_at_current_item_cost_kgs": str(valuation["sample_inventory_value"]),
            "negative_balance_items": valuation["negative_balance_items"],
            "item_count": valuation["item_count"],
            "valuation_as_of": "CURRENT_NOT_PERIOD_END",
        },
        "procurement_exposure": {
            "approved_unreceived_at_current_item_cost_kgs": str(commitments["approved_unreceived_estimate"]),
            "unapproved_requests_at_current_item_cost_kgs": str(commitments["unapproved_estimate"]),
            "approved_open_request_count": commitments["approved_open_request_count"],
            "pending_approval_count": commitments["pending_approval_count"],
            "settled_supplier_payables_kgs": None,
        },
        "truth": {
            "report_type": "MANAGEMENT_OPERATIONAL_COSTS_NOT_ACCOUNTING",
            "receipt": "Stock receipt is inventory inflow, not a supplier payment or P&L expense.",
            "consumption": "PRODUCTION, WASTE and SPOILAGE values are cost snapshots from immutable stock movements.",
            "procurement": "Open requests are indicative commitments, not supplier invoices or recorded payments.",
            "inventory": "Stock value is calculated using current item unit cost, not historical or period-end valuation.",
            "profit": "NOT_AVAILABLE_WITHOUT_RECOGNIZED_REVENUE_AND_EXPENSE_LEDGER",
            "payment_created": False,
        },
    }
