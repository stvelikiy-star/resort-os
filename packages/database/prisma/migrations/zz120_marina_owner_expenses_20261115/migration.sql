-- Additive owner-only expense obligations and separately confirmed manual settlement facts.
-- Neither a posted expense nor a payment recording creates Resort OS customer Payments.
CREATE TABLE owner_expenses (
 id uuid PRIMARY KEY,
 "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
 "expenseDate" date NOT NULL,
 category text NOT NULL CHECK (category IN ('SUPPLIES','UTILITIES','PAYROLL','MAINTENANCE','RENT','MARKETING','OTHER')),
 title text NOT NULL CHECK (char_length(trim(title)) BETWEEN 1 AND 150),
 "amountKgs" bigint NOT NULL CHECK ("amountKgs" > 0),
 "supplierName" text CHECK ("supplierName" IS NULL OR char_length("supplierName") BETWEEN 1 AND 150),
 "documentReference" text CHECK ("documentReference" IS NULL OR char_length("documentReference") BETWEEN 1 AND 150),
 notes text CHECK (notes IS NULL OR char_length(notes)<=500),
 status text NOT NULL DEFAULT 'POSTED' CHECK (status IN ('POSTED','VOID')),
 "createdById" uuid REFERENCES staff_users(id) ON DELETE SET NULL,
 "voidedById" uuid REFERENCES staff_users(id) ON DELETE SET NULL,
 "voidReason" text,
 "createdAt" timestamptz NOT NULL DEFAULT now(),
 "voidedAt" timestamptz,
 CONSTRAINT owner_expenses_void_reason_check CHECK (
   (status='POSTED' AND "voidReason" IS NULL AND "voidedAt" IS NULL)
   OR (status='VOID' AND "voidReason" IS NOT NULL AND char_length(trim("voidReason")) BETWEEN 5 AND 500 AND "voidedAt" IS NOT NULL)
 ),
 UNIQUE ("propertyId",id)
);
CREATE INDEX owner_expenses_property_date_idx ON owner_expenses ("propertyId","expenseDate" DESC);
CREATE TABLE owner_expense_settlements (
 id uuid PRIMARY KEY,
 "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
 "expenseId" uuid NOT NULL,
 "amountKgs" bigint NOT NULL CHECK ("amountKgs" > 0),
 "paidOn" date NOT NULL,
 method text NOT NULL CHECK(method IN ('CASH','BANK_TRANSFER','CARD','OTHER')),
 reference text CHECK(reference IS NULL OR char_length(reference) BETWEEN 1 AND 150),
 "recordedById" uuid REFERENCES staff_users(id) ON DELETE SET NULL,
 "createdAt" timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT owner_expense_settlement_fk FOREIGN KEY ("propertyId","expenseId")
   REFERENCES owner_expenses("propertyId",id)
);
CREATE INDEX owner_expense_settlements_expense_idx
 ON owner_expense_settlements ("propertyId","expenseId");
