-- Execute only against a disposable FLEX CI database after preview DDL.
-- All fixtures are rolled back. Expected failures are checked in savepoints.
BEGIN;
SET CONSTRAINTS flex_allocation_capacity IMMEDIATE;
DO $test$
DECLARE
  hotel uuid := gen_random_uuid();
  invoice uuid := gen_random_uuid();
  line uuid := gen_random_uuid();
  paid uuid := gen_random_uuid();
  another_payment uuid := gen_random_uuid();
  event_id uuid := gen_random_uuid();
BEGIN
  INSERT INTO flex_hotels(id,display_name) VALUES(hotel,'FLEX CI HOTEL');
  INSERT INTO flex_skus(sku,title,capability_key,product_status)
    VALUES('TEST_AI','AI tests','test_ai','AVAILABLE');
  INSERT INTO flex_invoices(id,hotel_id,invoice_number,currency,status,total)
    VALUES(invoice,hotel,'FLEX_CI_INV','KGS','ISSUED',100.00);
  INSERT INTO flex_invoice_lines(id,invoice_id,sku,currency,description,quantity,unit_price,amount)
    VALUES(line,invoice,'TEST_AI','KGS','Test module',1,100.00,100.00);
  INSERT INTO flex_confirmed_payments(id,hotel_id,invoice_id,provider,provider_payment_id,amount,currency,confirmed_at)
    VALUES(paid,hotel,invoice,'TEST','FLEX_CI_PAYMENT_1',100.00,'KGS',now());
  INSERT INTO flex_confirmed_payments(id,hotel_id,invoice_id,provider,provider_payment_id,amount,currency,confirmed_at)
    VALUES(another_payment,hotel,invoice,'TEST','FLEX_CI_PAYMENT_2',100.00,'KGS',now());

  INSERT INTO flex_payment_allocations(invoice_id,payment_id,invoice_line_id,amount)
    VALUES(invoice,paid,line,60.00);
  INSERT INTO flex_payment_allocations(invoice_id,payment_id,invoice_line_id,amount)
    VALUES(invoice,paid,line,40.00);
  -- The pair (payment_id,invoice_line_id) is unique, so the second
  -- allocation must be a separate payment; duplicate must be rejected.
EXCEPTION
  WHEN unique_violation THEN
    RAISE EXCEPTION 'FLEX fixture had unexpected duplicate key';
END
$test$;
ROLLBACK;
