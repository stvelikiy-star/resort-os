-- Preserve immutable journal; serialize all revenue-source lifecycle writes.
CREATE FUNCTION owner_guard_revenue_period_posting() RETURNS trigger
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
 IF EXISTS (SELECT 1 FROM owner_revenue_correction_events c
 WHERE c."propertyId"=NEW."propertyId" AND c."approvalId"=e.id AND c.action='RECORD'
 AND NOT EXISTS (SELECT 1 FROM owner_revenue_correction_events r
 WHERE r."propertyId"=c."propertyId" AND r."reversesId"=c.id AND r.action='REVERSE')) THEN
 RAISE EXCEPTION 'ACCOUNTING_CORRECTIONS_NOT_RECONCILED' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER ab_owner_revenue_period_posting BEFORE INSERT ON owner_accounting_postings
FOR EACH ROW EXECUTE FUNCTION owner_guard_revenue_period_posting();

CREATE FUNCTION owner_guard_correction_posting_lifecycle() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 PERFORM owner_lock_revenue_posting(NEW."propertyId",NEW."approvalId");
 IF owner_revenue_has_active_posting(NEW."propertyId",NEW."approvalId") THEN
 RAISE EXCEPTION 'REVENUE_CORRECTION_ACTIVE_POSTING_REQUIRES_REVERSAL' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER aa_owner_correction_posting_guard BEFORE INSERT ON owner_revenue_correction_events
FOR EACH ROW EXECUTE FUNCTION owner_guard_correction_posting_lifecycle();

-- Refuse migration rather than silently rewrite historic accounting facts.
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM owner_accounting_postings p
 JOIN owner_accounting_journal_proposals q ON q."propertyId"=p."propertyId" AND q.id=p."proposalId"
 JOIN owner_revenue_source_events e ON e."propertyId"=q."propertyId" AND e.id=q."sourceId"
 WHERE q."sourceType"='REVENUE_SOURCE' AND p.action='POST'
 AND p."accountingDate"<>e."serviceDate") THEN
 RAISE EXCEPTION 'OWNER_EXISTING_REVENUE_PERIOD_MISMATCH';
 END IF;
 IF EXISTS (SELECT 1 FROM owner_revenue_correction_events c
 WHERE c.action='RECORD' AND NOT EXISTS (SELECT 1 FROM owner_revenue_correction_events r
 WHERE r."propertyId"=c."propertyId" AND r."reversesId"=c.id AND r.action='REVERSE')
 AND owner_revenue_has_active_posting(c."propertyId",c."approvalId")) THEN
 RAISE EXCEPTION 'OWNER_EXISTING_UNRECONCILED_POSTED_CORRECTION';
 END IF;
END; $$;
