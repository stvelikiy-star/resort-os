-- Global module selections for FLEX QA. Hotel-specific terms stay on the offer.
BEGIN;
CREATE TABLE flex_tariff_templates (
    id uuid PRIMARY KEY REFERENCES flex_tariff_package_versions(id),
    package_kind text NOT NULL CHECK (package_kind IN ('BASE','BUSINESS','PREMIUM')),
    revision integer NOT NULL CHECK (revision > 0),
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (package_kind, revision)
);
ALTER TABLE flex_tariff_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_tariff_templates FORCE ROW LEVEL SECURITY;
GRANT SELECT, INSERT ON flex_tariff_templates TO flex_catalog_draft_writer;
CREATE POLICY flex_templates_read ON flex_tariff_templates
    FOR SELECT TO flex_catalog_draft_writer USING (true);
CREATE POLICY flex_templates_create ON flex_tariff_templates
    FOR INSERT TO flex_catalog_draft_writer WITH CHECK (
        created_by = NULLIF(current_setting('flex.actor_subject_id', true), '')
        AND EXISTS (SELECT 1 FROM flex_tariff_package_versions p
                    WHERE p.id = flex_tariff_templates.id
                      AND p.package_kind = flex_tariff_templates.package_kind)
    );
CREATE TRIGGER flex_template_immutable BEFORE UPDATE OR DELETE ON flex_tariff_templates
    FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
ALTER TABLE flex_tariff_package_versions ADD COLUMN source_template_id uuid
    REFERENCES flex_tariff_templates(id);
COMMIT;
