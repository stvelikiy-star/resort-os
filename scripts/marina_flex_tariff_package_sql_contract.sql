-- Isolated PostgreSQL16 test, after migrations 0001-0012. All data rolled back.
BEGIN;
DO $check$
BEGIN
 IF NOT (SELECT relrowsecurity AND relforcerowsecurity FROM pg_class
         WHERE oid='flex_tariff_package_versions'::regclass) THEN
   RAISE EXCEPTION 'QA_TARIFF_RLS_MISSING';
 END IF;
 IF has_table_privilege('flex_hotel_reader','flex_tariff_package_versions','SELECT')
   OR has_table_privilege('flex_identity_reader','flex_tariff_package_versions','SELECT')
   OR has_table_privilege('flex_catalog_draft_writer','flex_tariff_package_versions','UPDATE')
   OR has_table_privilege('flex_catalog_draft_writer','flex_tariff_package_versions','DELETE')
   OR has_table_privilege('flex_catalog_draft_writer','flex_subscriptions','INSERT')
   OR has_table_privilege('flex_catalog_draft_writer','flex_confirmed_payments','INSERT')
 THEN RAISE EXCEPTION 'QA_TARIFF_PRIVILEGE_ESCALATION'; END IF;
END $check$;

INSERT INTO flex_hotels(id,display_name,status)
VALUES ('33333333-3333-4333-8333-333333333333','FLEX PACKAGE CI HOTEL','PENDING');
INSERT INTO flex_skus(sku,title,capability_key,product_status,is_core)
VALUES ('PACKAGE_QA_SKU','QA isolated add-on','qa.package','AVAILABLE',false);
INSERT INTO flex_price_versions(sku,version,currency,monthly_price,valid_from)
VALUES ('PACKAGE_QA_SKU',1,'KGS',1200.00,now()-interval '2 days');

SET LOCAL ROLE flex_catalog_draft_writer;
SELECT set_config('flex.actor_subject_id','ci-package-admin',true);
INSERT INTO flex_tariff_package_versions(
 hotel_id,package_kind,version,title,sku_snapshot,list_monthly_total,
 discount_pct,trial_days,proposed_monthly_total,created_by
) VALUES (
 '33333333-3333-4333-8333-333333333333','BUSINESS',1,'QA Business',
 '[{"sku":"PACKAGE_QA_SKU","monthly_price":"1200.00","currency":"KGS","price_version":1}]',
 1200.00,10.00,14,1080.00,'ci-package-admin'
);
INSERT INTO flex_tariff_package_versions(
 hotel_id,package_kind,version,title,sku_snapshot,list_monthly_total,
 discount_pct,trial_days,custom_monthly_price,proposed_monthly_total,created_by
) VALUES (
 '33333333-3333-4333-8333-333333333333','CUSTOM',1,'QA custom plan',
 '[{"sku":"PACKAGE_QA_SKU","monthly_price":"1200.00","currency":"KGS","price_version":1}]',
 1200.00,0,0,999.00,999.00,'ci-package-admin'
);
DO $check$
BEGIN
 IF (SELECT count(*) FROM flex_tariff_package_versions WHERE enforcement='OFF' AND state='DRAFT')<>2
 THEN RAISE EXCEPTION 'QA_TARIFF_NOT_DRAFT_ONLY'; END IF;
 BEGIN
  INSERT INTO flex_tariff_package_versions(hotel_id,package_kind,version,title,sku_snapshot,
   list_monthly_total,discount_pct,trial_days,proposed_monthly_total,created_by)
  VALUES ('33333333-3333-4333-8333-333333333333','BUSINESS',2,'QA wrong sum',
   '[{"sku":"PACKAGE_QA_SKU"}]',1200,10,0,1200,'ci-package-admin');
  RAISE EXCEPTION 'QA_TARIFF_WRONG_TOTAL_ACCEPTED';
 EXCEPTION WHEN check_violation THEN NULL;
 END;
 BEGIN
  INSERT INTO flex_tariff_package_versions(hotel_id,package_kind,version,title,sku_snapshot,
   list_monthly_total,discount_pct,trial_days,proposed_monthly_total,created_by)
  VALUES ('33333333-3333-4333-8333-333333333333','BASE',1,'QA enforce',
   '[{"sku":"PACKAGE_QA_SKU"}]',1200,0,0,1200,'ci-package-admin');
  UPDATE flex_tariff_package_versions SET enforcement='ENFORCE' WHERE package_kind='BASE';
  RAISE EXCEPTION 'QA_TARIFF_UPDATE_ALLOWED';
 EXCEPTION WHEN insufficient_privilege THEN NULL;
 END;
END $check$;
RESET ROLE;
DO $check$
BEGIN
 IF (SELECT count(*) FROM flex_subscriptions)<>0
  OR (SELECT count(*) FROM flex_confirmed_payments)<>0
 THEN RAISE EXCEPTION 'QA_TARIFF_ALTERED_COMMERCIAL_RUNTIME'; END IF;
END $check$;
ROLLBACK;
