-- Additive supplier return + credit-note facts. Existing movement and payable rows immutable.
-- A supplier return is an inventory debit, NOT a Payment and NOT an operating expense.
ALTER TABLE kitchen_stock_movements
  DROP CONSTRAINT kitchen_stock_movement_kind_check;
ALTER TABLE kitchen_stock_movements
  ADD CONSTRAINT kitchen_stock_movement_kind_check
  CHECK (kind IN ('RECEIPT','PRODUCTION','WASTE','SPOILAGE','SUPPLIER_RETURN'));

ALTER TABLE kitchen_stock_movements
  DROP CONSTRAINT kitchen_stock_movement_context_check;
ALTER TABLE kitchen_stock_movements
  ADD CONSTRAINT kitchen_stock_movement_context_check
  CHECK (
    (kind='RECEIPT' AND "productionTargetId" IS NULL
      AND "preparedFrom" IS NULL AND "preparedTo" IS NULL)
    OR
    (kind='PRODUCTION' AND "productionTargetId" IS NOT NULL
      AND "preparedFrom" >= 0 AND "preparedTo" > "preparedFrom")
    OR
    (kind IN ('WASTE','SPOILAGE') AND "productionTargetId" IS NULL
      AND "preparedFrom" IS NULL AND "preparedTo" IS NULL
      AND notes IS NOT NULL AND char_length(btrim(notes)) BETWEEN 3 AND 500)
    OR
    (kind='SUPPLIER_RETURN' AND "productionTargetId" IS NULL
      AND "preparedFrom" IS NULL AND "preparedTo" IS NULL
      AND notes IS NOT NULL AND char_length(btrim(notes)) BETWEEN 3 AND 500)
  );

-- Property scoped return record. The movement id is shared for simple
-- cross-ledger reconciliation, but no existing receipt is overwritten.
CREATE UNIQUE INDEX kitchen_stock_movements_property_id_unique
 ON kitchen_stock_movements ("propertyId",id);

CREATE TABLE kitchen_supplier_returns (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL,
  "documentId" uuid NOT NULL,
  "documentLineId" uuid NOT NULL,
  "stockItemId" uuid NOT NULL,
  "creditReference" text NOT NULL
      CHECK (char_length(btrim("creditReference")) BETWEEN 1 AND 150),
  quantity numeric(16,6) NOT NULL CHECK (quantity > 0),
  "invoiceUnitCostKgs" numeric(16,4) NOT NULL CHECK ("invoiceUnitCostKgs" >= 0),
  "inventoryUnitCostKgs" numeric(14,4) NOT NULL CHECK ("inventoryUnitCostKgs" >= 0),
  "creditAmountKgs" numeric(20,4) NOT NULL CHECK ("creditAmountKgs" >= 0),
  reason text NOT NULL CHECK (char_length(btrim(reason)) BETWEEN 3 AND 500),
  "createdById" uuid REFERENCES staff_users(id) ON DELETE SET NULL,
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT supplier_return_line_fk
    FOREIGN KEY ("propertyId","documentLineId","stockItemId")
    REFERENCES kitchen_supplier_document_lines("propertyId",id,"stockItemId") ON DELETE RESTRICT,
  CONSTRAINT supplier_return_document_fk
    FOREIGN KEY ("propertyId","documentId")
    REFERENCES kitchen_supplier_documents("propertyId",id) ON DELETE RESTRICT,
  CONSTRAINT supplier_return_stock_movement_fk
    FOREIGN KEY ("propertyId",id)
    REFERENCES kitchen_stock_movements("propertyId",id) ON DELETE RESTRICT,
  UNIQUE ("propertyId","documentId","creditReference")
);
CREATE INDEX kitchen_supplier_returns_document_idx
  ON kitchen_supplier_returns ("propertyId","documentId","documentLineId");
