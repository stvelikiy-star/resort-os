-- Preserve the movement ledger; expand its inventory-outflow types without rewriting history.
ALTER TABLE kitchen_stock_movements
  DROP CONSTRAINT kitchen_stock_movement_kind_check;
ALTER TABLE kitchen_stock_movements
  ADD CONSTRAINT kitchen_stock_movement_kind_check
  CHECK (kind IN ('RECEIPT','PRODUCTION','WASTE','SPOILAGE'));

ALTER TABLE kitchen_stock_movements
  DROP CONSTRAINT kitchen_stock_movement_context_check;
ALTER TABLE kitchen_stock_movements
  ADD CONSTRAINT kitchen_stock_movement_context_check
  CHECK (
    (kind='RECEIPT' AND "productionTargetId" IS NULL AND "preparedFrom" IS NULL AND "preparedTo" IS NULL)
    OR
    (kind='PRODUCTION' AND "productionTargetId" IS NOT NULL AND "preparedFrom" >= 0 AND "preparedTo" > "preparedFrom")
    OR
    (kind IN ('WASTE','SPOILAGE') AND "productionTargetId" IS NULL AND "preparedFrom" IS NULL
       AND "preparedTo" IS NULL AND char_length(btrim(notes)) BETWEEN 3 AND 500)
  );

CREATE INDEX kitchen_stock_movements_losses_idx
  ON kitchen_stock_movements ("propertyId", "createdAt" DESC)
  WHERE kind IN ('WASTE','SPOILAGE');
