-- Append-only approval evidence for OWNER accounting proposals.
-- This migration deliberately does NOT post ledger entries or recognize P&L:
-- accounting policy, authorised accountant and complete source coverage are separate release gates.
CREATE TABLE owner_accounting_journal_decisions (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL,
  "proposalId" uuid NOT NULL,
  action text NOT NULL CHECK (action IN ('APPROVE','REVERSE')),
  "approvalId" uuid,
  "actorId" uuid NOT NULL REFERENCES staff_users(id) ON DELETE RESTRICT,
  reason text NOT NULL CHECK (char_length(reason) BETWEEN 8 AND 500),
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT owner_accounting_decision_proposal_property_fk
    FOREIGN KEY ("propertyId","proposalId")
    REFERENCES owner_accounting_journal_proposals("propertyId",id) ON DELETE RESTRICT,
  CONSTRAINT owner_accounting_decision_approval_fk
    FOREIGN KEY ("approvalId")
    REFERENCES owner_accounting_journal_decisions(id) ON DELETE RESTRICT,
  CONSTRAINT owner_accounting_decision_action_shape CHECK (
    (action='APPROVE' AND "approvalId" IS NULL) OR
    (action='REVERSE' AND "approvalId" IS NOT NULL)
  ),
  CONSTRAINT owner_accounting_decision_once UNIQUE ("propertyId","proposalId",action)
);
CREATE INDEX owner_accounting_decisions_property_created_idx
  ON owner_accounting_journal_decisions("propertyId","createdAt" DESC);
CREATE TRIGGER owner_accounting_decisions_append_only
  BEFORE UPDATE OR DELETE ON owner_accounting_journal_decisions
  FOR EACH ROW EXECUTE FUNCTION reject_owner_accounting_journal_mutation();

-- SQL guard for direct writers: an approval must be independent from the
-- proposal creator and strictly bound to the tenant and the real approver.
CREATE FUNCTION guard_owner_accounting_decision_insert() RETURNS trigger AS $$
DECLARE
  proposal_creator uuid;
  proposal_source_type text;
  proposal_source_id uuid;
  source_valid boolean;
  actor_property uuid;
  actor_role text;
  actor_active boolean;
  parent_row record;
BEGIN
  SELECT "createdById","sourceType","sourceId"
    INTO proposal_creator,proposal_source_type,proposal_source_id
    FROM owner_accounting_journal_proposals
    WHERE id=NEW."proposalId" AND "propertyId"=NEW."propertyId";
  SELECT "propertyId",role::text,"isActive"
    INTO actor_property,actor_role,actor_active
    FROM staff_users WHERE id=NEW."actorId";
  IF proposal_creator IS NULL OR actor_property IS DISTINCT FROM NEW."propertyId"
     OR actor_role IS DISTINCT FROM 'OWNER' OR actor_active IS DISTINCT FROM true
     OR proposal_creator=NEW."actorId" THEN
    RAISE EXCEPTION 'ACCOUNTING_DECISION_APPROVER_NOT_INDEPENDENT'
      USING ERRCODE='23514';
  END IF;
  -- Keep the database as strict as the API. A direct SQL actor may not
  -- approve a missing, foreign, or already reversed source.
  IF NEW.action='APPROVE' THEN
    IF proposal_source_type='REVENUE_SOURCE' THEN
      SELECT EXISTS(
        SELECT 1 FROM owner_revenue_source_events e
        WHERE e.id=proposal_source_id AND e."propertyId"=NEW."propertyId"
          AND e.action='APPROVE_SOURCE'
          AND NOT EXISTS (
            SELECT 1 FROM owner_revenue_source_events rev
            WHERE rev."propertyId"=NEW."propertyId" AND rev."reversesId"=e.id)
      ) INTO source_valid;
    ELSIF proposal_source_type='REVENUE_CORRECTION' THEN
      SELECT EXISTS(
        SELECT 1 FROM owner_revenue_correction_events e
        JOIN owner_revenue_evidence_documents d
          ON d.id=e."evidenceDocumentId" AND d."propertyId"=e."propertyId"
        WHERE e.id=proposal_source_id AND e."propertyId"=NEW."propertyId"
          AND e.action='RECORD'
          AND NOT EXISTS (
            SELECT 1 FROM owner_revenue_correction_events rev
            WHERE rev."propertyId"=NEW."propertyId" AND rev."reversesId"=e.id)
      ) INTO source_valid;
    ELSE
      source_valid:=false;
    END IF;
    IF source_valid IS DISTINCT FROM true THEN
      RAISE EXCEPTION 'ACCOUNTING_DECISION_SOURCE_UNVERIFIED'
        USING ERRCODE='23514';
    END IF;
  END IF;
  IF NEW.action='REVERSE' THEN
    SELECT "propertyId","proposalId",action INTO parent_row
      FROM owner_accounting_journal_decisions WHERE id=NEW."approvalId";
    IF NOT FOUND OR parent_row."propertyId" IS DISTINCT FROM NEW."propertyId"
       OR parent_row."proposalId" IS DISTINCT FROM NEW."proposalId"
       OR parent_row.action IS DISTINCT FROM 'APPROVE' THEN
      RAISE EXCEPTION 'ACCOUNTING_DECISION_REVERSE_TARGET_INVALID'
        USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER owner_accounting_decisions_guard
  BEFORE INSERT ON owner_accounting_journal_decisions
  FOR EACH ROW EXECUTE FUNCTION guard_owner_accounting_decision_insert();

-- Non-recognition is intentional: no changes to accrual-readiness profit.
