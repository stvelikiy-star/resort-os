-- Internal commercial review, never a client signature or live subscription.
BEGIN;
CREATE TABLE flex_agreement_internal_approvals (
 agreement_id uuid PRIMARY KEY,
 hotel_id uuid NOT NULL,
 terms_digest char(64) NOT NULL CHECK(terms_digest ~ '^[a-f0-9]{64}$'),
 approved_by text NOT NULL CHECK(length(btrim(approved_by)) BETWEEN 2 AND 180),
 approved_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(agreement_id,hotel_id) REFERENCES flex_commercial_agreement_versions(id,hotel_id)
);
ALTER TABLE flex_agreement_internal_approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_agreement_internal_approvals FORCE ROW LEVEL SECURITY;
CREATE TRIGGER flex_agreement_approval_immutable BEFORE UPDATE OR DELETE ON flex_agreement_internal_approvals
 FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
GRANT SELECT,INSERT ON flex_agreement_internal_approvals TO flex_catalog_draft_writer;
CREATE POLICY flex_internal_approval_read ON flex_agreement_internal_approvals
 FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_internal_approval_append ON flex_agreement_internal_approvals
 FOR INSERT TO flex_catalog_draft_writer WITH CHECK(
 approved_by=NULLIF(current_setting('flex.actor_subject_id',true),'')
 AND EXISTS(SELECT 1 FROM flex_commercial_agreement_versions a
 WHERE a.id=agreement_id AND a.hotel_id=flex_agreement_internal_approvals.hotel_id
 AND a.state='DRAFT' AND a.source_offer_id IS NOT NULL
 AND a.terms_digest=flex_agreement_internal_approvals.terms_digest)
 );
COMMENT ON TABLE flex_agreement_internal_approvals IS 'Internal review of an immutable draft. Does not record client acceptance, sign, issue an invoice, activate a subscription or confirm cash.';
COMMIT;
