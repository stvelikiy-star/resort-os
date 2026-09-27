ALTER TABLE "property_product_settings"
  ALTER COLUMN "enabledModules"
  SET DEFAULT '["GROUPS","AGENTS","MARKETING","DINING","OFFERS","GROWTH","CONTENT","ROOM_QR","POINT_QR","INBOX"]'::jsonb;

UPDATE "property_product_settings" AS pps
SET "enabledModules" = '["GROUPS","AGENTS","MARKETING","DINING","OFFERS","GROWTH","CONTENT","ROOM_QR","POINT_QR","INBOX"]'::jsonb,
    "updatedAt" = now()
FROM properties AS p
WHERE p.id = pps."propertyId"
  AND p.code = 'MARINA_TEST'
  AND pps."enabledModules" = '["AGENTS","DINING","ROOM_QR"]'::jsonb;
