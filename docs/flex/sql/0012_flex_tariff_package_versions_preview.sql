-- FLEX 0012: immutable tariff PACKAGE PROPOSALS per commercial hotel.
-- Apply only after 0001-0011 in isolated disposable FLEX PostgreSQL 16.
-- Never activate subscriptions, collect payments or modify PMS.
BEGIN;

CREATE TABLE flex_tariff_package_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
  package_kind text NOT NULL CHECK (package_kind IN ('BASE','BUSINESS','PREMIUM','CUSTOM')),
  version integer NOT NULL CHECK (version >= 1),
  title text NOT NULL CHECK (length(btrim(title)) BETWEEN 2 AND 120),
  sku_snapshot jsonb NOT NULL CHECK (
    jsonb_typeof(sku_snapshot)='array'
    AND jsonb_array_length(sku_snapshot) BETWEEN 1 AND 50
  ),
  list_monthly_total numeric(18,2) NOT NULL CHECK (list_monthly_total >= 0),
  discount_pct numeric(5,2) NOT NULL DEFAULT 0
    CHECK (discount_pct BETWEEN 0 AND 100),
  trial_days integer NOT NULL DEFAULT 0 CHECK (trial_days BETWEEN 0 AND 90),
  custom_monthly_price numeric(18,2) CHECK (custom_monthly_price >= 0),
  proposed_monthly_total numeric(18,2) NOT NULL CHECK (
    proposed_monthly_total = round(
      coalesce(custom_monthly_price,list_monthly_total*(100-discount_pct)/100),2
    )
  ),
  state text NOT NULL DEFAULT 'DRAFT' CHECK(state='DRAFT'),
  enforcement text NOT NULL DEFAULT 'OFF' CHECK(enforcement='OFF'),
  currency char(3) NOT NULL DEFAULT 'KGS' CHECK(currency='KGS'),
  created_by text NOT NULL CHECK(length(created_by) BETWEEN 2 AND 180),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (hotel_id,package_kind,version),
  CHECK (custom_monthly_price IS NULL OR discount_pct=0),
  CHECK (package_kind='CUSTOM' OR custom_monthly_price IS NULL)
);
CREATE INDEX flex_package_versions_hotel ON flex_tariff_package_versions
  (hotel_id,package_kind,version DESC);
ALTER TABLE flex_tariff_package_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_tariff_package_versions FORCE ROW LEVEL SECURITY;
CREATE TRIGGER flex_tariff_package_immutable
  BEFORE UPDATE OR DELETE ON flex_tariff_package_versions
  FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();

GRANT SELECT ON flex_tariff_package_versions TO flex_platform_admin_reader;
CREATE POLICY flex_tariff_package_admin_read
 ON flex_tariff_package_versions FOR SELECT TO flex_platform_admin_reader
 USING (true);

GRANT SELECT,INSERT ON flex_tariff_package_versions TO flex_catalog_draft_writer;
CREATE POLICY flex_tariff_package_writer_read
 ON flex_tariff_package_versions FOR SELECT TO flex_catalog_draft_writer
 USING (true);
CREATE POLICY flex_tariff_package_writer_create
 ON flex_tariff_package_versions FOR INSERT TO flex_catalog_draft_writer
 WITH CHECK (
   created_by=NULLIF(current_setting('flex.actor_subject_id',true),'')
   AND state='DRAFT' AND enforcement='OFF' AND currency='KGS'
 );
COMMENT ON TABLE flex_tariff_package_versions IS
 'Append-only proposed KGS tariff package versions. Not agreed, invoiced, paid or applied to PMS.';
COMMIT;
