-- Independently certify the exact active correction set before recognition.
-- Source face remains unchanged; only additional documented reductions may
-- reduce receivable. Refund and package allocation still require cash/delivery proof.
ALTER TABLE owner_revenue_accounting_certifications
 ADD COLUMN "correctionEventIds" uuid[],
 ADD COLUMN "reductionAmountKgs" numeric(20,4) NOT NULL DEFAULT 0,
 ADD COLUMN "reductionBasis" text;
ALTER TABLE owner_revenue_accounting_certifications
 DROP CONSTRAINT owner_cert_gross_split,
 ADD CONSTRAINT owner_cert_gross_split CHECK (
  "grossAmountKgs"="taxAmountKgs"+"netRevenueKgs"+"reductionAmountKgs"),
 ADD CONSTRAINT owner_cert_reduction_basis CHECK (
  ("reductionAmountKgs"=0 AND "reductionBasis" IS NULL)
  OR ("reductionAmountKgs">0 AND "reductionBasis" IS NOT DISTINCT FROM 'ADDITIONAL_TO_APPROVED_FACE'
      AND "correctionEventIds" IS NOT NULL));

CREATE FUNCTION owner_active_revenue_correction_ids(pid uuid,sid uuid)
RETURNS uuid[] LANGUAGE sql STABLE AS $$
 SELECT COALESCE(array_agg(c.id ORDER BY c.id),ARRAY[]::uuid[])
 FROM owner_revenue_correction_events c
 WHERE c."propertyId"=pid AND c."approvalId"=sid AND c.action='RECORD'
 AND NOT EXISTS(SELECT 1 FROM owner_revenue_correction_events r
   WHERE r."propertyId"=pid AND r."reversesId"=c.id AND r.action='REVERSE')
$$;

CREATE FUNCTION owner_revenue_corrections_match_snapshot(
 pid uuid,sid uuid,did uuid,reviewer uuid,tax numeric,reduction numeric,ids uuid[])
RETURNS boolean LANGUAGE sql STABLE AS $$
 WITH active AS (
   SELECT c.*,e."sourceType" AS service_type,e."serviceDate" AS service_day,
          d.id AS doc_id,d."uploadedById" AS uploader,d."documentReference" AS doc_ref,
          d."documentDate" AS doc_day,d.sha256 AS doc_sha,
          encode(digest(d.content,'sha256'),'hex') AS actual_sha
   FROM owner_revenue_correction_events c
   JOIN owner_revenue_source_events e ON e."propertyId"=pid AND e.id=sid
   LEFT JOIN owner_revenue_evidence_documents d
     ON d."propertyId"=pid AND d.id=c."evidenceDocumentId"
   WHERE c."propertyId"=pid AND c."approvalId"=sid AND c.action='RECORD'
     AND NOT EXISTS(SELECT 1 FROM owner_revenue_correction_events r
       WHERE r."propertyId"=pid AND r."reversesId"=c.id AND r.action='REVERSE')
 )
 SELECT COALESCE(
   ids=owner_active_revenue_correction_ids(pid,sid)
   AND reduction=COALESCE((SELECT sum("amountKgs") FROM active
                            WHERE kind IN ('DISCOUNT','CANCELLATION')),0)
   AND (NOT EXISTS(SELECT 1 FROM active WHERE kind='TAX_COMPONENT')
        OR tax=(SELECT sum("amountKgs") FROM active WHERE kind='TAX_COMPONENT'))
   AND NOT EXISTS(SELECT 1 FROM active c WHERE
       c.kind NOT IN ('DISCOUNT','CANCELLATION','TAX_COMPONENT')
       OR c.doc_id IS NULL OR c.uploader=reviewer OR c."createdById"=reviewer
       OR c."documentReference" IS DISTINCT FROM c.doc_ref
       OR c."documentDate" IS DISTINCT FROM c.doc_day
       OR c."documentDate">CURRENT_DATE
       OR c."documentSha256" IS DISTINCT FROM c.doc_sha
       OR c.actual_sha IS DISTINCT FROM c.doc_sha
       OR (c.kind='TAX_COMPONENT' AND (c.doc_id<>did OR c.component IS DISTINCT FROM
            CASE c.service_type WHEN 'ROOM_NIGHT' THEN 'LODGING'
              WHEN 'DINING_ORDER' THEN 'DINING' WHEN 'OTHER_SERVICE' THEN 'OTHER' END))
       OR (c.kind IN ('DISCOUNT','CANCELLATION') AND
          (c."documentDate"<c.service_day OR c.component NOT IN ('UNALLOCATED',
            CASE c.service_type WHEN 'ROOM_NIGHT' THEN 'LODGING'
              WHEN 'DINING_ORDER' THEN 'DINING' WHEN 'OTHER_SERVICE' THEN 'OTHER' END)))
   ),false)
$$;

CREATE FUNCTION owner_revenue_certificate_current(c owner_revenue_accounting_certifications)
RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT owner_revenue_corrections_match_snapshot(
  c."propertyId",c."sourceEventId",c."evidenceDocumentId",c."reviewedById",
  c."taxAmountKgs",c."reductionAmountKgs",
  COALESCE(c."correctionEventIds",
    CASE WHEN c."taxCorrectionEventId" IS NULL THEN ARRAY[]::uuid[]
         ELSE ARRAY[c."taxCorrectionEventId"] END))
$$;

CREATE OR REPLACE FUNCTION validate_owner_source_certification() RETURNS trigger AS $$
DECLARE
 e record;
 d record;
 reviewer record;
BEGIN
 PERFORM owner_lock_revenue_posting(NEW."propertyId",NEW."sourceEventId");
 -- Old single-tax clients remain compatible; multi-event reductions must
 -- explicitly supply the reviewed event IDs and amount.
 IF NEW."correctionEventIds" IS NULL THEN
   IF NEW."reductionAmountKgs"<>0 THEN
      RAISE EXCEPTION 'OWNER_REVENUE_REDUCTION_REVIEW_REQUIRED' USING ERRCODE='23514';
   END IF;
   NEW."correctionEventIds":=owner_active_revenue_correction_ids(NEW."propertyId",NEW."sourceEventId");
   IF cardinality(NEW."correctionEventIds")>1 THEN
      RAISE EXCEPTION 'OWNER_REVENUE_CORRECTION_SET_REVIEW_REQUIRED' USING ERRCODE='23514';
   END IF;
 END IF;
 SELECT CASE WHEN count(*)=1 THEN (array_agg(c.id))[1] ELSE NULL END
 INTO NEW."taxCorrectionEventId"
 FROM owner_revenue_correction_events c
 WHERE c."propertyId"=NEW."propertyId" AND c.id=ANY(NEW."correctionEventIds")
   AND c.kind='TAX_COMPONENT';
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
    OR NOT owner_revenue_corrections_match_snapshot(NEW."propertyId",NEW."sourceEventId",
         NEW."evidenceDocumentId",NEW."reviewedById",NEW."taxAmountKgs",
         NEW."reductionAmountKgs",NEW."correctionEventIds")
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
          AND owner_revenue_certificate_current(cert)) THEN
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
 AND NOT owner_revenue_certificate_current(c)) THEN
 RAISE EXCEPTION 'ACCOUNTING_CORRECTIONS_NOT_RECONCILED' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END; $$;


CREATE OR REPLACE FUNCTION validate_owner_certified_posted_split() RETURNS trigger AS $$
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
      WHEN 'DINING_ORDER' THEN '4200' WHEN 'OTHER_SERVICE' THEN '4300' ELSE 'UNSUPPORTED' END) AND side='CREDIT'),0),
  coalesce(sum("amountKgs") FILTER (WHERE "accountCode"='2100' AND side='CREDIT'),0),
  count(*) FILTER(WHERE NOT (
     ("accountCode"='1100' AND side='DEBIT')
     OR ("accountCode"='2100' AND side='CREDIT')
     OR ("accountCode"=(CASE e."sourceType" WHEN 'ROOM_NIGHT' THEN '4100'
                        WHEN 'DINING_ORDER' THEN '4200' WHEN 'OTHER_SERVICE' THEN '4300' ELSE 'UNSUPPORTED' END)
          AND side='CREDIT')))
 INTO debit_receivable,credit_revenue,credit_tax,unexpected
 FROM owner_accounting_posting_lines
 WHERE "postingId"=NEW.id AND "propertyId"=NEW."propertyId";
 IF debit_receivable<>c."grossAmountKgs"-c."reductionAmountKgs"
    OR credit_revenue<>c."netRevenueKgs"
    OR credit_tax<>c."taxAmountKgs"
    OR unexpected<>0 THEN
    RAISE EXCEPTION 'OWNER_REVENUE_DOCUMENT_SPLIT_MISMATCH' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION check_owner_accounting_posting_commit() RETURNS trigger AS $$
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
   ELSIF EXISTS(SELECT 1 FROM owner_accounting_journal_proposals pr
      WHERE pr.id=p."proposalId" AND pr."propertyId"=p."propertyId"
        AND pr."sourceType"='STOCK_CONSUMPTION') THEN
     SELECT owner_accounting_served_cogs_proof(
              pr."propertyId",pr."sourceId",pr."accountingDate")
       INTO debit_total
       FROM owner_accounting_journal_proposals pr
       WHERE pr.id=p."proposalId" AND pr."propertyId"=p."propertyId";
     IF debit_total IS NULL
         OR (SELECT COUNT(*) FROM owner_accounting_posting_lines l
              WHERE l."postingId"=p.id)<>2
         OR NOT EXISTS(SELECT 1 FROM owner_accounting_posting_lines l
               WHERE l."postingId"=p.id AND l."accountCode"='5100'
                 AND l.side='DEBIT' AND l."amountKgs"=debit_total)
         OR NOT EXISTS(SELECT 1 FROM owner_accounting_posting_lines l
               WHERE l."postingId"=p.id AND l."accountCode"='1300'
                 AND l.side='CREDIT' AND l."amountKgs"=debit_total)
     THEN
         RAISE EXCEPTION 'ACCOUNTING_POSTING_SERVED_COGS_ACCOUNT_POLICY_INVALID'
           USING ERRCODE='23514';
     END IF;
   ELSE
   -- Revenue posting: debit receivable for the source's exact face value;
   -- credit an approved revenue account and optional tax payable only.
   SELECT cert."grossAmountKgs"-cert."reductionAmountKgs",e."sourceType" INTO debit_total,source_service_type
     FROM owner_accounting_journal_proposals pr
     JOIN owner_revenue_source_events e ON e.id=pr."sourceId"
       AND e."propertyId"=pr."propertyId"
     JOIN owner_revenue_accounting_certifications cert
       ON cert."propertyId"=e."propertyId" AND cert."sourceEventId"=e.id
       AND cert."policyVersion"=p."policyVersion"
    WHERE pr.id=p."proposalId" AND pr."propertyId"=p."propertyId";
   expected_revenue_code := CASE source_service_type
     WHEN 'ROOM_NIGHT' THEN '4100'
     WHEN 'DINING_ORDER' THEN '4200' WHEN 'OTHER_SERVICE' THEN '4300' ELSE NULL END;
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
