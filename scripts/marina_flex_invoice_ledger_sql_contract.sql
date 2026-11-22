-- MARINA FLEX 0007 disposable invoice/ledger acceptance.
-- All fixture data is QA-only and rolled back. No real customer or bank.
BEGIN;
SET CONSTRAINTS flex_allocation_capacity IMMEDIATE;
DO $test$
DECLARE
  hotel_a uuid := '00000000-0000-0000-0000-00000000000a';
  hotel_b uuid := '00000000-0000-0000-0000-00000000000b';
  agreement_a uuid;
  tax_a uuid;
  issued_a uuid;
  invoice_a uuid;
  invoice_b uuid;
  line_base uuid;
  line_ai uuid;
  price_base uuid;
  price_ai uuid;
  pay_a uuid;
  pay_b uuid;
BEGIN
  -- Independently signed test contract, trusted deployment link and
  -- explicit CI-only fictional 12% ADDED tax policy.
  INSERT INTO flex_hotel_links(hotel_id,deployment_id,property_external_id,verified_at)
  VALUES(hotel_a,'ci-verified-pms','ci-linked-property-a',now());
  INSERT INTO flex_commercial_agreement_versions(
    hotel_id,version,currency,state,terms,terms_digest,signed_at,signed_by_subject_id,effective_from
  ) VALUES (
    hotel_a,1,'KGS','SIGNED','{"CI":"TEST ONLY","billing":"month"}',
    repeat('a',64),now(),'administrator','2026-11-01'
  ) RETURNING id INTO agreement_a;
  INSERT INTO flex_tax_policy_versions(
    hotel_id,agreement_version_id,version,treatment,rate_bps,
    approval_reference,approved_by,approved_at,valid_from
  ) VALUES (
    hotel_a,agreement_a,1,'ADDED',1200,'CI-FICTIONAL-12-PERCENT',
    'administrator',now(),'2026-11-01'
  ) RETURNING id INTO tax_a;
  SELECT id INTO price_base FROM flex_price_versions WHERE sku='BASE_PMS' AND version=1;
  SELECT id INTO price_ai FROM flex_price_versions WHERE sku='AI_ASSISTANT' AND version=1;

  INSERT INTO flex_invoices(hotel_id,invoice_number,currency,status,total,issued_at)
  VALUES(hotel_a,'FLEX_ISSUANCE_CI_A','KGS','ISSUED',179.20,now())
  RETURNING id INTO invoice_a;

  INSERT INTO flex_invoice_lines(invoice_id,sku,price_version_id,currency,
                                 description,quantity,unit_price,amount)
  VALUES(invoice_a,'BASE_PMS',price_base,'KGS','Base subscription',1,100.00,112.00)
  RETURNING id INTO line_base;
  INSERT INTO flex_invoice_lines(invoice_id,sku,price_version_id,currency,
                                 description,quantity,unit_price,amount)
  VALUES(invoice_a,'AI_ASSISTANT',price_ai,'KGS','AI addon',1,60.00,67.20)
  RETURNING id INTO line_ai;

  INSERT INTO flex_issued_invoice_records(
    invoice_id,hotel_id,agreement_version_id,tax_policy_version_id,
    period_start,period_end,quote_digest,issuance_digest,
    net_amount,tax_amount,total_amount
  ) VALUES (
    invoice_a,hotel_a,agreement_a,tax_a,'2026-11-01','2026-11-30',
    repeat('b',64),repeat('c',64),160.00,19.20,179.20
  ) RETURNING id INTO issued_a;
  INSERT INTO flex_issued_invoice_line_tax(
    invoice_id,invoice_line_id,net_amount,tax_amount,payable_amount
  ) VALUES
    (invoice_a,line_base,100.00,12.00,112.00),
    (invoice_a,line_ai,60.00,7.20,67.20);

  -- A deferred trigger verifies the entire invoice at commit; force now so
  -- this disposable rolled-back fixture is actually tested.
  SET CONSTRAINTS flex_issued_invoice_document_capacity IMMEDIATE;

  IF (SELECT count(*) FROM flex_issued_invoice_line_tax
      WHERE invoice_id=invoice_a)<>2 THEN
    RAISE EXCEPTION 'CI_FAILURE_MISSING_ISSUED_LINES';
  END IF;

  -- A finalized document cannot mutate invoice total or any line.
  BEGIN
    UPDATE flex_invoices SET total=1 WHERE id=invoice_a;
    RAISE EXCEPTION 'CI_FAILURE_INVOICE_REWRITTEN';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM <> 'FLEX_ISSUED_INVOICE_IMMUTABLE' THEN RAISE; END IF;
  END;
  BEGIN
    UPDATE flex_invoice_lines SET amount=1 WHERE id=line_ai;
    RAISE EXCEPTION 'CI_FAILURE_ISSUED_LINE_REWRITTEN';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM <> 'FLEX_ISSUED_INVOICE_IMMUTABLE' THEN RAISE; END IF;
  END;
  BEGIN
    INSERT INTO flex_invoice_lines(invoice_id,sku,price_version_id,currency,
                                   description,quantity,unit_price,amount)
    VALUES(invoice_a,'AI_ASSISTANT',price_ai,'KGS','Late added',1,1,1);
    RAISE EXCEPTION 'CI_FAILURE_ISSUED_LINE_APPEND';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM <> 'FLEX_ISSUED_INVOICE_IMMUTABLE' THEN RAISE; END IF;
  END;

  -- The same paid period/contract may not issue a second invoice,
  -- even with a different number or quote digest.
  INSERT INTO flex_invoices(hotel_id,invoice_number,currency,status,total,issued_at)
  VALUES(hotel_a,'FLEX_ISSUANCE_CI_DUP','KGS','ISSUED',179.20,now())
  RETURNING id INTO invoice_b;
  BEGIN
    INSERT INTO flex_issued_invoice_records(
      invoice_id,hotel_id,agreement_version_id,tax_policy_version_id,
      period_start,period_end,quote_digest,issuance_digest,
      net_amount,tax_amount,total_amount
    ) VALUES (
      invoice_b,hotel_a,agreement_a,tax_a,'2026-11-01','2026-11-30',
      repeat('d',64),repeat('e',64),160.00,19.20,179.20
    );
    RAISE EXCEPTION 'CI_FAILURE_DUPLICATE_MONTHLY_ISSUANCE';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;

  -- Confirmed payments here are *simulated in the CI database owner fixture*.
  -- Public QR / uploaded receipt is NOT proof of cash.
  INSERT INTO flex_confirmed_payments(
    hotel_id,invoice_id,provider,provider_payment_id,amount,currency,confirmed_at
  ) VALUES(hotel_a,invoice_a,'CI_SIMULATOR','CI_PAID_001',120.00,'KGS',now())
  RETURNING id INTO pay_a;
  INSERT INTO flex_payment_allocations(invoice_id,payment_id,invoice_line_id,amount)
  VALUES(invoice_a,pay_a,line_base,112.00),
        (invoice_a,pay_a,line_ai,8.00);

  BEGIN
    INSERT INTO flex_confirmed_payments(
      hotel_id,invoice_id,provider,provider_payment_id,amount,currency,confirmed_at
    ) VALUES(hotel_a,invoice_a,'CI_SIMULATOR','CI_PAID_001',120.00,'KGS',now());
    RAISE EXCEPTION 'CI_FAILURE_DUPLICATE_PROVIDER_PAYMENT';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;

  INSERT INTO flex_confirmed_payments(
    hotel_id,invoice_id,provider,provider_payment_id,amount,currency,confirmed_at
  ) VALUES(hotel_a,invoice_a,'CI_SIMULATOR','CI_PAID_002',80.00,'KGS',now())
  RETURNING id INTO pay_b;
  BEGIN
    INSERT INTO flex_payment_allocations(invoice_id,payment_id,invoice_line_id,amount)
    VALUES(invoice_a,pay_b,line_ai,65.00);
    RAISE EXCEPTION 'CI_FAILURE_OVERALLOCATED_ADDON';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM <> 'FLEX_ALLOCATIONS_EXCEED_INVOICE_LINE' THEN RAISE; END IF;
  END;

  -- Remaining AI charge 59.20, additional confirmed payment is 80,
  -- so 20.80 must remain UNALLOCATED (a hotel credit, not SKU revenue).
  INSERT INTO flex_payment_allocations(invoice_id,payment_id,invoice_line_id,amount)
  VALUES(invoice_a,pay_b,line_ai,59.20);

  IF (SELECT coalesce(sum(amount),0) FROM flex_payment_allocations
      WHERE invoice_id=invoice_a)<>179.20 THEN
    RAISE EXCEPTION 'CI_FAILURE_NOT_FULLY_ALLOCATED';
  END IF;
  IF (SELECT outstanding_before_reversals
      FROM flex_verified_invoice_balances
      WHERE invoice_id=invoice_a)<>0 THEN
    RAISE EXCEPTION 'CI_FAILURE_LEDGER_BALANCE';
  END IF;
  IF (SELECT amount FROM flex_confirmed_payments WHERE id=pay_b) -
     (SELECT sum(amount) FROM flex_payment_allocations WHERE payment_id=pay_b) <> 20.80 THEN
    RAISE EXCEPTION 'CI_FAILURE_OVERPAYMENT_CREDIT';
  END IF;

  -- Misplaced cross-hotel cash may not be attributed to this invoice.
  BEGIN
    INSERT INTO flex_confirmed_payments(
      hotel_id,invoice_id,provider,provider_payment_id,amount,currency,confirmed_at
    ) VALUES(hotel_b,invoice_a,'CI_SIMULATOR','CI_FOREIGN_HOTEL',20.00,'KGS',now());
    RAISE EXCEPTION 'CI_FAILURE_CROSS_HOTEL_CONFIRMED_PAYMENT';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
END
$test$;
ROLLBACK;
