-- Immutable source-to-document certification is distinct from service approval.
-- It records independently reviewed tax allocation against actual stored bytes.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE owner_revenue_accounting_certifications (
 id uuid PRIMARY KEY,
 "propertyId" uuid NOT NULL,
 "sourceEventId" uuid NOT NULL,
 "evidenceDocumentId" uuid NOT NULL,
 "reviewedById" uuid NOT NULL REFERENCES staff_users(id) ON DELETE RESTRICT,
 "grossAmountKgs" numeric(20,4) NOT NULL CHECK ("grossAmountKgs">0),
 "taxAmountKgs" numeric(20,4) NOT NULL CHECK ("taxAmountKgs">=0),
 "netRevenueKgs" numeric(20,4) NOT NULL CHECK ("netRevenueKgs">0),
 "policyVersion" text NOT NULL CHECK(length("policyVersion") BETWEEN 3 AND 80),
 reason text NOT NULL CHECK(length(reason) BETWEEN 8 AND 500),
 "createdAt" timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT owner_cert_gross_split CHECK ("grossAmountKgs"="taxAmountKgs"+"netRevenueKgs"),
 CONSTRAINT owner_cert_one_per_source UNIQUE("propertyId","sourceEventId"),
 CONSTRAINT owner_cert_source_fk FOREIGN KEY("propertyId","sourceEventId")
    REFERENCES owner_revenue_source_events("propertyId",id) ON DELETE RESTRICT,
 CONSTRAINT owner_cert_document_fk FOREIGN KEY("propertyId","evidenceDocumentId")
    REFERENCES owner_revenue_evidence_documents("propertyId",id) ON DELETE RESTRICT
);
CREATE FUNCTION validate_owner_source_certification() RETURNS trigger AS $$
DECLARE
 e record;
 d record;
 reviewer record;
BEGIN
 SELECT * INTO e FROM owner_revenue_source_events
  WHERE "propertyId"=NEW."propertyId" AND id=NEW."sourceEventId"
    AND action='APPROVE_SOURCE'
    AND NOT EXISTS (SELECT 1 FROM owner_revenue_source_events r
      WHERE r."propertyId"=e."propertyId" AND r."reversesId"=e.id);
 SELECT * INTO d FROM owner_revenue_evidence_documents
  WHERE "propertyId"=NEW."propertyId" AND id=NEW."evidenceDocumentId";
 SELECT "propertyId",role::text AS role,"isActive" AS active INTO reviewer
  FROM staff_users WHERE id=NEW."reviewedById";
 IF e.id IS NULL OR d.id IS NULL
    OR e."sourceType" NOT IN ('ROOM_NIGHT','DINING_ORDER')
    OR reviewer."propertyId" IS DISTINCT FROM NEW."propertyId"
    OR reviewer.role IS DISTINCT FROM 'OWNER'
    OR reviewer.active IS DISTINCT FROM TRUE
    OR e."createdById"=NEW."reviewedById"
    OR d."uploadedById"=NEW."reviewedById"
    OR encode(digest(d."content",'sha256'),'hex')<>d.sha256
    OR d."documentDate">CURRENT_DATE
    OR NEW."grossAmountKgs"<>e."faceValueKgs"
    OR EXISTS (
      SELECT 1 FROM owner_revenue_correction_events c
      WHERE c."propertyId"=NEW."propertyId"
        AND c."approvalId"=NEW."sourceEventId" AND c.action='RECORD'
        AND NOT EXISTS(SELECT 1 FROM owner_revenue_correction_events r
           WHERE r."propertyId"=NEW."propertyId" AND r."reversesId"=c.id))
 THEN
    RAISE EXCEPTION 'OWNER_REVENUE_DOCUMENT_CERTIFICATION_INVALID' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER owner_source_certificate_validate
 BEFORE INSERT ON owner_revenue_accounting_certifications
 FOR EACH ROW EXECUTE FUNCTION validate_owner_source_certification();
CREATE TRIGGER owner_source_certificate_immutable
 BEFORE UPDATE OR DELETE ON owner_revenue_accounting_certifications
 FOR EACH ROW EXECUTE FUNCTION reject_owner_accounting_journal_mutation();

-- Existing immutable service source keeps its original snapshot unchanged.
-- A separate independently approved byte-backed certificate is now required.
CREATE OR REPLACE FUNCTION guard_owner_accounting_posting_insert() RETURNS trigger AS $$
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
      source_proof."sourceType" NOT IN ('ROOM_NIGHT','DINING_ORDER')
      OR NOT EXISTS (
        SELECT 1 FROM owner_revenue_accounting_certifications cert
        WHERE cert."propertyId"=NEW."propertyId"
          AND cert."sourceEventId"=original_proposal."sourceId"
          AND cert."grossAmountKgs"=source_proof."faceValueKgs"
          AND cert."policyVersion"=NEW."policyVersion")
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
   ELSIF original_proposal."sourceType"='STOCK_CONSUMPTION' THEN
     IF owner_accounting_served_cogs_proof(
          NEW."propertyId",original_proposal."sourceId",
          NEW."accountingDate") IS NULL THEN
       RAISE EXCEPTION 'ACCOUNTING_POSTING_SERVED_COGS_SOURCE_UNVERIFIED'
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

-- Source gross, certified net revenue and tax must match exact journal lines;
-- the deferred check also guards direct SQL writers, not only the API.
CREATE FUNCTION validate_owner_certified_posted_split() RETURNS trigger AS $$
DECLARE
 p record;
 e record;
 c record;
 debit_receivable numeric(20,4);
 credit_revenue numeric(20,4);
 credit_tax numeric(20,4);
 unexpected integer;
BEGIN
 SELECT * INTO p FROM owner_accounting_journal_proposals
  WHERE "propertyId"=NEW."propertyId" AND id=NEW."proposalId";
 IF NEW.action<>'POST' OR p."sourceType"<>'REVENUE_SOURCE' THEN
   RETURN NEW;
 END IF;
 SELECT * INTO e FROM owner_revenue_source_events
  WHERE "propertyId"=NEW."propertyId" AND id=p."sourceId";
 SELECT * INTO c FROM owner_revenue_accounting_certifications
  WHERE "propertyId"=NEW."propertyId" AND "sourceEventId"=p."sourceId"
    AND "policyVersion"=NEW."policyVersion";
 IF c.id IS NULL THEN
    RAISE EXCEPTION 'OWNER_REVENUE_DOCUMENT_CERTIFICATION_REQUIRED' USING ERRCODE='23514';
 END IF;
 SELECT
  coalesce(sum("amountKgs") FILTER (WHERE "accountCode"='1100' AND side='DEBIT'),0),
  coalesce(sum("amountKgs") FILTER (WHERE "accountCode"=(
    CASE e."sourceType" WHEN 'ROOM_NIGHT' THEN '4100'
      WHEN 'DINING_ORDER' THEN '4200' ELSE 'UNSUPPORTED' END) AND side='CREDIT'),0),
  coalesce(sum("amountKgs") FILTER (WHERE "accountCode"='2100' AND side='CREDIT'),0),
  count(*) FILTER(WHERE NOT (
     ("accountCode"='1100' AND side='DEBIT')
     OR ("accountCode"='2100' AND side='CREDIT')
     OR ("accountCode"=(CASE e."sourceType" WHEN 'ROOM_NIGHT' THEN '4100'
                        WHEN 'DINING_ORDER' THEN '4200' ELSE 'UNSUPPORTED' END)
          AND side='CREDIT')))
 INTO debit_receivable,credit_revenue,credit_tax,unexpected
 FROM owner_accounting_posting_lines
 WHERE "postingId"=NEW.id AND "propertyId"=NEW."propertyId";
 IF debit_receivable<>c."grossAmountKgs"
    OR credit_revenue<>c."netRevenueKgs"
    OR credit_tax<>c."taxAmountKgs"
    OR unexpected<>0 THEN
    RAISE EXCEPTION 'OWNER_REVENUE_DOCUMENT_SPLIT_MISMATCH' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER owner_certified_posted_split_deferred
 AFTER INSERT ON owner_accounting_postings
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
 EXECUTE FUNCTION validate_owner_certified_posted_split();
