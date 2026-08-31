-- Public paid-access extension for QR-controlled toilets/other access points.
-- Payment provider remains external. Resort Core owns intent truth and one-time access grants.

CREATE TABLE IF NOT EXISTS public_access_payment_intents (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    "accessPointId" uuid NOT NULL REFERENCES smart_access_points(id) ON DELETE CASCADE,
    "tokenHash" text NOT NULL UNIQUE,
    "amountKgs" integer NOT NULL CHECK ("amountKgs" > 0),
    status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','PAID','USED','EXPIRED','CANCELLED')),
    provider text,
    "externalRef" text,
    "expiresAt" timestamptz NOT NULL,
    "paidAt" timestamptz,
    "usedAt" timestamptz,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS public_access_payment_intents_point_status_idx
    ON public_access_payment_intents ("accessPointId", status, "expiresAt");

CREATE UNIQUE INDEX IF NOT EXISTS public_access_payment_intents_provider_ref_unique_idx
    ON public_access_payment_intents (provider, "externalRef")
    WHERE provider IS NOT NULL AND "externalRef" IS NOT NULL;

COMMENT ON TABLE public_access_payment_intents IS
'Public QR payment intent for paid access (for example toilet). Payment is confirmed only by authenticated automation/provider callback; unlock remains fail-closed through Smart Access controller.';
