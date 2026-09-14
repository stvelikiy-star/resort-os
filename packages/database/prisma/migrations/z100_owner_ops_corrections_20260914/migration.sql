-- Three Crowns owner corrections: agents, commercial adjustments and period room holds.

CREATE TABLE booking_agents (
    id UUID PRIMARY KEY,
    "propertyId" UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    "contactName" TEXT,
    phone TEXT,
    whatsapp TEXT,
    email TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','INACTIVE')),
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE ("propertyId", name)
);

CREATE INDEX booking_agents_property_status_idx ON booking_agents ("propertyId", status, name);

CREATE TABLE booking_agent_interactions (
    id UUID PRIMARY KEY,
    "propertyId" UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    "agentId" UUID NOT NULL REFERENCES booking_agents(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('CALL','WHATSAPP','MESSAGE','MEETING','NOTE','TASK')),
    note TEXT NOT NULL,
    "nextContactAt" TIMESTAMPTZ,
    "createdBy" UUID REFERENCES staff_users(id) ON DELETE SET NULL,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX booking_agent_interactions_agent_created_idx
    ON booking_agent_interactions ("agentId", "createdAt" DESC);

ALTER TABLE reservations
    ADD COLUMN "agentId" UUID REFERENCES booking_agents(id) ON DELETE SET NULL,
    ADD COLUMN "extraBedCount" INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN "extraBedUnitKgs" INTEGER,
    ADD COLUMN "discountPercent" INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN "discountReason" TEXT;

ALTER TABLE reservations
    ADD CONSTRAINT reservations_extra_bed_count_check CHECK ("extraBedCount" >= 0 AND "extraBedCount" <= 10),
    ADD CONSTRAINT reservations_extra_bed_unit_check CHECK ("extraBedUnitKgs" IS NULL OR "extraBedUnitKgs" > 0),
    ADD CONSTRAINT reservations_discount_percent_check CHECK ("discountPercent" >= 0 AND "discountPercent" <= 100);

CREATE INDEX reservations_agent_dates_idx ON reservations ("agentId", "checkIn", "checkOut");

ALTER TABLE reservation_requests
    ADD COLUMN "agentId" UUID REFERENCES booking_agents(id) ON DELETE SET NULL;

CREATE INDEX reservation_requests_agent_idx ON reservation_requests ("agentId", "createdAt" DESC);

ALTER TABLE inventory_blocks
    ADD COLUMN "usageCategory" TEXT,
    ADD COLUMN "usageLabel" TEXT;

ALTER TABLE inventory_blocks
    ADD CONSTRAINT inventory_blocks_usage_category_check CHECK (
        "usageCategory" IS NULL OR "usageCategory" IN ('OWNER','STAFF','GUEST_HOLD','SERVICE','OTHER')
    );

CREATE INDEX inventory_blocks_period_usage_idx
    ON inventory_blocks ("roomId", "startDate", "endDate", "usageCategory")
    WHERE active = true;
