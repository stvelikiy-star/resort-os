-- Investor plan drafts only. No legal signature, principal receipt, accrual or payout.
BEGIN;
CREATE TABLE flex_qa_investor_plans (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 investor_id uuid NOT NULL REFERENCES flex_investors(id),
 revision integer NOT NULL CHECK(revision>0),
 principal numeric(18,2) NOT NULL,
 share_bps integer NOT NULL,
 bonus_months integer NOT NULL DEFAULT 3 CHECK(bonus_months=3),
 revenue_basis text NOT NULL DEFAULT 'ASSIGNED_HOTEL_SUBSCRIPTION' CHECK(revenue_basis='ASSIGNED_HOTEL_SUBSCRIPTION'),
 state text NOT NULL DEFAULT 'DRAFT' CHECK(state='DRAFT'),
 created_by text NOT NULL CHECK(length(btrim(created_by)) BETWEEN 2 AND 180),
 created_at timestamptz NOT NULL DEFAULT now(),
 CHECK((principal=150000 AND share_bps=2500) OR (principal=250000 AND share_bps=3500) OR (principal=400000 AND share_bps=5000)),
 UNIQUE(investor_id,revision), UNIQUE(id,investor_id)
);
CREATE TABLE flex_qa_investor_plan_hotels (
 plan_id uuid NOT NULL,
 investor_id uuid NOT NULL,
 hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
 hotel_name_snapshot text NOT NULL,
 PRIMARY KEY(plan_id,hotel_id),
 FOREIGN KEY(plan_id,investor_id) REFERENCES flex_qa_investor_plans(id,investor_id)
);
ALTER TABLE flex_qa_investor_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_qa_investor_plans FORCE ROW LEVEL SECURITY;
ALTER TABLE flex_qa_investor_plan_hotels ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_qa_investor_plan_hotels FORCE ROW LEVEL SECURITY;
CREATE TRIGGER flex_qa_investor_plan_immutable BEFORE UPDATE OR DELETE ON flex_qa_investor_plans
 FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
CREATE TRIGGER flex_qa_investor_plan_hotel_immutable BEFORE UPDATE OR DELETE ON flex_qa_investor_plan_hotels
 FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
GRANT SELECT,INSERT ON flex_qa_investor_plans,flex_qa_investor_plan_hotels TO flex_catalog_draft_writer;
GRANT SELECT(id,platform_subject_id,status) ON flex_investors TO flex_catalog_draft_writer;
CREATE POLICY flex_qa_investor_roster_read ON flex_investors FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_qa_investor_plan_admin_read ON flex_qa_investor_plans FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_qa_investor_plan_admin_append ON flex_qa_investor_plans FOR INSERT TO flex_catalog_draft_writer
 WITH CHECK(created_by=NULLIF(current_setting('flex.actor_subject_id',true),''));
CREATE POLICY flex_qa_investor_plan_hotel_admin_read ON flex_qa_investor_plan_hotels FOR SELECT TO flex_catalog_draft_writer USING(true);
CREATE POLICY flex_qa_investor_plan_hotel_admin_append ON flex_qa_investor_plan_hotels FOR INSERT TO flex_catalog_draft_writer
 WITH CHECK(EXISTS(SELECT 1 FROM flex_qa_investor_plans p WHERE p.id=plan_id AND p.investor_id=flex_qa_investor_plan_hotels.investor_id AND p.created_by=NULLIF(current_setting('flex.actor_subject_id',true),'') AND p.created_at=transaction_timestamp()));
GRANT SELECT(id,investor_id,revision,principal,share_bps,bonus_months,revenue_basis,state,created_at) ON flex_qa_investor_plans TO flex_investor_statement_reader;
GRANT SELECT ON flex_qa_investor_plan_hotels TO flex_investor_statement_reader;
CREATE POLICY flex_qa_investor_plan_own ON flex_qa_investor_plans FOR SELECT TO flex_investor_statement_reader
 USING(investor_id=NULLIF(current_setting('flex.authorized_investor_id',true),'')::uuid);
CREATE POLICY flex_qa_investor_plan_hotel_own ON flex_qa_investor_plan_hotels FOR SELECT TO flex_investor_statement_reader
 USING(investor_id=NULLIF(current_setting('flex.authorized_investor_id',true),'')::uuid);
COMMIT;
