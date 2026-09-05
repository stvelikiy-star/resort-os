-- dining_table_sessions is authoritative for live guest seating. Legacy kitchen
-- order completion must never make a table AVAILABLE while that guest is still
-- WAITING/SEATED. The trigger is deliberately narrow and only corrects an
-- attempted AVAILABLE transition.
CREATE OR REPLACE FUNCTION guard_active_dining_table_status()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    active_status text;
BEGIN
    IF NEW.status <> 'AVAILABLE' OR NEW.id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT ds.status INTO active_status
    FROM dining_table_sessions ds
    WHERE ds."tableId" = NEW.id
      AND ds.status IN ('SEATED','WAITING')
    ORDER BY CASE ds.status WHEN 'SEATED' THEN 0 ELSE 1 END, ds."createdAt" DESC
    LIMIT 1;

    IF active_status = 'SEATED' THEN
        NEW.status := 'OCCUPIED';
    ELSIF active_status = 'WAITING' THEN
        NEW.status := 'RESERVED';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS kitchen_tables_active_session_guard ON kitchen_tables;
CREATE TRIGGER kitchen_tables_active_session_guard
BEFORE UPDATE OF status ON kitchen_tables
FOR EACH ROW
EXECUTE FUNCTION guard_active_dining_table_status();
