-- Disposable CI price-version assertions. Requires seed fixtures + preview 0003.
BEGIN;
DO $test$
DECLARE
  v1 uuid;
BEGIN
  SELECT id INTO v1 FROM flex_price_versions WHERE sku='BASE_PMS' AND version=1;
  IF v1 IS NULL THEN RAISE EXCEPTION 'Missing BASE_PMS fixture'; END IF;

  -- A backdated price may not supersede a newer scheduled version.
  BEGIN
    INSERT INTO flex_price_versions(sku,version,monthly_price,currency,valid_from,valid_to)
      VALUES('BASE_PMS',3,15000.00,'KGS','2026-11-01','2026-12-01');
    RAISE EXCEPTION 'CI_FAILURE_BACKDATED_VERSION_ACCEPTED';
  EXCEPTION WHEN check_violation THEN
    IF SQLERRM != 'FLEX_PRICE_VERSION_NOT_MONOTONIC' THEN RAISE; END IF;
  END;

  -- Open-ended current prices can receive a future version without changing history.
  INSERT INTO flex_price_versions(sku,version,monthly_price,currency,valid_from)
    VALUES('AI_ASSISTANT',2,5000.00,'KGS','2027-01-01T00:00:00+00');
  IF (SELECT monthly_price FROM flex_price_versions
      WHERE sku='AI_ASSISTANT' AND valid_from<='2027-02-01'
      ORDER BY valid_from DESC,version DESC LIMIT 1) <> 5000.00 THEN
    RAISE EXCEPTION 'CI_FAILURE_PRICE_ROLLOVER';
  END IF;

  -- An already referenced/issued historical price cannot change retrospectively.
  BEGIN
    UPDATE flex_price_versions SET monthly_price=1.00 WHERE id=v1;
    RAISE EXCEPTION 'CI_FAILURE_PRICE_HISTORY_REWRITTEN';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM != 'FLEX_HISTORY_IS_APPEND_ONLY' THEN RAISE; END IF;
  END;

  -- Canonical version is the one with greatest effective start at a given time.
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
