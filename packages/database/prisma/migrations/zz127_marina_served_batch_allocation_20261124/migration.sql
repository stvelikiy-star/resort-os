-- Additive 52nd migration. Never changes historical 51 migrations.
-- Explicit operator assertion of which production batch served which order item.
-- This is NOT a cash transaction, accounting posting or automatic COGS booking.
ALTER TABLE kitchen_orders
  ADD CONSTRAINT kitchen_orders_property_id_unique UNIQUE ("propertyId",id);
ALTER TABLE kitchen_order_items
  ADD CONSTRAINT kitchen_order_items_order_id_unique UNIQUE ("orderId",id);
ALTER TABLE kitchen_production_targets
  ADD CONSTRAINT kitchen_production_targets_property_id_unique UNIQUE ("propertyId",id);

CREATE TABLE kitchen_served_batch_allocations (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL,
  "orderId" uuid NOT NULL,
  "orderItemId" uuid NOT NULL,
  "productionTargetId" uuid NOT NULL,
  portions integer NOT NULL CONSTRAINT kitchen_served_allocation_portions_check
    CHECK (portions BETWEEN 1 AND 10000),
  "unitCostKgs" numeric(16,6) NOT NULL CONSTRAINT kitchen_served_allocation_unit_cost_check
    CHECK ("unitCostKgs" >= 0),
  "totalCostKgs" numeric(18,4) NOT NULL CONSTRAINT kitchen_served_allocation_total_cost_check
    CHECK ("totalCostKgs" >= 0),
  "recordedById" uuid REFERENCES staff_users(id) ON DELETE SET NULL,
  source text NOT NULL DEFAULT 'OPERATOR_ATTESTED'
    CONSTRAINT kitchen_served_allocation_source_check
    CHECK (source = 'OPERATOR_ATTESTED'),
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT kitchen_served_allocation_property_order_fk FOREIGN KEY ("propertyId","orderId")
    REFERENCES kitchen_orders ("propertyId",id) ON DELETE RESTRICT,
  CONSTRAINT kitchen_served_allocation_order_item_fk FOREIGN KEY ("orderId","orderItemId")
    REFERENCES kitchen_order_items ("orderId",id) ON DELETE RESTRICT,
  CONSTRAINT kitchen_served_allocation_property_target_fk FOREIGN KEY ("propertyId","productionTargetId")
    REFERENCES kitchen_production_targets ("propertyId",id) ON DELETE RESTRICT,
  CONSTRAINT kitchen_served_allocation_unique_batch_per_item
    UNIQUE ("orderItemId","productionTargetId")
);
CREATE INDEX kitchen_served_batch_allocations_property_order_idx
  ON kitchen_served_batch_allocations ("propertyId","orderId");
CREATE INDEX kitchen_served_batch_allocations_property_target_idx
  ON kitchen_served_batch_allocations ("propertyId","productionTargetId");
