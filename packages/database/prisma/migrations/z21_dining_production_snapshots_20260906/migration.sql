-- Immutable Chef OS production snapshots.
-- A snapshot freezes the entitlement-derived production count for one meal/date.
-- Later entitlement edits are exposed as deltas; the frozen baseline is never
-- silently rewritten. This table does not represent a Payment or guest charge.

CREATE TABLE dining_production_snapshots (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    "serviceDate" date NOT NULL,
    "mealType" text NOT NULL,
    "adultPortions" integer NOT NULL DEFAULT 0,
    "childPortions" integer NOT NULL DEFAULT 0,
    "entitlementCount" integer NOT NULL DEFAULT 0,
    "sourceFingerprint" text NOT NULL,
    "sourceMaxUpdatedAt" timestamptz,
    "cutoffAt" timestamptz,
    "capturedAt" timestamptz NOT NULL DEFAULT now(),
    "capturedById" uuid,
    reason text NOT NULL DEFAULT 'CUTOFF',
    forced boolean NOT NULL DEFAULT false,
    notes text,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT dining_production_snapshots_property_fkey
      FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT dining_production_snapshots_captured_by_fkey
      FOREIGN KEY ("capturedById") REFERENCES staff_users(id) ON DELETE SET NULL,
    CONSTRAINT dining_production_snapshots_meal_check
      CHECK ("mealType" IN ('BREAKFAST','LUNCH','DINNER')),
    CONSTRAINT dining_production_snapshots_adult_check
      CHECK ("adultPortions" BETWEEN 0 AND 10000),
    CONSTRAINT dining_production_snapshots_child_check
      CHECK ("childPortions" BETWEEN 0 AND 10000),
    CONSTRAINT dining_production_snapshots_entitlement_count_check
      CHECK ("entitlementCount" BETWEEN 0 AND 10000),
    CONSTRAINT dining_production_snapshots_fingerprint_check
      CHECK (length("sourceFingerprint") = 64),
    CONSTRAINT dining_production_snapshots_reason_check
      CHECK (reason IN ('CUTOFF','MANAGER_FORCE_BEFORE_CUTOFF','MANAGER_FORCE_TIME_UNCONFIGURED'))
);

CREATE UNIQUE INDEX dining_production_snapshots_property_day_meal_key
  ON dining_production_snapshots ("propertyId", "serviceDate", "mealType");

CREATE INDEX dining_production_snapshots_property_date_idx
  ON dining_production_snapshots ("propertyId", "serviceDate", "capturedAt");
