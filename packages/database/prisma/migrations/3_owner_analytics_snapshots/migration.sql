-- Daily owner-management snapshots for real booking pickup / pace analysis.
-- Snapshot payloads are derived from canonical Resort Core facts; they are not a second reservation or finance source of truth.

CREATE TABLE IF NOT EXISTS owner_analytics_snapshots (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    "snapshotDate" date NOT NULL,
    "horizonDays" integer NOT NULL,
    "payloadJson" jsonb NOT NULL,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT owner_analytics_snapshots_property_fkey
        FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT owner_analytics_snapshots_horizon_check
        CHECK ("horizonDays" BETWEEN 1 AND 367),
    CONSTRAINT owner_analytics_snapshots_payload_object_check
        CHECK (jsonb_typeof("payloadJson") = 'object')
);

CREATE UNIQUE INDEX IF NOT EXISTS owner_analytics_snapshots_property_date_key
    ON owner_analytics_snapshots ("propertyId", "snapshotDate");

CREATE INDEX IF NOT EXISTS owner_analytics_snapshots_property_date_idx
    ON owner_analytics_snapshots ("propertyId", "snapshotDate" DESC);

COMMENT ON TABLE owner_analytics_snapshots IS
    'Daily immutable-by-date management snapshots derived from Resort Core for booking pickup/pace analysis; current operational truth remains reservations/inventory/payments.';
