BEGIN;
GRANT INSERT ON flex_commercial_policy_versions TO flex_catalog_draft_writer;
CREATE POLICY flex_commercial_policy_append ON flex_commercial_policy_versions
FOR INSERT TO flex_catalog_draft_writer
WITH CHECK (created_by = NULLIF(current_setting('flex.actor_subject_id',true),''));
COMMIT;
