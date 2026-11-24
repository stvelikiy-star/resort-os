-- MARINA P0: immutable balanced posted ledger. No legacy journal tables are edited.
-- Source approvals and proposed entries remain separate immutable evidence.
CREATE TABLE owner_accounting_postings (
 id uuid PRIMARY KEY,
 "propertyId" uuid NOT NULL,
 "proposalId" uuid NOT NULL,
 "decisionId" uuid NOT NULL,
 action text NOT NULL CHECK(action IN ('POST','REVERSE')),
 "reversesId" uuid,
 "accountingDate" date NOT NULL,
 "policyVersion" text NOT NULL CHECK(length("policyVersion") BETWEEN 3 AND 80),
 "postedById" uuid NOT NULL REFERENCES staff_users(id) ON DELETE RESTRICT,
 "sourceCompletenessAttested" boolean NOT NULL CHECK("sourceCompletenessAttested" = true),
 reason text NOT NULL CHECK(length(reason) BETWEEN 8 AND 500),
 "createdAt" timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT owner_accounting_postings_tenant_id UNIQUE("propertyId",id),
 CONSTRAINT owner_accounting_postings_proposal_fk FOREIGN KEY("propertyId","proposalId")
   REFERENCES owner_accounting_journal_proposals("propertyId",id) ON DELETE RESTRICT,
 CONSTRAINT owner_accounting_postings_decision_fk FOREIGN KEY("decisionId")
   REFERENCES owner_accounting_journal_decisions(id) ON DELETE RESTRICT,
 CONSTRAINT owner_accounting_postings_reverse_fk FOREIGN KEY("propertyId","reversesId")
   REFERENCES owner_accounting_postings("propertyId",id) ON DELETE RESTRICT,
 CONSTRAINT owner_accounting_postings_reverse_shape_check CHECK(
   (action='POST' AND "reversesId" IS NULL) OR
   (action='REVERSE' AND "reversesId" IS NOT NULL)),
 CONSTRAINT owner_accounting_postings_once UNIQUE("propertyId","proposalId",action)
);
CREATE INDEX owner_accounting_postings_period_idx
 ON owner_accounting_postings("propertyId","accountingDate","createdAt");

CREATE TABLE owner_accounting_posting_lines (
 "postingId" uuid NOT NULL,
 "propertyId" uuid NOT NULL,
 "lineNo" integer NOT NULL CHECK ("lineNo" BETWEEN 1 AND 128),
 "accountCode" text NOT NULL CHECK ("accountCode" IN
   ('1000','1100','1300','2100','2200','4100','4200','4300','5100','5200')),
 side text NOT NULL CHECK(side IN ('DEBIT','CREDIT')),
 "amountKgs" numeric(20,4) NOT NULL CHECK("amountKgs">0),
 PRIMARY KEY("postingId","lineNo"),
 CONSTRAINT owner_accounting_posting_lines_tenant_fk FOREIGN KEY("propertyId","postingId")
   REFERENCES owner_accounting_postings("propertyId",id) ON DELETE RESTRICT
);
CREATE TRIGGER owner_accounting_postings_immutable
 BEFORE UPDATE OR DELETE ON owner_accounting_postings
 FOR EACH ROW EXECUTE FUNCTION reject_owner_accounting_journal_mutation();
CREATE TRIGGER owner_accounting_posting_lines_immutable
 BEFORE UPDATE OR DELETE ON owner_accounting_posting_lines
 FOR EACH ROW EXECUTE FUNCTION reject_owner_accounting_journal_mutation();

CREATE FUNCTION guard_owner_accounting_posting_insert() RETURNS trigger AS $$
DECLARE
 original_proposal record;
 authorised_decision record;
 worker record;
 reversed_post record;
 source_proof record;
BEGIN
 SELECT * INTO original_proposal FROM owner_accounting_journal_proposals
 WHERE id=NEW."proposalId" AND "propertyId"=NEW."propertyId";
 SELECT * INTO authorised_decision FROM owner_accounting_journal_decisions
 WHERE id=NEW."decisionId" AND "propertyId"=NEW."propertyId"
   AND "proposalId"=NEW."proposalId";
 SELECT "propertyId",role::text AS role,"isActive" INTO worker FROM staff_users
 WHERE id=NEW."postedById";
 IF NOT FOUND OR worker."propertyId" IS DISTINCT FROM NEW."propertyId"
    OR worker.role IS DISTINCT FROM 'OWNER' OR worker."isActive" IS DISTINCT FROM true
    OR original_proposal.id IS NULL THEN
    RAISE EXCEPTION 'ACCOUNTING_POSTING_ACTOR_OR_PROPOSAL_INVALID' USING ERRCODE='23514';
 END IF;
 IF original_proposal."accountingDate"<>NEW."accountingDate"
    OR original_proposal."policyVersion"<>NEW."policyVersion" THEN
    RAISE EXCEPTION 'ACCOUNTING_POSTING_POLICY_PERIOD_MISMATCH' USING ERRCODE='23514';
 END IF;
 IF NEW.action='POST' THEN
   IF authorised_decision.action IS DISTINCT FROM 'APPROVE'
       OR authorised_decision."actorId" IS DISTINCT FROM NEW."postedById"
       OR EXISTS(SELECT 1 FROM owner_accounting_journal_decisions rev
           WHERE rev."propertyId"=NEW."propertyId"
             AND rev."proposalId"=NEW."proposalId" AND rev.action='REVERSE') THEN
      RAISE EXCEPTION 'ACCOUNTING_POSTING_APPROVAL_INVALID' USING ERRCODE='23514';
   END IF;
   IF original_proposal."sourceType"='REVENUE_SOURCE' THEN
   SELECT e."faceValueKgs",e."sourceType",e."sourceSnapshot" INTO source_proof
     FROM owner_revenue_source_events e
    WHERE e."propertyId"=NEW."propertyId" AND e.id=original_proposal."sourceId"
      AND e.action='APPROVE_SOURCE'
      AND NOT EXISTS(SELECT 1 FROM owner_revenue_source_events r
          WHERE r."propertyId"=e."propertyId" AND r."reversesId"=e.id);
   IF NOT FOUND OR
      (source_proof."sourceType"='ROOM_NIGHT'
         AND source_proof."sourceSnapshot"->>'rate_and_tax_accounting_approved' IS DISTINCT FROM 'true')
      OR (source_proof."sourceType"='DINING_ORDER'
         AND source_proof."sourceSnapshot"->>'tax_discount_refund_accounting_approved' IS DISTINCT FROM 'true')
      OR source_proof."sourceType" NOT IN ('ROOM_NIGHT','DINING_ORDER')
      OR EXISTS(SELECT 1 FROM owner_revenue_correction_events c
           WHERE c."propertyId"=NEW."propertyId"
             AND c."approvalId"=original_proposal."sourceId"
             AND c.action='RECORD'
             AND NOT EXISTS (SELECT 1 FROM owner_revenue_correction_events r
               WHERE r."propertyId"=c."propertyId" AND r."reversesId"=c.id)) THEN
      RAISE EXCEPTION 'ACCOUNTING_POSTING_SOURCE_COMPLETENESS_NOT_VERIFIED'
        USING ERRCODE='23514';
   END IF;
   ELSIF original_proposal."sourceType"='OPERATING_EXPENSE' THEN
     IF NOT EXISTS (
       SELECT 1 FROM owner_expenses e
       WHERE e.id=original_proposal."sourceId"
         AND e."propertyId"=NEW."propertyId"
         AND e.status='POSTED'
         AND e."expenseDate"=NEW."accountingDate"
         AND e.category IN ('UTILITIES','PAYROLL','MAINTENANCE','RENT','MARKETING')
         AND e."supplierName" IS NOT NULL
         AND e."documentReference" IS NOT NULL
         AND NOT EXISTS (
           SELECT 1 FROM kitchen_supplier_documents d
           WHERE d."propertyId"=e."propertyId"
             AND d."supplierName"=e."supplierName"
             AND d."documentReference"=e."documentReference")
     ) THEN
       RAISE EXCEPTION 'ACCOUNTING_POSTING_EXPENSE_UNVERIFIED_OR_DUPLICATE'
         USING ERRCODE='23514';
     END IF;
   ELSE
     RAISE EXCEPTION 'ACCOUNTING_POSTING_SOURCE_POLICY_UNSUPPORTED'
       USING ERRCODE='23514';
   END IF;
 ELSE
   SELECT * INTO reversed_post FROM owner_accounting_postings
     WHERE id=NEW."reversesId" AND "propertyId"=NEW."propertyId" AND action='POST';
   IF reversed_post.id IS NULL OR reversed_post."proposalId"<>NEW."proposalId"
      OR authorised_decision.action IS DISTINCT FROM 'REVERSE' THEN
      RAISE EXCEPTION 'ACCOUNTING_POSTING_REVERSAL_INVALID' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER owner_accounting_posting_guard
 BEFORE INSERT ON owner_accounting_postings
 FOR EACH ROW EXECUTE FUNCTION guard_owner_accounting_posting_insert();

-- Verify line-level accounting equality at transaction commit, including
-- reversal equality (same amounts and codes, opposite debit/credit sides).
CREATE FUNCTION check_owner_accounting_posting_commit() RETURNS trigger AS $$
DECLARE
 p owner_accounting_postings%ROWTYPE;
 n integer;
 debit_total numeric(24,4);
 credit_total numeric(24,4);
 mismatch_count integer;
 source_service_type text;
 expected_revenue_code text;
BEGIN
 IF TG_TABLE_NAME='owner_accounting_postings' THEN
   SELECT * INTO p FROM owner_accounting_postings WHERE id=NEW.id;
 ELSE
   SELECT * INTO p FROM owner_accounting_postings WHERE id=NEW."postingId";
 END IF;
 SELECT count(*)::integer,
        coalesce(sum("amountKgs") FILTER(WHERE side='DEBIT'),0),
        coalesce(sum("amountKgs") FILTER(WHERE side='CREDIT'),0)
 INTO n,debit_total,credit_total FROM owner_accounting_posting_lines
 WHERE "postingId"=p.id AND "propertyId"=p."propertyId";
 IF n<2 OR n>128 OR debit_total<=0 OR debit_total<>credit_total THEN
   RAISE EXCEPTION 'ACCOUNTING_POSTING_UNBALANCED' USING ERRCODE='23514';
 END IF;
 IF p.action='POST' THEN
   IF EXISTS(SELECT 1 FROM owner_accounting_journal_proposals pr
      WHERE pr.id=p."proposalId" AND pr."propertyId"=p."propertyId"
        AND pr."sourceType"='OPERATING_EXPENSE') THEN
     SELECT e."amountKgs" INTO debit_total
       FROM owner_accounting_journal_proposals pr
       JOIN owner_expenses e ON e.id=pr."sourceId" AND e."propertyId"=pr."propertyId"
       WHERE pr.id=p."proposalId" AND pr."propertyId"=p."propertyId";
     IF (SELECT COUNT(*) FROM owner_accounting_posting_lines l
          WHERE l."postingId"=p.id)<>2
         OR NOT EXISTS(SELECT 1 FROM owner_accounting_posting_lines l
               WHERE l."postingId"=p.id AND l."accountCode"='5200'
                 AND l.side='DEBIT' AND l."amountKgs"=debit_total)
         OR NOT EXISTS(SELECT 1 FROM owner_accounting_posting_lines l
               WHERE l."postingId"=p.id AND l."accountCode"='2200'
                 AND l.side='CREDIT' AND l."amountKgs"=debit_total)
     THEN
         RAISE EXCEPTION 'ACCOUNTING_POSTING_EXPENSE_ACCOUNT_POLICY_INVALID'
           USING ERRCODE='23514';
     END IF;
   ELSE
   -- Revenue posting: debit receivable for the source's exact face value;
   -- credit an approved revenue account and optional tax payable only.
   SELECT e."faceValueKgs",e."sourceType" INTO debit_total,source_service_type
     FROM owner_accounting_journal_proposals pr
     JOIN owner_revenue_source_events e ON e.id=pr."sourceId"
       AND e."propertyId"=pr."propertyId"
    WHERE pr.id=p."proposalId" AND pr."propertyId"=p."propertyId";
   expected_revenue_code := CASE source_service_type
     WHEN 'ROOM_NIGHT' THEN '4100'
     WHEN 'DINING_ORDER' THEN '4200' ELSE NULL END;
   IF expected_revenue_code IS NULL THEN
      RAISE EXCEPTION 'ACCOUNTING_POSTING_SERVICE_ACCOUNT_UNKNOWN' USING ERRCODE='23514';
   END IF;
   IF NOT EXISTS (
       SELECT 1 FROM owner_accounting_posting_lines l
       WHERE l."postingId"=p.id AND l."accountCode"='1100'
         AND l.side='DEBIT' AND l."amountKgs"=debit_total)
       OR NOT EXISTS (
       SELECT 1 FROM owner_accounting_posting_lines l
       WHERE l."postingId"=p.id AND l.side='CREDIT'
         AND l."accountCode"=expected_revenue_code)
       OR EXISTS (
       SELECT 1 FROM owner_accounting_posting_lines l
       WHERE l."postingId"=p.id AND NOT (
         (l.side='DEBIT' AND l."accountCode"='1100')
         OR (l.side='CREDIT' AND l."accountCode" IN (expected_revenue_code,'2100'))))
   THEN
       RAISE EXCEPTION 'ACCOUNTING_POSTING_REVENUE_ACCOUNT_POLICY_INVALID'
         USING ERRCODE='23514';
   END IF;

   END IF;
   SELECT count(*)::integer INTO mismatch_count FROM (
     (SELECT "lineNo","accountCode",side,"amountKgs"
      FROM owner_accounting_journal_proposal_lines
      WHERE "propertyId"=p."propertyId" AND "proposalId"=p."proposalId"
      EXCEPT ALL
      SELECT "lineNo","accountCode",side,"amountKgs"
      FROM owner_accounting_posting_lines WHERE "postingId"=p.id)
     UNION ALL
     (SELECT "lineNo","accountCode",side,"amountKgs"
      FROM owner_accounting_posting_lines WHERE "postingId"=p.id
      EXCEPT ALL
      SELECT "lineNo","accountCode",side,"amountKgs"
      FROM owner_accounting_journal_proposal_lines
      WHERE "propertyId"=p."propertyId" AND "proposalId"=p."proposalId")
   ) delta;
 ELSE
   SELECT count(*)::integer INTO mismatch_count FROM (
     (SELECT "lineNo","accountCode",side,"amountKgs"
      FROM owner_accounting_posting_lines WHERE "postingId"=p.id
      EXCEPT ALL
      SELECT "lineNo","accountCode",
             CASE side WHEN 'DEBIT' THEN 'CREDIT' ELSE 'DEBIT' END,"amountKgs"
      FROM owner_accounting_posting_lines WHERE "postingId"=p."reversesId")
     UNION ALL
     (SELECT "lineNo","accountCode",
             CASE side WHEN 'DEBIT' THEN 'CREDIT' ELSE 'DEBIT' END,"amountKgs"
      FROM owner_accounting_posting_lines WHERE "postingId"=p."reversesId"
      EXCEPT ALL
      SELECT "lineNo","accountCode",side,"amountKgs"
      FROM owner_accounting_posting_lines WHERE "postingId"=p.id)
   ) delta;
 END IF;
 IF mismatch_count<>0 THEN
   RAISE EXCEPTION 'ACCOUNTING_POSTING_LINES_SOURCE_OR_REVERSAL_MISMATCH'
     USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER owner_accounting_post_commit_header
 AFTER INSERT ON owner_accounting_postings DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION check_owner_accounting_posting_commit();
CREATE CONSTRAINT TRIGGER owner_accounting_post_commit_line
 AFTER INSERT ON owner_accounting_posting_lines DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION check_owner_accounting_posting_commit();

-- A sealed posting cannot acquire additional lines in a subsequent transaction.
CREATE FUNCTION guard_owner_accounting_post_lines_same_transaction() RETURNS trigger AS $$
DECLARE header_xmin bigint;
BEGIN
 SELECT xmin::text::bigint INTO header_xmin FROM owner_accounting_postings
 WHERE id=NEW."postingId" AND "propertyId"=NEW."propertyId";
 IF header_xmin IS NULL OR header_xmin<>(txid_current() % 4294967296) THEN
  RAISE EXCEPTION 'ACCOUNTING_POSTING_ALREADY_SEALED' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER owner_accounting_post_lines_atomic
 BEFORE INSERT ON owner_accounting_posting_lines
 FOR EACH ROW EXECUTE FUNCTION guard_owner_accounting_post_lines_same_transaction();

-- No account balances or recognized P&L are computed by this migration.
-- All statement outputs require independent full-period completeness proof.
