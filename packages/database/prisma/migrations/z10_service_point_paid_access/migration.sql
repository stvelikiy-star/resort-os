CREATE TYPE "ServicePointAccessMode" AS ENUM ('FREE_REQUEST', 'PAID_LOCK');
CREATE TYPE "ServicePointPaymentIntentStatus" AS ENUM (
    'CREATED',
    'AWAITING_PAYMENT',
    'PAID',
    'UNLOCK_PENDING',
    'UNLOCKED',
    'UNLOCK_FAILED',
    'PAYMENT_FAILED',
    'EXPIRED',
    'CANCELLED'
);
CREATE TYPE "ServicePointLockActionStatus" AS ENUM ('PENDING', 'SUCCEEDED', 'FAILED');

CREATE TABLE "service_point_access_profiles" (
    "servicePointId" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "mode" "ServicePointAccessMode" NOT NULL DEFAULT 'FREE_REQUEST',
    "amountKgs" INTEGER,
    "currency" TEXT NOT NULL DEFAULT 'KGS',
    "providerCode" TEXT,
    "lockProviderCode" TEXT,
    "lockExternalId" TEXT,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "service_point_access_profiles_pkey" PRIMARY KEY ("servicePointId"),
    CONSTRAINT "service_point_access_profiles_currency_check" CHECK ("currency"='KGS'),
    CONSTRAINT "service_point_access_profiles_paid_config_check" CHECK (
        ("mode"='FREE_REQUEST' AND "amountKgs" IS NULL AND "providerCode" IS NULL AND "lockProviderCode" IS NULL AND "lockExternalId" IS NULL)
        OR
        ("mode"='PAID_LOCK' AND "amountKgs">0 AND "providerCode" IS NOT NULL AND length(btrim("providerCode"))>=2
          AND "lockProviderCode" IS NOT NULL AND length(btrim("lockProviderCode"))>=2
          AND "lockExternalId" IS NOT NULL AND length(btrim("lockExternalId"))>=1)
    )
);

CREATE TABLE "service_point_payment_intents" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "servicePointId" UUID NOT NULL,
    "clientRequestId" TEXT NOT NULL,
    "reference" TEXT NOT NULL,
    "providerCode" TEXT NOT NULL,
    "providerPaymentId" TEXT,
    "lockProviderCode" TEXT NOT NULL,
    "lockExternalId" TEXT NOT NULL,
    "amountKgs" INTEGER NOT NULL,
    "currency" TEXT NOT NULL DEFAULT 'KGS',
    "status" "ServicePointPaymentIntentStatus" NOT NULL DEFAULT 'CREATED',
    "checkoutUrl" TEXT,
    "qrPayload" TEXT,
    "paidAt" TIMESTAMP(3),
    "expiresAt" TIMESTAMP(3) NOT NULL,
    "unlockAttemptedAt" TIMESTAMP(3),
    "unlockedAt" TIMESTAMP(3),
    "failureCode" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "service_point_payment_intents_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "service_point_payment_intents_amount_check" CHECK ("amountKgs">0),
    CONSTRAINT "service_point_payment_intents_currency_check" CHECK ("currency"='KGS'),
    CONSTRAINT "service_point_payment_intents_lock_snapshot_check" CHECK (
        length(btrim("lockProviderCode"))>=2 AND length(btrim("lockExternalId"))>=1
    ),
    CONSTRAINT "service_point_payment_intents_expiry_check" CHECK ("expiresAt">"createdAt"),
    CONSTRAINT "service_point_payment_intents_paid_state_check" CHECK (
        ("status" IN ('PAID','UNLOCK_PENDING','UNLOCKED','UNLOCK_FAILED') AND "paidAt" IS NOT NULL)
        OR
        ("status" NOT IN ('PAID','UNLOCK_PENDING','UNLOCKED','UNLOCK_FAILED'))
    ),
    CONSTRAINT "service_point_payment_intents_unlocked_state_check" CHECK (
        ("status"='UNLOCKED' AND "unlockedAt" IS NOT NULL)
        OR ("status"<>'UNLOCKED')
    )
);

CREATE TABLE "service_point_payment_events" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "intentId" UUID NOT NULL,
    "providerCode" TEXT NOT NULL,
    "providerEventId" TEXT,
    "eventType" TEXT NOT NULL,
    "providerPaymentId" TEXT,
    "payloadJson" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "service_point_payment_events_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "service_point_payment_events_payload_check" CHECK (jsonb_typeof("payloadJson")='object')
);

CREATE TABLE "service_point_lock_actions" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "servicePointId" UUID NOT NULL,
    "intentId" UUID NOT NULL,
    "providerCode" TEXT NOT NULL,
    "lockExternalId" TEXT NOT NULL,
    "status" "ServicePointLockActionStatus" NOT NULL DEFAULT 'PENDING',
    "attempts" INTEGER NOT NULL DEFAULT 0,
    "lastErrorCode" TEXT,
    "providerResultJson" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "service_point_lock_actions_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "service_point_lock_actions_attempts_check" CHECK ("attempts">=0),
    CONSTRAINT "service_point_lock_actions_result_check" CHECK (jsonb_typeof("providerResultJson")='object')
);

CREATE UNIQUE INDEX "service_point_payment_intents_reference_key" ON "service_point_payment_intents"("reference");
CREATE UNIQUE INDEX "service_point_payment_intents_point_client_key" ON "service_point_payment_intents"("servicePointId","clientRequestId");
CREATE UNIQUE INDEX "service_point_payment_intents_provider_payment_key" ON "service_point_payment_intents"("providerCode","providerPaymentId") WHERE "providerPaymentId" IS NOT NULL;
CREATE INDEX "service_point_payment_intents_point_status_created_idx" ON "service_point_payment_intents"("servicePointId","status","createdAt");
CREATE INDEX "service_point_payment_intents_property_status_created_idx" ON "service_point_payment_intents"("propertyId","status","createdAt");
CREATE UNIQUE INDEX "service_point_payment_events_provider_event_key" ON "service_point_payment_events"("providerCode","providerEventId") WHERE "providerEventId" IS NOT NULL;
CREATE INDEX "service_point_payment_events_intent_created_idx" ON "service_point_payment_events"("intentId","createdAt");
CREATE UNIQUE INDEX "service_point_lock_actions_intent_key" ON "service_point_lock_actions"("intentId");
CREATE INDEX "service_point_lock_actions_status_created_idx" ON "service_point_lock_actions"("status","createdAt");

ALTER TABLE "service_point_access_profiles"
  ADD CONSTRAINT "service_point_access_profiles_servicePointId_fkey"
  FOREIGN KEY ("servicePointId") REFERENCES "service_points"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "service_point_access_profiles"
  ADD CONSTRAINT "service_point_access_profiles_propertyId_fkey"
  FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "service_point_payment_intents"
  ADD CONSTRAINT "service_point_payment_intents_servicePointId_fkey"
  FOREIGN KEY ("servicePointId") REFERENCES "service_points"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "service_point_payment_intents"
  ADD CONSTRAINT "service_point_payment_intents_propertyId_fkey"
  FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "service_point_payment_events"
  ADD CONSTRAINT "service_point_payment_events_intentId_fkey"
  FOREIGN KEY ("intentId") REFERENCES "service_point_payment_intents"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "service_point_payment_events"
  ADD CONSTRAINT "service_point_payment_events_propertyId_fkey"
  FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "service_point_lock_actions"
  ADD CONSTRAINT "service_point_lock_actions_intentId_fkey"
  FOREIGN KEY ("intentId") REFERENCES "service_point_payment_intents"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "service_point_lock_actions"
  ADD CONSTRAINT "service_point_lock_actions_servicePointId_fkey"
  FOREIGN KEY ("servicePointId") REFERENCES "service_points"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "service_point_lock_actions"
  ADD CONSTRAINT "service_point_lock_actions_propertyId_fkey"
  FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
