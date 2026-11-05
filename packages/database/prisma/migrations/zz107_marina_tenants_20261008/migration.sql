-- MARINA SMART multi-tenant foundation.
-- Existing properties are deterministically assigned to a legacy tenant.
-- No guest, reservation, payment or room data is copied or changed.

CREATE TABLE IF NOT EXISTS "tenants" (
    "id" UUID NOT NULL,
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'ACTIVE',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "tenants_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "tenants_code_key"
    ON "tenants"("code");

ALTER TABLE "properties"
    ADD COLUMN IF NOT EXISTS "tenantId" UUID;

DO $$
DECLARE
    property_row RECORD;
    tenant_uuid UUID;
    tenant_code TEXT;
BEGIN
    FOR property_row IN
        SELECT id, code, name
        FROM "properties"
        WHERE "tenantId" IS NULL
    LOOP
        tenant_code := 'legacy_' || substr(md5(property_row.code), 1, 16);

        INSERT INTO "tenants" (
            "id", "code", "name", "status", "createdAt", "updatedAt"
        )
        VALUES (
            gen_random_uuid(),
            tenant_code,
            property_row.name,
            'ACTIVE',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT ("code") DO UPDATE
            SET "name" = EXCLUDED."name",
                "updatedAt" = CURRENT_TIMESTAMP
        RETURNING "id" INTO tenant_uuid;

        UPDATE "properties"
        SET "tenantId" = tenant_uuid,
            "updatedAt" = CURRENT_TIMESTAMP
        WHERE "id" = property_row.id;
    END LOOP;
END $$;

ALTER TABLE "properties"
    ALTER COLUMN "tenantId" SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'properties_tenant_fkey'
    ) THEN
        ALTER TABLE "properties"
            ADD CONSTRAINT "properties_tenant_fkey"
            FOREIGN KEY ("tenantId")
            REFERENCES "tenants"("id")
            ON DELETE RESTRICT
            ON UPDATE CASCADE;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS "properties_tenant_code_key"
    ON "properties"("tenantId", "code");

CREATE INDEX IF NOT EXISTS "properties_tenant_idx"
    ON "properties"("tenantId");
