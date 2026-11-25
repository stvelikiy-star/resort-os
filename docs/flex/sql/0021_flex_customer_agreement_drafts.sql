-- FLEX commercial customer history and non-signable contract drafts.
BEGIN;
CREATE TABLE flex_hotel_profile_versions (
 hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
 version integer NOT NULL CHECK(version>0),
 contact_name text NOT NULL CHECK(length(contact_name)<=180),
 contact_email text NOT NULL CHECK(length(contact_email)<=254),
 contact_phone text NOT NULL CHECK(length(contact_phone)<=40),
 responsible_name text NOT NULL CHECK(length(responsible_name)<=180),
 created_by text NOT NULL CHECK(length(btrim(created_by)) BETWEEN 2 AND 180),
 created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(hotel_id,version)
);
ALTER TABLE flex_hotel_profile_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_hotel_profile_versions FORCE ROW LEVEL SECURITY;
CREATE TRIGGER flex_hotel_profile_immutable BEFORE UPDATE OR DELETE ON flex_hotel_profile_versions
 FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
GRANT SELECT,INSERT ON flex_hotel_profile_versions TO flex_catalog_draft_writer;
CREATE POLICY flex_hotel_profile_read ON flex_hotel_profile_versions FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_hotel_profile_append ON flex_hotel_profile_versions FOR INSERT TO flex_catalog_draft_writer
 WITH CHECK(created_by=NULLIF(current_setting('flex.actor_subject_id',true),'')
 AND EXISTS(SELECT 1 FROM flex_hotels h WHERE h.id=hotel_id AND h.status IN ('PENDING','ACTIVE')));
ALTER TABLE flex_tariff_package_versions ADD CONSTRAINT flex_offer_hotel_identity UNIQUE(id,hotel_id);
ALTER TABLE flex_commercial_agreement_versions
 ADD COLUMN source_offer_id uuid,
 ADD COLUMN draft_created_by text,
 ADD CONSTRAINT flex_agreement_offer_hotel FOREIGN KEY(source_offer_id,hotel_id) REFERENCES flex_tariff_package_versions(id,hotel_id),
 ADD CONSTRAINT flex_agreement_offer_unique UNIQUE(source_offer_id),
 ADD CONSTRAINT flex_agreement_source_actor CHECK ((source_offer_id IS NULL AND draft_created_by IS NULL) OR (source_offer_id IS NOT NULL AND draft_created_by IS NOT NULL AND state='DRAFT'));
GRANT SELECT,INSERT ON flex_commercial_agreement_versions TO flex_catalog_draft_writer;
CREATE POLICY flex_agreement_draft_read ON flex_commercial_agreement_versions FOR SELECT TO flex_catalog_draft_writer USING(state='DRAFT' AND source_offer_id IS NOT NULL);
CREATE POLICY flex_agreement_draft_append ON flex_commercial_agreement_versions FOR INSERT TO flex_catalog_draft_writer WITH CHECK(
 state='DRAFT' AND signed_at IS NULL AND signed_by_subject_id IS NULL
 AND draft_created_by=NULLIF(current_setting('flex.actor_subject_id',true),'')
 AND EXISTS(SELECT 1 FROM flex_tariff_package_versions p WHERE p.id=source_offer_id AND p.hotel_id=flex_commercial_agreement_versions.hotel_id AND p.commercial_policy_version IS NOT NULL AND p.term_months IS NOT NULL)
);
GRANT SELECT,INSERT ON flex_non_issuable_invoice_previews TO flex_catalog_draft_writer;
CREATE POLICY flex_preview_draft_read ON flex_non_issuable_invoice_previews FOR SELECT TO flex_catalog_draft_writer USING(
 EXISTS(SELECT 1 FROM flex_commercial_agreement_versions a WHERE a.id=agreement_version_id AND a.hotel_id=flex_non_issuable_invoice_previews.hotel_id AND a.source_offer_id IS NOT NULL AND a.state='DRAFT'));
CREATE POLICY flex_preview_draft_append ON flex_non_issuable_invoice_previews FOR INSERT TO flex_catalog_draft_writer WITH CHECK(
 status='NON_ISSUABLE' AND tax_status='NOT_CALCULATED'
 AND EXISTS(SELECT 1 FROM flex_commercial_agreement_versions a JOIN flex_tariff_package_versions p ON p.id=a.source_offer_id
 WHERE a.id=agreement_version_id AND a.hotel_id=flex_non_issuable_invoice_previews.hotel_id AND a.state='DRAFT'
 AND quote_sha256=a.terms_digest AND flex_non_issuable_invoice_previews.period_start=p.period_start
 AND flex_non_issuable_invoice_previews.period_end=p.period_end_exclusive-1
 AND amount_before_unresolved_taxes=p.subscription_term_total+p.implementation_total));
COMMIT;
