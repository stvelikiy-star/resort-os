-- A documented full cancellation has zero earned value. Do not manufacture
-- a zero-value journal entry or alter the historical delivered-source face.
ALTER TABLE owner_revenue_accounting_certifications
 DROP CONSTRAINT "owner_revenue_accounting_certifications_netRevenueKgs_check";
ALTER TABLE owner_revenue_accounting_certifications
 ADD CONSTRAINT owner_cert_net_nonnegative CHECK ("netRevenueKgs">=0),
 ADD CONSTRAINT owner_cert_zero_only_full_reduction CHECK (
   "netRevenueKgs">0 OR ("taxAmountKgs"=0 AND "reductionAmountKgs"="grossAmountKgs"
    AND "reductionBasis" IS NOT DISTINCT FROM 'ADDITIONAL_TO_APPROVED_FACE'));

CREATE FUNCTION owner_full_cancellation_proof(pid uuid,sid uuid,gross numeric,ids uuid[])
RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT COALESCE(ids=owner_active_revenue_correction_ids(pid,sid)
   AND (SELECT count(*) FROM owner_revenue_correction_events c
     WHERE c."propertyId"=pid AND c."approvalId"=sid AND c.id=ANY(ids)
       AND c.action='RECORD' AND c.kind='CANCELLATION' AND c."amountKgs"=gross)=1
   AND NOT EXISTS(SELECT 1 FROM owner_revenue_correction_events c
     WHERE c."propertyId"=pid AND c."approvalId"=sid AND c.id=ANY(ids)
       AND c.kind NOT IN ('CANCELLATION','REFUND'))
   AND NOT owner_revenue_has_active_posting(pid,sid),false)
$$;

CREATE FUNCTION owner_validate_zero_revenue_certificate() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 IF NEW."netRevenueKgs"=0 AND NOT owner_full_cancellation_proof(
    NEW."propertyId",NEW."sourceEventId",NEW."grossAmountKgs",NEW."correctionEventIds") THEN
   RAISE EXCEPTION 'OWNER_FULL_CANCELLATION_PROOF_REQUIRED' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER zz_owner_validate_zero_revenue_certificate
 BEFORE INSERT ON owner_revenue_accounting_certifications
 FOR EACH ROW EXECUTE FUNCTION owner_validate_zero_revenue_certificate();

CREATE FUNCTION owner_guard_zero_revenue_posting() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.action='POST' AND EXISTS(
   SELECT 1 FROM owner_accounting_journal_proposals q
   JOIN owner_revenue_accounting_certifications c
     ON c."propertyId"=q."propertyId" AND c."sourceEventId"=q."sourceId"
   WHERE q."propertyId"=NEW."propertyId" AND q.id=NEW."proposalId"
     AND q."sourceType"='REVENUE_SOURCE' AND c."netRevenueKgs"=0) THEN
   RAISE EXCEPTION 'OWNER_CANCELLED_SOURCE_HAS_NO_POSTABLE_VALUE' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER zz_owner_guard_zero_revenue_posting
 BEFORE INSERT ON owner_accounting_postings
 FOR EACH ROW EXECUTE FUNCTION owner_guard_zero_revenue_posting();

CREATE FUNCTION owner_zero_revenue_certificate_current(c owner_revenue_accounting_certifications)
RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT COALESCE(c."netRevenueKgs"=0 AND c."taxAmountKgs"=0
    AND owner_revenue_certificate_current(c)
    AND owner_full_cancellation_proof(c."propertyId",c."sourceEventId",
      c."grossAmountKgs",c."correctionEventIds"),false)
$$;
