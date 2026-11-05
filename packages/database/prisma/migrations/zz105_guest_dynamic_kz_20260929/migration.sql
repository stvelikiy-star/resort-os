-- MARINA SMART Guest Web: first-class Kazakh fields for hotel-managed dynamic content.
-- Existing RU/KG/EN values are preserved; KZ stays NULL until reviewed by hotel staff.

ALTER TABLE kitchen_menu_items
  ADD COLUMN IF NOT EXISTS "nameKz" text;

ALTER TABLE guest_offer_campaigns
  ADD COLUMN IF NOT EXISTS "titleKz" text,
  ADD COLUMN IF NOT EXISTS "hookKz" text,
  ADD COLUMN IF NOT EXISTS "ctaKz" text;
