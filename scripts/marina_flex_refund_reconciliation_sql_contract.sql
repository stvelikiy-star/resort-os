-- MARINA FLEX 0008 refund-adjusted cash ledger tests. ALL writes rolled back.
-- CI simulator runs as ephemeral PostgreSQL owner; no bank funds are moved.
BEGIN;
SET CONSTRAINTS flex_allocation_capacity IMMEDIATE;
SET CONSTRAINTS flex_refund_cash_capacity DEFERRED;
SET CONSTRAINTS flex_refund_allocated_capacity DEFERRED;
SET CONSTRAINTS flex_post_refund_allocation_capacity DEFERRED;
DO $test$
DECLARE
  ia uuid;
  ib uuid;
  la uuid;
  lb uuid;
  p1 uuid;
  pb uuid;
  a1 uuid;
  ab uuid;
  refund1 uuid;
  refund2 uuid;
  before_a numeric(18,2);
BEGIN
  SELECT id INTO ia FROM flex_invoices WHERE invoice_number='FLEX_RLS_A';
  SELECT id INTO ib FROM flex_invoices WHERE invoice_number='FLEX_RLS_B';
  SELECT id INTO la FROM flex_invoice_lines WHERE invoice_id=ia LIMIT 1;
  SELECT id INTO lb FROM flex_invoice_lines WHERE invoice_id=ib LIMIT 1;
  IF ia IS NULL OR ib IS NULL OR la IS NULL OR lb IS NULL THEN
    RAISE EXCEPTION 'CI_MISSING_TWO_HOTEL_INVOICE_FIXTURE';
  END IF;

  INSERT INTO flex_confirmed_payments(
    hotel_id,invoice_id,provider,provider_payment_id,amount,currency,confirmed_at
  ) VALUES('00000000-0000-0000-0000-00000000000a',ia,'CI','refundable-cash-a',120.00,'KGS',now())
  RETURNING id INTO p1;
  INSERT INTO flex_payment_allocations(invoice_id,payment_id,invoice_line_id,amount)
    VALUES(ia,p1,la,100.00) RETURNING id INTO a1;

  SELECT unapplied_cash_credit INTO before_a
    FROM flex_refund_adjusted_invoice_balances WHERE invoice_id=ia;
  IF before_a<>20.00 THEN RAISE EXCEPTION 'CI_BAD_INITIAL_CREDIT'; END IF;

  -- First 10.00 refund reduces only unused credit, not feature revenue.
  INSERT INTO flex_payment_reversals(payment_id,external_reversal_key,amount,reason)
    VALUES(p1,'CI-REFUND-A-001',10.00,'unused credit')
    RETURNING id INTO refund1;
  SET CONSTRAINTS flex_refund_cash_capacity, flex_refund_allocated_capacity, flex_post_refund_allocation_capacity IMMEDIATE;
  IF (SELECT unapplied_cash_credit FROM flex_refund_adjusted_invoice_balances
      WHERE invoice_id=ia)<>10.00 THEN
    RAISE EXCEPTION 'CI_FAILED_TO_REDUCE_CREDIT';
  END IF;

  -- The second refund and matching SKU reversal must be atomically checked.
  SET CONSTRAINTS flex_refund_cash_capacity, flex_refund_allocated_capacity, flex_post_refund_allocation_capacity DEFERRED;
  -- Next 50.00 refund consumes remaining 10.00 credit and 40.00 allocation.
  -- Both rows commit atomically, ensuring subscription revenue is reversed.
  INSERT INTO flex_payment_reversals(payment_id,external_reversal_key,amount,reason)
    VALUES(p1,'CI-REFUND-A-002',50.00,'part of module purchase')
    RETURNING id INTO refund2;
  INSERT INTO flex_allocation_reversals(reversal_id,allocation_id,amount)
    VALUES(refund2,a1,40.00);
  SET CONSTRAINTS flex_refund_cash_capacity, flex_refund_allocated_capacity, flex_post_refund_allocation_capacity IMMEDIATE;
  IF (SELECT net_confirmed_cash FROM flex_refund_adjusted_invoice_balances
      WHERE invoice_id=ia)<>60.00 THEN
    RAISE EXCEPTION 'CI_WRONG_NET_CASH';
  END IF;
  IF (SELECT net_applied_to_lines FROM flex_refund_adjusted_invoice_balances
      WHERE invoice_id=ia)<>60.00 THEN
    RAISE EXCEPTION 'CI_WRONG_NET_REVENUE';
  END IF;
  IF (SELECT outstanding FROM flex_refund_adjusted_invoice_balances
      WHERE invoice_id=ia)<>40.00 THEN
    RAISE EXCEPTION 'CI_WRONG_REFUND_DEBT';
  END IF;
  IF (SELECT unapplied_cash_credit FROM flex_refund_adjusted_invoice_balances
      WHERE invoice_id=ia)<>0.00 THEN
    RAISE EXCEPTION 'CI_UNEXPLAINED_REMAINING_CREDIT';
  END IF;

  -- Never accept a duplicate provider/bank reversal key.
  BEGIN
    INSERT INTO flex_payment_reversals(payment_id,external_reversal_key,amount,reason)
    VALUES(p1,'CI-REFUND-A-002',1.00,'duplicate replay');
    RAISE EXCEPTION 'CI_DUPLICATE_REFUND_WAS_ACCEPTED';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;

  -- Cannot refund more than bank confirmed, even without allocations.
  BEGIN
    INSERT INTO flex_payment_reversals(payment_id,external_reversal_key,amount,reason)
    VALUES(p1,'CI-REFUND-A-003',80.00,'exceeds receipt');
    RAISE EXCEPTION 'CI_OVERREFUND_WAS_ACCEPTED';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM <> 'FLEX_REFUND_EXCEEDS_CASH' THEN RAISE; END IF;
  END;

  -- Cannot refund cash that remains allocated to a paid SKU.
  BEGIN
    INSERT INTO flex_payment_reversals(payment_id,external_reversal_key,amount,reason)
    VALUES(p1,'CI-REFUND-A-004',1.00,'forgot to reverse SKU allocation');
    RAISE EXCEPTION 'CI_STALE_PAID_FEATURE_WAS_ACCEPTED';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM <> 'FLEX_REFUNDED_CASH_STILL_ALLOCATED' THEN RAISE; END IF;
  END;

  -- A reversal from another hotel/payment cannot remove its invoice allocation.
  INSERT INTO flex_confirmed_payments(
    hotel_id,invoice_id,provider,provider_payment_id,amount,currency,confirmed_at
  ) VALUES('00000000-0000-0000-0000-00000000000b',ib,'CI','refundable-cash-b',80.00,'KGS',now())
  RETURNING id INTO pb;
  INSERT INTO flex_payment_allocations(invoice_id,payment_id,invoice_line_id,amount)
    VALUES(ib,pb,lb,80.00) RETURNING id INTO ab;
  BEGIN
    INSERT INTO flex_allocation_reversals(reversal_id,allocation_id,amount)
    VALUES(refund2,ab,1.00);
    RAISE EXCEPTION 'CI_CROSS_PAYMENT_REFUND_ACCEPTED';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM <> 'FLEX_REFUND_WRONG_PAYMENT' THEN RAISE; END IF;
  END;

  -- Attempting to edit the ledger must also fail (append-only).
  BEGIN
    DELETE FROM flex_payment_reversals WHERE id=refund1;
    RAISE EXCEPTION 'CI_DELETED_REFUND_HISTORY';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM <> 'FLEX_HISTORY_IS_APPEND_ONLY' THEN RAISE; END IF;
  END;
  BEGIN
    UPDATE flex_allocation_reversals SET amount=0.01 WHERE reversal_id=refund2;
    RAISE EXCEPTION 'CI_REWRITTEN_REVENUE_HISTORY';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM <> 'FLEX_HISTORY_IS_APPEND_ONLY' THEN RAISE; END IF;
  END;

  IF (SELECT count(*) FROM flex_payment_reversals WHERE payment_id=p1)<>2 THEN
    RAISE EXCEPTION 'CI_UNEXPECTED_PAYMENT_REFUND_COUNT';
  END IF;
END
$test$;
ROLLBACK;
