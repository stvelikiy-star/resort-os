-- Visual Dining Floor metadata. z14 already introduced zoneLabel/positionX/positionY.
-- New coordinates are normalized percentages so the same layout works on
-- desktop/tablet/mobile without storing device-specific pixels.
UPDATE kitchen_tables SET "zoneLabel"='Основной зал' WHERE "zoneLabel" IS NULL OR btrim("zoneLabel")='';
ALTER TABLE kitchen_tables ALTER COLUMN "zoneLabel" SET DEFAULT 'Основной зал';
ALTER TABLE kitchen_tables ALTER COLUMN "zoneLabel" SET NOT NULL;

ALTER TABLE kitchen_tables ADD COLUMN "floorX" numeric(5,2);
ALTER TABLE kitchen_tables ADD COLUMN "floorY" numeric(5,2);
ALTER TABLE kitchen_tables ADD COLUMN "floorShape" text NOT NULL DEFAULT 'ROUND';

ALTER TABLE kitchen_tables
    ADD CONSTRAINT kitchen_tables_floor_x_check CHECK ("floorX" IS NULL OR ("floorX" >= 0 AND "floorX" <= 100));
ALTER TABLE kitchen_tables
    ADD CONSTRAINT kitchen_tables_floor_y_check CHECK ("floorY" IS NULL OR ("floorY" >= 0 AND "floorY" <= 100));
ALTER TABLE kitchen_tables
    ADD CONSTRAINT kitchen_tables_floor_shape_check CHECK ("floorShape" IN ('ROUND','SQUARE','RECTANGLE'));

-- Preserve any legacy visual coordinates from z14. If none were configured,
-- give existing tables a deterministic starter layout. Business state is untouched.
WITH ranked AS (
    SELECT id, row_number() OVER (PARTITION BY "propertyId" ORDER BY code, id) AS rn
    FROM kitchen_tables
)
UPDATE kitchen_tables t
SET "floorX" = CASE
        WHEN t."positionX" IS NOT NULL THEN LEAST(100::numeric, GREATEST(0::numeric, t."positionX" / 100.0))
        ELSE 8 + (((r.rn - 1) % 6) * 16)
    END,
    "floorY" = CASE
        WHEN t."positionY" IS NOT NULL THEN LEAST(100::numeric, GREATEST(0::numeric, t."positionY" / 100.0))
        ELSE 12 + ((((r.rn - 1) / 6) % 4) * 24)
    END,
    "updatedAt" = now()
FROM ranked r
WHERE t.id = r.id AND (t."floorX" IS NULL OR t."floorY" IS NULL);

CREATE INDEX kitchen_tables_property_zone_idx
    ON kitchen_tables ("propertyId", "zoneLabel", "isActive", code);
