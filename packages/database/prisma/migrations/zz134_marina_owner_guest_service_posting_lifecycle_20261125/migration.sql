-- An operational guest service and its folio must not invalidate an active
-- accounting posting. This registry contains locks only, no financial facts.
-- Retain lock keys even when an unposted task is removed.
CREATE TABLE owner_guest_service_posting_serialization (
 "propertyId" uuid NOT NULL,
 "taskId" uuid NOT NULL,
 PRIMARY KEY ("propertyId","taskId")
);

CREATE FUNCTION owner_lock_guest_service_posting(pid uuid, tid uuid) RETURNS void
LANGUAGE plpgsql VOLATILE AS $$
BEGIN
 INSERT INTO owner_guest_service_posting_serialization ("propertyId","taskId")
 VALUES (pid,tid)
 ON CONFLICT ("propertyId","taskId") DO UPDATE
 SET "taskId"=EXCLUDED."taskId";
END; $$;

CREATE FUNCTION owner_assert_guest_service_posted_proof(pid uuid, tid uuid) RETURNS void
LANGUAGE plpgsql VOLATILE AS $$
BEGIN
 IF EXISTS (
   SELECT 1 FROM owner_revenue_source_events e
   WHERE e."propertyId"=pid AND e."sourceId"=tid
     AND e."sourceType"='OTHER_SERVICE' AND e.action='APPROVE_SOURCE'
     AND owner_revenue_has_active_posting(pid,e.id)
     AND owner_guest_service_revenue_proof(pid,tid,e."serviceDate")
         IS DISTINCT FROM e."faceValueKgs"
 ) THEN
   RAISE EXCEPTION 'OWNER_GUEST_SERVICE_ACTIVE_POSTING_REQUIRES_REVERSAL'
     USING ERRCODE='23514';
 END IF;
END; $$;

CREATE FUNCTION owner_guard_guest_service_posting_proof() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE e record;
BEGIN
 IF NEW.action<>'POST' THEN RETURN NEW; END IF;
 SELECT s.* INTO e FROM owner_accounting_journal_proposals q
 JOIN owner_revenue_source_events s ON s."propertyId"=q."propertyId" AND s.id=q."sourceId"
 WHERE q."propertyId"=NEW."propertyId" AND q.id=NEW."proposalId"
   AND q."sourceType"='REVENUE_SOURCE' AND s."sourceType"='OTHER_SERVICE';
 IF FOUND THEN
   PERFORM owner_lock_guest_service_posting(e."propertyId",e."sourceId");
   IF owner_guest_service_revenue_proof(e."propertyId",e."sourceId",e."serviceDate")
        IS DISTINCT FROM e."faceValueKgs" THEN
      RAISE EXCEPTION 'REVENUE_GUEST_SERVICE_NOT_QUALIFIED' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER ac_owner_guest_service_posting_proof
 BEFORE INSERT ON owner_accounting_postings
 FOR EACH ROW EXECUTE FUNCTION owner_guard_guest_service_posting_proof();

-- AFTER mutation: proof must see the actual changed row in this transaction.
-- The real registry write serializes concurrent posting/mutation, including
-- repeatable-read transactions. Ordinary OPEN->PAID / POSTED->PAID is allowed.
CREATE FUNCTION owner_guard_guest_service_task_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='UPDATE' THEN
   IF ROW(OLD.id,OLD."propertyId",OLD."reservationId",OLD."stayId",
          OLD."serviceCode",OLD."serviceDate",OLD.status,OLD."completedAt",
          OLD."chargeKgs",OLD."chargeStatus",OLD."chargeSource")
      IS NOT DISTINCT FROM
      ROW(NEW.id,NEW."propertyId",NEW."reservationId",NEW."stayId",
          NEW."serviceCode",NEW."serviceDate",NEW.status,NEW."completedAt",
          NEW."chargeKgs",NEW."chargeStatus",NEW."chargeSource") THEN
     RETURN NEW;
   END IF;
 END IF;
 -- Every task that could have supplied an approved paid service has either
 -- a positive charge or FOLIO provenance before the attempted modification.
 IF COALESCE(OLD."chargeKgs",0)>0 OR OLD."chargeSource"='FOLIO' THEN
   PERFORM owner_lock_guest_service_posting(OLD."propertyId",OLD.id);
   PERFORM owner_assert_guest_service_posted_proof(OLD."propertyId",OLD.id);
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER owner_guest_service_task_posted_proof
 AFTER UPDATE OR DELETE ON operational_tasks
 FOR EACH ROW EXECUTE FUNCTION owner_guard_guest_service_task_mutation();

CREATE FUNCTION owner_guard_guest_service_folio_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 IF OLD."sourceType"<>'GUEST_SERVICE' OR OLD."sourceId" IS NULL THEN
   IF TG_OP='DELETE' THEN RETURN OLD; END IF;
   RETURN NEW;
 END IF;
 IF TG_OP='UPDATE' THEN
   IF ROW(OLD.id,OLD."propertyId",OLD."reservationId",OLD."stayId",OLD."guestId",
          OLD."sourceType",OLD."sourceId",OLD.code,OLD."amountKgs",OLD.status,OLD."serviceDate")
      IS NOT DISTINCT FROM
      ROW(NEW.id,NEW."propertyId",NEW."reservationId",NEW."stayId",NEW."guestId",
          NEW."sourceType",NEW."sourceId",NEW.code,NEW."amountKgs",NEW.status,NEW."serviceDate") THEN
     RETURN NEW;
   END IF;
 END IF;
 PERFORM owner_lock_guest_service_posting(OLD."propertyId",OLD."sourceId");
 PERFORM owner_assert_guest_service_posted_proof(OLD."propertyId",OLD."sourceId");
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END; $$;
CREATE TRIGGER owner_guest_service_folio_posted_proof
 AFTER UPDATE OR DELETE ON guest_folio_charges
 FOR EACH ROW EXECUTE FUNCTION owner_guard_guest_service_folio_mutation();

-- Refuse an already inconsistent active source, without modifying history.
DO $$ DECLARE e record; BEGIN
 FOR e IN SELECT DISTINCT "propertyId","sourceId" FROM owner_revenue_source_events
     WHERE "sourceType"='OTHER_SERVICE' AND action='APPROVE_SOURCE'
 LOOP
   PERFORM owner_assert_guest_service_posted_proof(e."propertyId",e."sourceId");
 END LOOP;
END; $$;
