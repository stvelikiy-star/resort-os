-- MY STAY in-stay housekeeping/maintenance tasks need to remain bound to the
-- active reservation without becoming generic GUEST_REQUEST records.
--
-- Migration 2 deliberately restricted structured service metadata to
-- GUEST_REQUEST. MY STAY adds a narrower exception: HOUSEKEEPING and
-- MAINTENANCE may carry reservationId only. serviceCode/serviceDate/serviceTime
-- remain restricted to GUEST_REQUEST, preserving the original domain boundary.

ALTER TABLE operational_tasks
    DROP CONSTRAINT IF EXISTS operational_tasks_service_context_type_check;

ALTER TABLE operational_tasks
    ADD CONSTRAINT operational_tasks_service_context_type_check
    CHECK (
        (
            "serviceCode" IS NULL
            AND "serviceDate" IS NULL
            AND "serviceTime" IS NULL
            AND (
                "reservationId" IS NULL
                OR type IN ('HOUSEKEEPING', 'MAINTENANCE', 'GUEST_REQUEST')
            )
        )
        OR type = 'GUEST_REQUEST'
    );

COMMENT ON CONSTRAINT operational_tasks_service_context_type_check ON operational_tasks IS
    'GUEST_REQUEST may carry full service context; in-stay HOUSEKEEPING/MAINTENANCE may carry reservationId only.';
