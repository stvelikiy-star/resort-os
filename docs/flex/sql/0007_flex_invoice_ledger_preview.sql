-- MARINA FLEX preview 0007: invoice immutable fiscal evidence + ledger reconciliation.
-- Apply ONLY in disposable commercial CI/QA Postgres after 0001..0006.
-- THIS IS NOT a real fiscal document, not a bank payment and not a PMS migration.
BEGIN;

CREATE TABLE flex_tax_policy_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id uuid NOT NULL,
  agreement_version_id uuid NOT NULL,
  version integer NOT NULL CHECK(version > 0),
  treatment text NOT NULL CHECK(treatment IN ('EXEMPT','ADDED')),
  rate_bps integer NOT NULL CHECK(rate_bps BETWEEN 0 AND 10000),
  approval_reference text NOT NULL CHECK(length(btrim(approval_reference)) > 0),
  approved_by text NOT NULL,
  approved_at timestamptz NOT NULL,
  valid_from date NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK(treatment <> 'EXEMPT' OR rate_bps=0),
  FOREIGN KEY(agreement_version_id,hotel_id)
    REFERENCES flex_commercial_agreement_versions(id,hotel_id),
  UNIQUE (id,hotel_id,agreement_version_id),
  UNIQUE (hotel_id,agreement_version_id,version)
);
ALTER TABLE flex_tax_policy_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_tax_policy_versions FORCE ROW LEVEL SECURITY;
CREATE TRIGGER flex_tax_policy_history_no_rewrite
BEFORE UPDATE OR DELETE ON flex_tax_policy_versions
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();

CREATE TABLE flex_issued_invoice_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id uuid NOT NULL,
  hotel_id uuid NOT NULL,
  agreement_version_id uuid NOT NULL,
  tax_policy_version_id uuid NOT NULL,
  period_start date NOT NULL,
  period_end date NOT NULL,
  quote_digest char(64) NOT NULL CHECK(quote_digest ~ '^[0-9a-f]{64}$'),
  issuance_digest char(64) NOT NULL CHECK(issuance_digest ~ '^[0-9a-f]{64}$'),
  net_amount numeric(18,2) NOT NULL CHECK(net_amount >= 0),
  tax_amount numeric(18,2) NOT NULL CHECK(tax_amount >= 0),
  total_amount numeric(18,2) NOT NULL CHECK(total_amount >= 0),
  issued_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY(invoice_id,hotel_id) REFERENCES flex_invoices(id,hotel_id),
  FOREIGN KEY(agreement_version_id,hotel_id)
    REFERENCES flex_commercial_agreement_versions(id,hotel_id),
  FOREIGN KEY(tax_policy_version_id,hotel_id,agreement_version_id)
    REFERENCES flex_tax_policy_versions(id,hotel_id,agreement_version_id),
  CHECK(period_end >= period_start),
  CHECK(net_amount + tax_amount = total_amount),
  UNIQUE (invoice_id),
  UNIQUE (hotel_id,agreement_version_id,period_start,period_end),
  UNIQUE (hotel_id,issuance_digest)
);
ALTER TABLE flex_issued_invoice_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_issued_invoice_records FORCE ROW LEVEL SECURITY;

CREATE TABLE flex_issued_invoice_line_tax (
  invoice_id uuid NOT NULL,
  invoice_line_id uuid PRIMARY KEY,
  net_amount numeric(18,2) NOT NULL CHECK (net_amount >= 0),
  tax_amount numeric(18,2) NOT NULL CHECK (tax_amount >= 0),
  payable_amount numeric(18,2) NOT NULL CHECK (payable_amount >= 0),
  FOREIGN KEY(invoice_id) REFERENCES flex_issued_invoice_records(invoice_id),
  FOREIGN KEY(invoice_line_id,invoice_id)
    REFERENCES flex_invoice_lines(id,invoice_id),
  CHECK (net_amount+tax_amount=payable_amount)
);
ALTER TABLE flex_issued_invoice_line_tax ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_issued_invoice_line_tax FORCE ROW LEVEL SECURITY;

CREATE TRIGGER flex_issued_invoice_history_no_rewrite
BEFORE UPDATE OR DELETE ON flex_issued_invoice_records
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
CREATE TRIGGER flex_issued_invoice_line_tax_no_rewrite
BEFORE UPDATE OR DELETE ON flex_issued_invoice_line_tax
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();

-- Every final invoice must balance at the end of the *same transaction*.
CREATE FUNCTION flex_verified_invoice_issuance_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  document flex_issued_invoice_records%ROWTYPE;
  header flex_invoices%ROWTYPE;
  agreement flex_commercial_agreement_versions%ROWTYPE;
  policy flex_tax_policy_versions%ROWTYPE;
  n integer;
  net numeric(18,2);
  tax numeric(18,2);
  payable numeric(18,2);
  mismatches integer;
BEGIN
  SELECT * INTO document FROM flex_issued_invoice_records WHERE invoice_id=NEW.invoice_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'FLEX_ISSUANCE_MISSING' USING ERRCODE='23514';
  END IF;
  SELECT * INTO header FROM flex_invoices WHERE id=document.invoice_id;
  SELECT * INTO agreement FROM flex_commercial_agreement_versions
    WHERE id=document.agreement_version_id;
  SELECT * INTO policy FROM flex_tax_policy_versions
    WHERE id=document.tax_policy_version_id;
  IF header.status <> 'ISSUED' OR header.currency <> 'KGS' OR
     header.total <> document.total_amount OR
     agreement.state <> 'SIGNED' OR agreement.signed_at IS NULL OR
     policy.valid_from > document.period_start OR
     policy.approved_at > document.issued_at OR
     NOT EXISTS (SELECT 1 FROM flex_hotel_links l WHERE l.hotel_id=document.hotel_id
                 AND l.verified_at IS NOT NULL)
  THEN
    RAISE EXCEPTION 'FLEX_ISSUANCE_EVIDENCE_INVALID' USING ERRCODE='23514';
  END IF;
  SELECT count(*),coalesce(sum(t.net_amount),0),coalesce(sum(t.tax_amount),0),
         coalesce(sum(t.payable_amount),0)
    INTO n,net,tax,payable
    FROM flex_issued_invoice_line_tax t WHERE t.invoice_id=document.invoice_id;
  SELECT count(*) INTO mismatches FROM flex_invoice_lines line
    LEFT JOIN flex_issued_invoice_line_tax t ON t.invoice_line_id=line.id
    WHERE line.invoice_id=document.invoice_id
      AND (t.invoice_line_id IS NULL
           OR line.amount <> t.payable_amount
           OR line.price_version_id IS NULL);
  IF n=0 OR mismatches<>0 OR
     n<>(SELECT count(*) FROM flex_invoice_lines WHERE invoice_id=document.invoice_id)
     OR net<>document.net_amount OR tax<>document.tax_amount
     OR payable<>document.total_amount
  THEN
    RAISE EXCEPTION 'FLEX_ISSUANCE_LINES_UNBALANCED' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER flex_issued_invoice_document_capacity
AFTER INSERT ON flex_issued_invoice_records DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION flex_verified_invoice_issuance_guard();

-- Issued headers and invoiced prices are immutable. Payment status must be
-- derived from verified cash allocations/reversals, not UPDATE to invoice.
CREATE FUNCTION flex_reject_issued_invoice_rewrite() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS(SELECT 1 FROM flex_issued_invoice_records
            WHERE invoice_id=OLD.id) THEN
    RAISE EXCEPTION 'FLEX_ISSUED_INVOICE_IMMUTABLE';
  END IF;
  RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE TRIGGER flex_issued_invoice_header_no_rewrite
BEFORE UPDATE OR DELETE ON flex_invoices
FOR EACH ROW EXECUTE FUNCTION flex_reject_issued_invoice_rewrite();

CREATE FUNCTION flex_reject_issued_invoice_line_rewrite() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS(SELECT 1 FROM flex_issued_invoice_records
            WHERE invoice_id=OLD.invoice_id) THEN
    RAISE EXCEPTION 'FLEX_ISSUED_INVOICE_IMMUTABLE';
  END IF;
  RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE TRIGGER flex_issued_invoice_lines_no_rewrite
BEFORE UPDATE OR DELETE ON flex_invoice_lines
FOR EACH ROW EXECUTE FUNCTION flex_reject_issued_invoice_line_rewrite();

CREATE INDEX flex_issued_invoice_hotel_period
 ON flex_issued_invoice_records(hotel_id,period_start,period_end);
CREATE INDEX flex_tax_policy_by_agreement
 ON flex_tax_policy_versions(agreement_version_id,version);

-- A _cash balance_ is derived from immutable allocations; this is NOT
-- an invoice status UPDATE. Credit/reversals must be reconciled separately.
-- SECURITY INVOKER ensures callers still need explicit base-table RLS grants.
CREATE VIEW flex_verified_invoice_balances WITH (security_invoker=true) AS
SELECT
  i.id AS invoice_id, i.hotel_id, i.currency, i.total AS invoice_total,
  coalesce(sum(a.amount),0)::numeric(18,2) AS gross_allocated,
  greatest(i.total-coalesce(sum(a.amount),0),0)::numeric(18,2) AS outstanding_before_reversals
FROM flex_invoices i
LEFT JOIN flex_payment_allocations a ON a.invoice_id=i.id
GROUP BY i.id,i.hotel_id,i.currency,i.total;
-- Deliberately NO grants on this view to hotel/public users yet.

COMMENT ON VIEW flex_verified_invoice_balances IS
 'Internal unadjusted paid balances. Refund reversals MUST be subtracted before final collection/reconciliation.';
COMMIT;
