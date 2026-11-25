-- Bind exactly one independently reviewed tax classification to the
-- existing immutable certification; no second tax/revenue posting.
ALTER TABLE owner_revenue_accounting_certifications
 ADD COLUMN "taxCorrectionEventId" uuid;
ALTER TABLE owner_revenue_accounting_certifications
 ADD CONSTRAINT owner_revenue_cert_tax_event_property_fkey
 FOREIGN KEY ("propertyId","taxCorrectionEventId")
 REFERENCES owner_revenue_correction_events ("propertyId",id) ON DELETE RESTRICT;

CREATE FUNCTION owner_active_revenue_correction_id(pid uuid,sid uuid)
RETURNS uuid LANGUAGE sql STABLE AS $$
 SELECT c.id FROM owner_revenue_correction_events c
 WHERE c."propertyId"=pid AND c."approvalId"=sid AND c.action='RECORD'
 AND NOT EXISTS(SELECT 1 FROM owner_revenue_correction_events r
   WHERE r."propertyId"=pid AND r."reversesId"=c.id AND r.action='REVERSE')
 ORDER BY c.id LIMIT 1
$$;

CREATE FUNCTION owner_revenue_corrections_match_certificate(
 pid uuid,sid uuid,did uuid,reviewer uuid,tax numeric,cid uuid)
RETURNS boolean LANGUAGE sql STABLE AS $$
 WITH active AS (
 SELECT c.* FROM owner_revenue_correction_events c
 WHERE c."propertyId"=pid AND c."approvalId"=sid AND c.action='RECORD'
 AND NOT EXISTS(SELECT 1 FROM owner_revenue_correction_events r
   WHERE r."propertyId"=pid AND r."reversesId"=c.id AND r.action='REVERSE')
 )
 SELECT CASE WHEN cid IS NULL THEN NOT EXISTS(SELECT 1 FROM active)
 ELSE (SELECT count(*) FROM active)=1 AND EXISTS(
 SELECT 1 FROM active c
 JOIN owner_revenue_source_events e ON e."propertyId"=pid AND e.id=sid
 JOIN owner_revenue_evidence_documents d ON d."propertyId"=pid AND d.id=did
 WHERE c.id=cid AND c.kind='TAX_COMPONENT' AND c."amountKgs"=tax
   AND c.component=CASE e."sourceType" WHEN 'ROOM_NIGHT' THEN 'LODGING'
       WHEN 'DINING_ORDER' THEN 'DINING' WHEN 'OTHER_SERVICE' THEN 'OTHER' END
   AND c."evidenceDocumentId"=did AND c."documentReference"=d."documentReference"
   AND c."documentDate"=d."documentDate" AND c."documentDate"<=CURRENT_DATE
   AND c."documentSha256"=d.sha256
   AND encode(digest(d.content,'sha256'),'hex')=d.sha256
   AND c."createdById"<>reviewer AND d."uploadedById"<>reviewer
 ) END
$$;

CREATE OR REPLACE FUNCTION validate_owner_source_certification() RETURNS trigger AS $$
DECLARE
 e record;
 d record;
 reviewer record;
BEGIN
 PERFORM owner_lock_revenue_posting(NEW."propertyId",NEW."sourceEventId");
 NEW."taxCorrectionEventId":=owner_active_revenue_correction_id(NEW."propertyId",NEW."sourceEventId");
 SELECT src.* INTO e FROM owner_revenue_source_events src
  WHERE src."propertyId"=NEW."propertyId" AND src.id=NEW."sourceEventId"
    AND src.action='APPROVE_SOURCE'
    AND NOT EXISTS (SELECT 1 FROM owner_revenue_source_events r
      WHERE r."propertyId"=src."propertyId" AND r."reversesId"=src.id);
 SELECT * INTO d FROM owner_revenue_evidence_documents
  WHERE "propertyId"=NEW."propertyId" AND id=NEW."evidenceDocumentId";
 SELECT "propertyId",role::text AS role,"isActive" AS active INTO reviewer
  FROM staff_users WHERE id=NEW."reviewedById";
 IF e.id IS NULL OR d.id IS NULL
    OR e."sourceType" NOT IN ('ROOM_NIGHT','DINING_ORDER','OTHER_SERVICE')
    OR (e."sourceType"='OTHER_SERVICE' AND owner_guest_service_revenue_proof(e."propertyId",e."sourceId",e."serviceDate") IS DISTINCT FROM e."faceValueKgs")
    OR reviewer."propertyId" IS DISTINCT FROM NEW."propertyId"
    OR reviewer.role IS DISTINCT FROM 'OWNER'
    OR reviewer.active IS DISTINCT FROM TRUE
    OR e."createdById"=NEW."reviewedById"
    OR d."uploadedById"=NEW."reviewedById"
    OR encode(digest(d."content",'sha256'),'hex')<>d.sha256
    OR d."documentDate">CURRENT_DATE
    OR NEW."grossAmountKgs"<>e."faceValueKgs"
    OR NOT owner_revenue_corrections_match_certificate(NEW."propertyId",NEW."sourceEventId",
         NEW."evidenceDocumentId",NEW."reviewedById",NEW."taxAmountKgs",NEW."taxCorrectionEventId")
 THEN
    RAISE EXCEPTION 'OWNER_REVENUE_DOCUMENT_CERTIFICATION_INVALID' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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
   SELECT e."faceValueKgs",e."sourceType",e."sourceSnapshot",e."sourceId",e."serviceDate" INTO source_proof
     FROM owner_revenue_source_events e
    WHERE e."propertyId"=NEW."propertyId" AND e.id=original_proposal."sourceId"
      AND e.action='APPROVE_SOURCE'
      AND NOT EXISTS(SELECT 1 FROM owner_revenue_source_events r
          WHERE r."propertyId"=e."propertyId" AND r."reversesId"=e.id);
   IF NOT FOUND OR
      source_proof."sourceType" NOT IN ('ROOM_NIGHT','DINING_ORDER','OTHER_SERVICE')
      OR (source_proof."sourceType"='OTHER_SERVICE' AND owner_guest_service_revenue_proof(NEW."propertyId",source_proof."sourceId",source_proof."serviceDate") IS DISTINCT FROM source_proof."faceValueKgs")
      OR NOT EXISTS (
        SELECT 1 FROM owner_revenue_accounting_certifications cert
        WHERE cert."propertyId"=NEW."propertyId"
          AND cert."sourceEventId"=original_proposal."sourceId"
          AND cert."grossAmountKgs"=source_proof."faceValueKgs"
          AND cert."policyVersion"=NEW."policyVersion"
          AND owner_revenue_corrections_match_certificate(cert."propertyId",cert."sourceEventId",
              cert."evidenceDocumentId",cert."reviewedById",cert."taxAmountKgs",cert."taxCorrectionEventId")) THEN
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

CREATE OR REPLACE FUNCTION owner_guard_revenue_period_posting() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE e record;
BEGIN
 IF NEW.action <> 'POST' THEN RETURN NEW; END IF;
 SELECT s.id,s."serviceDate" INTO e
 FROM owner_accounting_journal_proposals q
 JOIN owner_revenue_source_events s ON s."propertyId"=q."propertyId" AND s.id=q."sourceId"
 WHERE q."propertyId"=NEW."propertyId" AND q.id=NEW."proposalId"
 AND q."sourceType"='REVENUE_SOURCE';
 IF NOT FOUND THEN RETURN NEW; END IF;
 PERFORM owner_lock_revenue_posting(NEW."propertyId",e.id);
 IF NEW."accountingDate"<>e."serviceDate" THEN
 RAISE EXCEPTION 'ACCOUNTING_REVENUE_SERVICE_DATE_MISMATCH' USING ERRCODE='23514';
 END IF;
 IF EXISTS (SELECT 1 FROM owner_revenue_accounting_certifications c
 WHERE c."propertyId"=NEW."propertyId" AND c."sourceEventId"=e.id
 AND NOT owner_revenue_corrections_match_certificate(c."propertyId",c."sourceEventId",
     c."evidenceDocumentId",c."reviewedById",c."taxAmountKgs",c."taxCorrectionEventId")) THEN
 RAISE EXCEPTION 'ACCOUNTING_CORRECTIONS_NOT_RECONCILED' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END; $$;
