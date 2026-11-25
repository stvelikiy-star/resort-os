-- Reuse existing completed task, folio, document and immutable posting.
ALTER TABLE owner_revenue_source_events DROP CONSTRAINT owner_revenue_source_type_check;
ALTER TABLE owner_revenue_source_events ADD CONSTRAINT owner_revenue_source_type_check
 CHECK ("sourceType" IN ('ROOM_NIGHT','DINING_ORDER','OTHER_SERVICE'));

CREATE FUNCTION owner_guest_service_revenue_proof(pid uuid, tid uuid, day date)
RETURNS numeric LANGUAGE sql STABLE AS $$
 SELECT f."amountKgs"::numeric
 FROM operational_tasks t
 JOIN properties p ON p.id=t."propertyId"
 JOIN guest_folio_charges f ON f."propertyId"=t."propertyId"
    AND f."sourceType"='GUEST_SERVICE' AND f."sourceId"=t.id
 JOIN reservations r ON r.id=t."reservationId" AND r."propertyId"=t."propertyId"
 JOIN stays s ON s.id=t."stayId" AND s."propertyId"=t."propertyId"
    AND s."reservationId"=t."reservationId"
 WHERE t."propertyId"=pid AND t.id=tid AND t.status='DONE'
   AND t."completedAt" IS NOT NULL
   AND ((t."completedAt" AT TIME ZONE 'UTC') AT TIME ZONE p.timezone)::date=day
   AND t."serviceDate"=day AND f."serviceDate"=day
   AND f.status IN ('OPEN','PAID') AND f."amountKgs">0
   AND t."chargeKgs"=f."amountKgs" AND t."chargeStatus" IN ('POSTED','PAID')
   AND t."chargeSource"='FOLIO'
   AND f."reservationId"=t."reservationId" AND f."stayId"=t."stayId"
   AND f."guestId" IS NOT DISTINCT FROM s."guestId"
   AND f.code=COALESCE(t."serviceCode",'GUEST_SERVICE')
$$;

CREATE FUNCTION owner_guard_guest_service_approval() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 IF NEW."sourceType"='OTHER_SERVICE' AND NEW.action='APPROVE_SOURCE' THEN
   PERFORM 1 FROM operational_tasks t WHERE t.id=NEW."sourceId" AND t."propertyId"=NEW."propertyId" FOR SHARE;
   PERFORM 1 FROM guest_folio_charges f WHERE f."sourceType"='GUEST_SERVICE' AND f."sourceId"=NEW."sourceId"
       AND f."propertyId"=NEW."propertyId" AND f.status IN ('OPEN','PAID') FOR SHARE;
   IF owner_guest_service_revenue_proof(NEW."propertyId",NEW."sourceId",NEW."serviceDate")
       IS DISTINCT FROM NEW."faceValueKgs" THEN
     RAISE EXCEPTION 'REVENUE_GUEST_SERVICE_NOT_QUALIFIED' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER ab_owner_guest_service_approval BEFORE INSERT ON owner_revenue_source_events
 FOR EACH ROW EXECUTE FUNCTION owner_guard_guest_service_approval();

CREATE OR REPLACE FUNCTION validate_owner_source_certification() RETURNS trigger AS $$
DECLARE
 e record;
 d record;
 reviewer record;
BEGIN
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
 IF debit_receivable<>c."grossAmountKgs"
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
   SELECT e."faceValueKgs",e."sourceType" INTO debit_total,source_service_type
     FROM owner_accounting_journal_proposals pr
     JOIN owner_revenue_source_events e ON e.id=pr."sourceId"
       AND e."propertyId"=pr."propertyId"
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
