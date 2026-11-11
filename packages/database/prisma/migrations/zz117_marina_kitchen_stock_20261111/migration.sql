-- Per-property kitchen stock. Receipts do not represent payments and planning never deducts stock.
CREATE TABLE kitchen_stock_items (
 id uuid PRIMARY KEY, "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
 name text NOT NULL, "nameKey" text NOT NULL, unit text NOT NULL CONSTRAINT kitchen_stock_item_unit_check CHECK(unit IN ('KG','L','PCS')),
 "costPerUnitKgs" numeric(14,4) NOT NULL DEFAULT 0 CONSTRAINT kitchen_stock_item_unit_cost_check CHECK ("costPerUnitKgs" >= 0),
 "isSample" boolean NOT NULL DEFAULT true,
 "createdAt" timestamptz NOT NULL DEFAULT now(), "updatedAt" timestamptz NOT NULL DEFAULT now(),
 UNIQUE("propertyId","nameKey",unit), UNIQUE("propertyId",id),
 CONSTRAINT kitchen_stock_item_name_check CHECK (char_length(name) BETWEEN 1 AND 120)
);
CREATE TABLE kitchen_stock_movements (
 id uuid PRIMARY KEY, "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
 "stockItemId" uuid NOT NULL, kind text NOT NULL CONSTRAINT kitchen_stock_movement_kind_check CHECK(kind IN ('RECEIPT','PRODUCTION')),
 quantity numeric(16,6) NOT NULL CONSTRAINT kitchen_stock_movement_quantity_check CHECK(quantity > 0),
 "unitCostKgs" numeric(14,4) NOT NULL CONSTRAINT kitchen_stock_movement_cost_check CHECK("unitCostKgs" >= 0),
 "productionTargetId" uuid REFERENCES kitchen_production_targets(id) ON DELETE RESTRICT,
 "preparedFrom" integer, "preparedTo" integer,
 "createdById" uuid REFERENCES staff_users(id) ON DELETE SET NULL,
 notes text, "createdAt" timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY ("propertyId","stockItemId") REFERENCES kitchen_stock_items("propertyId",id),
 CONSTRAINT kitchen_stock_movement_context_check CHECK ((kind='RECEIPT' AND "productionTargetId" IS NULL AND "preparedFrom" IS NULL AND "preparedTo" IS NULL)
 OR (kind='PRODUCTION' AND "productionTargetId" IS NOT NULL AND "preparedFrom" >= 0 AND "preparedTo" > "preparedFrom"))
);
CREATE INDEX kitchen_stock_movements_item_idx ON kitchen_stock_movements("propertyId","stockItemId","createdAt");
CREATE INDEX kitchen_stock_movements_target_idx ON kitchen_stock_movements("propertyId","productionTargetId");
CREATE TABLE kitchen_stock_production_progress (
 "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
 "productionTargetId" uuid PRIMARY KEY REFERENCES kitchen_production_targets(id) ON DELETE RESTRICT,
 "deductedPortions" integer NOT NULL DEFAULT 0 CONSTRAINT kitchen_stock_progress_quantity_check CHECK("deductedPortions" >= 0),
 "updatedAt" timestamptz NOT NULL DEFAULT now()
);
