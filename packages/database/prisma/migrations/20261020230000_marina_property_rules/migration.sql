-- Hotel-owned information policies, independent by Property. This does not change pricing/payment execution.
CREATE TABLE property_hotel_rules (
    "propertyId" uuid PRIMARY KEY REFERENCES properties(id) ON DELETE CASCADE,
    "version" integer NOT NULL DEFAULT 1 CHECK ("version">=1),
    "policy" jsonb NOT NULL,
    "updatedBy" uuid,
    "updatedAt" timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE property_hotel_rules_history (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    "version" integer NOT NULL,
    "policy" jsonb NOT NULL,
    "updatedBy" uuid,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT property_hotel_rules_history_version_uk UNIQUE ("propertyId","version")
);
CREATE INDEX property_hotel_rules_history_property_date_idx
ON property_hotel_rules_history ("propertyId","createdAt" DESC);
