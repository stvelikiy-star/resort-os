-- Three Crowns marketing foundation for db-push/local CI environments.
-- Production remains governed by the matching Prisma forward migration.

ALTER TABLE "reservation_requests"
  ADD COLUMN IF NOT EXISTS "utmSource" TEXT,
  ADD COLUMN IF NOT EXISTS "utmMedium" TEXT,
  ADD COLUMN IF NOT EXISTS "utmCampaign" TEXT,
  ADD COLUMN IF NOT EXISTS "utmContent" TEXT,
  ADD COLUMN IF NOT EXISTS "utmTerm" TEXT,
  ADD COLUMN IF NOT EXISTS "landingPage" TEXT,
  ADD COLUMN IF NOT EXISTS referrer TEXT;

CREATE TABLE IF NOT EXISTS "marketing_consents" (
  id UUID NOT NULL,
  "propertyId" UUID NOT NULL,
  "requestId" UUID,
  "guestId" UUID,
  "contactKey" TEXT NOT NULL,
  channel TEXT NOT NULL,
  status TEXT NOT NULL,
  source TEXT NOT NULL,
  "policyVersion" TEXT NOT NULL,
  proof TEXT,
  "occurredAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  "createdByStaffId" UUID,
  "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT marketing_consents_pkey PRIMARY KEY (id),
  CONSTRAINT marketing_consents_channel_check CHECK (channel IN ('WHATSAPP','EMAIL','SMS','TELEGRAM','PHONE')),
  CONSTRAINT marketing_consents_status_check CHECK (status IN ('OPTED_IN','OPTED_OUT')),
  CONSTRAINT marketing_consents_identity_check CHECK ("requestId" IS NOT NULL OR "guestId" IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS "marketing_touchpoints" (
  id UUID NOT NULL,
  "propertyId" UUID NOT NULL,
  "requestId" UUID,
  "guestId" UUID,
  "campaignCode" TEXT,
  channel TEXT NOT NULL,
  direction TEXT NOT NULL DEFAULT 'OUTBOUND',
  "eventType" TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'RECORDED',
  "providerMessageId" TEXT,
  "metadataJson" JSONB,
  "occurredAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  "createdByStaffId" UUID,
  "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT marketing_touchpoints_pkey PRIMARY KEY (id),
  CONSTRAINT marketing_touchpoints_channel_check CHECK (channel IN ('WHATSAPP','EMAIL','SMS','TELEGRAM','PHONE','OTHER')),
  CONSTRAINT marketing_touchpoints_direction_check CHECK (direction IN ('INBOUND','OUTBOUND','INTERNAL')),
  CONSTRAINT marketing_touchpoints_identity_check CHECK ("requestId" IS NOT NULL OR "guestId" IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS marketing_consents_property_contact_channel_time_idx
  ON "marketing_consents" ("propertyId", "contactKey", channel, "occurredAt" DESC);
CREATE INDEX IF NOT EXISTS marketing_consents_request_time_idx
  ON "marketing_consents" ("requestId", "occurredAt" DESC);
CREATE INDEX IF NOT EXISTS marketing_consents_guest_time_idx
  ON "marketing_consents" ("guestId", "occurredAt" DESC);
CREATE INDEX IF NOT EXISTS marketing_touchpoints_property_time_idx
  ON "marketing_touchpoints" ("propertyId", "occurredAt" DESC);
CREATE INDEX IF NOT EXISTS marketing_touchpoints_request_time_idx
  ON "marketing_touchpoints" ("requestId", "occurredAt" DESC);
CREATE INDEX IF NOT EXISTS reservation_requests_attribution_idx
  ON "reservation_requests" ("propertyId", "utmSource", "utmCampaign", "createdAt");

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='marketing_consents_property_fkey') THEN
    ALTER TABLE "marketing_consents" ADD CONSTRAINT marketing_consents_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='marketing_consents_request_fkey') THEN
    ALTER TABLE "marketing_consents" ADD CONSTRAINT marketing_consents_request_fkey FOREIGN KEY ("requestId") REFERENCES reservation_requests(id) ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='marketing_consents_guest_fkey') THEN
    ALTER TABLE "marketing_consents" ADD CONSTRAINT marketing_consents_guest_fkey FOREIGN KEY ("guestId") REFERENCES guests(id) ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='marketing_consents_staff_fkey') THEN
    ALTER TABLE "marketing_consents" ADD CONSTRAINT marketing_consents_staff_fkey FOREIGN KEY ("createdByStaffId") REFERENCES staff_users(id) ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='marketing_touchpoints_property_fkey') THEN
    ALTER TABLE "marketing_touchpoints" ADD CONSTRAINT marketing_touchpoints_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='marketing_touchpoints_request_fkey') THEN
    ALTER TABLE "marketing_touchpoints" ADD CONSTRAINT marketing_touchpoints_request_fkey FOREIGN KEY ("requestId") REFERENCES reservation_requests(id) ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='marketing_touchpoints_guest_fkey') THEN
    ALTER TABLE "marketing_touchpoints" ADD CONSTRAINT marketing_touchpoints_guest_fkey FOREIGN KEY ("guestId") REFERENCES guests(id) ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='marketing_touchpoints_staff_fkey') THEN
    ALTER TABLE "marketing_touchpoints" ADD CONSTRAINT marketing_touchpoints_staff_fkey FOREIGN KEY ("createdByStaffId") REFERENCES staff_users(id) ON DELETE SET NULL ON UPDATE CASCADE;
  END IF;
END $$;
