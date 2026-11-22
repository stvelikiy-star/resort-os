-- MARINA FLEX 0011 independent PG16 QA contract. No payment or PMS writes.
-- Requires 0001..0011 applied to disposable PostgreSQL 16.
BEGIN;

DO $test$
DECLARE
  name text;
BEGIN
  IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='flex_catalog_draft_writer') THEN
    RAISE EXCEPTION 'CI_ROLE_MISSING';
  END IF;
  FOREACH name IN ARRAY ARRAY[
    'flex_subscriptions','flex_subscription_items','flex_hotel_links',
    'flex_invoices','flex_invoice_lines','flex_payment_intents',
    'flex_confirmed_payments','flex_payment_allocations',
    'flex_agents','flex_investors','flex_platform_memberships',
    'flex_platform_hotel_grants'
  ] LOOP
    IF has_table_privilege('flex_catalog_draft_writer',name,'INSERT')
       OR has_table_privilege('flex_catalog_draft_writer',name,'UPDATE')
       OR has_table_privilege('flex_catalog_draft_writer',name,'DELETE') THEN
      RAISE EXCEPTION 'CI_FORBIDDEN_FLEX_WRITE_ROLE: %',name;
    END IF;
  END LOOP;
  IF has_table_privilege('flex_catalog_draft_writer','flex_skus','UPDATE')
      OR has_table_privilege('flex_catalog_draft_writer','flex_price_versions','UPDATE')
      OR has_table_privilege('flex_catalog_draft_writer','flex_subscription_configuration_drafts','UPDATE') THEN
    RAISE EXCEPTION 'CI_WRITER_CAN_MODIFY_HISTORY';
  END IF;
  IF has_table_privilege('PUBLIC','flex_subscription_configuration_drafts','SELECT') OR
     has_table_privilege('PUBLIC','flex_subscription_configuration_drafts','INSERT') THEN
    RAISE EXCEPTION 'CI_DRAFTS_PUBLICLY_EXPOSED';
  END IF;
  IF NOT (SELECT relrowsecurity AND relforcerowsecurity
      FROM pg_class WHERE oid='flex_subscription_configuration_drafts'::regclass) THEN
    RAISE EXCEPTION 'CI_DRAFT_RLS_NOT_FORCED';
  END IF;
END
$test$;

-- Seed two commercial test hotels and a pre-approved catalog SKU only within
-- the disposable and ROLLBACK-protected transaction. No operational PMS data.
INSERT INTO flex_hotels(id,display_name,status)
VALUES
 ('11111111-1111-4111-8111-111111111111','FLEX QA ONLY Hotel A','PENDING'),
 ('22222222-2222-4222-8222-222222222222','FLEX QA ONLY Hotel B','PENDING');
INSERT INTO flex_skus(sku,title,capability_key,product_status,is_core)
VALUES('APPROVED_QA','Approved QA capability','approved.qa','AVAILABLE',false);
INSERT INTO flex_price_versions(sku,version,currency,monthly_price,valid_from)
VALUES('APPROVED_QA',1,'KGS',1200.00,now()-interval '1 day');

SET LOCAL ROLE flex_catalog_draft_writer;
SELECT set_config('flex.actor_subject_id','qa-super-admin',true);

-- Allowed: add only PLANNED sku, no UPDATE and no activation.
INSERT INTO flex_skus(sku,title,capability_key,product_status,is_core)
VALUES('PLANNED_EXTRA','QA planned only','planned.extra','PLANNED',false);
DO $test$
BEGIN
  BEGIN
    INSERT INTO flex_skus(sku,title,capability_key,product_status,is_core)
    VALUES('MALICIOUS_ACTIVE','Not allowed','malicious.active','AVAILABLE',false);
    RAISE EXCEPTION 'CI_ACTIVE_SKU_INSERT_ALLOWED';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
END
$test$;

INSERT INTO flex_price_versions(sku,version,currency,monthly_price,valid_from)
VALUES('PLANNED_EXTRA',1,'KGS',750.00,now()+interval '2 days');
INSERT INTO flex_price_versions(sku,version,currency,monthly_price,valid_from)
VALUES('PLANNED_EXTRA',2,'KGS',800.00,now()+interval '3 days');
DO $test$
BEGIN
  BEGIN
    INSERT INTO flex_price_versions(sku,version,currency,monthly_price,valid_from)
    VALUES('PLANNED_EXTRA',2,'KGS',950.00,now()+interval '4 days');
    RAISE EXCEPTION 'CI_NONMONOTONIC_PRICE_VERSION_ACCEPTED';
  EXCEPTION WHEN check_violation THEN
    IF SQLERRM<>'FLEX_PRICE_VERSION_NOT_MONOTONIC' THEN RAISE; END IF;
  END;
END
$test$;

-- Subscription draft is not a subscription and cannot change access.
INSERT INTO flex_subscription_configuration_drafts(
 hotel_id,version,title,period_start,period_end,items,
 proposed_monthly_total,created_by
) VALUES(
 '11111111-1111-4111-8111-111111111111',1,'QA trial configuration',
 current_date+interval '7 days',current_date+interval '37 days',
 '[{"sku":"APPROVED_QA","monthly_price":"1200.00","currency":"KGS"}]'::jsonb,
 1200.00,'qa-super-admin'
);
DO $test$
BEGIN
  IF (SELECT state FROM flex_subscription_configuration_drafts
     WHERE hotel_id='11111111-1111-4111-8111-111111111111')<>'DRAFT' THEN
    RAISE EXCEPTION 'CI_DRAFT_ACTIVATED';
  END IF;
  IF (SELECT enforcement FROM flex_subscription_configuration_drafts
     WHERE hotel_id='11111111-1111-4111-8111-111111111111')<>'OFF' THEN
    RAISE EXCEPTION 'CI_DRAFT_ENFORCEMENT_ENABLED';
  END IF;
  BEGIN
    INSERT INTO flex_subscription_configuration_drafts(
      hotel_id,version,title,period_start,period_end,items,
      proposed_monthly_total,created_by,enforcement
    ) VALUES (
      '22222222-2222-4222-8222-222222222222',1,'Untrusted enable',
      current_date,current_date+interval '30 days','[{}]'::jsonb,0,
      'qa-super-admin','ENFORCE'
    );
    RAISE EXCEPTION 'CI_ENFORCE_DRAFT_ALLOWED';
  EXCEPTION WHEN check_violation OR insufficient_privilege THEN NULL;
  END;
END
$test$;

RESET ROLE;
DO $test$
BEGIN
  BEGIN
    UPDATE flex_subscription_configuration_drafts SET title='rewritten'
    WHERE hotel_id='11111111-1111-4111-8111-111111111111';
    RAISE EXCEPTION 'CI_HISTORY_REWRITE_ALLOWED';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM<>'FLEX_HISTORY_IS_APPEND_ONLY' THEN RAISE; END IF;
  END;
  IF (SELECT count(*) FROM flex_subscriptions WHERE
      hotel_id IN ('11111111-1111-4111-8111-111111111111',
      '22222222-2222-4222-8222-222222222222'))<>0 THEN
    RAISE EXCEPTION 'CI_DRAFT_MODIFIED_ACTIVE_SUBSCRIPTION';
  END IF;
  IF (SELECT count(*) FROM flex_confirmed_payments)<>0 THEN
    RAISE EXCEPTION 'CI_PAYMENT_SHOULD_NOT_BE_CREATED';
  END IF;
END
$test$;

ROLLBACK;
SELECT 'PASS: FLEX P0 catalog/draft RLS and immutable price history without payments' AS result;
