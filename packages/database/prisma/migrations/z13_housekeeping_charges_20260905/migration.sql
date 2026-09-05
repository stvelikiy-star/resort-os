-- Explicit commercial metadata for operational service tasks. A task is not a
-- Payment; chargeStatus=PENDING means the amount belongs to the guest folio work
-- queue and still requires an explicit financial posting/collection workflow.
ALTER TABLE operational_tasks ADD COLUMN "chargeKgs" integer;
ALTER TABLE operational_tasks ADD COLUMN "chargeStatus" text NOT NULL DEFAULT 'NONE';
ALTER TABLE operational_tasks ADD COLUMN "chargeSource" text;
ALTER TABLE operational_tasks ADD CONSTRAINT operational_tasks_charge_nonnegative CHECK ("chargeKgs" IS NULL OR "chargeKgs" >= 0);
ALTER TABLE operational_tasks ADD CONSTRAINT operational_tasks_charge_status_check CHECK ("chargeStatus" IN ('NONE','PENDING','POSTED','PAID','WAIVED','CANCELLED'));

-- One scheduled housekeeping task per stay/date. Cancellation means a deliberate
-- operational decision; reopening the app must not silently recreate it.
CREATE UNIQUE INDEX operational_tasks_housekeeping_schedule_unique
ON operational_tasks ("stayId", "serviceDate")
WHERE source='HOUSEKEEPING_SCHEDULE' AND "serviceCode"='SCHEDULED_HOUSEKEEPING';
