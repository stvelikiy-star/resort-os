BEGIN;
CREATE TABLE flex_installation_completions (
 hotel_id uuid PRIMARY KEY REFERENCES flex_hotels(id),
 completed_at timestamptz NOT NULL DEFAULT now(),
 completed_by text NOT NULL CHECK(length(btrim(completed_by)) BETWEEN 2 AND 180),
 trial_start date NOT NULL,
 trial_end_exclusive date NOT NULL,
 CHECK(trial_end_exclusive=trial_start+5),
 CHECK(trial_start=(completed_at AT TIME ZONE 'Asia/Bishkek')::date)
);
ALTER TABLE flex_installation_completions ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_installation_completions FORCE ROW LEVEL SECURITY;
CREATE TRIGGER flex_installation_completion_immutable BEFORE UPDATE OR DELETE ON flex_installation_completions
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
GRANT SELECT,INSERT ON flex_installation_completions TO flex_catalog_draft_writer;
CREATE POLICY flex_installation_read ON flex_installation_completions FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_installation_append ON flex_installation_completions FOR INSERT TO flex_catalog_draft_writer
WITH CHECK(completed_by=NULLIF(current_setting('flex.actor_subject_id',true),''));
COMMIT;
