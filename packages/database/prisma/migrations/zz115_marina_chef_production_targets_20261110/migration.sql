-- MARINA Chef OS: dated production targets are not menu stock or paid orders.
-- Tenant isolation reinforced by composite property/menu FK.
ALTER TABLE kitchen_menu_items
  ADD CONSTRAINT kitchen_menu_items_property_id_unique UNIQUE ("propertyId", id);

CREATE TABLE kitchen_production_targets (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  "menuItemId" uuid NOT NULL,
  "serviceDate" date NOT NULL,
  "mealType" text NOT NULL,
  "plannedQuantity" integer NOT NULL,
  "preparedQuantity" integer NOT NULL DEFAULT 0,
  notes text,
  "updatedById" uuid REFERENCES staff_users(id) ON DELETE SET NULL,
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  "updatedAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT kitchen_prod_target_property_item_fk
    FOREIGN KEY ("propertyId", "menuItemId")
    REFERENCES kitchen_menu_items("propertyId", id) ON DELETE CASCADE,
  CONSTRAINT kitchen_prod_target_meal_check
    CHECK ("mealType" IN ('BREAKFAST','LUNCH','DINNER','OTHER')),
  CONSTRAINT kitchen_prod_target_quantity_check
    CHECK ("plannedQuantity" BETWEEN 0 AND 10000
       AND "preparedQuantity" BETWEEN 0 AND "plannedQuantity"),
  CONSTRAINT kitchen_prod_target_note_limit CHECK (char_length(notes) <= 500),
  CONSTRAINT kitchen_prod_target_unique
    UNIQUE ("propertyId", "menuItemId", "serviceDate", "mealType")
);
CREATE INDEX kitchen_prod_target_property_date_idx
  ON kitchen_production_targets ("propertyId", "serviceDate", "mealType");
