-- Explicit synthetic finance journal, completely separate from confirmed cash.
BEGIN;
CREATE TABLE flex_qa_cash_events (
 agreement_id uuid NOT NULL,
 hotel_id uuid NOT NULL,
 sequence integer NOT NULL CHECK(sequence BETWEEN 1 AND 100),
 event_id text NOT NULL CHECK(event_id ~ '^[a-zA-Z0-9_-]{1,64}$'),
 kind text NOT NULL CHECK(kind IN ('PAYMENT','REFUND')),
 amount numeric(18,2) NOT NULL CHECK(amount>0),
 payment_id text,
 created_by text NOT NULL CHECK(length(btrim(created_by)) BETWEEN 2 AND 180),
 created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(agreement_id,event_id),
 UNIQUE(agreement_id,sequence),
 FOREIGN KEY(agreement_id,hotel_id) REFERENCES flex_commercial_agreement_versions(id,hotel_id),
 FOREIGN KEY(agreement_id) REFERENCES flex_customer_agreement_acceptances(agreement_id),
 FOREIGN KEY(agreement_id,payment_id) REFERENCES flex_qa_cash_events(agreement_id,event_id),
 CHECK((kind='PAYMENT' AND payment_id IS NULL) OR (kind='REFUND' AND payment_id IS NOT NULL AND payment_id<>event_id))
);
ALTER TABLE flex_qa_cash_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_qa_cash_events FORCE ROW LEVEL SECURITY;
CREATE TRIGGER flex_qa_cash_history_immutable BEFORE UPDATE OR DELETE ON flex_qa_cash_events
 FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
GRANT SELECT,INSERT ON flex_qa_cash_events TO flex_catalog_draft_writer;
CREATE POLICY flex_qa_cash_read ON flex_qa_cash_events FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_qa_cash_append ON flex_qa_cash_events FOR INSERT TO flex_catalog_draft_writer
 WITH CHECK(created_by=NULLIF(current_setting('flex.actor_subject_id',true),'')
 AND EXISTS(SELECT 1 FROM flex_customer_agreement_acceptances a
 WHERE a.agreement_id=flex_qa_cash_events.agreement_id AND a.hotel_id=flex_qa_cash_events.hotel_id));
COMMENT ON TABLE flex_qa_cash_events IS 'SYNTHETIC QA ONLY. Never join into actual cash, investor earnings, entitlement or launch eligibility. No bank transaction.';
COMMIT;
