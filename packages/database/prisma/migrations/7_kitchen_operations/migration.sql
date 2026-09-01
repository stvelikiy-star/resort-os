-- Kitchen operations are an operational sales/service domain.
-- They never mutate Reservation.totalKgs or create hotel Payment records automatically.

CREATE TABLE kitchen_menu_items (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    code text NOT NULL,
    category text NOT NULL,
    "nameRu" text NOT NULL,
    "nameKg" text NOT NULL,
    "nameEn" text NOT NULL,
    "descriptionRu" text,
    "descriptionKg" text,
    "descriptionEn" text,
    "priceKgs" integer NOT NULL,
    "isActive" boolean NOT NULL DEFAULT true,
    "isDraft" boolean NOT NULL DEFAULT true,
    "sortOrder" integer NOT NULL DEFAULT 0,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kitchen_menu_items_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT kitchen_menu_items_price_check CHECK ("priceKgs" >= 0),
    CONSTRAINT kitchen_menu_items_category_check CHECK (category IN ('BREAKFAST','SOUP','SALAD','MAIN','SIDE','DESSERT','DRINK'))
);
CREATE UNIQUE INDEX kitchen_menu_items_property_code_key ON kitchen_menu_items ("propertyId", code);
CREATE INDEX kitchen_menu_items_property_active_sort_idx ON kitchen_menu_items ("propertyId", "isActive", "sortOrder", category);

CREATE TABLE kitchen_tables (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    code text NOT NULL,
    name text NOT NULL,
    seats integer NOT NULL,
    status text NOT NULL DEFAULT 'AVAILABLE',
    "isActive" boolean NOT NULL DEFAULT true,
    notes text,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kitchen_tables_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT kitchen_tables_seats_check CHECK (seats BETWEEN 1 AND 30),
    CONSTRAINT kitchen_tables_status_check CHECK (status IN ('AVAILABLE','RESERVED','OCCUPIED','CLEANING','OUT_OF_SERVICE'))
);
CREATE UNIQUE INDEX kitchen_tables_property_code_key ON kitchen_tables ("propertyId", code);
CREATE INDEX kitchen_tables_property_status_idx ON kitchen_tables ("propertyId", status, "isActive");

CREATE TABLE kitchen_orders (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    "orderNumber" text NOT NULL,
    status text NOT NULL DEFAULT 'NEW',
    source text NOT NULL,
    "tableId" uuid,
    "stayId" uuid,
    "reservationId" uuid,
    "roomId" uuid,
    "guestTaskId" uuid,
    "guestCount" integer NOT NULL DEFAULT 1,
    "mealType" text,
    notes text,
    "totalKgs" integer NOT NULL DEFAULT 0,
    "openedById" uuid,
    "openedAt" timestamptz NOT NULL DEFAULT now(),
    "acceptedAt" timestamptz,
    "readyAt" timestamptz,
    "completedAt" timestamptz,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kitchen_orders_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT kitchen_orders_table_fkey FOREIGN KEY ("tableId") REFERENCES kitchen_tables(id) ON DELETE SET NULL,
    CONSTRAINT kitchen_orders_stay_fkey FOREIGN KEY ("stayId") REFERENCES stays(id) ON DELETE SET NULL,
    CONSTRAINT kitchen_orders_reservation_fkey FOREIGN KEY ("reservationId") REFERENCES reservations(id) ON DELETE SET NULL,
    CONSTRAINT kitchen_orders_room_fkey FOREIGN KEY ("roomId") REFERENCES rooms(id) ON DELETE SET NULL,
    CONSTRAINT kitchen_orders_guest_task_fkey FOREIGN KEY ("guestTaskId") REFERENCES operational_tasks(id) ON DELETE SET NULL,
    CONSTRAINT kitchen_orders_opened_by_fkey FOREIGN KEY ("openedById") REFERENCES staff_users(id) ON DELETE SET NULL,
    CONSTRAINT kitchen_orders_status_check CHECK (status IN ('NEW','ACCEPTED','COOKING','READY','SERVED','CANCELLED')),
    CONSTRAINT kitchen_orders_source_check CHECK (source IN ('TABLE','ROOM','GUEST_OS','RECEPTION','MANAGER')),
    CONSTRAINT kitchen_orders_guest_count_check CHECK ("guestCount" BETWEEN 1 AND 30),
    CONSTRAINT kitchen_orders_total_check CHECK ("totalKgs" >= 0),
    CONSTRAINT kitchen_orders_meal_type_check CHECK ("mealType" IS NULL OR "mealType" IN ('BREAKFAST','LUNCH','DINNER','OTHER'))
);
CREATE UNIQUE INDEX kitchen_orders_property_number_key ON kitchen_orders ("propertyId", "orderNumber");
CREATE UNIQUE INDEX kitchen_orders_guest_task_key ON kitchen_orders ("guestTaskId") WHERE "guestTaskId" IS NOT NULL;
CREATE INDEX kitchen_orders_property_status_opened_idx ON kitchen_orders ("propertyId", status, "openedAt" DESC);
CREATE INDEX kitchen_orders_table_status_idx ON kitchen_orders ("tableId", status);
CREATE INDEX kitchen_orders_stay_idx ON kitchen_orders ("stayId", "openedAt" DESC);

CREATE TABLE kitchen_order_items (
    id uuid PRIMARY KEY,
    "orderId" uuid NOT NULL,
    "menuItemId" uuid NOT NULL,
    quantity integer NOT NULL,
    "unitPriceKgs" integer NOT NULL,
    "lineTotalKgs" integer NOT NULL,
    status text NOT NULL DEFAULT 'NEW',
    notes text,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT kitchen_order_items_order_fkey FOREIGN KEY ("orderId") REFERENCES kitchen_orders(id) ON DELETE CASCADE,
    CONSTRAINT kitchen_order_items_menu_fkey FOREIGN KEY ("menuItemId") REFERENCES kitchen_menu_items(id) ON DELETE RESTRICT,
    CONSTRAINT kitchen_order_items_quantity_check CHECK (quantity BETWEEN 1 AND 99),
    CONSTRAINT kitchen_order_items_price_check CHECK ("unitPriceKgs" >= 0 AND "lineTotalKgs" >= 0),
    CONSTRAINT kitchen_order_items_status_check CHECK (status IN ('NEW','COOKING','READY','SERVED','CANCELLED'))
);
CREATE INDEX kitchen_order_items_order_idx ON kitchen_order_items ("orderId", "createdAt");
CREATE INDEX kitchen_order_items_menu_idx ON kitchen_order_items ("menuItemId", "createdAt" DESC);
