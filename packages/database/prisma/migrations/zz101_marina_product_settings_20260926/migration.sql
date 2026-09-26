CREATE TABLE "property_product_settings" (
  "id" UUID NOT NULL,
  "propertyId" UUID NOT NULL,
  "checkInTime" TIME NOT NULL DEFAULT TIME '14:00',
  "checkOutTime" TIME NOT NULL DEFAULT TIME '12:00',
  "enabledModules" JSONB NOT NULL DEFAULT '["AGENTS","DINING","ROOM_QR"]'::jsonb,
  "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT "property_product_settings_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "property_product_settings_propertyId_key" UNIQUE ("propertyId"),
  CONSTRAINT "property_product_settings_propertyId_fkey"
    FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT "property_product_settings_check_times"
    CHECK ("checkInTime" <> "checkOutTime"),
  CONSTRAINT "property_product_settings_enabled_modules_array"
    CHECK (jsonb_typeof("enabledModules") = 'array')
);
