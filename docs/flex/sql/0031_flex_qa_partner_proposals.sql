-- Separate PARTNER membership and immutable commercial proposals. No account or money creation.
BEGIN;
ALTER TABLE flex_platform_memberships DROP CONSTRAINT flex_platform_memberships_role_check,
 ADD CONSTRAINT flex_platform_memberships_role_check CHECK(role IN ('SUPER_ADMIN','BILLING','HOTEL_OWNER','SALES_AGENT','INVESTOR','PARTNER'));
CREATE TABLE flex_qa_partner_proposals (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 partner_subject_id text NOT NULL REFERENCES flex_platform_memberships(subject_id),
 hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
 revision integer NOT NULL CHECK(revision>0),
 hotel_name_snapshot text NOT NULL,
 title text NOT NULL CHECK(length(btrim(title)) BETWEEN 2 AND 120),
 terms_text text NOT NULL CHECK(length(btrim(terms_text)) BETWEEN 2 AND 2000),
 state text NOT NULL DEFAULT 'DRAFT' CHECK(state='DRAFT'),
 created_by text NOT NULL CHECK(length(btrim(created_by)) BETWEEN 2 AND 180),
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(partner_subject_id,hotel_id,revision)
);
ALTER TABLE flex_qa_partner_proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_qa_partner_proposals FORCE ROW LEVEL SECURITY;
CREATE TRIGGER flex_qa_partner_proposals_immutable BEFORE UPDATE OR DELETE ON flex_qa_partner_proposals
 FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
GRANT SELECT(subject_id,role,active) ON flex_platform_memberships TO flex_catalog_draft_writer;
CREATE POLICY flex_qa_partner_roster_read ON flex_platform_memberships FOR SELECT TO flex_catalog_draft_writer
 USING(role='PARTNER');
GRANT SELECT,INSERT ON flex_qa_partner_proposals TO flex_catalog_draft_writer;
CREATE POLICY flex_qa_partner_proposal_admin_read ON flex_qa_partner_proposals FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_qa_partner_proposal_admin_append ON flex_qa_partner_proposals FOR INSERT TO flex_catalog_draft_writer
 WITH CHECK(created_by=NULLIF(current_setting('flex.actor_subject_id',true),'')
 AND EXISTS(SELECT 1 FROM flex_platform_memberships m WHERE m.subject_id=partner_subject_id AND m.role='PARTNER' AND m.active));
GRANT SELECT(id,partner_subject_id,hotel_id,revision,hotel_name_snapshot,title,terms_text,state,created_at)
 ON flex_qa_partner_proposals TO flex_identity_reader;
CREATE POLICY flex_qa_partner_proposal_self ON flex_qa_partner_proposals FOR SELECT TO flex_identity_reader
 USING(partner_subject_id=NULLIF(current_setting('flex.authorized_subject_id',true),'')
 AND EXISTS(SELECT 1 FROM flex_platform_memberships m WHERE m.subject_id=partner_subject_id AND m.role='PARTNER' AND m.active));
COMMENT ON TABLE flex_qa_partner_proposals IS 'Individual QA proposals; no signed contract, accrual, entitlement or payout.';
COMMIT;
