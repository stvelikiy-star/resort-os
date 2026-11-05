-- Dedicated planning date for housekeeping, separate from guest-service context.
ALTER TABLE operational_tasks ADD COLUMN "scheduledFor" date;

-- Preserve existing service-context restrictions; keep historical housekeeping tasks intact.
DROP INDEX IF EXISTS operational_tasks_housekeeping_schedule_unique;
CREATE UNIQUE INDEX operational_tasks_housekeeping_schedule_unique
  ON operational_tasks ("stayId", "scheduledFor")
  WHERE source = 'HOUSEKEEPING_SCHEDULE' AND type = 'HOUSEKEEPING';

ALTER TABLE operational_tasks ADD CONSTRAINT operational_tasks_housekeeping_schedule_date_check
  CHECK (source <> 'HOUSEKEEPING_SCHEDULE' OR (type = 'HOUSEKEEPING' AND "stayId" IS NOT NULL AND "scheduledFor" IS NOT NULL));
