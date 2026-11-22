-- MARINA FLEX integration backup / restore acceptance, PostgreSQL 16 QA only.
-- SELECT-only except transaction-local role/scopes. Uses fixture created in CI.
-- This is not a substitute for off-host, encrypted production backups.
SELECT 1 / CASE WHEN
  (SELECT count(*) FROM flex_hotels)=2 AND
  (SELECT count(*) FROM flex_invoices)=2 AND
  (SELECT count(*) FROM flex_invoice_lines)=2 AND
  (SELECT count(*) FROM flex_subscriptions)=2 AND
  (SELECT count(*) FROM flex_platform_memberships)=6 AND
  (SELECT count(*) FROM flex_platform_hotel_grants)=2
THEN 1 ELSE 0 END AS verified_fixture_restored;

-- All FLEX commercial tables must enable PostgreSQL RLS.
SELECT 1 / CASE WHEN NOT EXISTS (
    SELECT 1
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='public' AND c.relkind='r'
      AND c.relname LIKE 'flex_%' AND NOT c.relrowsecurity
) THEN 1 ELSE 0 END AS all_flex_tables_rls;

-- Confirm important write controls and audit invariants survived backup.
SELECT 1 / CASE WHEN
  EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='flex_confirmed_payments_no_rewrite' AND NOT tgisinternal) AND
  EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='flex_issued_invoice_history_no_rewrite' AND NOT tgisinternal) AND
  EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='flex_refund_cash_capacity' AND NOT tgisinternal) AND
  EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='flex_qa_partner_earnings_capacity' AND NOT tgisinternal)
THEN 1 ELSE 0 END AS immutable_ledger_guards_restored;

SELECT 1 / CASE WHEN
  EXISTS (SELECT 1 FROM pg_policies WHERE tablename='flex_partner_earnings_entries'
              AND policyname='flex_agent_statement_own') AND
  EXISTS (SELECT 1 FROM pg_policies WHERE tablename='flex_partner_earnings_entries'
              AND policyname='flex_investor_statement_own') AND
  EXISTS (SELECT 1 FROM pg_policies WHERE tablename='flex_invoices'
              AND policyname='flex_hotel_reader_invoices')
THEN 1 ELSE 0 END AS tenant_access_policies_restored;

SELECT 1 / CASE WHEN
  (SELECT count(*) FROM pg_roles WHERE rolname IN (
    'flex_identity_reader','flex_hotel_reader','flex_platform_admin_reader',
    'flex_agent_statement_reader','flex_investor_statement_reader',
    'flex_platform_statement_reader'
  ) AND NOT rolcanlogin)=6
THEN 1 ELSE 0 END AS no_login_reader_roles;

-- Missing hotel scope => no data, even after restoring the backup.
BEGIN;
SET LOCAL ROLE flex_hotel_reader;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_hotels)=0 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_invoices)=0 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_invoice_lines)=0 THEN 1 ELSE 0 END;
ROLLBACK;

-- Explicitly scoped test Hotel A cannot read B's commercial objects.
BEGIN;
SELECT set_config('flex.authorized_hotel_id','00000000-0000-0000-0000-00000000000a',true);
SET LOCAL ROLE flex_hotel_reader;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_hotels)=1 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_invoices)=1 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_invoice_lines)=1 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT sum(total) FROM flex_invoices)=100.00 THEN 1 ELSE 0 END;
ROLLBACK;

-- No investor/agent identity scope => default deny earnings.
BEGIN;
SET LOCAL ROLE flex_agent_statement_reader;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_partner_earnings_entries)=0 THEN 1 ELSE 0 END;
ROLLBACK;

BEGIN;
SET LOCAL ROLE flex_investor_statement_reader;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_partner_earnings_entries)=0 THEN 1 ELSE 0 END;
ROLLBACK;

-- Must not accidentally include operational hospitality data.
SELECT 1 / CASE WHEN NOT EXISTS (
  SELECT 1 FROM pg_tables WHERE schemaname='public'
    AND tablename IN ('properties','reservations','guests','folio','staff_users')
) THEN 1 ELSE 0 END AS pms_isolation_restored;
