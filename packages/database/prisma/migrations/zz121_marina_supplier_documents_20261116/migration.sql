-- P0 supplier source documents: additive, property-scoped facts only.
-- This migration does NOT post an owner_expense, customer Payment or recognized P&L.
-- Historic procurement receipts remain unlinked until explicitly reconciled.
CREATE TABLE kitchen_supplier_documents (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  "supplierName" text NOT NULL CHECK (char_length(trim("supplierName")) BETWEEN 1 AND 150),
  "documentReference" text NOT NULL CHECK (char_length(trim("documentReference")) BETWEEN 1 AND 150),
  "documentDate" date NOT NULL,
  currency text NOT NULL DEFAULT 'KGS' CHECK (currency='KGS'),
  "createdById" uuid REFERENCES staff_users(id) ON DELETE SET NULL,
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  UNIQUE ("propertyId",id),
  UNIQUE ("propertyId","supplierName","documentReference")
);

CREATE TABLE kitchen_supplier_document_lines (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL,
  "documentId" uuid NOT NULL,
  "stockItemId" uuid NOT NULL,
  quantity numeric(16,6) NOT NULL CHECK (quantity>0),
  "unitCostKgs" numeric(16,4) NOT NULL CHECK ("unitCostKgs">=0),
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT supplier_line_document_fk FOREIGN KEY ("propertyId","documentId")
    REFERENCES kitchen_supplier_documents("propertyId",id) ON DELETE RESTRICT,
  CONSTRAINT supplier_line_stock_fk FOREIGN KEY ("propertyId","stockItemId")
    REFERENCES kitchen_stock_items("propertyId",id) ON DELETE RESTRICT,
  UNIQUE ("propertyId",id),
  UNIQUE ("propertyId",id,"stockItemId")
);
CREATE INDEX kitchen_supplier_lines_document_idx
  ON kitchen_supplier_document_lines ("propertyId","documentId");

-- One procurement stock movement can refer to one immutable supplier source line.
-- No retroactive inference from unrelated owner manual expenses.
CREATE UNIQUE INDEX kitchen_procurement_receipts_property_id_unique
  ON kitchen_procurement_receipts ("propertyId",id);

CREATE TABLE kitchen_supplier_receipt_links (
  "receiptId" uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL,
  "documentLineId" uuid NOT NULL,
  "stockItemId" uuid NOT NULL,
  quantity numeric(16,6) NOT NULL CHECK (quantity>0),
  "unitCostKgs" numeric(16,4) NOT NULL CHECK ("unitCostKgs">=0),
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT supplier_receipt_existing_fk FOREIGN KEY ("propertyId","receiptId")
    REFERENCES kitchen_procurement_receipts("propertyId",id) ON DELETE RESTRICT,
  CONSTRAINT supplier_receipt_line_fk FOREIGN KEY ("propertyId","documentLineId","stockItemId")
    REFERENCES kitchen_supplier_document_lines("propertyId",id,"stockItemId") ON DELETE RESTRICT
);
CREATE INDEX kitchen_supplier_receipt_links_line_idx
  ON kitchen_supplier_receipt_links ("propertyId","documentLineId");

-- These are supplier payable settlements, never customer Payments.
CREATE TABLE kitchen_supplier_settlements (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL,
  "documentId" uuid NOT NULL,
  "amountKgs" numeric(20,4) NOT NULL CHECK ("amountKgs">0),
  "paidOn" date NOT NULL,
  method text NOT NULL CHECK (method IN ('CASH','BANK_TRANSFER','CARD','OTHER')),
  reference text CHECK (reference IS NULL OR char_length(reference) BETWEEN 1 AND 150),
  "recordedById" uuid REFERENCES staff_users(id) ON DELETE SET NULL,
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT kitchen_supplier_settlement_document_fk FOREIGN KEY ("propertyId","documentId")
    REFERENCES kitchen_supplier_documents("propertyId",id) ON DELETE RESTRICT
);
CREATE INDEX kitchen_supplier_settlements_document_idx
  ON kitchen_supplier_settlements ("propertyId","documentId");
