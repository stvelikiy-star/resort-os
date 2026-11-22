-- MARINA FLEX preview 0009: signed QA settlement, NOT a Finik bank adapter.
-- Disposable PostgreSQL ONLY after preview 0001-0008.
-- No production credentials, provider clients, or PMS tables.
BEGIN;

CREATE TABLE flex_qa_settlement_evidence (
  provider_payment_id text PRIMARY KEY,
  provider text NOT NULL DEFAULT 'FLEX_QA_SIMULATOR'
    CHECK (provider='FLEX_QA_SIMULATOR'),
  intent_id uuid NOT NULL UNIQUE REFERENCES flex_payment_intents(id),
  invoice_id uuid NOT NULL,
  hotel_id uuid NOT NULL,
  amount numeric(18,2) NOT NULL CHECK (amount>0),
  currency char(3) NOT NULL CHECK (currency='KGS'),
  payload_sha256 char(64) NOT NULL CHECK (payload_sha256 ~ '^[a-f0-9]{64}$'),
  confirmed_payment_id uuid UNIQUE NOT NULL,
  verified_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (invoice_id,hotel_id) REFERENCES flex_invoices(id,hotel_id),
  FOREIGN KEY (confirmed_payment_id,invoice_id)
    REFERENCES flex_confirmed_payments(id,invoice_id)
);
ALTER TABLE flex_qa_settlement_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_qa_settlement_evidence FORCE ROW LEVEL SECURITY;
CREATE TRIGGER flex_qa_settlement_evidence_append_only
BEFORE UPDATE OR DELETE ON flex_qa_settlement_evidence
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();

CREATE ROLE flex_qa_settlement_writer NOLOGIN;
GRANT USAGE ON SCHEMA public TO flex_qa_settlement_writer;
GRANT SELECT ON flex_payment_intents, flex_invoices, flex_invoice_lines,
  flex_issued_invoice_records, flex_confirmed_payments,
  flex_payment_allocations, flex_allocation_reversals,
  flex_qa_settlement_evidence TO flex_qa_settlement_writer;
GRANT INSERT ON flex_confirmed_payments, flex_payment_allocations,
  flex_qa_settlement_evidence, flex_provider_events,
  flex_provider_event_attempts TO flex_qa_settlement_writer;

-- Grant select for correlation and replay checks, not arbitrary ledger mutation.
GRANT SELECT ON flex_provider_events TO flex_qa_settlement_writer;

-- Existing base RLS is default-deny. Each row is constrained to a sandbox-only
-- provider and hotel identity from a signed ephemeral test envelope.
CREATE POLICY flex_qa_intent_read ON flex_payment_intents
FOR SELECT TO flex_qa_settlement_writer USING (
  provider='FLEX_QA_SIMULATOR'
  AND current_setting('flex.qa_mode',true)='CI_DISPOSABLE_ONLY'
  AND EXISTS (
    SELECT 1 FROM flex_invoices i WHERE i.id=invoice_id
      AND i.hotel_id=NULLIF(current_setting('flex.qa_hotel_id',true),'')::uuid
  )
);
CREATE POLICY flex_qa_invoice_read ON flex_invoices
FOR SELECT TO flex_qa_settlement_writer USING (
  current_setting('flex.qa_mode',true)='CI_DISPOSABLE_ONLY'
  AND hotel_id=NULLIF(current_setting('flex.qa_hotel_id',true),'')::uuid
);
CREATE POLICY flex_qa_invoice_lines_read ON flex_invoice_lines
FOR SELECT TO flex_qa_settlement_writer USING (
  EXISTS(SELECT 1 FROM flex_invoices i WHERE i.id=invoice_id)
);
CREATE POLICY flex_qa_issued_read ON flex_issued_invoice_records
FOR SELECT TO flex_qa_settlement_writer USING (
  current_setting('flex.qa_mode',true)='CI_DISPOSABLE_ONLY'
  AND hotel_id=NULLIF(current_setting('flex.qa_hotel_id',true),'')::uuid
);
CREATE POLICY flex_qa_receipt_read ON flex_confirmed_payments
FOR SELECT TO flex_qa_settlement_writer USING (
  current_setting('flex.qa_mode',true)='CI_DISPOSABLE_ONLY'
  AND provider='FLEX_QA_SIMULATOR'
  AND hotel_id=NULLIF(current_setting('flex.qa_hotel_id',true),'')::uuid
);
CREATE POLICY flex_qa_receipt_insert ON flex_confirmed_payments
FOR INSERT TO flex_qa_settlement_writer WITH CHECK (
  current_setting('flex.qa_mode',true)='CI_DISPOSABLE_ONLY'
  AND provider='FLEX_QA_SIMULATOR'
  AND hotel_id=NULLIF(current_setting('flex.qa_hotel_id',true),'')::uuid
  AND currency='KGS'
);
CREATE POLICY flex_qa_allocations_read ON flex_payment_allocations
FOR SELECT TO flex_qa_settlement_writer USING (
  EXISTS (
    SELECT 1 FROM flex_confirmed_payments p
    WHERE p.id=payment_id AND p.invoice_id=invoice_id
  )
);
CREATE POLICY flex_qa_allocations_insert ON flex_payment_allocations
FOR INSERT TO flex_qa_settlement_writer WITH CHECK (
  EXISTS (
    SELECT 1 FROM flex_confirmed_payments p
    WHERE p.id=payment_id AND p.invoice_id=invoice_id
  )
);
CREATE POLICY flex_qa_allocations_reversed_read ON flex_allocation_reversals
FOR SELECT TO flex_qa_settlement_writer USING (
  EXISTS (SELECT 1 FROM flex_payment_allocations a WHERE a.id=allocation_id)
);
CREATE POLICY flex_qa_event_read ON flex_provider_events
FOR SELECT TO flex_qa_settlement_writer USING (
  current_setting('flex.qa_mode',true)='CI_DISPOSABLE_ONLY'
  AND provider='FLEX_QA_SIMULATOR'
);
CREATE POLICY flex_qa_event_insert ON flex_provider_events
FOR INSERT TO flex_qa_settlement_writer WITH CHECK (
  current_setting('flex.qa_mode',true)='CI_DISPOSABLE_ONLY'
  AND provider='FLEX_QA_SIMULATOR'
);
CREATE POLICY flex_qa_attempt_insert ON flex_provider_event_attempts
FOR INSERT TO flex_qa_settlement_writer WITH CHECK (
  status IN ('APPLIED','IGNORED')
  AND EXISTS (SELECT 1 FROM flex_provider_events e
    WHERE e.id=provider_event_id AND e.provider='FLEX_QA_SIMULATOR')
);
CREATE POLICY flex_qa_evidence_read ON flex_qa_settlement_evidence
FOR SELECT TO flex_qa_settlement_writer USING (
  current_setting('flex.qa_mode',true)='CI_DISPOSABLE_ONLY'
  AND provider='FLEX_QA_SIMULATOR'
  AND hotel_id=NULLIF(current_setting('flex.qa_hotel_id',true),'')::uuid
);
CREATE POLICY flex_qa_evidence_insert ON flex_qa_settlement_evidence
FOR INSERT TO flex_qa_settlement_writer WITH CHECK (
  current_setting('flex.qa_mode',true)='CI_DISPOSABLE_ONLY'
  AND provider='FLEX_QA_SIMULATOR'
  AND hotel_id=NULLIF(current_setting('flex.qa_hotel_id',true),'')::uuid
  AND currency='KGS'
);

-- Existing row-capacity trigger locks invoice lines and receipts, which
-- requires the internal trusted trigger to bypass the caller's INSERT-only
-- privileges. Keep its SQL name resolution fixed and change no public grants.
ALTER FUNCTION flex_allocation_guard() SECURITY DEFINER SET search_path=public,pg_temp;
ALTER FUNCTION flex_net_payment_capacity_guard() SECURITY DEFINER SET search_path=public,pg_temp;

COMMENT ON ROLE flex_qa_settlement_writer IS
 'No-login CI-only writer for synthetic signed payment evidence; never deploy against production';
COMMENT ON TABLE flex_qa_settlement_evidence IS
 'SIMULATOR ONLY. Evidence from ephemeral CI signing key, NOT real bank confirmation.';
COMMIT;
