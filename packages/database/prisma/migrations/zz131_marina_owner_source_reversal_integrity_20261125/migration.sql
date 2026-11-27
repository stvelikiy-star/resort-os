-- Serialize accounting posting and source cancellation for each tenant/source.
-- Existing source and journal rows remain immutable. This is a lock registry,
-- not a financial ledger or a new source of financial amounts.
CREATE TABLE owner_revenue_posting_serialization (
 "propertyId" uuid NOT NULL,
 "sourceEventId" uuid NOT NULL,
 PRIMARY KEY ("propertyId","sourceEventId"),
 FOREIGN KEY ("propertyId","sourceEventId")
 REFERENCES owner_revenue_source_events ("propertyId",id) ON DELETE RESTRICT
);

CREATE FUNCTION owner_lock_revenue_posting(pid uuid, sid uuid) RETURNS void
LANGUAGE plpgsql VOLATILE AS $$
BEGIN
 -- A real row write, not only an advisory lock: concurrent repeatable-read
 -- writers must serialize or fail with a serialization error.
 INSERT INTO owner_revenue_posting_serialization ("propertyId","sourceEventId")
 VALUES (pid,sid)
 ON CONFLICT ("propertyId","sourceEventId") DO UPDATE
 SET "sourceEventId"=EXCLUDED."sourceEventId";
END;
$$;

CREATE FUNCTION owner_revenue_has_active_posting(pid uuid, sid uuid)
RETURNS boolean LANGUAGE sql VOLATILE AS $$
 SELECT EXISTS (
   SELECT 1 FROM owner_accounting_journal_proposals q
   JOIN owner_accounting_postings p
     ON p."propertyId"=q."propertyId" AND p."proposalId"=q.id
   WHERE q."propertyId"=pid AND q."sourceType"='REVENUE_SOURCE'
     AND q."sourceId"=sid AND p.action='POST'
     AND NOT EXISTS (
       SELECT 1 FROM owner_accounting_postings r
       WHERE r."propertyId"=p."propertyId"
         AND r."reversesId"=p.id AND r.action='REVERSE'
     )
 );
$$;

-- Refuse to install over inconsistent existing data. Never silently rewrite
-- or reverse historical postings.
DO $$
BEGIN
 IF EXISTS (
   SELECT 1 FROM owner_revenue_source_events r
   WHERE r.action='REVERSE_SOURCE'
     AND owner_revenue_has_active_posting(r."propertyId",r."reversesId")
 ) THEN
   RAISE EXCEPTION 'OWNER_REVENUE_EXISTING_ACTIVE_POSTING_ON_REVERSED_SOURCE';
 END IF;
END;
$$;

CREATE FUNCTION owner_guard_source_reversal_after_posting() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.action='REVERSE_SOURCE' THEN
   PERFORM owner_lock_revenue_posting(NEW."propertyId",NEW."reversesId");
   IF owner_revenue_has_active_posting(NEW."propertyId",NEW."reversesId") THEN
     RAISE EXCEPTION 'OWNER_REVENUE_ACTIVE_POSTING_REQUIRES_REVERSAL'
       USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER aa_owner_source_reversal_posting_guard
 BEFORE INSERT ON owner_revenue_source_events
 FOR EACH ROW EXECUTE FUNCTION owner_guard_source_reversal_after_posting();

CREATE FUNCTION owner_guard_posting_source_lifecycle() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE sid uuid;
BEGIN
 SELECT q."sourceId" INTO sid FROM owner_accounting_journal_proposals q
 WHERE q."propertyId"=NEW."propertyId" AND q.id=NEW."proposalId"
   AND q."sourceType"='REVENUE_SOURCE';
 IF sid IS NULL THEN RETURN NEW; END IF;
 PERFORM owner_lock_revenue_posting(NEW."propertyId",sid);
 IF NEW.action='POST' AND EXISTS (
   SELECT 1 FROM owner_revenue_source_events r
   WHERE r."propertyId"=NEW."propertyId" AND r."reversesId"=sid
     AND r.action='REVERSE_SOURCE'
 ) THEN
   RAISE EXCEPTION 'OWNER_REVENUE_SOURCE_ALREADY_REVERSED'
     USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END;
$$;
-- Alphabetical order makes this serialization guard run before the existing
-- validation trigger. Both original posting and exact reversal acquire it.
CREATE TRIGGER aa_owner_posting_source_lifecycle_guard
 BEFORE INSERT ON owner_accounting_postings
 FOR EACH ROW EXECUTE FUNCTION owner_guard_posting_source_lifecycle();
