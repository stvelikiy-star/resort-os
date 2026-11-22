-- Disposable FLEX contract and lifecycle evidence invariants.
-- Requires preview 0001 through 0006 and two-hotel fixture.
BEGIN;
DO $test$
DECLARE
  hotel_a uuid := '00000000-0000-0000-0000-00000000000a';
  hotel_b uuid := '00000000-0000-0000-0000-00000000000b';
  agreement uuid;
  invoice_a uuid;
  invoice_b uuid;
  sub_a uuid;
BEGIN
  SELECT id INTO sub_a FROM flex_subscriptions WHERE hotel_id=hotel_a LIMIT 1;
  SELECT id INTO invoice_a FROM flex_invoices WHERE hotel_id=hotel_a LIMIT 1;
  SELECT id INTO invoice_b FROM flex_invoices WHERE hotel_id=hotel_b LIMIT 1;
  IF sub_a IS NULL OR invoice_a IS NULL OR invoice_b IS NULL THEN
    RAISE EXCEPTION 'CI_FAILURE_MISSING_TWO_HOTEL_FIXTURE';
  END IF;

  INSERT INTO flex_commercial_agreement_versions(
    hotel_id,version,currency,state,terms,terms_digest,effective_from
  ) VALUES (
    hotel_a,1,'KGS','DRAFT','{"base_monthly_som":"10000","terms_status":"preview"}',
    repeat('a',64),'2026-11-01'
  ) RETURNING id INTO agreement;

  -- It is impossible to make an unsigned agreement SIGNED just by changing a flag.
  BEGIN
    INSERT INTO flex_commercial_agreement_versions(
      hotel_id,version,currency,state,terms,terms_digest,effective_from
    ) VALUES (
      hotel_a,2,'KGS','SIGNED','{}',repeat('b',64),'2026-11-01'
    );
    RAISE EXCEPTION 'CI_FAILURE_UNSIGNED_AGREEMENT_ACCEPTED';
  EXCEPTION WHEN check_violation THEN NULL;
  END;

  BEGIN
    UPDATE flex_commercial_agreement_versions SET state='SIGNED' WHERE id=agreement;
    RAISE EXCEPTION 'CI_FAILURE_HISTORY_REWRITE_ALLOWED';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM != 'FLEX_HISTORY_IS_APPEND_ONLY' THEN RAISE; END IF;
  END;

  INSERT INTO flex_non_issuable_invoice_previews(
    hotel_id,agreement_version_id,preview_sha256,quote_sha256,
    period_start,period_end,amount_before_unresolved_taxes
  ) VALUES(
    hotel_a,agreement,repeat('c',64),repeat('d',64),
    '2026-11-01','2026-11-30',10000.00
  );
  BEGIN
    INSERT INTO flex_non_issuable_invoice_previews(
      hotel_id,agreement_version_id,preview_sha256,quote_sha256,
      period_start,period_end,status,amount_before_unresolved_taxes
    ) VALUES (
      hotel_a,agreement,repeat('e',64),repeat('f',64),
      '2026-11-01','2026-11-30','ISSUED',10000.00
    );
    RAISE EXCEPTION 'CI_FAILURE_REAL_INVOICE_FROM_PREVIEW';
  EXCEPTION WHEN check_violation THEN NULL;
  END;

  -- Lifecycle events cannot reference a different hotel's invoice.
  BEGIN
    INSERT INTO flex_subscription_lifecycle_events(
      hotel_id,subscription_id,prior_state,next_state,transition_code,
      source_invoice_id,event_digest
    ) VALUES (
      hotel_a,sub_a,'ACTIVE','PAYMENT_DUE','MARK_PAYMENT_DUE',
      invoice_b,repeat('0',64)
    );
    RAISE EXCEPTION 'CI_FAILURE_CROSS_HOTEL_LIFECYCLE';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;

  -- Reactivation is never recorded without a confirmed payment reference.
  BEGIN
    INSERT INTO flex_subscription_lifecycle_events(
      hotel_id,subscription_id,prior_state,next_state,transition_code,
      source_invoice_id,event_digest
    ) VALUES (
      hotel_a,sub_a,'SUSPENDED','ACTIVE','REACTIVATE_PAID',
      invoice_a,repeat('1',64)
    );
    RAISE EXCEPTION 'CI_FAILURE_REACTIVATE_WITHOUT_PAYMENT';
  EXCEPTION WHEN check_violation THEN NULL;
  END;

  INSERT INTO flex_subscription_lifecycle_events(
    hotel_id,subscription_id,prior_state,next_state,transition_code,
    source_invoice_id,event_digest
  ) VALUES (
    hotel_a,sub_a,'ACTIVE','PAYMENT_DUE','MARK_PAYMENT_DUE',
    invoice_a,repeat('2',64)
  );
  BEGIN
    UPDATE flex_subscription_lifecycle_events
      SET event_digest=repeat('3',64) WHERE event_digest=repeat('2',64);
    RAISE EXCEPTION 'CI_FAILURE_LIFECYCLE_HISTORY_REWRITE';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM != 'FLEX_HISTORY_IS_APPEND_ONLY' THEN RAISE; END IF;
  END;
END
$test$;
ROLLBACK;
