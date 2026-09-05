-- Media placement has its own draft/publish lifecycle. One published assignment
-- applies consistently to RU/KG/EN so media cannot drift by locale.
CREATE TABLE site_media_slots (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    slot text NOT NULL,
    "draftAssetId" uuid,
    "publishedAssetId" uuid,
    "draftAltText" text,
    "publishedAltText" text,
    version integer NOT NULL DEFAULT 0,
    "publishedVersion" integer NOT NULL DEFAULT 0,
    "publishedAt" timestamptz,
    "updatedById" uuid,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT site_media_slots_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT site_media_slots_draft_asset_fkey FOREIGN KEY ("draftAssetId") REFERENCES site_media_assets(id) ON DELETE RESTRICT,
    CONSTRAINT site_media_slots_published_asset_fkey FOREIGN KEY ("publishedAssetId") REFERENCES site_media_assets(id) ON DELETE RESTRICT,
    CONSTRAINT site_media_slots_updated_by_fkey FOREIGN KEY ("updatedById") REFERENCES staff_users(id) ON DELETE SET NULL,
    CONSTRAINT site_media_slots_versions_check CHECK (version >= 0 AND "publishedVersion" >= 0 AND "publishedVersion" <= version)
);
CREATE UNIQUE INDEX site_media_slots_property_slot_key ON site_media_slots ("propertyId", slot);
CREATE INDEX site_media_slots_draft_asset_idx ON site_media_slots ("draftAssetId");
CREATE INDEX site_media_slots_published_asset_idx ON site_media_slots ("publishedAssetId");
