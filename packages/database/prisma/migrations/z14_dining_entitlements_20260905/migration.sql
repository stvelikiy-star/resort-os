-- Dining entitlement + seating domain for Three Crowns Resort OS.
-- PostgreSQL/Resort Core remain authoritative. Included meal rights are not Payments
-- and table seating is linked to Stay/Reservation rather than a room code string.

CREATE TABLE dining_entitlements (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    "stayId" uuid NOT NULL,
    "reservationId" uuid NOT NULL,
    "guestId" uuid NOT NULL,
    "serviceDate" date NOT NULL,
    "mealType" text NOT NULL,
    "adultPortions" integer NOT NULL DEFAULT 0,
    "childPortions" integer NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'ACTIVE',
    source text NOT NULL DEFAULT 'MANAGER',
    notes text,
    "createdById" uuid,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT dining_entitlements_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT dining_entitlements_stay_fkey FOREIGN KEY ("stayId") REFERENCES stays(id) ON DELETE CASCADE,
    CONSTRAINT dining_entitlements_reservation_fkey FOREIGN KEY ("reservationId") REFERENCES reservations(id) ON DELETE CASCADE,
    CONSTRAINT dining_entitlements_guest_fkey FOREIGN KEY ("guestId") REFERENCES guests(id) ON DELETE RESTRICT,
    CONSTRAINT dining_entitlements_created_by_fkey FOREIGN KEY ("createdById") REFERENCES staff_users(id) ON DELETE SET NULL,
    CONSTRAINT dining_entitlements_meal_check CHECK ("mealType" IN ('BREAKFAST','LUNCH','DINNER')),
    CONSTRAINT dining_entitlements_status_check CHECK (status IN ('ACTIVE','CANCELLED')),
    CONSTRAINT dining_entitlements_adult_check CHECK ("adultPortions" BETWEEN 0 AND 50),
    CONSTRAINT dining_entitlements_child_check CHECK ("childPortions" BETWEEN 0 AND 50),
    CONSTRAINT dining_entitlements_nonempty_check CHECK ("adultPortions" + "childPortions" > 0)
);
CREATE UNIQUE INDEX dining_entitlements_stay_day_meal_key
    ON dining_entitlements ("stayId", "serviceDate", "mealType");
CREATE INDEX dining_entitlements_property_day_meal_idx
    ON dining_entitlements ("propertyId", "serviceDate", "mealType", status);
CREATE INDEX dining_entitlements_reservation_idx
    ON dining_entitlements ("reservationId", "serviceDate");

ALTER TABLE kitchen_tables ADD COLUMN "zoneLabel" text;
ALTER TABLE kitchen_tables ADD COLUMN "positionX" integer;
ALTER TABLE kitchen_tables ADD COLUMN "positionY" integer;
ALTER TABLE kitchen_tables ADD CONSTRAINT kitchen_tables_position_x_check CHECK ("positionX" IS NULL OR "positionX" BETWEEN 0 AND 10000);
ALTER TABLE kitchen_tables ADD CONSTRAINT kitchen_tables_position_y_check CHECK ("positionY" IS NULL OR "positionY" BETWEEN 0 AND 10000);

CREATE TABLE dining_table_sessions (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    "stayId" uuid NOT NULL,
    "reservationId" uuid NOT NULL,
    "tableId" uuid NOT NULL,
    "waiterId" uuid,
    "serviceDate" date NOT NULL,
    "mealType" text,
    status text NOT NULL DEFAULT 'WAITING',
    "partySize" integer NOT NULL,
    adults integer NOT NULL DEFAULT 0,
    children integer NOT NULL DEFAULT 0,
    notes text,
    source text NOT NULL DEFAULT 'DINING_FLOOR',
    "seatedAt" timestamptz,
    "releasedAt" timestamptz,
    "createdById" uuid,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT dining_table_sessions_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT dining_table_sessions_stay_fkey FOREIGN KEY ("stayId") REFERENCES stays(id) ON DELETE CASCADE,
    CONSTRAINT dining_table_sessions_reservation_fkey FOREIGN KEY ("reservationId") REFERENCES reservations(id) ON DELETE CASCADE,
    CONSTRAINT dining_table_sessions_table_fkey FOREIGN KEY ("tableId") REFERENCES kitchen_tables(id) ON DELETE RESTRICT,
    CONSTRAINT dining_table_sessions_waiter_fkey FOREIGN KEY ("waiterId") REFERENCES staff_users(id) ON DELETE SET NULL,
    CONSTRAINT dining_table_sessions_created_by_fkey FOREIGN KEY ("createdById") REFERENCES staff_users(id) ON DELETE SET NULL,
    CONSTRAINT dining_table_sessions_meal_check CHECK ("mealType" IS NULL OR "mealType" IN ('BREAKFAST','LUNCH','DINNER','OTHER')),
    CONSTRAINT dining_table_sessions_status_check CHECK (status IN ('WAITING','SEATED','RELEASED','CANCELLED')),
    CONSTRAINT dining_table_sessions_party_check CHECK ("partySize" BETWEEN 1 AND 30),
    CONSTRAINT dining_table_sessions_adults_check CHECK (adults BETWEEN 0 AND 30),
    CONSTRAINT dining_table_sessions_children_check CHECK (children BETWEEN 0 AND 30),
    CONSTRAINT dining_table_sessions_party_sum_check CHECK (adults + children <= "partySize")
);
CREATE INDEX dining_table_sessions_property_day_idx
    ON dining_table_sessions ("propertyId", "serviceDate", status, "mealType");
CREATE INDEX dining_table_sessions_waiter_idx
    ON dining_table_sessions ("waiterId", status, "serviceDate");
CREATE INDEX dining_table_sessions_table_idx
    ON dining_table_sessions ("tableId", status, "serviceDate");
CREATE UNIQUE INDEX dining_table_sessions_active_stay_key
    ON dining_table_sessions ("stayId") WHERE status IN ('WAITING','SEATED');
CREATE UNIQUE INDEX dining_table_sessions_seated_table_key
    ON dining_table_sessions ("tableId") WHERE status='SEATED';

-- Explicit non-payment commercial bridge for food/service charges.
-- This is intentionally separate from payments: a charge says "guest owes", Payment says "money received".
CREATE TABLE guest_folio_charges (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    "reservationId" uuid NOT NULL,
    "stayId" uuid,
    "guestId" uuid,
    "sourceType" text NOT NULL,
    "sourceId" uuid,
    code text NOT NULL,
    description text NOT NULL,
    "amountKgs" integer NOT NULL,
    status text NOT NULL DEFAULT 'OPEN',
    "serviceDate" date,
    "createdByType" text NOT NULL,
    "createdById" text,
    metadata jsonb,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT guest_folio_charges_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT guest_folio_charges_reservation_fkey FOREIGN KEY ("reservationId") REFERENCES reservations(id) ON DELETE CASCADE,
    CONSTRAINT guest_folio_charges_stay_fkey FOREIGN KEY ("stayId") REFERENCES stays(id) ON DELETE SET NULL,
    CONSTRAINT guest_folio_charges_guest_fkey FOREIGN KEY ("guestId") REFERENCES guests(id) ON DELETE SET NULL,
    CONSTRAINT guest_folio_charges_amount_check CHECK ("amountKgs" >= 0),
    CONSTRAINT guest_folio_charges_status_check CHECK (status IN ('OPEN','PAID','WAIVED','VOID')),
    CONSTRAINT guest_folio_charges_source_check CHECK ("sourceType" IN ('KITCHEN_ORDER','GUEST_SERVICE','MANUAL','BANQUET'))
);
CREATE UNIQUE INDEX guest_folio_charges_source_key
    ON guest_folio_charges ("sourceType", "sourceId") WHERE "sourceId" IS NOT NULL AND status <> 'VOID';
CREATE INDEX guest_folio_charges_reservation_status_idx
    ON guest_folio_charges ("reservationId", status, "createdAt");
CREATE INDEX guest_folio_charges_property_date_idx
    ON guest_folio_charges ("propertyId", "serviceDate", status);

ALTER TABLE kitchen_orders ADD COLUMN "folioChargeId" uuid;
ALTER TABLE kitchen_orders ADD CONSTRAINT kitchen_orders_folio_charge_fkey FOREIGN KEY ("folioChargeId") REFERENCES guest_folio_charges(id) ON DELETE SET NULL;
CREATE UNIQUE INDEX kitchen_orders_folio_charge_key ON kitchen_orders ("folioChargeId") WHERE "folioChargeId" IS NOT NULL;
