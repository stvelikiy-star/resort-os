-- FLEX read-only reconciliation; no settlement writer, no payment activation.
BEGIN;
GRANT SELECT ON flex_refund_adjusted_invoice_balances TO flex_platform_admin_reader;
GRANT SELECT(invoice_id,hotel_id) ON flex_issued_invoice_records TO flex_platform_admin_reader;
CREATE POLICY flex_admin_scoped_issued_read ON flex_issued_invoice_records FOR SELECT TO flex_platform_admin_reader
 USING(hotel_id=NULLIF(current_setting('flex.authorized_hotel_id',true),'')::uuid);
GRANT SELECT(id,hotel_id,invoice_id,amount) ON flex_confirmed_payments TO flex_platform_admin_reader;
GRANT SELECT(id,invoice_id,payment_id,amount) ON flex_payment_allocations TO flex_platform_admin_reader;
GRANT SELECT(payment_id,amount) ON flex_payment_reversals TO flex_platform_admin_reader;
GRANT SELECT(allocation_id,amount) ON flex_allocation_reversals TO flex_platform_admin_reader;
CREATE POLICY flex_admin_scoped_cash_read ON flex_confirmed_payments FOR SELECT TO flex_platform_admin_reader
 USING(hotel_id=NULLIF(current_setting('flex.authorized_hotel_id',true),'')::uuid);
CREATE POLICY flex_admin_scoped_allocations_read ON flex_payment_allocations FOR SELECT TO flex_platform_admin_reader
 USING(EXISTS(SELECT 1 FROM flex_confirmed_payments p WHERE p.id=payment_id AND p.invoice_id=flex_payment_allocations.invoice_id));
CREATE POLICY flex_admin_scoped_refunds_read ON flex_payment_reversals FOR SELECT TO flex_platform_admin_reader
 USING(EXISTS(SELECT 1 FROM flex_confirmed_payments p WHERE p.id=payment_id));
CREATE POLICY flex_admin_scoped_allocation_refunds_read ON flex_allocation_reversals FOR SELECT TO flex_platform_admin_reader
 USING(EXISTS(SELECT 1 FROM flex_payment_allocations a WHERE a.id=allocation_id));
COMMIT;
