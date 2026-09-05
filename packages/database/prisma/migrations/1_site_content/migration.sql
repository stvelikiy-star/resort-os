-- Forward migration for Resort OS public-site CMS storage.
-- Keep booking, inventory and payment truth in Core-owned canonical tables;
-- this table stores versioned public-site copy only.

CREATE TABLE IF NOT EXISTS site_content_documents (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    locale text NOT NULL,
    scope text NOT NULL DEFAULT 'PUBLIC_SITE',
    "draftJson" jsonb NOT NULL DEFAULT '{}'::jsonb,
    "publishedJson" jsonb NOT NULL DEFAULT '{}'::jsonb,
    version integer NOT NULL DEFAULT 1 CHECK (version > 0),
    "publishedVersion" integer NOT NULL DEFAULT 0 CHECK ("publishedVersion" >= 0),
    "publishedAt" timestamptz,
    "updatedByStaffId" uuid REFERENCES staff_users(id) ON DELETE SET NULL,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT site_content_documents_locale_check CHECK (locale IN ('ru', 'kg', 'en')),
    CONSTRAINT site_content_documents_scope_check CHECK (scope = 'PUBLIC_SITE'),
    UNIQUE ("propertyId", locale, scope)
);

CREATE INDEX IF NOT EXISTS site_content_documents_property_idx
    ON site_content_documents ("propertyId", scope, locale);

COMMENT ON TABLE site_content_documents IS
    'Versioned public-site copy managed by Resort OS. Booking/inventory truth never belongs here.';
