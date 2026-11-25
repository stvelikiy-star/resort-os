-- FLEX QA assignment history; no accrual, identity or entitlement changes.
BEGIN;
CREATE TABLE flex_qa_agent_assignments (
 hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
 revision integer NOT NULL CHECK(revision>0),
 agent_id uuid NOT NULL REFERENCES flex_agents(id),
 action text NOT NULL CHECK(action IN ('ASSIGN','RELEASE')),
 created_by text NOT NULL CHECK(length(btrim(created_by)) BETWEEN 2 AND 180),
 created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(hotel_id,revision)
);
ALTER TABLE flex_qa_agent_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_qa_agent_assignments FORCE ROW LEVEL SECURITY;
CREATE TRIGGER flex_qa_agent_assignments_immutable BEFORE UPDATE OR DELETE ON flex_qa_agent_assignments
 FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
GRANT SELECT,INSERT ON flex_qa_agent_assignments TO flex_catalog_draft_writer;
GRANT SELECT(id,platform_subject_id,status) ON flex_agents TO flex_catalog_draft_writer;
CREATE POLICY flex_qa_agent_roster_read ON flex_agents FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_qa_assignment_admin_read ON flex_qa_agent_assignments FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_qa_assignment_admin_append ON flex_qa_agent_assignments FOR INSERT TO flex_catalog_draft_writer
 WITH CHECK(created_by=NULLIF(current_setting('flex.actor_subject_id',true),''));
GRANT SELECT ON flex_qa_agent_assignments TO flex_agent_statement_reader;
CREATE POLICY flex_qa_assignment_agent_read ON flex_qa_agent_assignments FOR SELECT TO flex_agent_statement_reader
 USING(agent_id=NULLIF(current_setting('flex.authorized_agent_id',true),'')::uuid);
CREATE POLICY flex_qa_assigned_hotel_read ON flex_hotels FOR SELECT TO flex_agent_statement_reader
 USING(EXISTS(SELECT 1 FROM flex_qa_agent_assignments a WHERE a.hotel_id=flex_hotels.id));
COMMENT ON TABLE flex_qa_agent_assignments IS 'QA administrative assignment only; does not establish a paid connection or authorize commissions.';
COMMIT;
