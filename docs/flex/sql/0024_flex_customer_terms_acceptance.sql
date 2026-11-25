-- Explicit customer acceptance of immutable commercial terms, not fiscal issuance.
BEGIN;
CREATE ROLE flex_customer_acceptance_writer NOLOGIN;
GRANT USAGE ON SCHEMA public TO flex_customer_acceptance_writer;
GRANT SELECT ON flex_platform_memberships,flex_platform_hotel_grants TO flex_customer_acceptance_writer;
CREATE POLICY flex_acceptance_own_membership ON flex_platform_memberships FOR SELECT TO flex_customer_acceptance_writer
 USING(subject_id=NULLIF(current_setting('flex.authorized_subject_id',true),'') AND active AND role='HOTEL_OWNER');
CREATE POLICY flex_acceptance_own_grants ON flex_platform_hotel_grants FOR SELECT TO flex_customer_acceptance_writer
 USING(subject_id=NULLIF(current_setting('flex.authorized_subject_id',true),''));
GRANT SELECT ON flex_agreement_internal_approvals,flex_commercial_agreement_versions TO flex_customer_acceptance_writer;
CREATE POLICY flex_acceptance_approved_read ON flex_agreement_internal_approvals FOR SELECT TO flex_customer_acceptance_writer
 USING(EXISTS(SELECT 1 FROM flex_platform_hotel_grants g JOIN flex_platform_memberships m ON m.subject_id=g.subject_id
 WHERE g.hotel_id=flex_agreement_internal_approvals.hotel_id));
CREATE POLICY flex_acceptance_terms_read ON flex_commercial_agreement_versions FOR SELECT TO flex_customer_acceptance_writer
 USING(state='DRAFT' AND EXISTS(SELECT 1 FROM flex_agreement_internal_approvals a WHERE a.agreement_id=id AND a.hotel_id=flex_commercial_agreement_versions.hotel_id AND a.terms_digest=flex_commercial_agreement_versions.terms_digest));
CREATE TABLE flex_customer_agreement_acceptances (
 agreement_id uuid PRIMARY KEY,
 hotel_id uuid NOT NULL,
 terms_digest char(64) NOT NULL CHECK(terms_digest ~ '^[a-f0-9]{64}$'),
 accepted_by text NOT NULL CHECK(length(btrim(accepted_by)) BETWEEN 2 AND 180),
 accepted_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(agreement_id,hotel_id) REFERENCES flex_commercial_agreement_versions(id,hotel_id),
 FOREIGN KEY(agreement_id) REFERENCES flex_agreement_internal_approvals(agreement_id)
);
ALTER TABLE flex_customer_agreement_acceptances ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_customer_agreement_acceptances FORCE ROW LEVEL SECURITY;
CREATE TRIGGER flex_customer_acceptance_immutable BEFORE UPDATE OR DELETE ON flex_customer_agreement_acceptances
 FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
GRANT SELECT,INSERT ON flex_customer_agreement_acceptances TO flex_customer_acceptance_writer;
GRANT SELECT ON flex_customer_agreement_acceptances TO flex_catalog_draft_writer;
CREATE POLICY flex_acceptance_customer_read ON flex_customer_agreement_acceptances FOR SELECT TO flex_customer_acceptance_writer
 USING(EXISTS(SELECT 1 FROM flex_agreement_internal_approvals a WHERE a.agreement_id=flex_customer_agreement_acceptances.agreement_id AND a.hotel_id=flex_customer_agreement_acceptances.hotel_id));
CREATE POLICY flex_acceptance_admin_read ON flex_customer_agreement_acceptances FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_acceptance_customer_append ON flex_customer_agreement_acceptances FOR INSERT TO flex_customer_acceptance_writer
 WITH CHECK(accepted_by=NULLIF(current_setting('flex.authorized_subject_id',true),'')
 AND EXISTS(SELECT 1 FROM flex_commercial_agreement_versions a WHERE a.id=agreement_id AND a.hotel_id=flex_customer_agreement_acceptances.hotel_id AND a.terms_digest=flex_customer_agreement_acceptances.terms_digest));
COMMENT ON TABLE flex_customer_agreement_acceptances IS 'Authenticated owner acceptance of exact internally approved commercial draft; not a legal signature, entitlement, confirmed payment or fiscal document.';
COMMIT;
