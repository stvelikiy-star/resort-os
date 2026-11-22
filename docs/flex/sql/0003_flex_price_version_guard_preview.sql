-- FLEX preview 0003: enforce deterministic, immutable commercial price versions.
-- Isolated QA only, after 0001 + 0002. Does NOT change PMS prices or schema.
BEGIN;

CREATE FUNCTION flex_price_version_period_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  -- Serialize edits for the same commercial SKU under concurrent transactions.
  PERFORM 1 FROM flex_skus WHERE sku=NEW.sku FOR UPDATE;
  IF EXISTS (
    SELECT 1 FROM flex_price_versions old
    WHERE old.sku=NEW.sku AND old.id <> NEW.id
      AND tstzrange(old.valid_from,COALESCE(old.valid_to,'infinity'::timestamptz),'[)')
          && tstzrange(NEW.valid_from,COALESCE(NEW.valid_to,'infinity'::timestamptz),'[)')
  ) THEN
    RAISE EXCEPTION 'FLEX_PRICE_VERSIONS_OVERLAP' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER flex_price_version_unique_time
BEFORE INSERT ON flex_price_versions
FOR EACH ROW EXECUTE FUNCTION flex_price_version_period_guard();

-- Price snapshot (including period) is not editable once created. A future
-- version must be inserted with non-overlapping effective dates.
CREATE TRIGGER flex_price_version_append_only
BEFORE UPDATE OR DELETE ON flex_price_versions
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();

COMMIT;
