-- Ephemeral PostgreSQL security probe. No real hotel data.
-- Requires 0001 + 0002 preview SQL. Rejects missing or cross-property grants.
BEGIN;
INSERT INTO flex_hotels(id,display_name) VALUES
 ('00000000-0000-0000-0000-00000000000a','Hotel A'),
 ('00000000-0000-0000-0000-00000000000b','Hotel B');
INSERT INTO flex_skus(sku,title,capability_key,product_status) VALUES
 ('BASE_PMS','Core PMS','base_pms','AVAILABLE'),
 ('AI_ASSISTANT','AI Assistant','ai_assistant','AVAILABLE'),
 ('UNFINISHED_MODULE','Unfinished module','unfinished','PLANNED');
INSERT INTO flex_price_versions(sku,version,monthly_price,currency,valid_from,valid_to) VALUES
 ('BASE_PMS',1,10000.00,'KGS','2026-01-01T00:00:00+00','2027-01-01T00:00:00+00'),
 ('BASE_PMS',2,11000.00,'KGS','2027-01-01T00:00:00+00',NULL),
 ('AI_ASSISTANT',1,4000.00,'KGS','2026-01-01T00:00:00+00',NULL),
 ('UNFINISHED_MODULE',1,9999.00,'KGS','2026-01-01T00:00:00+00',NULL);
INSERT INTO flex_platform_memberships(subject_id,role,active)
 VALUES ('owner-a','HOTEL_OWNER',true),
 ('owner-b','HOTEL_OWNER',true),
 ('administrator','SUPER_ADMIN',true),
 ('disabled-owner','HOTEL_OWNER',false);
INSERT INTO flex_platform_hotel_grants(subject_id,hotel_id,granted_by)
 VALUES ('owner-a','00000000-0000-0000-0000-00000000000a','fixture'),
 ('owner-b','00000000-0000-0000-0000-00000000000b','fixture');
INSERT INTO flex_invoices(hotel_id,invoice_number,currency,status,total)
 VALUES ('00000000-0000-0000-0000-00000000000a','FLEX_RLS_A','KGS','ISSUED',100.00),
 ('00000000-0000-0000-0000-00000000000b','FLEX_RLS_B','KGS','ISSUED',200.00);
INSERT INTO flex_subscriptions(hotel_id,status,period_start,period_end)
 VALUES ('00000000-0000-0000-0000-00000000000a','ACTIVE','2026-11-01','2026-11-30'),
 ('00000000-0000-0000-0000-00000000000b','GRACE','2026-11-01','2026-11-30');
COMMIT;

-- No scoped identity = no identity rows, grants, agent or investor identities.
BEGIN;
SET LOCAL ROLE flex_identity_reader;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_platform_memberships) = 0 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_platform_hotel_grants) = 0 THEN 1 ELSE 0 END;
ROLLBACK;

-- Verified subject owner-a can retrieve only their own membership and grant.
BEGIN;
SELECT set_config('flex.authorized_subject_id','owner-a',true);
SET LOCAL ROLE flex_identity_reader;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_platform_memberships) = 1 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_platform_hotel_grants) = 1 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_platform_hotel_grants
   WHERE hotel_id='00000000-0000-0000-0000-00000000000b') = 0 THEN 1 ELSE 0 END;
ROLLBACK;

-- Missing verified hotel scope must reveal zero hotel, invoice, subscription rows.
BEGIN;
SET LOCAL ROLE flex_hotel_reader;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_hotels) = 0 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_invoices) = 0 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_subscriptions) = 0 THEN 1 ELSE 0 END;
ROLLBACK;

-- Hotel A may not see Hotel B's invoice, hotel or subscription.
BEGIN;
SELECT set_config('flex.authorized_hotel_id','00000000-0000-0000-0000-00000000000a',true);
SET LOCAL ROLE flex_hotel_reader;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_hotels) = 1 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_invoices) = 1 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT sum(total) FROM flex_invoices) = 100.00 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_subscriptions) = 1 THEN 1 ELSE 0 END;
ROLLBACK;

-- Switching trusted scope to B isolates B.
BEGIN;
SELECT set_config('flex.authorized_hotel_id','00000000-0000-0000-0000-00000000000b',true);
SET LOCAL ROLE flex_hotel_reader;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_hotels) = 1 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT sum(total) FROM flex_invoices) = 200.00 THEN 1 ELSE 0 END;
ROLLBACK;

-- Only a separately authorized admin-reader DB role sees the whole registry.
BEGIN;
SET LOCAL ROLE flex_platform_admin_reader;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_hotels) = 2 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_invoices) = 2 THEN 1 ELSE 0 END;
ROLLBACK;

SELECT 1 / CASE WHEN (
 SELECT count(*) FROM pg_roles
 WHERE rolname IN ('flex_hotel_reader','flex_identity_reader','flex_platform_admin_reader')
   AND rolcanlogin = false
) = 3 THEN 1 ELSE 0 END;
