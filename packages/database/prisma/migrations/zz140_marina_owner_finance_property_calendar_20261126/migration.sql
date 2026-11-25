-- Additive correction: compare financial evidence to the hotel's calendar, not server UTC.
-- Preserve every previous migration, the independent review and immutable posting guards.
CREATE FUNCTION owner_finance_property_day(pid uuid, at_time timestamptz DEFAULT now())
RETURNS date LANGUAGE sql STABLE AS $$
 SELECT (at_time AT TIME ZONE p.timezone)::date FROM properties p WHERE p.id=pid
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
    OR (owner_finance_property_day(NEW."propertyId") IS NULL OR d."documentDate">owner_finance_property_day(NEW."propertyId"))
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

CREATE OR REPLACE FUNCTION owner_revenue_corrections_match_snapshot(
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
       c.kind NOT IN ('DISCOUNT','CANCELLATION','TAX_COMPONENT','REFUND')
       OR (c.kind='REFUND' AND owner_revenue_refund_payment_id(pid,c.id,reviewer) IS NULL)
       OR c.doc_id IS NULL OR c.uploader=reviewer OR c."createdById"=reviewer
       OR c."documentReference" IS DISTINCT FROM c.doc_ref
       OR c."documentDate" IS DISTINCT FROM c.doc_day
       OR (owner_finance_property_day(pid) IS NULL OR c."documentDate">owner_finance_property_day(pid))
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
