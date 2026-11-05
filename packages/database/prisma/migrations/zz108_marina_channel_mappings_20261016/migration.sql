-- Configuration only: no provider connection or outbound delivery is enabled.
ALTER TABLE room_types ADD CONSTRAINT room_types_property_id_key UNIQUE ("propertyId", id);
ALTER TABLE rate_plans ADD CONSTRAINT rate_plans_property_id_key UNIQUE ("propertyId", id);
CREATE TABLE channel_mappings (
 id UUID PRIMARY KEY,
 "propertyId" UUID NOT NULL REFERENCES properties(id) ON DELETE RESTRICT,
 provider TEXT NOT NULL CONSTRAINT channel_mapping_provider_check CHECK (provider IN ('BOOKING_COM','AIRBNB','OSTROVOK')),
 "externalPropertyId" TEXT NOT NULL CONSTRAINT channel_mapping_property_id_check CHECK (length(trim("externalPropertyId")) BETWEEN 1 AND 180),
 "externalRoomTypeId" TEXT NOT NULL CONSTRAINT channel_mapping_room_id_check CHECK (length(trim("externalRoomTypeId")) BETWEEN 1 AND 180),
 "externalRatePlanId" TEXT NOT NULL CONSTRAINT channel_mapping_rate_id_check CHECK (length(trim("externalRatePlanId")) BETWEEN 1 AND 180),
 "roomTypeId" UUID NOT NULL,
 "ratePlanId" UUID NOT NULL,
 currency TEXT NOT NULL CONSTRAINT channel_mapping_currency_check CHECK (currency = 'KGS'),
 active BOOLEAN NOT NULL DEFAULT true,
 revision INTEGER NOT NULL DEFAULT 1 CONSTRAINT channel_mapping_revision_check CHECK (revision > 0),
 "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
 "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT channel_mappings_room_type_fkey FOREIGN KEY ("propertyId","roomTypeId") REFERENCES room_types("propertyId",id) ON DELETE RESTRICT,
 CONSTRAINT channel_mappings_rate_plan_fkey FOREIGN KEY ("propertyId","ratePlanId") REFERENCES rate_plans("propertyId",id) ON DELETE RESTRICT,
 CONSTRAINT channel_mappings_external_key UNIQUE ("propertyId",provider,"externalPropertyId","externalRoomTypeId","externalRatePlanId")
);
