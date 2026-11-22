-- MARINA FLEX 0011: P0 catalog maintenance and subscription CONFIGURATION DRAFTS.
-- Run AFTER 0001..0010 on a separate disposable FLEX PostgreSQL 16 ONLY.
-- No PMS, payments, invoices, receivables, bank keys or subscriptions are changed.
BEGIN;

CREATE TABLE flex_subscription_configuration_drafts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
  version integer NOT NULL CHECK (version > 0),
  title text NOT NULL CHECK (length(btrim(title)) BETWEEN 2 AND 120),
  period_start date NOT NULL,
  period_end date NOT NULL,
  enforcement text NOT NULL DEFAULT 'OFF' CHECK (enforcement='OFF'),
  state text NOT NULL DEFAULT 'DRAFT' CHECK (state='DRAFT'),
  currency char(3) NOT NULL DEFAULT 'KGS' CHECK (currency='KGS'),
  items jsonb NOT NULL CHECK (
    jsonb_typeof(items)='array'
    AND jsonb_array_length(items) BETWEEN 1 AND 50
  ),
  proposed_monthly_total numeric(18,2) NOT NULL CHECK (proposed_monthly_total>=0),
  created_by text NOT NULL CHECK (length(created_by) BETWEEN 2 AND 180),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (hotel_id, version),
  CHECK (period_end>=period_start)
);
CREATE INDEX flex_subscription_drafts_hotel_created
  ON flex_subscription_configuration_drafts(hotel_id,created_at DESC,id);

ALTER TABLE flex_subscription_configuration_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_subscription_configuration_drafts FORCE ROW LEVEL SECURITY;
CREATE TRIGGER flex_subscription_config_draft_immutable
  BEFORE UPDATE OR DELETE ON flex_subscription_configuration_drafts
  FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();

-- Existing global SUPER_ADMIN reader can inspect proposals. HOTEL_OWNER does not
-- receive draft access because they are not approved subscription entitlements.
GRANT SELECT ON flex_subscription_configuration_drafts TO flex_platform_admin_reader;
CREATE POLICY flex_admin_read_configuration_drafts
  ON flex_subscription_configuration_drafts
  FOR SELECT TO flex_platform_admin_reader USING (true);

-- The only writer role; the dedicated API runtime must have NOINHERIT membership.
-- It has *no* rights on flex_subscriptions, *_items, hotel links, invoice,
-- payment, provider, partner earning, entitlement or PMS tables.
CREATE ROLE flex_catalog_draft_writer NOLOGIN NOINHERIT;
GRANT USAGE ON SCHEMA public TO flex_catalog_draft_writer;
GRANT SELECT, INSERT ON flex_skus, flex_price_versions,
  flex_subscription_configuration_drafts TO flex_catalog_draft_writer;
GRANT SELECT ON flex_hotels TO flex_catalog_draft_writer;

CREATE POLICY flex_draft_writer_hotel_read
  ON flex_hotels FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_draft_writer_sku_read
  ON flex_skus FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_draft_writer_sku_create
  ON flex_skus FOR INSERT TO flex_catalog_draft_writer
  WITH CHECK(product_status='PLANNED' AND is_core=false);
CREATE POLICY flex_draft_writer_price_read
  ON flex_price_versions FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_draft_writer_price_create
  ON flex_price_versions FOR INSERT TO flex_catalog_draft_writer
  WITH CHECK(
    currency='KGS' AND valid_from>now()+interval '1 day'
    AND EXISTS (SELECT 1 FROM flex_skus s
      WHERE s.sku=flex_price_versions.sku
      AND s.product_status IN ('PLANNED','AVAILABLE')
      AND s.is_core=false)
  );
CREATE POLICY flex_draft_writer_proposal_read
  ON flex_subscription_configuration_drafts FOR SELECT
  TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_draft_writer_proposal_create
  ON flex_subscription_configuration_drafts FOR INSERT
  TO flex_catalog_draft_writer WITH CHECK(
    state='DRAFT' AND enforcement='OFF' AND currency='KGS'
    AND created_by=NULLIF(current_setting('flex.actor_subject_id',true),'')
  );

-- For all legacy roles, the new table is FORCE RLS default-deny unless
-- explicitly listed above. No grants to anon, authenticated or PUBLIC.
COMMENT ON TABLE flex_subscription_configuration_drafts IS
  'Proposed commercial plan only. NEVER a live subscription, invoice, payment, or PMS entitlement.';
COMMENT ON ROLE flex_catalog_draft_writer IS
  'Dedicated FLEX QA admin draft writer; not a login and no authority over payments or active subscriptions.';

COMMIT;
