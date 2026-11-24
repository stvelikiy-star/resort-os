"""Read-only source evidence reconciliation; never a general-ledger posting.

Payments and refunds are cash facts, discounts/cancellations change the
source's face value, and VAT / package amounts require separate classification.
Missing confirmations produce NULL candidates rather than invented profit.
"""
from decimal import Decimal, InvalidOperation

MONEY = Decimal("0.0001")
KINDS = frozenset({"DISCOUNT", "CANCELLATION", "REFUND",
                    "TAX_COMPONENT", "PACKAGE_SPLIT"})
REDUCERS = frozenset({"DISCOUNT", "CANCELLATION"})


def money(value):
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid monetary amount") from exc
    if not d.is_finite() or d < 0 or d.as_tuple().exponent < -4:
        raise ValueError("Monetary amounts must be nonnegative and exact to four places")
    return d.quantize(MONEY)


def source_candidate(face_value, correction_rows, *, tax_classification_complete=False):
    """Classify a single active source approval; never return recognized P&L.

    `correction_rows` must contain only active RECORD events associated with
    this ONE source approval, already filtered for tenant and reversals.
    """
    face = money(face_value)
    totals = {kind: Decimal(0) for kind in KINDS}
    seen = set()
    for row in correction_rows:
        identifier = str(row["id"])
        if identifier in seen:
            raise ValueError("Duplicate correction event")
        seen.add(identifier)
        kind = row["kind"]
        if kind not in KINDS:
            raise ValueError("Unrecognized financial correction kind")
        totals[kind] += money(row["amount_kgs"])
    reduced = totals["DISCOUNT"] + totals["CANCELLATION"]
    if reduced > face or totals["TAX_COMPONENT"] > face - reduced:
        raise ValueError("Corrections exceed source face value")
    if totals["PACKAGE_SPLIT"] > face - reduced:
        raise ValueError("Package split exceeds available value")
    if totals["REFUND"] > face:
        raise ValueError("Cash refund evidence exceeds source face value")
    net_before_tax = face - reduced
    # Refund is CASH evidence. Never subtract it again from service revenue.
    # A PACKAGE_SPLIT classifies the source, not an additional deduction.
    candidate = (net_before_tax - totals["TAX_COMPONENT"]
                 if tax_classification_complete else None)
    blockers = []
    if not tax_classification_complete:
        blockers.append("TAX_CLASSIFICATION_NOT_VERIFIED")
    return {
        "gross_service_candidate_kgs": str(face),
        "discount_candidate_kgs": str(totals["DISCOUNT"].quantize(MONEY)),
        "cancellation_candidate_kgs": str(totals["CANCELLATION"].quantize(MONEY)),
        "refund_cash_evidence_kgs": str(totals["REFUND"].quantize(MONEY)),
        "package_component_evidence_kgs": str(totals["PACKAGE_SPLIT"].quantize(MONEY)),
        "tax_component_evidence_kgs": str(totals["TAX_COMPONENT"].quantize(MONEY)),
        "net_before_tax_candidate_kgs": str(net_before_tax.quantize(MONEY)),
        "net_ex_tax_candidate_kgs": str(candidate.quantize(MONEY)) if candidate is not None else None,
        "recognized_revenue_kgs": None,
        "recognized_profit_kgs": None,
        "accounting_posted": False,
        "blockers": blockers + ["APPROVED_DOUBLE_ENTRY_RECOGNITION_REQUIRED"],
    }


def classify_owner_expense(category, amount_kgs, *, supplier_document_matched=False):
    amount = money(amount_kgs)
    if category in {"SUPPLIES", "OTHER"} or supplier_document_matched:
        reason = ("SUPPLIER_INVOICE_OVERLAP_REVIEW_REQUIRED"
                  if supplier_document_matched else "STOCK_OR_OTHER_CLASSIFICATION_REQUIRED")
        eligible = None
    elif category in {"UTILITIES", "PAYROLL", "MAINTENANCE", "RENT", "MARKETING"}:
        reason = "ACCOUNTING_EXPENSE_POSTING_REQUIRED"
        eligible = str(amount)
    else:
        raise ValueError("Unknown OWNER expense category")
    return {
        "obligation_kgs": str(amount),
        "non_stock_expense_candidate_kgs": eligible,
        "recognized_expense_kgs": None,
        "accounting_posted": False,
        "blockers": [reason],
    }
