-- FLEX launch offer reservation, not payment, activation or entitlement.
BEGIN;
CREATE TABLE flex_launch_offer_reservations (
 hotel_id uuid PRIMARY KEY REFERENCES flex_hotels(id),
 slot integer NOT NULL UNIQUE CHECK (slot BETWEEN 1 AND 50),
 offer_id uuid NOT NULL UNIQUE REFERENCES flex_tariff_package_versions(id),
 created_by text NOT NULL CHECK(length(btrim(created_by)) BETWEEN 2 AND 180),
 created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE flex_launch_offer_reservations ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_launch_offer_reservations FORCE ROW LEVEL SECURITY;
CREATE TRIGGER flex_launch_offer_immutable BEFORE UPDATE OR DELETE ON flex_launch_offer_reservations
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
GRANT SELECT,INSERT ON flex_launch_offer_reservations TO flex_catalog_draft_writer;
GRANT SELECT ON flex_launch_offer_reservations TO flex_platform_admin_reader;
CREATE POLICY flex_launch_offer_read ON flex_launch_offer_reservations FOR SELECT TO flex_catalog_draft_writer,flex_platform_admin_reader USING (true);
CREATE POLICY flex_launch_offer_append ON flex_launch_offer_reservations FOR INSERT TO flex_catalog_draft_writer
WITH CHECK (
 created_by=NULLIF(current_setting('flex.actor_subject_id',true),'')
 AND EXISTS (SELECT 1 FROM flex_tariff_package_versions p
 WHERE p.id=flex_launch_offer_reservations.offer_id AND p.hotel_id=flex_launch_offer_reservations.hotel_id
 AND p.created_by=flex_launch_offer_reservations.created_by
 AND p.package_kind IN ('BASE','BUSINESS','PREMIUM') AND p.term_months=12
 AND p.commercial_policy_version IS NOT NULL AND p.discount_pct=40
 AND p.custom_monthly_price IS NULL AND p.state='DRAFT' AND p.enforcement='OFF'
 AND p.source_template_id IS NULL
 AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(p.sku_snapshot) i
 WHERE i->>'sku'<>'BASE_PMS' AND coalesce(i->>'included_in_package','false')<>'true'))
);
COMMENT ON TABLE flex_launch_offer_reservations IS 'At most 50 distinct draft reservations; no payment confirmation. Eligibility becomes final only after verified annual prepayment. No automatic slot recycling.';
COMMIT;
