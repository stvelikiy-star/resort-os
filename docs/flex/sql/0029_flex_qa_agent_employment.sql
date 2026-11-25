-- QA employment history: separate from authentication and actual cash.
BEGIN;
CREATE TABLE flex_qa_agent_employment_events (
 agent_id uuid NOT NULL REFERENCES flex_agents(id),
 revision integer NOT NULL CHECK(revision>0),
 action text NOT NULL CHECK(action IN ('START','STOP')),
 created_by text NOT NULL CHECK(length(btrim(created_by)) BETWEEN 2 AND 180),
 created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(agent_id,revision)
);
ALTER TABLE flex_qa_agent_employment_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_qa_agent_employment_events FORCE ROW LEVEL SECURITY;
CREATE TRIGGER flex_qa_agent_employment_immutable BEFORE UPDATE OR DELETE ON flex_qa_agent_employment_events
 FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
GRANT SELECT,INSERT ON flex_qa_agent_employment_events TO flex_catalog_draft_writer;
CREATE POLICY flex_qa_agent_employment_admin_read ON flex_qa_agent_employment_events FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_qa_agent_employment_admin_append ON flex_qa_agent_employment_events FOR INSERT TO flex_catalog_draft_writer
 WITH CHECK(created_by=NULLIF(current_setting('flex.actor_subject_id',true),''));
GRANT SELECT(agent_id,revision,action,created_at) ON flex_qa_agent_employment_events TO flex_agent_statement_reader;
CREATE POLICY flex_qa_agent_employment_own ON flex_qa_agent_employment_events FOR SELECT TO flex_agent_statement_reader
 USING(agent_id=NULLIF(current_setting('flex.authorized_agent_id',true),'')::uuid);
COMMENT ON TABLE flex_qa_agent_employment_events IS 'QA status only; no account disable, payroll liability, bank payment or entitlement.';
COMMIT;
