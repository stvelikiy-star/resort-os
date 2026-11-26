-- Commercial hotel name editing only; no lifecycle, subscription or PMS mutation.
BEGIN;
GRANT UPDATE(display_name) ON flex_hotels TO flex_onboarding_writer;
CREATE POLICY flex_writer_hotel_name_read ON flex_hotels FOR SELECT TO flex_onboarding_writer USING (status IN ('PENDING','ACTIVE'));
CREATE POLICY flex_writer_hotel_name_update ON flex_hotels FOR UPDATE TO flex_onboarding_writer
USING (status IN ('PENDING','ACTIVE') AND NULLIF(current_setting('flex.actor_subject_id',true),'') IS NOT NULL)
WITH CHECK (status IN ('PENDING','ACTIVE') AND length(trim(display_name)) BETWEEN 2 AND 180);
CREATE POLICY flex_writer_hotel_name_audit ON flex_audit_events FOR INSERT TO flex_onboarding_writer
WITH CHECK (platform_subject_id = NULLIF(current_setting('flex.actor_subject_id',true),'') AND action='HOTEL_NAME_UPDATED' AND resource_type='FLEX_HOTEL');
COMMIT;
