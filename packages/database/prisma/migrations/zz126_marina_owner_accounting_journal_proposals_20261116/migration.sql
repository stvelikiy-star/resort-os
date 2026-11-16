-- P0 foundation: proposed double-entry accounting journal, never recognized P&L.
-- No existing financial sources are migrated or reclassified.
CREATE TABLE owner_accounting_journal_proposals (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE RESTRICT,
  "sourceType" text NOT NULL CHECK ("sourceType" IN ('REVENUE_SOURCE','REVENUE_CORRECTION','OPERATING_EXPENSE','STOCK_CONSUMPTION','SUPPLIER_OBLIGATION')),
  "sourceId" uuid NOT NULL,
  "accountingDate" date NOT NULL,
  "currency" text NOT NULL DEFAULT 'KGS' CHECK ("currency"='KGS'),
  "policyVersion" text NOT NULL CHECK (char_length("policyVersion") BETWEEN 3 AND 80),
  "reason" text NOT NULL CHECK (char_length("reason") BETWEEN 8 AND 500),
  "payloadHash" text NOT NULL CHECK ("payloadHash" ~ '^[0-9a-f]{64}$'),
  "createdById" uuid NOT NULL REFERENCES staff_users(id) ON DELETE RESTRICT,
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  "status" text NOT NULL DEFAULT 'PENDING_ACCOUNTANT_APPROVAL'
      CHECK ("status"='PENDING_ACCOUNTANT_APPROVAL'),
  CONSTRAINT owner_accounting_journal_proposals_tenant_id UNIQUE ("propertyId", id),
  CONSTRAINT owner_accounting_journal_proposals_source_once UNIQUE ("propertyId","sourceType","sourceId")
);

CREATE TABLE owner_accounting_journal_proposal_lines (
  "proposalId" uuid NOT NULL,
  "propertyId" uuid NOT NULL,
  "lineNo" integer NOT NULL CHECK ("lineNo" BETWEEN 1 AND 128),
  "accountCode" text NOT NULL CHECK ("accountCode" ~ '^[A-Za-z0-9._-]{2,32}$'),
  "side" text NOT NULL CHECK ("side" IN ('DEBIT','CREDIT')),
  "amountKgs" numeric(20,4) NOT NULL CHECK ("amountKgs">0),
  "memo" text NOT NULL DEFAULT '',
  PRIMARY KEY ("proposalId","lineNo"),
  CONSTRAINT owner_accounting_journal_proposal_lines_property_fk
    FOREIGN KEY ("propertyId","proposalId")
    REFERENCES owner_accounting_journal_proposals ("propertyId",id) ON DELETE RESTRICT
);
CREATE INDEX owner_accounting_journal_proposals_period_idx
 ON owner_accounting_journal_proposals ("propertyId","accountingDate","createdAt" DESC);

-- Keep even draft evidence immutable. Revisions require a new, separately reviewed proposal.
CREATE FUNCTION reject_owner_accounting_journal_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'OWNER_ACCOUNTING_JOURNAL_IMMUTABLE';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER owner_accounting_proposal_append_only
  BEFORE UPDATE OR DELETE ON owner_accounting_journal_proposals
  FOR EACH ROW EXECUTE FUNCTION reject_owner_accounting_journal_mutation();
CREATE TRIGGER owner_accounting_proposal_lines_append_only
  BEFORE UPDATE OR DELETE ON owner_accounting_journal_proposal_lines
  FOR EACH ROW EXECUTE FUNCTION reject_owner_accounting_journal_mutation();

-- Explicitly no accounting postings, profit, taxes or statement balances here.
