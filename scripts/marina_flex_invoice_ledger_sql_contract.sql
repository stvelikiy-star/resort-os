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
  refund_id uuid;
  allocation_b uuid;
  subscription_a uuid;
  ledger record;
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

  -- One financial chain on the actual issued invoice, rather than unrelated fixtures.
  -- The older 0007-only test remains usable before refund migration 0008.
  IF to_regclass('flex_refund_adjusted_invoice_balances') IS NOT NULL THEN
    SELECT id INTO allocation_b FROM flex_payment_allocations
      WHERE payment_id=pay_b AND invoice_line_id=line_ai;
    SELECT * INTO ledger FROM flex_refund_adjusted_invoice_balances WHERE invoice_id=invoice_a;
    IF ledger.amount_due IS DISTINCT FROM 179.20 OR ledger.net_confirmed_cash IS DISTINCT FROM 200.00
       OR ledger.net_applied_to_lines IS DISTINCT FROM 179.20 OR ledger.outstanding IS DISTINCT FROM 0.00
       OR ledger.unapplied_cash_credit IS DISTINCT FROM 20.80 THEN
      RAISE EXCEPTION 'FLEX_CHAIN_INITIAL_RECONCILIATION_FAILED';
    END IF;
    -- Synthetic 30.00 reversal: first consume 20.80 unused credit,
    -- then reverse 9.20 of the line allocation from the same receipt.
    SET CONSTRAINTS flex_refund_cash_capacity, flex_refund_allocated_capacity, flex_post_refund_allocation_capacity DEFERRED;
    INSERT INTO flex_payment_reversals(payment_id,external_reversal_key,amount,reason)
      VALUES(pay_b,'CI-ISSUED-CHAIN-REFUND-001',30.00,'Synthetic credit and allocated line refund')
      RETURNING id INTO refund_id;
    INSERT INTO flex_allocation_reversals(reversal_id,allocation_id,amount)
      VALUES(refund_id,allocation_b,9.20);
    SET CONSTRAINTS flex_refund_cash_capacity, flex_refund_allocated_capacity, flex_post_refund_allocation_capacity IMMEDIATE;
    SELECT * INTO ledger FROM flex_refund_adjusted_invoice_balances WHERE invoice_id=invoice_a;
    IF ledger.amount_due IS DISTINCT FROM 179.20 OR ledger.net_confirmed_cash IS DISTINCT FROM 170.00
       OR ledger.net_applied_to_lines IS DISTINCT FROM 170.00 OR ledger.outstanding IS DISTINCT FROM 9.20
       OR ledger.unapplied_cash_credit IS DISTINCT FROM 0.00
       OR ledger.amount_due <> ledger.net_applied_to_lines+ledger.outstanding
       OR ledger.net_confirmed_cash <> ledger.net_applied_to_lines+ledger.unapplied_cash_credit THEN
      RAISE EXCEPTION 'FLEX_CHAIN_REFUND_RECONCILIATION_FAILED';
    END IF;
    -- Record lifecycle evidence only; never mutate the actual subscription or PMS.
    SELECT id INTO subscription_a FROM flex_subscriptions WHERE hotel_id=hotel_a LIMIT 1;
    IF subscription_a IS NULL THEN RAISE EXCEPTION 'FLEX_CHAIN_SUBSCRIPTION_MISSING'; END IF;
    INSERT INTO flex_subscription_lifecycle_events(hotel_id,subscription_id,prior_state,next_state,
      transition_code,source_invoice_id,event_digest)
      VALUES(hotel_a,subscription_a,'ACTIVE','PAYMENT_DUE','MARK_PAYMENT_DUE',invoice_a,repeat('9',64));
    RAISE NOTICE 'PASS FLEX issued invoice 179.20, cash 200.00, refund 30.00, applied 170.00, debt 9.20, credit 0.00, discrepancy 0.00; lifecycle evidence only';
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
-- When migration 0022 is installed, exercise the exact issued-invoice
-- query used by the HTTP endpoint under its non-writing runtime reader.
SELECT CASE WHEN to_regclass('flex_refund_adjusted_invoice_balances') IS NULL THEN false
 ELSE has_table_privilege('flex_platform_admin_reader','flex_refund_adjusted_invoice_balances','SELECT') END AS flex_chain_reader_ready \gset
\if :flex_chain_reader_ready
SET LOCAL flex.authorized_hotel_id='00000000-0000-0000-0000-00000000000a';
SET LOCAL ROLE flex_platform_admin_reader;
DO $reader$
DECLARE b record;
BEGIN
 SELECT v.* INTO b FROM flex_refund_adjusted_invoice_balances v
 JOIN flex_issued_invoice_records e ON e.invoice_id=v.invoice_id AND e.hotel_id=v.hotel_id
 JOIN flex_invoices i ON i.id=v.invoice_id
 WHERE v.hotel_id='00000000-0000-0000-0000-00000000000a' AND i.invoice_number='FLEX_ISSUANCE_CI_A'
   AND i.status IN ('ISSUED','PARTIALLY_PAID','PAID');
 IF NOT FOUND OR b.net_confirmed_cash IS DISTINCT FROM 170.00 OR b.outstanding IS DISTINCT FROM 9.20
    OR b.unapplied_cash_credit IS DISTINCT FROM 0.00 THEN
  RAISE EXCEPTION 'FLEX_CHAIN_RUNTIME_READER_MISMATCH';
 END IF;
 IF has_table_privilege(current_user,'flex_confirmed_payments','INSERT') OR
    has_table_privilege(current_user,'flex_payment_reversals','INSERT') THEN
  RAISE EXCEPTION 'FLEX_CHAIN_READER_MUST_NOT_WRITE';
 END IF;
 RAISE NOTICE 'PASS FLEX issued-invoice reconciliation runtime reader, cash 170.00, debt 9.20, credit 0.00';
END $reader$;
RESET ROLE;
\endif
ROLLBACK;
