-- MARINA FLEX preview 0008: reversible append-only cash accounting.
-- Isolated commercial PostgreSQL QA only after 0001..0007.
-- Does NOT send money, initiate refunds, change subscriptions or access PMS.
BEGIN;

-- Every refund is immutable; any correction must be a NEW reconciliation event.
CREATE TRIGGER flex_payment_reversal_history_no_rewrite
BEFORE UPDATE OR DELETE ON flex_payment_reversals
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();

CREATE TRIGGER flex_allocation_reversal_history_no_rewrite
BEFORE UPDATE OR DELETE ON flex_allocation_reversals
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();

CREATE FUNCTION flex_net_payment_capacity_guard() RETURNS trigger
LANGUAGE plpgsql AS $flex$
DECLARE
  pid uuid;
  confirmed numeric(18,2);
  reversed_cash numeric(18,2);
  applied numeric(18,2);
  unapplied_reversals numeric(18,2);
  reversals_per_allocation numeric(18,2);
  reversals_per_event numeric(18,2);
  target_payment uuid;
BEGIN
  IF TG_TABLE_NAME='flex_payment_reversals' THEN
    pid := NEW.payment_id;
  ELSIF TG_TABLE_NAME='flex_allocation_reversals' THEN
    SELECT payment_id INTO pid FROM flex_payment_allocations
    WHERE id=NEW.allocation_id;
    SELECT payment_id INTO target_payment FROM flex_payment_reversals
    WHERE id=NEW.reversal_id;
    IF pid<>target_payment THEN
      RAISE EXCEPTION 'FLEX_REFUND_WRONG_PAYMENT' USING ERRCODE='23514';
    END IF;
  ELSIF TG_TABLE_NAME='flex_payment_allocations' THEN
    pid := NEW.payment_id;
  ELSE
    RAISE EXCEPTION 'FLEX_UNKNOWN_LEDGER_EVENT' USING ERRCODE='23514';
  END IF;

  -- Serialize cash/refund capacity on the verified receipt row.
  SELECT amount INTO confirmed FROM flex_confirmed_payments
    WHERE id=pid FOR UPDATE;
  IF confirmed IS NULL THEN
    RAISE EXCEPTION 'FLEX_MISSING_CONFIRMED_PAYMENT' USING ERRCODE='23514';
  END IF;
  SELECT coalesce(sum(amount),0) INTO reversed_cash
    FROM flex_payment_reversals WHERE payment_id=pid;
  SELECT coalesce(sum(amount),0) INTO applied
    FROM flex_payment_allocations WHERE payment_id=pid;
  SELECT coalesce(sum(ar.amount),0) INTO unapplied_reversals
    FROM flex_allocation_reversals ar
    JOIN flex_payment_allocations a ON a.id=ar.allocation_id
    WHERE a.payment_id=pid;

  IF reversed_cash > confirmed THEN
    RAISE EXCEPTION 'FLEX_REFUND_EXCEEDS_CASH' USING ERRCODE='23514';
  END IF;
  IF unapplied_reversals > applied OR
     applied - unapplied_reversals > confirmed - reversed_cash THEN
    RAISE EXCEPTION 'FLEX_REFUNDED_CASH_STILL_ALLOCATED' USING ERRCODE='23514';
  END IF;

  IF TG_TABLE_NAME='flex_allocation_reversals' THEN
    SELECT coalesce(sum(amount),0) INTO reversals_per_allocation
      FROM flex_allocation_reversals
      WHERE allocation_id=NEW.allocation_id;
    IF reversals_per_allocation >
       (SELECT amount FROM flex_payment_allocations WHERE id=NEW.allocation_id)
    THEN
      RAISE EXCEPTION 'FLEX_ALLOCATION_OVERREVERSED' USING ERRCODE='23514';
    END IF;
    SELECT coalesce(sum(amount),0) INTO reversals_per_event
      FROM flex_allocation_reversals WHERE reversal_id=NEW.reversal_id;
    IF reversals_per_event >
       (SELECT amount FROM flex_payment_reversals WHERE id=NEW.reversal_id)
    THEN
      RAISE EXCEPTION 'FLEX_REFUND_ALLOCATION_EXCEEDS_EVENT' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END $flex$;

CREATE CONSTRAINT TRIGGER flex_refund_cash_capacity
AFTER INSERT ON flex_payment_reversals DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION flex_net_payment_capacity_guard();

CREATE CONSTRAINT TRIGGER flex_refund_allocated_capacity
AFTER INSERT ON flex_allocation_reversals DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION flex_net_payment_capacity_guard();

CREATE CONSTRAINT TRIGGER flex_post_refund_allocation_capacity
AFTER INSERT ON flex_payment_allocations DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION flex_net_payment_capacity_guard();

-- Only SQL owner/internal reconciliation has access to this financial view;
-- caller inherits no user-visible SELECT grants on sensitive ledgers.
CREATE VIEW flex_refund_adjusted_invoice_balances WITH (security_invoker=true) AS
WITH allocations AS (
  SELECT invoice_id,coalesce(sum(amount),0)::numeric(18,2) gross_allocated
  FROM flex_payment_allocations GROUP BY invoice_id
), allocation_reversals AS (
  SELECT a.invoice_id,coalesce(sum(ar.amount),0)::numeric(18,2) refunded_allocated
  FROM flex_allocation_reversals ar
  JOIN flex_payment_allocations a ON a.id=ar.allocation_id
  GROUP BY a.invoice_id
), payments AS (
  SELECT invoice_id,coalesce(sum(amount),0)::numeric(18,2) gross_confirmed
  FROM flex_confirmed_payments GROUP BY invoice_id
), payment_reversals AS (
  SELECT p.invoice_id,coalesce(sum(r.amount),0)::numeric(18,2) gross_refunded
  FROM flex_payment_reversals r
  JOIN flex_confirmed_payments p ON p.id=r.payment_id
  GROUP BY p.invoice_id
)
SELECT i.id AS invoice_id,i.hotel_id,i.currency,i.total AS amount_due,
       (coalesce(p.gross_confirmed,0)-coalesce(pr.gross_refunded,0))::numeric(18,2)
          AS net_confirmed_cash,
       (coalesce(a.gross_allocated,0)-coalesce(ar.refunded_allocated,0))::numeric(18,2)
          AS net_applied_to_lines,
       greatest(i.total-(coalesce(a.gross_allocated,0)-
                    coalesce(ar.refunded_allocated,0)),0)::numeric(18,2)
          AS outstanding,
       (coalesce(p.gross_confirmed,0)-coalesce(pr.gross_refunded,0)-
          (coalesce(a.gross_allocated,0)-coalesce(ar.refunded_allocated,0)))::numeric(18,2)
          AS unapplied_cash_credit
FROM flex_invoices i
LEFT JOIN allocations a ON a.invoice_id=i.id
LEFT JOIN allocation_reversals ar ON ar.invoice_id=i.id
LEFT JOIN payments p ON p.invoice_id=i.id
LEFT JOIN payment_reversals pr ON pr.invoice_id=i.id;

COMMENT ON VIEW flex_refund_adjusted_invoice_balances IS
 'Internal cash reconciliation only. Derived from verified receipts, refunds, allocation reversals. No user grant.';
CREATE INDEX flex_payment_reversals_cash ON flex_payment_reversals(payment_id);
CREATE INDEX flex_allocation_reversals_allocation ON flex_allocation_reversals(allocation_id);
COMMIT;
