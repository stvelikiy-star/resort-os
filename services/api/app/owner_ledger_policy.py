"""Fail-closed general-ledger posting policy for MARINA OWNER.

Cash settlements and inventory purchases are balance-sheet entries; only
service revenue, supported COGS and period expenses affect recognized profit.
No period completeness may be inferred from the presence of journal entries.
"""
from decimal import Decimal, InvalidOperation

ACCOUNTS = {
    "1100": ("RECEIVABLE", "ASSET"),
    "1000": ("CASH", "ASSET"),
    "1300": ("INVENTORY", "ASSET"),
    "2100": ("TAX_PAYABLE", "LIABILITY"),
    "2200": ("SUPPLIER_PAYABLE", "LIABILITY"),
    "4100": ("LODGING_REVENUE", "REVENUE"),
    "4200": ("DINING_REVENUE", "REVENUE"),
    "4300": ("OTHER_SERVICE_REVENUE", "REVENUE"),
    "5100": ("SERVED_FOOD_COGS", "EXPENSE"),
    "5200": ("OPERATING_EXPENSE", "EXPENSE"),
}
REVENUE_CODES = frozenset(k for k,v in ACCOUNTS.items() if v[1]=="REVENUE")
EXPENSE_CODES = frozenset(k for k,v in ACCOUNTS.items() if v[1]=="EXPENSE")
MONEY = Decimal("0.0001")


def exact_amount(value):
    try:
        x = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError("Invalid KGS amount") from exc
    if not x.is_finite() or x<=0 or x.as_tuple().exponent < -4:
        raise ValueError("KGS must be positive with four decimal places or fewer")
    return x.quantize(MONEY)


def validate_posting(proposal_lines, *, source_type, evidence_complete, source_amount,\n                     revenue_service_type=None):
    """Return balanced amount; NO automatic approval of missing evidence.

    Inputs must come from database-owned proposal and independently verified
    source. Arbitrary chart-of-account codes or source-created sums are denied.
    """
    if evidence_complete is not True:
        raise ValueError("RECOGNITION_SOURCE_INCOMPLETE")
    source_amount=exact_amount(source_amount)
    debits=credits=Decimal(0)
    for line in proposal_lines:
        code=line["account_code"]
        side=line["side"]
        amount=exact_amount(line["amount_kgs"])
        if code not in ACCOUNTS or side not in ("DEBIT","CREDIT"):
            raise ValueError("ACCOUNT_OR_SIDE_UNSUPPORTED")
        if source_type=="REVENUE_SOURCE":
            revenue_code={"ROOM_NIGHT":"4100","DINING_ORDER":"4200"}.get(
                revenue_service_type)
            if revenue_code is None:
                raise ValueError("REVENUE_SERVICE_CLASSIFICATION_UNVERIFIED")
            if code not in ("1100",revenue_code,"2100"):
                raise ValueError("SOURCE_ACCOUNT_MISMATCH")
        if source_type=="OPERATING_EXPENSE" and code not in ("5200","2200"):
            raise ValueError("SOURCE_ACCOUNT_MISMATCH")
        if source_type=="STOCK_CONSUMPTION" and code not in ("5100","1300"):
            raise ValueError("SOURCE_ACCOUNT_MISMATCH")
        debits+=amount if side=="DEBIT" else 0
        credits+=amount if side=="CREDIT" else 0
    if debits<=0 or debits!=credits:
        raise ValueError("UNBALANCED_POSTING")
    if debits!=source_amount:
        raise ValueError("SOURCE_AMOUNT_MISMATCH")
    sides={(r["account_code"],r["side"]) for r in proposal_lines}
    if source_type=="REVENUE_SOURCE":
        allowed_revenue={"ROOM_NIGHT":"4100","DINING_ORDER":"4200"}[
            revenue_service_type]
        if ("1100","DEBIT") not in sides or (allowed_revenue,"CREDIT") not in sides:
            raise ValueError("REVENUE_DOUBLE_ENTRY_PATTERN_INVALID")
    elif source_type=="OPERATING_EXPENSE":
        if not {("5200","DEBIT"),("2200","CREDIT")}<=sides:
            raise ValueError("OPERATING_EXPENSE_PATTERN_INVALID")
    elif source_type=="STOCK_CONSUMPTION":
        if not {("5100","DEBIT"),("1300","CREDIT")}<=sides:
            raise ValueError("COGS_PATTERN_INVALID")
    else:
        raise ValueError("SOURCE_TYPE_UNSUPPORTED")
    return str(debits.quantize(MONEY))


def posted_totals(lines, *, completeness_verified):
    """Compute recognized P&L only for a fully reconciled period."""
    if completeness_verified is not True:
        return {"status":"NOT_READY","recognized_revenue_kgs":None,
                "recognized_expenses_kgs":None,"recognized_profit_kgs":None}
    revenue=Decimal(0)
    expense=Decimal(0)
    for row in lines:
        code=row["account_code"]
        value=exact_amount(row["amount_kgs"])
        side=row["side"]
        if code in REVENUE_CODES:
            revenue += value if side=="CREDIT" else -value
        elif code in EXPENSE_CODES:
            expense += value if side=="DEBIT" else -value
        elif code not in ACCOUNTS:
            raise ValueError("UNKNOWN_LEDGER_ACCOUNT")
        if side not in ("DEBIT","CREDIT"):
            raise ValueError("INVALID_POSTED_SIDE")
    profit = revenue-expense
    return {"status":"RECONCILED","recognized_revenue_kgs":str(revenue.quantize(MONEY)),
            "recognized_expenses_kgs":str(expense.quantize(MONEY)),
            "recognized_profit_kgs":str(profit.quantize(MONEY))}
