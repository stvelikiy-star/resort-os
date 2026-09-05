-- Dining Service Control extends Kitchen Operations without changing hotel reservation totals or Payment records.
-- Guest-visible food remains fail-closed: a menu item must be active, non-draft and explicitly published for the hotel-local service date.

CREATE TABLE kitchen_menu_availability (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    "menuItemId" uuid NOT NULL,
    "serviceDate" date NOT NULL,
    "mealType" text NOT NULL,
    "isAvailable" boolean NOT NULL DEFAULT true,
    "soldOut" boolean NOT NULL DEFAULT false,
    notes text,
    "createdById" uuid,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kitchen_menu_availability_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT kitchen_menu_availability_item_fkey FOREIGN KEY ("menuItemId") REFERENCES kitchen_menu_items(id) ON DELETE CASCADE,
    CONSTRAINT kitchen_menu_availability_created_by_fkey FOREIGN KEY ("createdById") REFERENCES staff_users(id) ON DELETE SET NULL,
    CONSTRAINT kitchen_menu_availability_meal_check CHECK ("mealType" IN ('BREAKFAST','LUNCH','DINNER','OTHER'))
);
CREATE UNIQUE INDEX kitchen_menu_availability_item_day_meal_key
    ON kitchen_menu_availability ("menuItemId", "serviceDate", "mealType");
CREATE INDEX kitchen_menu_availability_property_day_idx
    ON kitchen_menu_availability ("propertyId", "serviceDate", "mealType", "isAvailable", "soldOut");

CREATE TABLE kitchen_table_reservations (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    "tableId" uuid NOT NULL,
    "stayId" uuid,
    "reservationId" uuid,
    "guestName" text NOT NULL,
    phone text,
    "partySize" integer NOT NULL,
    "startsAt" timestamptz NOT NULL,
    "endsAt" timestamptz NOT NULL,
    status text NOT NULL DEFAULT 'BOOKED',
    notes text,
    "createdById" uuid,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kitchen_table_reservations_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT kitchen_table_reservations_table_fkey FOREIGN KEY ("tableId") REFERENCES kitchen_tables(id) ON DELETE CASCADE,
    CONSTRAINT kitchen_table_reservations_stay_fkey FOREIGN KEY ("stayId") REFERENCES stays(id) ON DELETE SET NULL,
    CONSTRAINT kitchen_table_reservations_reservation_fkey FOREIGN KEY ("reservationId") REFERENCES reservations(id) ON DELETE SET NULL,
    CONSTRAINT kitchen_table_reservations_created_by_fkey FOREIGN KEY ("createdById") REFERENCES staff_users(id) ON DELETE SET NULL,
    CONSTRAINT kitchen_table_reservations_party_check CHECK ("partySize" BETWEEN 1 AND 30),
    CONSTRAINT kitchen_table_reservations_time_check CHECK ("endsAt" > "startsAt"),
    CONSTRAINT kitchen_table_reservations_status_check CHECK (status IN ('BOOKED','SEATED','COMPLETED','CANCELLED','NO_SHOW'))
);
CREATE INDEX kitchen_table_reservations_property_start_idx
    ON kitchen_table_reservations ("propertyId", "startsAt", status);
CREATE INDEX kitchen_table_reservations_table_window_idx
    ON kitchen_table_reservations ("tableId", "startsAt", "endsAt", status);

ALTER TABLE kitchen_orders ADD COLUMN "waiterId" uuid;
ALTER TABLE kitchen_orders
    ADD CONSTRAINT kitchen_orders_waiter_fkey FOREIGN KEY ("waiterId") REFERENCES staff_users(id) ON DELETE SET NULL;
CREATE INDEX kitchen_orders_waiter_status_idx ON kitchen_orders ("waiterId", status, "openedAt" DESC);
