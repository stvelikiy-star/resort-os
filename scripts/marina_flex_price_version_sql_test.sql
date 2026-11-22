-- Disposable CI price-version assertions. Requires seed fixtures + preview 0003.
BEGIN;
DO $test$
DECLARE
  v1 uuid;
BEGIN
  SELECT id INTO v1 FROM flex_price_versions WHERE sku='BASE_PMS' AND version=1;
  IF v1 IS NULL THEN RAISE EXCEPTION 'Missing BASE_PMS fixture'; END IF;

  -- Overlapping price periods for same SKU must be refused, even at new version.
  BEGIN
    INSERT INTO flex_price_versions(sku,version,monthly_price,currency,valid_from,valid_to)
      VALUES('BASE_PMS',3,15000.00,'KGS','2026-11-01','2026-12-01');
    RAISE EXCEPTION 'CI_FAILURE_OVERLAPPING_VERSION_ACCEPTED';
  EXCEPTION WHEN check_violation THEN
    IF SQLERRM != 'FLEX_PRICE_VERSIONS_OVERLAP' THEN RAISE; END IF;
  END;

  -- An already referenced/issued historical price cannot change retrospectively.
  BEGIN
    UPDATE flex_price_versions SET monthly_price=1.00 WHERE id=v1;
    RAISE EXCEPTION 'CI_FAILURE_PRICE_HISTORY_REWRITTEN';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM != 'FLEX_HISTORY_IS_APPEND_ONLY' THEN RAISE; END IF;
  END;

  -- Exactly one active version at a given time for each SKU.
  IF (SELECT count(*) FROM flex_price_versions
    WHERE sku='BASE_PMS' AND valid_from<='2026-11-22'
    AND (valid_to IS NULL OR valid_to>'2026-11-22')) <> 1 THEN
    RAISE EXCEPTION 'CI_FAILURE_PRICE_VERSION_AMBIGUOUS';
  END IF;

  IF (SELECT count(*) FROM flex_price_versions WHERE sku='BASE_PMS') <> 2 THEN
    RAISE EXCEPTION 'CI_FAILURE_PRICE_VERSION_INTEGRITY';
  END IF;
END
$test$;
ROLLBACK;
