ALTER TYPE "StaffRole" ADD VALUE IF NOT EXISTS 'AGENT';

ALTER TABLE staff_users
  ADD COLUMN IF NOT EXISTS "bookingAgentId" UUID;

CREATE INDEX IF NOT EXISTS "staff_users_bookingAgentId_idx"
  ON staff_users("bookingAgentId");

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'staff_users_bookingAgentId_fkey'
  ) THEN
    ALTER TABLE staff_users
      ADD CONSTRAINT "staff_users_bookingAgentId_fkey"
      FOREIGN KEY ("bookingAgentId") REFERENCES booking_agents(id)
      ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;
END $$;
