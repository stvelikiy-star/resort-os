-- Structured guest-service context for existing OperationalTask/GUEST_REQUEST.
-- This does not create a second booking or finance source of truth.
-- Service requests remain operational tasks; accommodation pricing/payment stays in Resort Core.

ALTER TABLE operational_tasks
    ADD COLUMN IF NOT EXISTS "reservationId" uuid,
    ADD COLUMN IF NOT EXISTS "serviceCode" text,
    ADD COLUMN IF NOT EXISTS "serviceDate" date,
    ADD COLUMN IF NOT EXISTS "serviceTime" text;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'operational_tasks_reservationId_fkey'
    ) THEN
        ALTER TABLE operational_tasks
            ADD CONSTRAINT "operational_tasks_reservationId_fkey"
            FOREIGN KEY ("reservationId") REFERENCES reservations(id) ON DELETE SET NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'operational_tasks_service_context_type_check'
    ) THEN
        ALTER TABLE operational_tasks
            ADD CONSTRAINT operational_tasks_service_context_type_check
            CHECK (
                ("serviceCode" IS NULL AND "serviceDate" IS NULL AND "serviceTime" IS NULL AND "reservationId" IS NULL)
                OR type = 'GUEST_REQUEST'
            );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'operational_tasks_service_time_check'
    ) THEN
        ALTER TABLE operational_tasks
            ADD CONSTRAINT operational_tasks_service_time_check
            CHECK ("serviceTime" IS NULL OR "serviceTime" ~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$');
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS "operational_tasks_reservationId_status_idx"
    ON operational_tasks ("reservationId", status);

CREATE INDEX IF NOT EXISTS "operational_tasks_propertyId_serviceCode_status_serviceDate_idx"
    ON operational_tasks ("propertyId", "serviceCode", status, "serviceDate");

COMMENT ON COLUMN operational_tasks."reservationId" IS
    'Optional Reservation context for a structured guest-service GUEST_REQUEST; validated against the task property by Core.';
COMMENT ON COLUMN operational_tasks."serviceCode" IS
    'Controlled Three Crowns guest-service code; operational metadata only, never a price source.';
