-- Guest offer campaigns turn the authenticated in-stay Guest OS into a controlled upsell channel.
-- Campaigns never confirm availability, price, payment or service delivery by themselves.

CREATE TABLE guest_offer_campaigns (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    code text NOT NULL,
    "titleRu" text NOT NULL,
    "titleKg" text NOT NULL,
    "titleEn" text NOT NULL,
    "hookRu" text NOT NULL,
    "hookKg" text NOT NULL,
    "hookEn" text NOT NULL,
    "ctaRu" text NOT NULL DEFAULT 'Хочу',
    "ctaKg" text NOT NULL DEFAULT 'Каалайм',
    "ctaEn" text NOT NULL DEFAULT 'Request',
    "imageUrl" text,
    "actionType" text NOT NULL,
    "requestCode" text,
    "externalUrl" text,
    "aiPrompt" text,
    "activeFrom" timestamptz,
    "activeTo" timestamptz,
    "minAdults" integer NOT NULL DEFAULT 0,
    "minChildren" integer NOT NULL DEFAULT 0,
    "minStayNights" integer NOT NULL DEFAULT 0,
    "maxStayNights" integer,
    priority integer NOT NULL DEFAULT 100,
    "sortOrder" integer NOT NULL DEFAULT 0,
    "isActive" boolean NOT NULL DEFAULT false,
    "createdById" uuid,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT guest_offer_campaigns_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT guest_offer_campaigns_created_by_fkey FOREIGN KEY ("createdById") REFERENCES staff_users(id) ON DELETE SET NULL,
    CONSTRAINT guest_offer_campaigns_action_check CHECK ("actionType" IN ('GUEST_REQUEST','EXTERNAL_URL','AI_PROMPT')),
    CONSTRAINT guest_offer_campaigns_request_code_check CHECK (
      "requestCode" IS NULL OR "requestCode" IN ('HOUSEKEEPING','TOWELS','LINEN','MAINTENANCE','TRANSFER','MEALS','PARKING','SAUNA','BILLIARDS','EXCURSIONS','ADMIN')
    ),
    CONSTRAINT guest_offer_campaigns_external_url_check CHECK ("externalUrl" IS NULL OR "externalUrl" ~ '^https://'),
    CONSTRAINT guest_offer_campaigns_window_check CHECK ("activeTo" IS NULL OR "activeFrom" IS NULL OR "activeTo" > "activeFrom"),
    CONSTRAINT guest_offer_campaigns_audience_check CHECK (
      "minAdults" >= 0 AND "minChildren" >= 0 AND "minStayNights" >= 0 AND
      ("maxStayNights" IS NULL OR "maxStayNights" >= "minStayNights")
    )
);
CREATE UNIQUE INDEX guest_offer_campaigns_property_code_key ON guest_offer_campaigns ("propertyId", code);
CREATE INDEX guest_offer_campaigns_property_active_idx ON guest_offer_campaigns ("propertyId", "isActive", priority, "sortOrder");
CREATE INDEX guest_offer_campaigns_active_window_idx ON guest_offer_campaigns ("activeFrom", "activeTo") WHERE "isActive"=true;

CREATE TABLE guest_offer_events (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    "campaignId" uuid NOT NULL,
    "guestId" uuid NOT NULL,
    "stayId" uuid NOT NULL,
    "eventType" text NOT NULL,
    "guestSessionId" uuid,
    metadata jsonb,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT guest_offer_events_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT guest_offer_events_campaign_fkey FOREIGN KEY ("campaignId") REFERENCES guest_offer_campaigns(id) ON DELETE CASCADE,
    CONSTRAINT guest_offer_events_guest_fkey FOREIGN KEY ("guestId") REFERENCES guests(id) ON DELETE CASCADE,
    CONSTRAINT guest_offer_events_stay_fkey FOREIGN KEY ("stayId") REFERENCES stays(id) ON DELETE CASCADE,
    CONSTRAINT guest_offer_events_session_fkey FOREIGN KEY ("guestSessionId") REFERENCES guest_sessions(id) ON DELETE SET NULL,
    CONSTRAINT guest_offer_events_type_check CHECK ("eventType" IN ('CLICK','REQUEST','EXTERNAL_OPEN','AI_PROMPT'))
);
CREATE INDEX guest_offer_events_campaign_created_idx ON guest_offer_events ("campaignId", "createdAt" DESC);
CREATE INDEX guest_offer_events_property_created_idx ON guest_offer_events ("propertyId", "createdAt" DESC);
CREATE INDEX guest_offer_events_guest_created_idx ON guest_offer_events ("guestId", "createdAt" DESC);
