"""Read-only production-to-served-dish cost trace for OWNER.

Production batches are grouped by hotel/menu/date. An individual served order
is NOT linked to a batch yet: all allocated amounts below are *candidates*,
not booked COGS or recognized profit. Read under the caller's repeatable-read
transaction, with property ID resolved from its authenticated OWNER session.
"""
from decimal import Decimal, ROUND_HALF_UP

ROUND = Decimal("0.0001")


def money(value):
    return str(Decimal(value).quantize(ROUND, rounding=ROUND_HALF_UP))


def reconcile_menu_day(prepared_rows, served_rows):
    """Aggregate same-day production and service without double counting stock.

    If served > deducted, the excess cannot be given a production cost.
    All matching is an estimate by item/date, never evidence of per-order batch
    consumption. Production on a different date is not silently matched.
    """
    groups = {}
    for row in prepared_rows:
        key = (str(row["menu_item_id"]), row["service_date"])
        group = groups.setdefault(key, {
            "menu_item_id": key[0], "service_date": key[1].isoformat(),
            "prepared_portions": 0, "deducted_portions": 0, "served_portions": 0,
            "production_cost": Decimal(0), "meal_types": set(),
        })
        group["prepared_portions"] += int(row["prepared_portions"])
        group["deducted_portions"] += int(row["deducted_portions"])
        group["production_cost"] += Decimal(row["cost_kgs"])
        group["meal_types"].add(row["meal_type"])
    for row in served_rows:
        key = (str(row["menu_item_id"]), row["service_date"])
        group = groups.setdefault(key, {
            "menu_item_id": key[0], "service_date": key[1].isoformat(),
            "prepared_portions": 0, "deducted_portions": 0, "served_portions": 0,
            "production_cost": Decimal(0), "meal_types": set(),
        })
        group["served_portions"] += int(row["served_portions"])
    result = []
    for group in sorted(groups.values(), key=lambda x: (x["service_date"], x["menu_item_id"])):
        deducted = group["deducted_portions"]
        served = group["served_portions"]
        matched = min(served, deducted)
        rate = group["production_cost"] / deducted if deducted else Decimal(0)
        candidate = rate * matched
        remaining = group["production_cost"] - candidate
        result.append({
            "menu_item_id": group["menu_item_id"],
            "service_date": group["service_date"],
            "meal_type_count": len(group["meal_types"]),
            "prepared_portions": group["prepared_portions"],
            "deducted_portions": deducted,
            "served_portions": served,
            "potentially_matched_portions": matched,
            "served_without_same_day_production_portions": max(0, served - deducted),
            "produced_not_matched_to_served_portions": max(0, deducted - served),
            "production_cost_kgs": money(group["production_cost"]),
            "proportional_served_cost_candidate_kgs": money(candidate),
            "unallocated_production_cost_candidate_kgs": money(remaining),
            "batch_match_verified": False,
        })
    return {
        "status": "CANDIDATE_NOT_RECOGNIZED",
        "matching_basis": "SAME_HOTEL_MENU_ITEM_LOCAL_SERVICE_DATE",
        "batch_to_order_link_verified": False,
        "served_cost_is_accounting_cogs": False,
        "totals": {
            "production_cost_kgs": money(sum((Decimal(x["production_cost_kgs"]) for x in result), Decimal(0))),
            "proportional_served_cost_candidate_kgs": money(sum((Decimal(x["proportional_served_cost_candidate_kgs"]) for x in result), Decimal(0))),
            "unallocated_production_cost_candidate_kgs": money(sum((Decimal(x["unallocated_production_cost_candidate_kgs"]) for x in result), Decimal(0))),
            "served_without_same_day_production_portions": sum(x["served_without_same_day_production_portions"] for x in result),
        },
        "items": result,
        "limitations": (
            "This is a proportional same-day menu-item estimate, not actual batch-to-order "
            "traceability. Other-day prep, multiple meal periods, waste of prepared dishes, "
            "sample batches and late service may require individual reconciliation."
        ),
    }


async def owner_served_kitchen_cost_trace(conn, property_id, from_date, to_date, timezone):
    end = to_date
    # Aggregate EACH target first: joining order items directly to stock movements
    # would multiply both expense and served counts (cartesian fanout).
    prepared = await conn.fetch(
        """
        SELECT t."menuItemId" AS menu_item_id, t."serviceDate" AS service_date,
               t."mealType" AS meal_type,
               t."preparedQuantity"::int AS prepared_portions,
               COALESCE(progress."deductedPortions",0)::int AS deducted_portions,
               COALESCE(cost.cost_kgs,0)::numeric AS cost_kgs
        FROM kitchen_production_targets t
        LEFT JOIN kitchen_stock_production_progress progress
          ON progress."propertyId"=t."propertyId"
         AND progress."productionTargetId"=t.id
        LEFT JOIN LATERAL (
           SELECT COALESCE(SUM(m.quantity*m."unitCostKgs")
             FILTER (WHERE NOT i."isSample"),0) AS cost_kgs
           FROM kitchen_stock_movements m
           JOIN kitchen_stock_items i ON i.id=m."stockItemId"
             AND i."propertyId"=m."propertyId"
           WHERE m."propertyId"=t."propertyId"
             AND m."productionTargetId"=t.id AND m.kind='PRODUCTION'
        ) cost ON true
        WHERE t."propertyId"=$1 AND t."serviceDate">=$2 AND t."serviceDate"<=$3
        """, property_id, from_date, end,
    )
    served = await conn.fetch(
        """
        SELECT i."menuItemId" AS menu_item_id,
               (o."completedAt" AT TIME ZONE $4)::date AS service_date,
               SUM(i.quantity)::int AS served_portions
        FROM kitchen_orders o
        JOIN kitchen_order_items i ON i."orderId"=o.id
        WHERE o."propertyId"=$1 AND o.status='SERVED'
          AND o."completedAt" IS NOT NULL
          AND (o."completedAt" AT TIME ZONE $4)::date BETWEEN $2 AND $3
          AND i.status='SERVED'
        GROUP BY i."menuItemId", (o."completedAt" AT TIME ZONE $4)::date
        """, property_id, from_date, end, timezone,
    )
    return reconcile_menu_day(prepared, served)
