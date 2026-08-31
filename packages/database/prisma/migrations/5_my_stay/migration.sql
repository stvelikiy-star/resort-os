-- Three Crowns MY STAY / Dining / ancillary folio / smart access extension.
-- EXTEND > REWRITE: existing reservations, rooms, payments and operational_tasks remain authoritative.

ALTER TYPE "StaffRole" ADD VALUE IF NOT EXISTS 'ADMIN';
ALTER TYPE "StaffRole" ADD VALUE IF NOT EXISTS 'RECEPTION';
ALTER TYPE "StaffRole" ADD VALUE IF NOT EXISTS 'DINING';

CREATE TABLE IF NOT EXISTS guest_access_credentials (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    "reservationId" uuid NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
    "pinHash" text NOT NULL,
    "activationTokenHash" text,
    "isActive" boolean NOT NULL DEFAULT true,
    "expiresAt" timestamptz NOT NULL,
    "issuedAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    UNIQUE ("reservationId")
);
CREATE INDEX IF NOT EXISTS guest_access_credentials_property_active_idx
    ON guest_access_credentials ("propertyId", "isActive", "expiresAt");

CREATE TABLE IF NOT EXISTS guest_sessions (
    id uuid PRIMARY KEY,
    "credentialId" uuid NOT NULL REFERENCES guest_access_credentials(id) ON DELETE CASCADE,
    "tokenHash" text NOT NULL UNIQUE,
    "expiresAt" timestamptz NOT NULL,
    "revokedAt" timestamptz,
    "lastSeenAt" timestamptz NOT NULL DEFAULT now(),
    "createdAt" timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS guest_sessions_credential_expires_idx
    ON guest_sessions ("credentialId", "expiresAt");

CREATE TABLE IF NOT EXISTS reservation_meal_plans (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    "reservationId" uuid NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
    "serviceDate" date NOT NULL,
    "mealType" text NOT NULL CHECK ("mealType" IN ('BREAKFAST','LUNCH','DINNER')),
    included boolean NOT NULL DEFAULT false,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    UNIQUE ("reservationId", "serviceDate", "mealType")
);
CREATE INDEX IF NOT EXISTS reservation_meal_plans_property_date_idx
    ON reservation_meal_plans ("propertyId", "serviceDate", "mealType");

CREATE TABLE IF NOT EXISTS dining_menu_items (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    "serviceDate" date NOT NULL,
    "mealType" text NOT NULL CHECK ("mealType" IN ('BREAKFAST','LUNCH','DINNER')),
    name text NOT NULL,
    description text,
    "priceKgs" integer NOT NULL DEFAULT 0 CHECK ("priceKgs" >= 0),
    "availableQty" integer CHECK ("availableQty" IS NULL OR "availableQty" >= 0),
    "includedInMealPlan" boolean NOT NULL DEFAULT false,
    active boolean NOT NULL DEFAULT true,
    "sortOrder" integer NOT NULL DEFAULT 0,
    "createdById" uuid REFERENCES staff_users(id) ON DELETE SET NULL,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS dining_menu_items_property_date_idx
    ON dining_menu_items ("propertyId", "serviceDate", "mealType", active, "sortOrder");

CREATE TABLE IF NOT EXISTS dining_orders (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    "reservationId" uuid NOT NULL REFERENCES reservations(id) ON DELETE RESTRICT,
    "serviceDate" date NOT NULL,
    "mealType" text NOT NULL CHECK ("mealType" IN ('BREAKFAST','LUNCH','DINNER')),
    status text NOT NULL DEFAULT 'NEW' CHECK (status IN ('NEW','ACCEPTED','PREPARING','READY','DELIVERED','CANCELLED')),
    "paymentMode" text NOT NULL DEFAULT 'ROOM_FOLIO' CHECK ("paymentMode" IN ('INCLUDED','ROOM_FOLIO','RECEPTION')),
    "totalKgs" integer NOT NULL DEFAULT 0 CHECK ("totalKgs" >= 0),
    notes text,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    "completedAt" timestamptz
);
CREATE INDEX IF NOT EXISTS dining_orders_property_status_idx
    ON dining_orders ("propertyId", status, "serviceDate", "mealType");
CREATE INDEX IF NOT EXISTS dining_orders_reservation_idx
    ON dining_orders ("reservationId", "createdAt");

CREATE TABLE IF NOT EXISTS dining_order_items (
    id uuid PRIMARY KEY,
    "orderId" uuid NOT NULL REFERENCES dining_orders(id) ON DELETE CASCADE,
    "menuItemId" uuid NOT NULL REFERENCES dining_menu_items(id) ON DELETE RESTRICT,
    name text NOT NULL,
    quantity integer NOT NULL CHECK (quantity > 0),
    "unitPriceKgs" integer NOT NULL CHECK ("unitPriceKgs" >= 0),
    "lineTotalKgs" integer NOT NULL CHECK ("lineTotalKgs" >= 0),
    "includedByPlan" boolean NOT NULL DEFAULT false,
    "createdAt" timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS dining_order_items_order_idx ON dining_order_items ("orderId");

CREATE TABLE IF NOT EXISTS reservation_charges (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    "reservationId" uuid NOT NULL REFERENCES reservations(id) ON DELETE RESTRICT,
    "sourceType" text NOT NULL,
    "sourceId" uuid,
    description text NOT NULL,
    "amountKgs" integer NOT NULL CHECK ("amountKgs" >= 0),
    status text NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','PAID','VOID')),
    "paymentId" uuid REFERENCES payments(id) ON DELETE SET NULL,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    "paidAt" timestamptz
);
CREATE UNIQUE INDEX IF NOT EXISTS reservation_charges_source_unique_idx
    ON reservation_charges ("sourceType", "sourceId") WHERE "sourceId" IS NOT NULL;
CREATE INDEX IF NOT EXISTS reservation_charges_reservation_status_idx
    ON reservation_charges ("reservationId", status, "createdAt");

CREATE TABLE IF NOT EXISTS smart_access_points (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    code text NOT NULL,
    name text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('ROOM','TOILET','OTHER')),
    "roomId" uuid REFERENCES rooms(id) ON DELETE SET NULL,
    "priceKgs" integer NOT NULL DEFAULT 0 CHECK ("priceKgs" >= 0),
    active boolean NOT NULL DEFAULT false,
    "controllerRef" text,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    UNIQUE ("propertyId", code)
);
CREATE INDEX IF NOT EXISTS smart_access_points_room_idx ON smart_access_points ("roomId", active);

CREATE TABLE IF NOT EXISTS smart_access_grants (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    "accessPointId" uuid NOT NULL REFERENCES smart_access_points(id) ON DELETE CASCADE,
    "reservationId" uuid REFERENCES reservations(id) ON DELETE CASCADE,
    "guestSessionId" uuid REFERENCES guest_sessions(id) ON DELETE SET NULL,
    "paymentId" uuid REFERENCES payments(id) ON DELETE SET NULL,
    "tokenHash" text NOT NULL UNIQUE,
    status text NOT NULL DEFAULT 'ISSUED' CHECK (status IN ('ISSUED','USED','EXPIRED','REVOKED')),
    "expiresAt" timestamptz NOT NULL,
    "usedAt" timestamptz,
    "createdAt" timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS smart_access_grants_point_status_idx
    ON smart_access_grants ("accessPointId", status, "expiresAt");

COMMENT ON TABLE guest_access_credentials IS 'MY STAY credential bound to one reservation; QR activation token is not a room key.';
COMMENT ON TABLE reservation_charges IS 'Ancillary folio ledger. Accommodation total remains reservation.totalKgs; a charge is PAID only when linked to a RECEIVED Payment.';
COMMENT ON TABLE smart_access_points IS 'Physical access integration points. active=false is fail-closed until real controller E2E is approved.';
