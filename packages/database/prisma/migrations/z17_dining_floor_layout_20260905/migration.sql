-- Visual Dining Floor metadata. Positions are normalized percentages so the same
-- layout works on desktop/tablet/mobile without storing device-specific pixels.
ALTER TABLE kitchen_tables ADD COLUMN "zoneLabel" text NOT NULL DEFAULT 'Основной зал';
ALTER TABLE kitchen_tables ADD COLUMN "floorX" numeric(5,2);
ALTER TABLE kitchen_tables ADD COLUMN "floorY" numeric(5,2);
ALTER TABLE kitchen_tables ADD COLUMN "floorShape" text NOT NULL DEFAULT 'ROUND';

ALTER TABLE kitchen_tables
    ADD CONSTRAINT kitchen_tables_floor_x_check CHECK ("floorX" IS NULL OR ("floorX" >= 0 AND "floorX" <= 100));
ALTER TABLE kitchen_tables
    ADD CONSTRAINT kitchen_tables_floor_y_check CHECK ("floorY" IS NULL OR ("floorY" >= 0 AND "floorY" <= 100));
ALTER TABLE kitchen_tables
    ADD CONSTRAINT kitchen_tables_floor_shape_check CHECK ("floorShape" IN ('ROUND','SQUARE','RECTANGLE'));

-- Give existing tables a deterministic starter layout. Management may drag them
-- afterwards; no business state is changed by this seed.
WITH ranked AS (
    SELECT id, row_number() OVER (PARTITION BY "propertyId" ORDER BY code, id) AS rn
    FROM kitchen_tables
)
UPDATE kitchen_tables t
SET "floorX" = 8 + (((r.rn - 1) % 6) * 16),
    "floorY" = 12 + ((((r.rn - 1) / 6) % 4) * 24),
    "updatedAt" = now()
FROM ranked r
WHERE t.id = r.id AND (t."floorX" IS NULL OR t."floorY" IS NULL);

CREATE INDEX kitchen_tables_property_zone_idx
    ON kitchen_tables ("propertyId", "zoneLabel", "isActive", code);
