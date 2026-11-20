"""Read-only OWNER stock and supplier payable reconciliation.

Only persisted PostgreSQL movement and supplier-document facts are used.
The reported inventory carrying value is not recognized revenue or net profit.
Reports use a REPEATABLE READ caller transaction for an internally consistent
snapshot and never infer legacy invoice costs or generate customer Payments.
"""
from decimal import Decimal, ROUND_HALF_UP

MONEY=Decimal("0.0001")
EPSILON=Decimal("0.01")


def kgs(value):
    """Expose exact 4dp som amounts as text, not floating-point JSON."""
    return str(Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP))


def summarize_stock(rows):
    """Return explicit movement valuation, with invalid legacy stock fail-closed."""
    real=sample=Decimal(0)
    real_catalog=sample_catalog=Decimal(0)
    invalid=[]
    for row in rows:
        balance=Decimal(row["balance"])
        book=Decimal(row["book_value"])
        catalog=balance*Decimal(row["costPerUnitKgs"])
        if balance<0 or book<0 or (balance==0 and abs(book)>EPSILON):
            invalid.append(str(row["id"]))
        if row["isSample"]:
            sample+=book
            sample_catalog+=catalog
        else:
            real+=book
            real_catalog+=catalog
    return {
        "real_book_inventory_value_kgs":kgs(real) if not invalid else None,
        "sample_book_inventory_value_kgs":kgs(sample) if not invalid else None,
        "real_catalog_estimate_kgs":kgs(real_catalog),
        "sample_catalog_estimate_kgs":kgs(sample_catalog),
        "valuation_status":"RECONCILIATION_REQUIRED" if invalid else "MOVEMENT_BASED",
        "invalid_item_count":len(invalid),
        # No cross-unit quantity total: KG, L, PCS cannot be added.
        "item_count":len(rows),
        "as_of":"CURRENT_SNAPSHOT_NOT_PERIOD_END",
    }


async def owner_inventory_reconciliation(conn, property_id):
    rows=await conn.fetch(
        '''SELECT i.id,i."isSample",i."costPerUnitKgs",
                   COALESCE(SUM(CASE WHEN m.kind='RECEIPT'
                         THEN m.quantity ELSE -m.quantity END),0) AS balance,
                   COALESCE(SUM(CASE WHEN m.kind='RECEIPT'
                         THEN m.quantity*m."unitCostKgs"
                         ELSE -m.quantity*m."unitCostKgs" END),0) AS book_value
           FROM kitchen_stock_items i
           LEFT JOIN kitchen_stock_movements m
             ON m."propertyId"=i."propertyId" AND m."stockItemId"=i.id
           WHERE i."propertyId"=$1
           GROUP BY i.id''', property_id)
    stock=summarize_stock(rows)
    source=await conn.fetchrow(
        '''SELECT COUNT(*)::int AS linked_receipt_count,
                  ROUND(COALESCE(SUM(l.quantity*l."unitCostKgs"),0),4)
                    AS invoice_linked_receipt_cost,
                  ROUND(COALESCE(SUM(m.quantity*m."unitCostKgs"),0),4)
                    AS original_stock_receipt_cost,
                  COUNT(*) FILTER (WHERE l.quantity!=m.quantity
                    OR l."unitCostKgs"!=m."unitCostKgs")::int AS mismatch_count
           FROM kitchen_supplier_receipt_links l
           JOIN kitchen_stock_movements m ON m.id=l."receiptId"
             AND m."propertyId"=l."propertyId"
           WHERE l."propertyId"=$1''', property_id)
    supplier_gross=await conn.fetchrow(
        '''SELECT COUNT(*)::int AS document_count,
                 COALESCE(SUM(source_total),0) AS gross
           FROM (
             SELECT d.id,ROUND(COALESCE(SUM(
               l.quantity*l."unitCostKgs"),0),4) AS source_total
             FROM kitchen_supplier_documents d
             LEFT JOIN kitchen_supplier_document_lines l
               ON l."propertyId"=d."propertyId" AND l."documentId"=d.id
             WHERE d."propertyId"=$1 GROUP BY d.id
           ) documents''', property_id)
    settlements=await conn.fetchval(
        '''SELECT COALESCE(SUM("amountKgs"),0)
           FROM kitchen_supplier_settlements WHERE "propertyId"=$1''',
        property_id)
    credits=await conn.fetchrow(
        '''SELECT COUNT(*)::int AS return_count,
                  COALESCE(SUM("creditAmountKgs"),0) AS credit_amount,
                  ROUND(COALESCE(SUM(
                    quantity*"inventoryUnitCostKgs"),0),4) AS inventory_return_cost
           FROM kitchen_supplier_returns WHERE "propertyId"=$1''',
        property_id)
    gross=Decimal(supplier_gross["gross"])
    settled=Decimal(settlements)
    credited=Decimal(credits["credit_amount"])
    outstanding=gross-settled-credited
    link_difference=Decimal(source["invoice_linked_receipt_cost"])-Decimal(
        source["original_stock_receipt_cost"])
    return_delta=credited-Decimal(credits["inventory_return_cost"])
    stock["linked_source"]={
        "receipt_count":source["linked_receipt_count"],
        "original_stock_cost_kgs":kgs(source["original_stock_receipt_cost"]),
        "invoice_source_cost_kgs":kgs(source["invoice_linked_receipt_cost"]),
        "legacy_invoice_vs_stock_cost_delta_kgs":kgs(link_difference),
        "source_mismatch_count":source["mismatch_count"],
        "source_status":"REVIEW_LEGACY_LINKED_RECEIPT_COST"
            if source["mismatch_count"] else "LINKED_MOVEMENTS_MATCH_INVOICE",
    }
    return {
        "inventory":stock,
        "supplier_documents":{
            "document_count":supplier_gross["document_count"],
            "gross_obligations_kgs":kgs(gross),
            "manual_settlements_kgs":kgs(settled),
            "credit_notes_kgs":kgs(credited),
            "outstanding_payables_kgs":kgs(outstanding),
            "return_count":credits["return_count"],
            "return_stock_carrying_cost_kgs":kgs(credits["inventory_return_cost"]),
            "return_credit_minus_stock_cost_kgs":kgs(return_delta),
            "payables_status":"RECONCILIATION_REQUIRED"
                if outstanding<0 else "RECORDED_OBLIGATIONS_BALANCED",
        },
        "financial_truth":{
            "recognized_revenue_kgs":None,
            "recognized_profit_kgs":None,
            "is_recognized_profit_complete":False,
            "supplier_settlements_are_customer_payments":False,
            "stock_receipts_are_expenses":False,
            "stock_return_credit_difference_recognized":False,
            "scope":"CURRENT_PROPERTY_POSTED_FACTS_NOT_PERIOD_END",
        },
    }
