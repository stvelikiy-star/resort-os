-- FLEX preview 0003: enforce deterministic, immutable commercial price versions.
-- Isolated QA only, after 0001 + 0002. Does NOT change PMS prices or schema.
BEGIN;

-- Versions are append-only. A newer version supersedes an earlier open-ended
-- one at its valid_from; no rewriting of previous price snapshots is needed.
-- This avoids the impossible demand to know an indefinite version's end-date.
-- Canonical current price = greatest valid_from <= as_of (then version).
CREATE FUNCTION flex_price_version_period_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  -- Lock the SKU to serialize two concurrent price publications.
  PERFORM 1 FROM flex_skus WHERE sku=NEW.sku FOR UPDATE;
  IF EXISTS (
    SELECT 1 FROM flex_price_versions old
    WHERE old.sku=NEW.sku
      AND (old.version >= NEW.version OR old.valid_from >= NEW.valid_from)
  ) THEN
    RAISE EXCEPTION 'FLEX_PRICE_VERSION_NOT_MONOTONIC' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;

CREATE UNIQUE INDEX flex_price_version_effective_start
 ON flex_price_versions(sku,valid_from);

CREATE TRIGGER flex_price_version_unique_time
BEFORE INSERT ON flex_price_versions
FOR EACH ROW EXECUTE FUNCTION flex_price_version_period_guard();

-- Price snapshot (including period) is not editable once created. A future
-- version supersedes earlier prices by a strictly later effective date.
CREATE TRIGGER flex_price_version_append_only
BEFORE UPDATE OR DELETE ON flex_price_versions
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();

COMMIT;
