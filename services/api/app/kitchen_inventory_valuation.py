"""Moving weighted-average inventory valuation for a single locked stock item.

All callers MUST hold kitchen_stock_items ... FOR UPDATE inside the same transaction
before reading the movement ledger and posting a debit. Historical movement rows are
immutable. Existing receipt snapshots (including unlinked legacy receipts) remain
the opening valuation basis; the algorithm must never silently substitute catalog
prices when historical movement value is inconsistent.
"""
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException

COST_QUANTUM = Decimal("0.0001")
COST_MAX = Decimal("9999999999.9999")  # numeric(14,4)


def weighted_unit_cost(quantity: Decimal, inventory_value: Decimal) -> Decimal:
    """Return 4dp weighted price; block unknown/corrupt historical opening balances."""
    if quantity <= 0 or inventory_value < 0:
        raise HTTPException(409, detail={"code": "KITCHEN_VALUATION_RECONCILIATION_REQUIRED"})
    raw = inventory_value / quantity
    result = raw.quantize(COST_QUANTUM, rounding=ROUND_HALF_UP)
    if result < 0 or result > COST_MAX:
        raise HTTPException(409, detail={"code": "KITCHEN_VALUATION_RECONCILIATION_REQUIRED"})
    return result


async def locked_stock_valuation(conn, property_id, stock_item_id):
    """Get remaining physical quantity and acquisition-based movement value.

    The current historical ledger uses quantity * unitCostKgs for both receipts
    and debits. No retroactive price overwrite, no supplier payment or P&L posting.
    """
    row = await conn.fetchrow(
        '''SELECT COALESCE(SUM(CASE WHEN kind='RECEIPT' THEN quantity
                                    ELSE -quantity END),0) AS balance,
                  COALESCE(SUM(CASE WHEN kind='RECEIPT'
                                THEN quantity*"unitCostKgs"
                                ELSE -quantity*"unitCostKgs" END),0) AS value
           FROM kitchen_stock_movements
           WHERE "propertyId"=$1 AND "stockItemId"=$2''',
        property_id,stock_item_id)
    balance, value = row["balance"], row["value"]
    if balance < 0 or value < 0 or (balance == 0 and abs(value) > Decimal("0.01")):
        raise HTTPException(409, detail={"code": "KITCHEN_VALUATION_RECONCILIATION_REQUIRED"})
    return balance,value


def debit_cost(balance: Decimal, value: Decimal, quantity: Decimal) -> Decimal:
    if quantity > balance or quantity <= 0:
        raise HTTPException(409, detail={"code": "KITCHEN_STOCK_INSUFFICIENT"})
    if balance <= 0 or value < 0:
        raise HTTPException(409, detail={"code": "KITCHEN_VALUATION_RECONCILIATION_REQUIRED"})
    return weighted_unit_cost(balance,value)
