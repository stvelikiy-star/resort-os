-- A documented full refund is a cash fact, not a revenue deduction.
-- Only the canonical manual full-refund payment and audit evidence qualify.
CREATE TABLE owner_revenue_refund_bindings (
 "propertyId" uuid NOT NULL,
 "correctionEventId" uuid NOT NULL,
 "paymentId" uuid NOT NULL REFERENCES payments(id) ON DELETE RESTRICT,
 "certificateId" uuid NOT NULL REFERENCES owner_revenue_accounting_certifications(id) ON DELETE RESTRICT,
 "createdAt" timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY ("propertyId","correctionEventId"),
 UNIQUE ("paymentId"),
 FOREIGN KEY ("propertyId","correctionEventId")
 REFERENCES owner_revenue_correction_events ("propertyId",id) ON DELETE RESTRICT
);
CREATE TRIGGER owner_revenue_refund_bindings_immutable
 BEFORE UPDATE OR DELETE ON owner_revenue_refund_bindings
 FOR EACH ROW EXECUTE FUNCTION reject_owner_revenue_correction_mutation();

CREATE FUNCTION owner_revenue_refund_payment_id(pid uuid,cid uuid,reviewer uuid)
RETURNS uuid LANGUAGE sql STABLE AS $$
 WITH eligible AS (
 SELECT DISTINCT pay.id
 FROM owner_revenue_correction_events c
 JOIN owner_revenue_source_events e
   ON e."propertyId"=c."propertyId" AND e.id=c."approvalId"
 JOIN properties p ON p.id=c."propertyId"
 JOIN owner_revenue_evidence_documents d
   ON d."propertyId"=c."propertyId" AND d.id=c."evidenceDocumentId"
 LEFT JOIN kitchen_orders o ON e."sourceType"='DINING_ORDER'
   AND o."propertyId"=e."propertyId" AND o.id=e."sourceId"
 LEFT JOIN guest_folio_charges f ON f."propertyId"=e."propertyId"
   AND f.id=o."folioChargeId" AND f."sourceType"='KITCHEN_ORDER' AND f."sourceId"=o.id
 LEFT JOIN operational_tasks t ON e."sourceType"='OTHER_SERVICE'
   AND t."propertyId"=e."propertyId" AND t.id=e."sourceId"
 JOIN reservations r ON r."propertyId"=e."propertyId"
   AND r.id=CASE e."sourceType" WHEN 'ROOM_NIGHT' THEN e."sourceId"
       WHEN 'DINING_ORDER' THEN f."reservationId"
       WHEN 'OTHER_SERVICE' THEN t."reservationId" END
 JOIN payments pay ON pay."reservationId"=r.id
 JOIN audit_logs a ON a."propertyId"=r."propertyId" AND a."resourceId"=pay.id::text
   AND a.action='CONFIRM_MANUAL_FULL_REFUND' AND a.resource='Payment'
   AND a.source='PMS_MANUAL_REFUND' AND a.result='SUCCESS'
 WHERE c."propertyId"=pid AND c.id=cid AND c.kind='REFUND' AND c.action='RECORD'
   AND e.action='APPROVE_SOURCE'
   AND NOT EXISTS(SELECT 1 FROM owner_revenue_correction_events rev
     WHERE rev."propertyId"=pid AND rev."reversesId"=c.id AND rev.action='REVERSE')
   AND c."createdById"<>reviewer AND d."uploadedById"<>reviewer
   AND a."actorType"='STAFF' AND a."actorId" IS NOT NULL AND a."actorId"<>reviewer::text
   AND pay.status='REFUNDED' AND pay.provider='MANAGER_MANUAL'
   AND pay."paidAt" IS NOT NULL AND pay."amountKgs"=c."amountKgs"
   AND pay.metadata->'manual_full_refund_evidence'->>'origin'='EXTERNAL_ALREADY_COMPLETED'
   AND pay.metadata->'manual_full_refund_evidence'->'funds_sent_by_platform'='false'::jsonb
   AND pay.metadata->'manual_full_refund_evidence'->'amount_kgs'=to_jsonb(pay."amountKgs")
   AND pay.metadata->'manual_full_refund_evidence'->>'reference'=c."evidenceReference"
   AND pay.metadata->'manual_full_refund_evidence'->>'recorded_by_staff_id'=a."actorId"
   AND a."afterJson"->>'reservation_id'=r.id::text
   AND a."afterJson"->>'evidence_reference'=c."evidenceReference"
   AND a."afterJson"->'amount_kgs'=to_jsonb(pay."amountKgs")
   AND a."afterJson"->'external_refund_previously_completed'='true'::jsonb
   AND a."afterJson"->'funds_sent_by_platform'='false'::jsonb
   AND a."createdAt">=pay."paidAt"
   AND ((a."createdAt" AT TIME ZONE 'UTC') AT TIME ZONE p.timezone)::date=c."documentDate"
   AND NOT EXISTS(SELECT 1 FROM owner_revenue_refund_bindings b
       WHERE b."paymentId"=pay.id AND
       (b."propertyId"<>pid OR b."correctionEventId"<>cid))
 )
 SELECT CASE WHEN count(*)=1 THEN (array_agg(id))[1] ELSE NULL END FROM eligible
$$;

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


CREATE FUNCTION owner_bind_certified_refund_payments() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE c record; payment_id uuid;
BEGIN
 FOR c IN SELECT id FROM owner_revenue_correction_events
   WHERE "propertyId"=NEW."propertyId" AND id=ANY(NEW."correctionEventIds")
     AND kind='REFUND'
 LOOP
   payment_id:=owner_revenue_refund_payment_id(NEW."propertyId",c.id,NEW."reviewedById");
   IF payment_id IS NULL THEN
      RAISE EXCEPTION 'OWNER_REFUND_PAYMENT_PROOF_REQUIRED' USING ERRCODE='23514';
   END IF;
   INSERT INTO owner_revenue_refund_bindings
       ("propertyId","correctionEventId","paymentId","certificateId")
   VALUES(NEW."propertyId",c.id,payment_id,NEW.id);
 END LOOP;
 RETURN NEW;
END; $$;
CREATE TRIGGER owner_bind_certified_refund_payments
 AFTER INSERT ON owner_revenue_accounting_certifications
 FOR EACH ROW EXECUTE FUNCTION owner_bind_certified_refund_payments();

-- Proof is checked again before posting and by period coverage.
-- No payment is created or changed by these functions.

CREATE FUNCTION owner_validate_refund_binding() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE cert record;
BEGIN
 SELECT * INTO cert FROM owner_revenue_accounting_certifications
 WHERE id=NEW."certificateId" AND "propertyId"=NEW."propertyId";
 IF NOT FOUND OR NOT COALESCE(NEW."correctionEventId"=ANY(cert."correctionEventIds"),false)
   OR owner_revenue_refund_payment_id(NEW."propertyId",NEW."correctionEventId",cert."reviewedById")
       IS DISTINCT FROM NEW."paymentId" THEN
    RAISE EXCEPTION 'OWNER_REFUND_BINDING_INVALID' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER owner_validate_refund_binding
 BEFORE INSERT ON owner_revenue_refund_bindings
 FOR EACH ROW EXECUTE FUNCTION owner_validate_refund_binding();

CREATE OR REPLACE FUNCTION owner_revenue_certificate_current(c owner_revenue_accounting_certifications)
RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT owner_revenue_corrections_match_snapshot(
  c."propertyId",c."sourceEventId",c."evidenceDocumentId",c."reviewedById",
  c."taxAmountKgs",c."reductionAmountKgs",
  COALESCE(c."correctionEventIds",
    CASE WHEN c."taxCorrectionEventId" IS NULL THEN ARRAY[]::uuid[]
         ELSE ARRAY[c."taxCorrectionEventId"] END))
 AND NOT EXISTS (
   SELECT 1 FROM owner_revenue_correction_events r
   WHERE r."propertyId"=c."propertyId" AND r.id=ANY(c."correctionEventIds")
      AND r.kind='REFUND'
      AND NOT EXISTS(SELECT 1 FROM owner_revenue_refund_bindings b
        WHERE b."propertyId"=c."propertyId" AND b."certificateId"=c.id
        AND b."correctionEventId"=r.id AND b."paymentId"=
         owner_revenue_refund_payment_id(c."propertyId",r.id,c."reviewedById"))
 )
$$;
