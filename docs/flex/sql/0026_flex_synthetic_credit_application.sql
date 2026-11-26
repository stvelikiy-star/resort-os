-- Explicit application of synthetic credit only; never real cash or entitlement.
BEGIN;
ALTER TABLE flex_qa_cash_events
 DROP CONSTRAINT flex_qa_cash_events_kind_check,
 DROP CONSTRAINT flex_qa_cash_events_check,
 ADD CONSTRAINT flex_qa_cash_events_kind_check CHECK(kind IN ('PAYMENT','REFUND','CREDIT_APPLY')),
 ADD CONSTRAINT flex_qa_cash_events_reference_check CHECK(
   (kind='PAYMENT' AND payment_id IS NULL) OR
   (kind IN ('REFUND','CREDIT_APPLY') AND payment_id IS NOT NULL AND payment_id<>event_id));
COMMIT;
