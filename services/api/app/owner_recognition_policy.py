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


async def reconciliation_snapshot(conn, property_id, from_date, to_date):
    """Read only: active evidence and classification blockers for ONE property.

    All SQL predicates are scoped by server-resolved property_id. Nothing in
    this snapshot is a recognized accounting posting, including valid events.
    """
    sources = await conn.fetch(
        """SELECT e.id, e."faceValueKgs" AS face
           FROM owner_revenue_source_events e
           WHERE e."propertyId"=$1 AND e."serviceDate" BETWEEN $2 AND $3
             AND e.action='APPROVE_SOURCE'
             AND NOT EXISTS(
               SELECT 1 FROM owner_revenue_source_events r
               WHERE r."propertyId"=$1 AND r."reversesId"=e.id)
           ORDER BY e.id""", property_id, from_date, to_date)
    corrections = await conn.fetch(
        """SELECT c.id,c."approvalId",c.kind,c."amountKgs" AS amount
           FROM owner_revenue_correction_events c
           JOIN owner_revenue_source_events e
             ON e.id=c."approvalId" AND e."propertyId"=c."propertyId"
           WHERE c."propertyId"=$1 AND e."serviceDate" BETWEEN $2 AND $3
             AND c.action='RECORD' AND e.action='APPROVE_SOURCE'
             AND NOT EXISTS(
               SELECT 1 FROM owner_revenue_source_events r
               WHERE r."propertyId"=$1 AND r."reversesId"=e.id)
             AND NOT EXISTS(
               SELECT 1 FROM owner_revenue_correction_events r
               WHERE r."propertyId"=$1 AND r."reversesId"=c.id)
           ORDER BY c.id""",property_id,from_date,to_date)
    by_source = {}
    for row in corrections:
        by_source.setdefault(row["approvalId"], []).append({
            "id":str(row["id"]),"kind":row["kind"],"amount_kgs":row["amount"]
        })
    gross = Decimal(0)
    before_tax = Decimal(0)
    reported_refunds = Decimal(0)
    for row in sources:
        computed = source_candidate(row["face"],by_source.get(row["id"], []))
        gross += money(computed["gross_service_candidate_kgs"])
        before_tax += money(computed["net_before_tax_candidate_kgs"])
        reported_refunds += money(computed["refund_cash_evidence_kgs"])

    expenses = await conn.fetch(
        """SELECT e.id,e.category,e."amountKgs",EXISTS(
             SELECT 1 FROM kitchen_supplier_documents d
             WHERE d."propertyId"=e."propertyId"
               AND d."supplierName"=e."supplierName"
               AND d."documentReference"=e."documentReference"
           ) AS supplier_document_matched
           FROM owner_expenses e
           WHERE e."propertyId"=$1 AND e.status='POSTED'
             AND e."expenseDate" BETWEEN $2 AND $3
           ORDER BY e.id""",property_id,from_date,to_date)
    expense_total = Decimal(0)
    ambiguous = Decimal(0)
    candidate_nonstock = Decimal(0)
    for row in expenses:
        classified = classify_owner_expense(
            row["category"],row["amountKgs"],
            supplier_document_matched=row["supplier_document_matched"])
        amount = money(classified["obligation_kgs"])
        expense_total += amount
        if classified["non_stock_expense_candidate_kgs"] is None:
            ambiguous += amount
        else:
            candidate_nonstock += money(classified["non_stock_expense_candidate_kgs"])

    return {
        "scope":"PROPERTY_SCOPED_READ_ONLY_EVIDENCE",
        "approved_active_source_count":len(sources),
        "gross_approved_source_face_candidate_kgs":str(gross.quantize(MONEY)),
        "net_before_tax_source_candidate_kgs":str(before_tax.quantize(MONEY)),
        "cash_refund_evidence_kgs":str(reported_refunds.quantize(MONEY)),
        "posted_owner_expense_obligation_kgs":str(expense_total.quantize(MONEY)),
        "non_stock_expense_candidate_kgs":str(candidate_nonstock.quantize(MONEY)),
        "unclassified_or_supplier_overlap_expense_kgs":str(ambiguous.quantize(MONEY)),
        "net_ex_tax_candidate_kgs":None,
        "recognized_revenue_kgs":None,
        "recognized_expenses_kgs":None,
        "recognized_profit_kgs":None,
        "accounting_posted":False,
        "completeness_verified":False,
        "blockers":[
            "TAX_DISCOUNT_PACKAGE_RECONCILIATION_NOT_VERIFIED",
            "RECOGNITION_DOUBLE_ENTRY_POSTING_NOT_IMPLEMENTED",
            "SERVED_COGS_AND_PERIOD_EXPENSES_NOT_FULLY_RECONCILED",
        ] + (["EXPENSE_CLASSIFICATION_OR_SUPPLIER_OVERLAP_REQUIRED"]
             if ambiguous else []),
    }
