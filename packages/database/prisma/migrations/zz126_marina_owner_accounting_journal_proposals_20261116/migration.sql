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


-- Enforce the complete, balanced journal also for direct SQL writes.
-- DEFERRABLE checks run at transaction commit, after the header and all lines
-- have been inserted. An empty/partial/unbalanced proposal cannot commit.
CREATE FUNCTION check_owner_accounting_proposal_balanced() RETURNS trigger AS $
DECLARE
  target_id uuid;
  total_lines integer;
  debit_total numeric(24,4);
  credit_total numeric(24,4);
BEGIN
  target_id := CASE WHEN TG_TABLE_NAME = 'owner_accounting_journal_proposals'
                    THEN NEW.id ELSE NEW."proposalId" END;
  SELECT COUNT(*)::integer,
         COALESCE(SUM("amountKgs") FILTER (WHERE side='DEBIT'),0),
         COALESCE(SUM("amountKgs") FILTER (WHERE side='CREDIT'),0)
    INTO total_lines,debit_total,credit_total
    FROM owner_accounting_journal_proposal_lines
   WHERE "proposalId"=target_id;
  IF total_lines < 2 OR total_lines > 128 OR debit_total<=0
      OR debit_total<>credit_total THEN
    RAISE EXCEPTION 'OWNER_ACCOUNTING_PROPOSAL_UNBALANCED'
      USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END;
$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER owner_accounting_proposal_balance_on_header
  AFTER INSERT ON owner_accounting_journal_proposals
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION check_owner_accounting_proposal_balanced();
CREATE CONSTRAINT TRIGGER owner_accounting_proposal_balance_on_line
  AFTER INSERT ON owner_accounting_journal_proposal_lines
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION check_owner_accounting_proposal_balanced();

-- An immutable proposal cannot gain additional lines in a later transaction.
-- Its initial header and every initial line must be created atomically.
CREATE FUNCTION require_owner_accounting_initial_transaction() RETURNS trigger AS $
DECLARE
  header_xmin bigint;
BEGIN
  SELECT xmin::text::bigint INTO header_xmin
    FROM owner_accounting_journal_proposals
   WHERE id=NEW."proposalId" AND "propertyId"=NEW."propertyId";
  IF header_xmin IS NULL OR header_xmin<>(txid_current() % 4294967296) THEN
    RAISE EXCEPTION 'OWNER_ACCOUNTING_PROPOSAL_ALREADY_SEALED'
      USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END;
$ LANGUAGE plpgsql;

CREATE TRIGGER owner_accounting_lines_same_transaction
  BEFORE INSERT ON owner_accounting_journal_proposal_lines
  FOR EACH ROW EXECUTE FUNCTION require_owner_accounting_initial_transaction();

-- Explicitly no accounting postings, profit, taxes or statement balances here.
