-- Additive, dormant evidence model. No application write route is enabled.
-- Retain the original receipt and keep refund cash separate from revenue.
CREATE TABLE owner_partial_refund_events (
 id uuid PRIMARY KEY,
 "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE RESTRICT,
 "paymentId" uuid NOT NULL REFERENCES payments(id) ON DELETE RESTRICT,
 "reservationId" uuid NOT NULL REFERENCES reservations(id) ON DELETE RESTRICT,
 "amountKgs" integer NOT NULL CHECK ("amountKgs">0),
 "refundedAt" timestamptz NOT NULL,
 "evidenceDocumentId" uuid NOT NULL,
 "evidenceReference" text NOT NULL UNIQUE CHECK(length(btrim("evidenceReference")) BETWEEN 8 AND 180),
 "recordedById" uuid NOT NULL REFERENCES staff_users(id) ON DELETE RESTRICT,
 "reviewedById" uuid NOT NULL REFERENCES staff_users(id) ON DELETE RESTRICT,
 reason text NOT NULL CHECK(length(btrim(reason)) BETWEEN 8 AND 500),
 "createdAt" timestamptz NOT NULL DEFAULT now(),
 CHECK ("recordedById"<>"reviewedById"),
 FOREIGN KEY ("propertyId","evidenceDocumentId")
 REFERENCES owner_revenue_evidence_documents ("propertyId",id) ON DELETE RESTRICT
);
CREATE INDEX owner_partial_refund_payment_idx ON owner_partial_refund_events ("paymentId");
CREATE INDEX owner_partial_refund_period_idx ON owner_partial_refund_events ("propertyId","refundedAt");
CREATE FUNCTION owner_validate_partial_refund_event() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE pay record; doc record; accumulated bigint;
BEGIN
 -- Deliberately disabled until all consumers use the refund-aware read model.
 IF current_setting('marina.partial_refund_evidence_qa',true) IS DISTINCT FROM 'on' THEN
    RAISE EXCEPTION 'PARTIAL_REFUND_WRITE_NOT_RELEASED' USING ERRCODE='23514';
 END IF;
 SELECT p.*,r."propertyId" AS pid,prop.timezone INTO pay
 FROM payments p JOIN reservations r ON r.id=p."reservationId"
 JOIN properties prop ON prop.id=r."propertyId"
 WHERE p.id=NEW."paymentId" AND r.id=NEW."reservationId"
   AND r."propertyId"=NEW."propertyId" FOR UPDATE OF p;
 IF NOT FOUND OR pay.provider IS DISTINCT FROM 'MANAGER_MANUAL'
   OR pay.status<>'RECEIVED' OR pay."paidAt" IS NULL
   OR NEW."refundedAt"<(pay."paidAt" AT TIME ZONE 'UTC')
   OR NEW."refundedAt">now()
   OR NOT EXISTS(SELECT 1 FROM staff_users s WHERE s.id=NEW."recordedById"
        AND s."propertyId"=NEW."propertyId" AND s."isActive" AND s.role IN ('OWNER','MANAGER'))
   OR NOT EXISTS(SELECT 1 FROM staff_users s WHERE s.id=NEW."reviewedById"
        AND s."propertyId"=NEW."propertyId" AND s."isActive" AND s.role='OWNER')
 THEN RAISE EXCEPTION 'PARTIAL_REFUND_PAYMENT_OR_ACTOR_INVALID' USING ERRCODE='23514'; END IF;
 SELECT * INTO doc FROM owner_revenue_evidence_documents d
 WHERE d."propertyId"=NEW."propertyId" AND d.id=NEW."evidenceDocumentId";
 IF NOT FOUND OR doc."uploadedById"=NEW."reviewedById"
   OR doc."documentReference" IS DISTINCT FROM NEW."evidenceReference"
   OR doc."documentDate" IS DISTINCT FROM (NEW."refundedAt" AT TIME ZONE pay.timezone)::date
   OR encode(digest(doc.content,'sha256'),'hex') IS DISTINCT FROM doc.sha256
 THEN RAISE EXCEPTION 'PARTIAL_REFUND_DOCUMENT_INVALID' USING ERRCODE='23514'; END IF;
 -- Write to the locked payment row to serialize concurrent inserts even
 -- at repeatable read. Original amount/status/receipt timestamp unchanged.
 UPDATE payments SET "updatedAt"="updatedAt" WHERE id=NEW."paymentId";
 SELECT COALESCE(sum("amountKgs"),0) INTO accumulated
 FROM owner_partial_refund_events WHERE "paymentId"=NEW."paymentId";
 IF accumulated+NEW."amountKgs">pay."amountKgs" THEN
   RAISE EXCEPTION 'PARTIAL_REFUND_EXCEEDS_RECEIPT' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER owner_validate_partial_refund_event BEFORE INSERT
 ON owner_partial_refund_events FOR EACH ROW EXECUTE FUNCTION owner_validate_partial_refund_event();
CREATE TRIGGER owner_partial_refund_events_immutable BEFORE UPDATE OR DELETE
 ON owner_partial_refund_events FOR EACH ROW EXECUTE FUNCTION reject_owner_accounting_journal_mutation();

CREATE FUNCTION owner_guard_partial_refund_payment() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM owner_partial_refund_events e WHERE e."paymentId"=OLD.id) THEN
   IF TG_OP='DELETE' THEN
     RAISE EXCEPTION 'PARTIAL_REFUND_RECEIPT_IMMUTABLE' USING ERRCODE='23514';
   END IF;
   IF ROW(NEW.id,NEW."reservationId",NEW."requestId",NEW."amountKgs",NEW.status,NEW.provider,NEW."paidAt",NEW.method)
      IS DISTINCT FROM ROW(OLD.id,OLD."reservationId",OLD."requestId",OLD."amountKgs",OLD.status,OLD.provider,OLD."paidAt",OLD.method) THEN
     RAISE EXCEPTION 'PARTIAL_REFUND_RECEIPT_IMMUTABLE' USING ERRCODE='23514';
   END IF;
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER owner_guard_partial_refund_payment BEFORE UPDATE OR DELETE ON payments
 FOR EACH ROW EXECUTE FUNCTION owner_guard_partial_refund_payment();

CREATE VIEW owner_reservation_payment_balances AS
 SELECT p.id AS "paymentId",r."propertyId",r.id AS "reservationId",
    p."amountKgs" AS "originalAmountKgs",
    CASE WHEN p.status='REFUNDED' THEN p."amountKgs"::bigint
         ELSE COALESCE(e.refunded,0) END AS "refundedKgs",
    CASE WHEN p.status='RECEIVED' THEN p."amountKgs"::bigint-COALESCE(e.refunded,0)
         ELSE 0::bigint END AS "remainingReceivedKgs",
    p.status AS "receiptStatus"
 FROM payments p JOIN reservations r ON r.id=p."reservationId"
 LEFT JOIN (SELECT "paymentId",sum("amountKgs") AS refunded
            FROM owner_partial_refund_events GROUP BY "paymentId") e
 ON e."paymentId"=p.id;
