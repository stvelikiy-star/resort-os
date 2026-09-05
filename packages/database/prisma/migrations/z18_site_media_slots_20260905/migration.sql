-- Published media placement is separate from localized text content. One image
-- assignment therefore applies consistently to RU/KG/EN and cannot drift by locale.
CREATE TABLE site_media_slots (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    slot text NOT NULL,
    "assetId" uuid NOT NULL,
    "altText" text,
    "updatedById" uuid,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT site_media_slots_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT site_media_slots_asset_fkey FOREIGN KEY ("assetId") REFERENCES site_media_assets(id) ON DELETE RESTRICT,
    CONSTRAINT site_media_slots_updated_by_fkey FOREIGN KEY ("updatedById") REFERENCES staff_users(id) ON DELETE SET NULL
);
CREATE UNIQUE INDEX site_media_slots_property_slot_key ON site_media_slots ("propertyId", slot);
CREATE INDEX site_media_slots_asset_idx ON site_media_slots ("assetId");
