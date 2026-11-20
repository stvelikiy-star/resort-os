-- MARINA SMART: split dining staff into server-enforced cook and waiter roles.
-- DINING_STAFF remains in the enum for backwards-compatible data reads, but is
-- intentionally rejected by the kitchen/dining route guards after this migration.
ALTER TYPE "StaffRole" ADD VALUE IF NOT EXISTS 'COOK';
ALTER TYPE "StaffRole" ADD VALUE IF NOT EXISTS 'WAITER';
