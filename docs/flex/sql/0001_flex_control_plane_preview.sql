-- MARINA SMART FLEX central commercial control-plane, preview DDL.
-- NOT an automatic PMS migration. Apply ONLY to a disposable, isolated PostgreSQL.
-- Not suitable for production until service auth, RLS, backups and provider reconciliation.
-- No guest, reservation, folio, PMS or user-password tables are referenced.
BEGIN;

CREATE TABLE flex_hotels (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name text NOT NULL CHECK (length(trim(display_name)) > 0),
  billing_currency char(3) NOT NULL DEFAULT 'KGS',
  status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','ACTIVE','ARCHIVED')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE flex_hotel_links (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
  deployment_id text NOT NULL,
  property_external_id text NOT NULL,
  tenant_external_id text,
  verified_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (deployment_id,property_external_id),
  UNIQUE (hotel_id,deployment_id,property_external_id)
);
CREATE TABLE flex_skus (
  sku text PRIMARY KEY CHECK (sku ~ '^[A-Z][A-Z0-9_]{1,79}$'),
  title text NOT NULL,
  capability_key text NOT NULL,
  product_status text NOT NULL CHECK (product_status IN ('AVAILABLE','BETA','PLANNED','RETIRED')),
  is_core boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE flex_price_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sku text NOT NULL REFERENCES flex_skus(sku),
  version integer NOT NULL CHECK (version >= 1),
  currency char(3) NOT NULL DEFAULT 'KGS',
  monthly_price numeric(18,2) NOT NULL CHECK (monthly_price >= 0),
  valid_from timestamptz NOT NULL,
  valid_to timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (valid_to IS NULL OR valid_to > valid_from),
  UNIQUE (sku,version)
);
CREATE TABLE flex_subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
  status text NOT NULL CHECK (status IN (
    'TRIAL','ACTIVE','PAYMENT_DUE','GRACE','SUSPENDED','CANCELLED','GRANDFATHERED'
  )),
  enforcement text NOT NULL DEFAULT 'OFF' CHECK (enforcement IN ('OFF','SHADOW','ENFORCE')),
  period_start date NOT NULL,
  period_end date NOT NULL,
  grace_until timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (period_end >= period_start),
  UNIQUE (id,hotel_id)
);
CREATE UNIQUE INDEX flex_one_current_subscription_per_hotel
  ON flex_subscriptions(hotel_id)
  WHERE status IN ('TRIAL','ACTIVE','PAYMENT_DUE','GRACE','SUSPENDED','GRANDFATHERED');
CREATE TABLE flex_subscription_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subscription_id uuid NOT NULL REFERENCES flex_subscriptions(id),
  sku text NOT NULL REFERENCES flex_skus(sku),
  price_version_id uuid REFERENCES flex_price_versions(id),
  unit_price numeric(18,2) NOT NULL CHECK (unit_price >= 0),
  currency char(3) NOT NULL DEFAULT 'KGS',
  source text NOT NULL CHECK (source IN ('BUNDLE','PURCHASE','TRIAL','MANUAL','LEGACY')),
  active_from timestamptz NOT NULL,
  active_until timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (active_until IS NULL OR active_until > active_from)
);
CREATE TABLE flex_invoices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
  invoice_number text NOT NULL UNIQUE,
  currency char(3) NOT NULL DEFAULT 'KGS',
  status text NOT NULL CHECK (status IN ('DRAFT','ISSUED','PARTIALLY_PAID','PAID','VOID')),
  total numeric(18,2) NOT NULL CHECK (total >= 0),
  issued_at timestamptz,
  due_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (id,hotel_id)
);
CREATE TABLE flex_invoice_lines (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id uuid NOT NULL REFERENCES flex_invoices(id),
  sku text NOT NULL REFERENCES flex_skus(sku),
  price_version_id uuid REFERENCES flex_price_versions(id),
  currency char(3) NOT NULL DEFAULT 'KGS',
  description text NOT NULL,
  quantity numeric(12,2) NOT NULL CHECK (quantity > 0),
  unit_price numeric(18,2) NOT NULL CHECK (unit_price >= 0),
  amount numeric(18,2) NOT NULL CHECK (amount >= 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (id,invoice_id)
);
CREATE TABLE flex_payment_intents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id uuid NOT NULL REFERENCES flex_invoices(id),
  provider text NOT NULL,
  external_intent_id text,
  requested_amount numeric(18,2) NOT NULL CHECK (requested_amount > 0),
  currency char(3) NOT NULL,
  state text NOT NULL CHECK (state IN ('REQUESTED','READY','FAILED','EXPIRED')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (provider,external_intent_id)
);
CREATE TABLE flex_provider_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider text NOT NULL,
  event_id text NOT NULL,
  payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[a-f0-9]{64}$'),
  received_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (provider,event_id)
);
CREATE TABLE flex_provider_event_attempts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_event_id uuid NOT NULL REFERENCES flex_provider_events(id),
  processed_at timestamptz NOT NULL DEFAULT now(),
  status text NOT NULL CHECK (status IN ('IGNORED','APPLIED','FAILED')),
  error_class text
);
CREATE TABLE flex_confirmed_payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id uuid NOT NULL,
  invoice_id uuid NOT NULL,
  provider text NOT NULL,
  provider_payment_id text NOT NULL,
  amount numeric(18,2) NOT NULL CHECK (amount > 0),
  currency char(3) NOT NULL,
  confirmed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (invoice_id,hotel_id) REFERENCES flex_invoices(id,hotel_id),
  UNIQUE (id,invoice_id),
  UNIQUE (provider,provider_payment_id)
);
CREATE TABLE flex_payment_allocations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id uuid NOT NULL,
  payment_id uuid NOT NULL,
  invoice_line_id uuid NOT NULL,
  amount numeric(18,2) NOT NULL CHECK (amount > 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (payment_id,invoice_id) REFERENCES flex_confirmed_payments(id,invoice_id),
  FOREIGN KEY (invoice_line_id,invoice_id) REFERENCES flex_invoice_lines(id,invoice_id),
  UNIQUE (payment_id,invoice_line_id)
);
-- Under the same transaction we must lock the payment and line, then ensure
-- that cumulative allocations do not exceed confirmed cash or line charges.
CREATE FUNCTION flex_allocation_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE paid numeric(18,2); invoiced numeric(18,2); applied numeric(18,2);
BEGIN
  SELECT amount INTO paid FROM flex_confirmed_payments WHERE id=NEW.payment_id FOR UPDATE;
  SELECT amount INTO invoiced FROM flex_invoice_lines WHERE id=NEW.invoice_line_id FOR UPDATE;
  SELECT COALESCE(SUM(amount),0) INTO applied
    FROM flex_payment_allocations WHERE payment_id=NEW.payment_id;
  IF applied > paid THEN
    RAISE EXCEPTION 'FLEX_ALLOCATIONS_EXCEED_PAYMENT';
  END IF;
  SELECT COALESCE(SUM(amount),0) INTO applied
    FROM flex_payment_allocations WHERE invoice_line_id=NEW.invoice_line_id;
  IF applied > invoiced THEN
    RAISE EXCEPTION 'FLEX_ALLOCATIONS_EXCEED_INVOICE_LINE';
  END IF;
  RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER flex_allocation_capacity
AFTER INSERT OR UPDATE ON flex_payment_allocations DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION flex_allocation_guard();

-- All financial reversal entries are new rows; do not edit/delete the originals.
CREATE TABLE flex_payment_reversals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  payment_id uuid NOT NULL REFERENCES flex_confirmed_payments(id),
  external_reversal_key text NOT NULL UNIQUE,
  amount numeric(18,2) NOT NULL CHECK (amount > 0),
  reason text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE flex_allocation_reversals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  reversal_id uuid NOT NULL REFERENCES flex_payment_reversals(id),
  allocation_id uuid NOT NULL REFERENCES flex_payment_allocations(id),
  amount numeric(18,2) NOT NULL CHECK (amount > 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (reversal_id,allocation_id)
);
CREATE TABLE flex_agents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  platform_subject_id text NOT NULL UNIQUE,
  status text NOT NULL CHECK (status IN ('ACTIVE','DISABLED')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE flex_agent_attributions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id uuid NOT NULL REFERENCES flex_agents(id),
  hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
  sku text REFERENCES flex_skus(sku),
  attributed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE flex_agent_commission_accruals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  attribution_id uuid NOT NULL REFERENCES flex_agent_attributions(id),
  allocation_id uuid NOT NULL REFERENCES flex_payment_allocations(id),
  rate_bps integer NOT NULL CHECK (rate_bps BETWEEN 0 AND 10000),
  amount numeric(18,2) NOT NULL CHECK (amount >= 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (attribution_id,allocation_id)
);
CREATE TABLE flex_investors (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  platform_subject_id text NOT NULL UNIQUE,
  status text NOT NULL CHECK (status IN ('ACTIVE','DISABLED')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE flex_investor_contract_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  investor_id uuid NOT NULL REFERENCES flex_investors(id),
  contract_key text NOT NULL,
  version integer NOT NULL CHECK (version >= 1),
  principal numeric(18,2) NOT NULL CHECK (principal > 0),
  share_bps integer NOT NULL CHECK (share_bps BETWEEN 0 AND 10000),
  terms jsonb NOT NULL,
  effective_from date NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (contract_key,version)
);
CREATE TABLE flex_investor_accruals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contract_version_id uuid NOT NULL REFERENCES flex_investor_contract_versions(id),
  allocation_id uuid NOT NULL REFERENCES flex_payment_allocations(id),
  phase text NOT NULL CHECK (phase IN ('RETURN','BONUS')),
  amount numeric(18,2) NOT NULL CHECK (amount >= 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (contract_version_id,allocation_id,phase)
);
CREATE TABLE flex_audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  platform_subject_id text NOT NULL,
  action text NOT NULL,
  resource_type text NOT NULL,
  resource_id text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE FUNCTION flex_reject_history_rewrite() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'FLEX_HISTORY_IS_APPEND_ONLY';
END $$;
CREATE TRIGGER flex_provider_events_no_rewrite
  BEFORE UPDATE OR DELETE ON flex_provider_events
  FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
CREATE TRIGGER flex_audit_events_no_rewrite
  BEFORE UPDATE OR DELETE ON flex_audit_events
  FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
CREATE TRIGGER flex_confirmed_payments_no_rewrite
  BEFORE UPDATE OR DELETE ON flex_confirmed_payments
  FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
CREATE TRIGGER flex_allocations_no_rewrite
  BEFORE UPDATE OR DELETE ON flex_payment_allocations
  FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
CREATE TRIGGER flex_investor_accruals_no_rewrite
  BEFORE UPDATE OR DELETE ON flex_investor_accruals
  FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
CREATE TRIGGER flex_agent_accruals_no_rewrite
  BEFORE UPDATE OR DELETE ON flex_agent_commission_accruals
  FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();

CREATE INDEX flex_invoices_hotel_status ON flex_invoices(hotel_id,status);
CREATE INDEX flex_subscription_items_sub ON flex_subscription_items(subscription_id);
CREATE INDEX flex_allocations_line ON flex_payment_allocations(invoice_line_id);
CREATE INDEX flex_investor_accruals_contract ON flex_investor_accruals(contract_version_id);
CREATE INDEX flex_agent_accruals_attr ON flex_agent_commission_accruals(attribution_id);

-- No platform login, RLS claim, user credentials, banking provider or payouts.
-- Explicit RLS role policies and service boundary are the gate before any live use.
-- Defend the financial dimensions at the database boundary.
-- An invoice cannot contain a different currency than its line or payment,
-- and a quoted price version cannot be reassigned to another SKU.
ALTER TABLE flex_price_versions ADD CONSTRAINT flex_price_version_composite
  UNIQUE (id,sku);
ALTER TABLE flex_subscription_items ADD CONSTRAINT flex_subscription_item_price_sku
  FOREIGN KEY (price_version_id,sku) REFERENCES flex_price_versions(id,sku);
ALTER TABLE flex_invoice_lines ADD CONSTRAINT flex_invoice_line_price_sku
  FOREIGN KEY (price_version_id,sku) REFERENCES flex_price_versions(id,sku);
ALTER TABLE flex_invoices ADD CONSTRAINT flex_invoice_hotel_currency
  UNIQUE (id,hotel_id,currency);
ALTER TABLE flex_invoices ADD CONSTRAINT flex_invoice_currency
  UNIQUE (id,currency);
ALTER TABLE flex_invoice_lines ADD CONSTRAINT flex_invoice_line_currency
  FOREIGN KEY (invoice_id,currency) REFERENCES flex_invoices(id,currency);
ALTER TABLE flex_payment_intents ADD CONSTRAINT flex_intent_invoice_currency
  FOREIGN KEY (invoice_id,currency) REFERENCES flex_invoices(id,currency);
ALTER TABLE flex_confirmed_payments ADD CONSTRAINT flex_confirmed_payment_currency
  FOREIGN KEY (invoice_id,hotel_id,currency) REFERENCES flex_invoices(id,hotel_id,currency);

COMMIT;
