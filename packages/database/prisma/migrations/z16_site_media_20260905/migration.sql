CREATE TABLE site_media_assets (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    filename text NOT NULL,
    "mimeType" text NOT NULL,
    "byteSize" integer NOT NULL,
    "sha256Hex" text NOT NULL,
    content bytea NOT NULL,
    "altText" text,
    "isActive" boolean NOT NULL DEFAULT true,
    "createdById" uuid,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT site_media_assets_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT site_media_assets_created_by_fkey FOREIGN KEY ("createdById") REFERENCES staff_users(id) ON DELETE SET NULL,
    CONSTRAINT site_media_assets_size_check CHECK ("byteSize" > 0 AND "byteSize" <= 8388608),
    CONSTRAINT site_media_assets_mime_check CHECK ("mimeType" IN ('image/jpeg','image/png','image/webp'))
);
CREATE INDEX site_media_assets_property_active_idx ON site_media_assets ("propertyId","isActive","createdAt");
CREATE INDEX site_media_assets_sha_idx ON site_media_assets ("propertyId","sha256Hex");
