-- MARINA FLEX preview 0006: contract and lifecycle evidence, NOT operational billing.
-- Only a disposable commercial QA database. No PMS migration or API writes.
BEGIN;

CREATE TABLE flex_commercial_agreement_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
  version integer NOT NULL CHECK (version >= 1),
  currency char(3) NOT NULL DEFAULT 'KGS' CHECK (currency='KGS'),
  state text NOT NULL CHECK (state IN ('DRAFT','SIGNED','SUPERSEDED')),
  terms jsonb NOT NULL,
  terms_digest char(64) NOT NULL CHECK (terms_digest ~ '^[a-f0-9]{64}$'),
  signed_at timestamptz,
  signed_by_subject_id text,
  effective_from date NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((state='DRAFT' AND signed_at IS NULL AND signed_by_subject_id IS NULL)
    OR (state IN ('SIGNED','SUPERSEDED') AND signed_at IS NOT NULL
      AND signed_by_subject_id IS NOT NULL)),
  UNIQUE (hotel_id,version),
  UNIQUE (id,hotel_id)
);
ALTER TABLE flex_commercial_agreement_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_commercial_agreement_versions FORCE ROW LEVEL SECURITY;

CREATE TABLE flex_non_issuable_invoice_previews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
  agreement_version_id uuid NOT NULL,
  preview_sha256 char(64) NOT NULL CHECK (preview_sha256 ~ '^[a-f0-9]{64}$'),
  quote_sha256 char(64) NOT NULL CHECK (quote_sha256 ~ '^[a-f0-9]{64}$'),
  period_start date NOT NULL,
  period_end date NOT NULL,
  currency char(3) NOT NULL DEFAULT 'KGS' CHECK (currency='KGS'),
  amount_before_unresolved_taxes numeric(18,2) NOT NULL
    CHECK (amount_before_unresolved_taxes >= 0),
  tax_status text NOT NULL DEFAULT 'NOT_CALCULATED'
    CHECK (tax_status='NOT_CALCULATED'),
  status text NOT NULL DEFAULT 'NON_ISSUABLE' CHECK (status='NON_ISSUABLE'),
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (agreement_version_id,hotel_id)
    REFERENCES flex_commercial_agreement_versions(id,hotel_id),
  CHECK (period_end >= period_start),
  UNIQUE (hotel_id,agreement_version_id,period_start,preview_sha256)
);
ALTER TABLE flex_non_issuable_invoice_previews ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_non_issuable_invoice_previews FORCE ROW LEVEL SECURITY;

CREATE TABLE flex_subscription_lifecycle_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subscription_id uuid NOT NULL REFERENCES flex_subscriptions(id),
  prior_state text NOT NULL,
  next_state text NOT NULL,
  transition_code text NOT NULL
    CHECK (transition_code IN (
      'MARK_PAYMENT_DUE','ENTER_GRACE','SUSPEND_EXPIRED','REACTIVATE_PAID'
    )),
  source_invoice_id uuid NOT NULL REFERENCES flex_invoices(id),
  source_confirmed_payment_id uuid REFERENCES flex_confirmed_payments(id),
  event_digest char(64) NOT NULL UNIQUE
    CHECK (event_digest ~ '^[a-f0-9]{64}$'),
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (prior_state<>next_state),
  CHECK (transition_code<>'REACTIVATE_PAID' OR source_confirmed_payment_id IS NOT NULL)
);
ALTER TABLE flex_subscription_lifecycle_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_subscription_lifecycle_events FORCE ROW LEVEL SECURITY;

-- Immutable drafts and lifecycle audit; no role can alter history.
CREATE TRIGGER flex_agreement_history_no_rewrite
BEFORE UPDATE OR DELETE ON flex_commercial_agreement_versions
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
CREATE TRIGGER flex_invoice_preview_no_rewrite
BEFORE UPDATE OR DELETE ON flex_non_issuable_invoice_previews
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
CREATE TRIGGER flex_subscription_events_no_rewrite
BEFORE UPDATE OR DELETE ON flex_subscription_lifecycle_events
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();

COMMENT ON TABLE flex_non_issuable_invoice_previews IS
 'Preview only. NOT a fiscal invoice, NOT an issued QR, and NOT authorization to suspend PMS.';
COMMENT ON TABLE flex_subscription_lifecycle_events IS
 'Immutable transition evidence. No live scheduler or PMS enforcement is wired.';

COMMIT;
