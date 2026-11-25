BEGIN;
ALTER TABLE flex_tariff_package_versions
 ADD COLUMN commercial_policy_version integer REFERENCES flex_commercial_policy_versions(version),
 ADD COLUMN term_months integer CHECK (term_months IN (1,3,6,12)),
 ADD COLUMN period_start date,
 ADD COLUMN period_end_exclusive date,
 ADD COLUMN subscription_term_total numeric(18,2),
 ADD COLUMN implementation_total numeric(18,2),
 ADD CONSTRAINT flex_package_term_snapshot_check CHECK (
 (commercial_policy_version IS NULL AND term_months IS NULL AND period_start IS NULL AND period_end_exclusive IS NULL AND subscription_term_total IS NULL AND implementation_total IS NULL)
 OR (commercial_policy_version IS NOT NULL AND term_months IS NOT NULL AND period_start IS NOT NULL AND period_end_exclusive IS NOT NULL AND period_end_exclusive > period_start AND subscription_term_total IS NOT NULL AND subscription_term_total >= 0 AND implementation_total IS NOT NULL AND implementation_total >= 0)
 );
COMMIT;
