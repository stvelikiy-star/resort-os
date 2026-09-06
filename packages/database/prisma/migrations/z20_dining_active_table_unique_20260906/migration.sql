-- A physical dining table may belong to only one live guest seating session.
-- z14 protected SEATED only, which still allowed multiple WAITING sessions on
-- the same table and a WAITING + SEATED collision. Fail closed instead of
-- silently deleting ambiguous operational history during migration.
DO $$
DECLARE
    duplicate_count integer;
BEGIN
    SELECT count(*) INTO duplicate_count
    FROM (
        SELECT "tableId"
        FROM dining_table_sessions
        WHERE status IN ('WAITING','SEATED')
        GROUP BY "tableId"
        HAVING count(*) > 1
    ) duplicates;

    IF duplicate_count > 0 THEN
        RAISE EXCEPTION 'DINING_ACTIVE_TABLE_DUPLICATES: % table(s) have multiple WAITING/SEATED sessions; resolve explicitly before migration', duplicate_count;
    END IF;
END;
$$;

DROP INDEX IF EXISTS dining_table_sessions_seated_table_key;
CREATE UNIQUE INDEX dining_table_sessions_active_table_key
    ON dining_table_sessions ("tableId")
    WHERE status IN ('WAITING','SEATED');
