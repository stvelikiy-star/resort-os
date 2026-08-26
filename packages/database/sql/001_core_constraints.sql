-- Resort OS critical PostgreSQL constraints not expressible in Prisma schema.
-- Apply after Prisma migration.

CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE "rate_periods"
  ADD CONSTRAINT rate_period_valid_dates CHECK ("validFrom" <= "validTo"),
  ADD CONSTRAINT rate_period_nonnegative_price CHECK ("priceKgs" >= 0);

ALTER TABLE "reservation_requests"
  ADD CONSTRAINT reservation_request_valid_dates CHECK ("checkIn" < "checkOut"),
  ADD CONSTRAINT reservation_request_positive_adults CHECK (adults > 0),
  ADD CONSTRAINT reservation_request_nonnegative_children CHECK (children >= 0);

ALTER TABLE "reservations"
  ADD CONSTRAINT reservation_valid_dates CHECK ("checkIn" < "checkOut"),
  ADD CONSTRAINT reservation_positive_adults CHECK (adults > 0),
  ADD CONSTRAINT reservation_nonnegative_children CHECK (children >= 0),
  ADD CONSTRAINT reservation_nonnegative_total CHECK ("totalKgs" >= 0);

ALTER TABLE "inventory_blocks"
  ADD CONSTRAINT inventory_block_valid_dates CHECK ("startDate" < "endDate");

-- One room cannot have two active inventory blocks for overlapping nights.
-- This is the primary database-level double-booking protection.
ALTER TABLE "inventory_blocks"
  ADD CONSTRAINT no_overlapping_active_room_blocks
  EXCLUDE USING gist (
    "roomId" WITH =,
    daterange("startDate", "endDate", '[)') WITH &&
  ) WHERE (active = true);

ALTER TABLE "payments"
  ADD CONSTRAINT payment_positive_amount CHECK ("amountKgs" > 0),
  ADD CONSTRAINT payment_has_context CHECK ("requestId" IS NOT NULL OR "reservationId" IS NOT NULL);

-- Operational task creation can be initiated from several manager/automation
-- surfaces. Before installing the invariant, fail closed if historical data
-- already violates it. Never delete or merge tasks automatically during a
-- migration: operators must reconcile the conflicting active records first.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM operational_tasks
    WHERE "roomId" IS NOT NULL
      AND type IN ('HOUSEKEEPING', 'MAINTENANCE')
      AND status IN ('OPEN', 'IN_PROGRESS', 'IN_INSPECTION')
    GROUP BY "roomId", type
    HAVING count(*) > 1
  ) THEN
    RAISE EXCEPTION 'active operational task duplicates exist; reconcile same-room/same-type HOUSEKEEPING or MAINTENANCE tasks before applying the invariant';
  END IF;
END
$$;

-- The database is the final concurrency boundary: for a room there may be at
-- most one active HOUSEKEEPING task and one active MAINTENANCE task.
-- Completed/cancelled history remains unlimited, and GUEST_REQUEST is not
-- constrained because multiple independent guest requests may legitimately
-- be active for the same room.
CREATE UNIQUE INDEX active_room_operational_task_type_unique
  ON operational_tasks ("roomId", type)
  WHERE "roomId" IS NOT NULL
    AND type IN ('HOUSEKEEPING', 'MAINTENANCE')
    AND status IN ('OPEN', 'IN_PROGRESS', 'IN_INSPECTION');
