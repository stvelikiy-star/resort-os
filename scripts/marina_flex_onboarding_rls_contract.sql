-- Negative security tests after FLEX preview 0004, disposable PostgreSQL only.
BEGIN;
SELECT set_config('flex.actor_subject_id','administrator',true);
SET LOCAL ROLE flex_onboarding_writer;

DO $test$
BEGIN
  BEGIN
    INSERT INTO flex_hotels(display_name,billing_currency,status)
    VALUES ('Unauthorized ACTIVE','KGS','ACTIVE');
    RAISE EXCEPTION 'CI_FAILURE_WRITER_CREATED_ACTIVE';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;

  BEGIN
    UPDATE flex_hotels SET status='ACTIVE' WHERE status='PENDING';
    RAISE EXCEPTION 'CI_FAILURE_WRITER_HAS_UPDATE';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;

  BEGIN
    INSERT INTO flex_audit_events(platform_subject_id,action,resource_type,resource_id)
    VALUES('administrator','PAYMENT_CONFIRMED','FLEX_HOTEL','forbidden');
    RAISE EXCEPTION 'CI_FAILURE_WRITER_CAN_FORGE_PAYMENT_AUDIT';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;

  BEGIN
    INSERT INTO flex_hotel_onboarding_requests(
      actor_subject_id,idempotency_key,payload_sha256,hotel_id
    ) VALUES(
      'owner-a','forbidden-actor-001',repeat('a',64),
      '00000000-0000-0000-0000-00000000000a'
    );
    RAISE EXCEPTION 'CI_FAILURE_WRITER_CAN_IMPERSONATE';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
END
$test$;
ROLLBACK;

-- Verify table explicitly permits neither direct lifecycle mutations nor
-- production-side PMS changes through the restricted writer role.
SELECT 1 / CASE WHEN (
 SELECT count(*) FROM information_schema.role_table_grants
 WHERE grantee='flex_onboarding_writer'
   AND table_name IN ('flex_hotels','flex_invoices','flex_subscriptions','flex_payment_allocations')
   AND privilege_type IN ('UPDATE','DELETE')
) = 0 THEN 1 ELSE 0 END;
