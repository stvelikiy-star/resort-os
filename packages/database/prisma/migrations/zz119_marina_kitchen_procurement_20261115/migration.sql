-- Explicit kitchen procurement lifecycle. Planning and approval do not change stock or create payments.
CREATE TABLE kitchen_procurement_requests (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  "stockItemId" uuid NOT NULL,
  "requestedQuantity" numeric(16,6) NOT NULL CHECK ("requestedQuantity" > 0),
  "receivedQuantity" numeric(16,6) NOT NULL DEFAULT 0 CHECK ("receivedQuantity" >= 0),
  status text NOT NULL DEFAULT 'REQUESTED',
  "serviceDate" date,
  notes text,
  "createdById" uuid REFERENCES staff_users(id) ON DELETE SET NULL,
  "approvedById" uuid REFERENCES staff_users(id) ON DELETE SET NULL,
  "approvedAt" timestamptz,
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  "updatedAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT kitchen_proc_request_status_check CHECK (
    (status='REQUESTED' AND "receivedQuantity"=0 AND "approvedAt" IS NULL)
    OR (status='APPROVED' AND "receivedQuantity"=0 AND "approvedAt" IS NOT NULL)
    OR (status='PARTIAL' AND "receivedQuantity">0 AND "receivedQuantity"<"requestedQuantity" AND "approvedAt" IS NOT NULL)
    OR (status='RECEIVED' AND "receivedQuantity"="requestedQuantity" AND "approvedAt" IS NOT NULL)
  ),
  CONSTRAINT kitchen_proc_request_quantity_check CHECK ("receivedQuantity"<="requestedQuantity"),
  CONSTRAINT kitchen_proc_request_notes_check CHECK (notes IS NULL OR char_length(notes)<=500),
  CONSTRAINT kitchen_proc_request_item_fk FOREIGN KEY ("propertyId","stockItemId")
    REFERENCES kitchen_stock_items("propertyId",id),
  UNIQUE ("propertyId",id)
);
CREATE INDEX kitchen_proc_request_property_date_idx
  ON kitchen_procurement_requests ("propertyId","createdAt" DESC);
CREATE TABLE kitchen_procurement_receipts (
  id uuid PRIMARY KEY REFERENCES kitchen_stock_movements(id) ON DELETE RESTRICT,
  "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  "requestId" uuid NOT NULL,
  quantity numeric(16,6) NOT NULL CHECK(quantity>0),
  "createdById" uuid REFERENCES staff_users(id) ON DELETE SET NULL,
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT kitchen_proc_receipt_request_fk FOREIGN KEY ("propertyId","requestId")
    REFERENCES kitchen_procurement_requests("propertyId",id)
);
CREATE INDEX kitchen_proc_receipt_request_idx ON kitchen_procurement_receipts ("propertyId","requestId");
