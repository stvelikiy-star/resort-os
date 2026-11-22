-- Runs only against an ephemeral GitHub Actions PostgreSQL instance.
-- No production DB or hospitality tables involved. Roll back all fixture writes.
BEGIN;
SET CONSTRAINTS flex_allocation_capacity IMMEDIATE;
DO $test$
DECLARE
  hotel uuid := gen_random_uuid();
  invoice uuid := gen_random_uuid();
  line uuid := gen_random_uuid();
  paid uuid := gen_random_uuid();
  paid2 uuid := gen_random_uuid();
  raw_event uuid := gen_random_uuid();
BEGIN
  INSERT INTO flex_hotels(id,display_name) VALUES(hotel,'FLEX CI HOTEL');
  INSERT INTO flex_skus(sku,title,capability_key,product_status)
    VALUES('TEST_AI','Test AI','test_ai','AVAILABLE');
  INSERT INTO flex_invoices(id,hotel_id,invoice_number,currency,status,total)
    VALUES(invoice,hotel,'FLEX_CI_INV','KGS','ISSUED',100.00);
  INSERT INTO flex_invoice_lines(id,invoice_id,sku,currency,description,quantity,unit_price,amount)
    VALUES(line,invoice,'TEST_AI','KGS','Test feature',1,100.00,100.00);
  INSERT INTO flex_confirmed_payments(id,hotel_id,invoice_id,provider,provider_payment_id,amount,currency,confirmed_at)
    VALUES(paid,hotel,invoice,'TEST','FLEX_CI_PAY_1',100.00,'KGS',now());
  INSERT INTO flex_confirmed_payments(id,hotel_id,invoice_id,provider,provider_payment_id,amount,currency,confirmed_at)
    VALUES(paid2,hotel,invoice,'TEST','FLEX_CI_PAY_2',100.00,'KGS',now());
  INSERT INTO flex_payment_allocations(invoice_id,payment_id,invoice_line_id,amount)
    VALUES(invoice,paid,line,100.00);

  -- A second payment cannot allocate more than the billed feature amount.
  BEGIN
    INSERT INTO flex_payment_allocations(invoice_id,payment_id,invoice_line_id,amount)
      VALUES(invoice,paid2,line,1.00);
    RAISE EXCEPTION 'CI_FAILURE_LINE_OVERALLOC_ACCEPTED';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM != 'FLEX_ALLOCATIONS_EXCEED_INVOICE_LINE' THEN RAISE; END IF;
  END;

  -- A different hotel's invoice cannot be substituted in an allocation.
  BEGIN
    INSERT INTO flex_payment_allocations(invoice_id,payment_id,invoice_line_id,amount)
      VALUES(invoice,paid2,gen_random_uuid(),1.00);
    RAISE EXCEPTION 'CI_FAILURE_CROSS_LINE_ACCEPTED';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;

  INSERT INTO flex_provider_events(id,provider,event_id,payload_sha256)
    VALUES(raw_event,'TEST','evt-001',repeat('a',64));
  BEGIN
    INSERT INTO flex_provider_events(provider,event_id,payload_sha256)
      VALUES('TEST','evt-001',repeat('a',64));
    RAISE EXCEPTION 'CI_FAILURE_DUPLICATE_EVENT_ACCEPTED';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;

  -- Raw provider events are immutable; processing status lives separately.
  BEGIN
    UPDATE flex_provider_events SET event_id='rewritten' WHERE id=raw_event;
    RAISE EXCEPTION 'CI_FAILURE_EVENT_REWRITE_ACCEPTED';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM != 'FLEX_HISTORY_IS_APPEND_ONLY' THEN RAISE; END IF;
  END;

  IF (SELECT SUM(amount) FROM flex_payment_allocations WHERE invoice_line_id=line) != 100.00 THEN
    RAISE EXCEPTION 'CI_FAILURE_UNBALANCED_FEATURE_ALLOCATION';
  END IF;
END
$test$;
ROLLBACK;
