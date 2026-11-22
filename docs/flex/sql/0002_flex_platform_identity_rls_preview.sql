-- MARINA FLEX PREVIEW 0002. Test only on disposable FLEX PostgreSQL after 0001.
-- Never run against the PMS DB. No production roll-out is configured.
-- The identity grants below are administered by the future control-plane service,
-- NOT by a hotel worker or by a token-supplied role claim.
BEGIN;

CREATE TABLE flex_platform_memberships (
  subject_id text PRIMARY KEY CHECK (length(subject_id) BETWEEN 2 AND 180),
  role text NOT NULL CHECK (role IN ('SUPER_ADMIN','BILLING','HOTEL_OWNER','SALES_AGENT','INVESTOR')),
  active boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE flex_platform_hotel_grants (
  subject_id text NOT NULL REFERENCES flex_platform_memberships(subject_id),
  hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
  granted_at timestamptz NOT NULL DEFAULT now(),
  granted_by text NOT NULL,
  PRIMARY KEY (subject_id,hotel_id)
);

-- Scope rows by a verified hotel selected server-side from platform grants.
-- Runtime must NOT open direct PostgreSQL access for end users.
CREATE ROLE flex_hotel_reader NOLOGIN;
GRANT USAGE ON SCHEMA public TO flex_hotel_reader;
GRANT SELECT ON flex_hotels, flex_subscriptions, flex_subscription_items,
  flex_invoices, flex_invoice_lines, flex_skus, flex_price_versions
TO flex_hotel_reader;

ALTER TABLE flex_hotels ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_hotels FORCE ROW LEVEL SECURITY;
CREATE POLICY flex_hotel_reader_hotels ON flex_hotels
FOR SELECT TO flex_hotel_reader
USING (id = NULLIF(current_setting('flex.authorized_hotel_id', true),'')::uuid);

ALTER TABLE flex_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_subscriptions FORCE ROW LEVEL SECURITY;
CREATE POLICY flex_hotel_reader_subscriptions ON flex_subscriptions
FOR SELECT TO flex_hotel_reader
USING (hotel_id = NULLIF(current_setting('flex.authorized_hotel_id', true),'')::uuid);

ALTER TABLE flex_subscription_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_subscription_items FORCE ROW LEVEL SECURITY;
CREATE POLICY flex_hotel_reader_subscription_items ON flex_subscription_items
FOR SELECT TO flex_hotel_reader
USING (EXISTS (
  SELECT 1 FROM flex_subscriptions s
  WHERE s.id = subscription_id
    AND s.hotel_id = NULLIF(current_setting('flex.authorized_hotel_id', true),'')::uuid
));

ALTER TABLE flex_invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_invoices FORCE ROW LEVEL SECURITY;
CREATE POLICY flex_hotel_reader_invoices ON flex_invoices
FOR SELECT TO flex_hotel_reader
USING (hotel_id = NULLIF(current_setting('flex.authorized_hotel_id', true),'')::uuid);

ALTER TABLE flex_invoice_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_invoice_lines FORCE ROW LEVEL SECURITY;
CREATE POLICY flex_hotel_reader_invoice_lines ON flex_invoice_lines
FOR SELECT TO flex_hotel_reader
USING (EXISTS (
  SELECT 1 FROM flex_invoices i
  WHERE i.id = invoice_id
    AND i.hotel_id = NULLIF(current_setting('flex.authorized_hotel_id', true),'')::uuid
));

ALTER TABLE flex_skus ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_skus FORCE ROW LEVEL SECURITY;
CREATE POLICY flex_hotel_reader_catalog ON flex_skus
FOR SELECT TO flex_hotel_reader
USING (product_status = 'AVAILABLE');

ALTER TABLE flex_price_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_price_versions FORCE ROW LEVEL SECURITY;
CREATE POLICY flex_hotel_reader_prices ON flex_price_versions
FOR SELECT TO flex_hotel_reader
USING (EXISTS (SELECT 1 FROM flex_skus s WHERE s.sku=flex_price_versions.sku));

-- These commercially sensitive tables are default-deny until a reviewed,
-- independently tested role-specific RLS policy is added. They are not
-- granted to flex_hotel_reader. SUPER_ADMIN is NOT an SQL role.
ALTER TABLE flex_hotel_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_payment_intents ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_provider_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_provider_event_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_confirmed_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_payment_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_payment_reversals ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_allocation_reversals ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_agent_attributions ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_agent_commission_accruals ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_investors ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_investor_contract_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_investor_accruals ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_platform_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_platform_hotel_grants ENABLE ROW LEVEL SECURITY;

-- No app user can log in as reader; only a trusted DB runtime may SET LOCAL ROLE
-- and SET LOCAL flex.authorized_hotel_id in a transaction after verifying JWT
-- + database-backed hotel membership. An injected request header is insufficient.
COMMENT ON ROLE flex_hotel_reader IS
  'FLEX isolated server-only read scope; never grant direct DB login to guests/hotel employees';
COMMIT;
