-- Owner-configurable guest service policy. Times/prices that were not confirmed are
-- deliberately nullable and must be configured by management rather than guessed.

CREATE TABLE property_guest_service_settings (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL UNIQUE,
    "breakfastStart" time,
    "lunchStart" time,
    "dinnerStart" time,
    "mealOrderCutoffMinutes" integer NOT NULL DEFAULT 60,
    "roomDeliveryEnabled" boolean NOT NULL DEFAULT true,
    "roomDeliveryFeeKgs" integer NOT NULL DEFAULT 200,
    "scheduledHousekeepingIntervalDays" integer NOT NULL DEFAULT 3,
    "scheduledLinenChangeIncluded" boolean NOT NULL DEFAULT true,
    "onDemandHousekeepingPriceKgs" integer,
    "onDemandLinenPriceKgs" integer,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT property_guest_service_settings_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT property_guest_service_settings_cutoff_check CHECK ("mealOrderCutoffMinutes" BETWEEN 0 AND 360),
    CONSTRAINT property_guest_service_settings_delivery_fee_check CHECK ("roomDeliveryFeeKgs" >= 0),
    CONSTRAINT property_guest_service_settings_housekeeping_interval_check CHECK ("scheduledHousekeepingIntervalDays" BETWEEN 1 AND 30),
    CONSTRAINT property_guest_service_settings_housekeeping_price_check CHECK ("onDemandHousekeepingPriceKgs" IS NULL OR "onDemandHousekeepingPriceKgs" >= 0),
    CONSTRAINT property_guest_service_settings_linen_price_check CHECK ("onDemandLinenPriceKgs" IS NULL OR "onDemandLinenPriceKgs" >= 0)
);

INSERT INTO property_guest_service_settings (
    id,"propertyId","mealOrderCutoffMinutes","roomDeliveryEnabled","roomDeliveryFeeKgs",
    "scheduledHousekeepingIntervalDays","scheduledLinenChangeIncluded","createdAt","updatedAt"
)
SELECT gen_random_uuid(),p.id,60,true,200,3,true,now(),now()
FROM properties p
WHERE p.code='THREE_CROWNS'
ON CONFLICT ("propertyId") DO UPDATE SET
    "mealOrderCutoffMinutes"=60,
    "roomDeliveryEnabled"=true,
    "roomDeliveryFeeKgs"=200,
    "scheduledHousekeepingIntervalDays"=3,
    "scheduledLinenChangeIncluded"=true,
    "updatedAt"=now();

-- Keep the food subtotal and delivery fee explicit. Existing/staff order writers are
-- backward compatible: subtotal may be NULL and readers fall back to totalKgs.
ALTER TABLE kitchen_orders ADD COLUMN "subtotalKgs" integer;
ALTER TABLE kitchen_orders ADD COLUMN "deliveryFeeKgs" integer NOT NULL DEFAULT 0;
ALTER TABLE kitchen_orders ADD COLUMN "deliveryToRoom" boolean NOT NULL DEFAULT false;
UPDATE kitchen_orders SET "subtotalKgs"="totalKgs" WHERE "subtotalKgs" IS NULL;
ALTER TABLE kitchen_orders ADD CONSTRAINT kitchen_orders_subtotal_nonnegative CHECK ("subtotalKgs" IS NULL OR "subtotalKgs" >= 0);
ALTER TABLE kitchen_orders ADD CONSTRAINT kitchen_orders_delivery_fee_nonnegative CHECK ("deliveryFeeKgs" >= 0);
