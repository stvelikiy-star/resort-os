-- Separate short-lived hotel inventory holds from long-lived owner room blocks.
CREATE TABLE IF NOT EXISTS marina_reservation_holds (
 id uuid PRIMARY KEY,
 "propertyId" uuid NOT NULL REFERENCES properties(id),
 "roomId" uuid NOT NULL REFERENCES rooms(id),
 "inventoryBlockId" uuid NOT NULL UNIQUE REFERENCES inventory_blocks(id),
 "createdBy" uuid NOT NULL,
 "checkIn" date NOT NULL,
 "checkOut" date NOT NULL,
 "guestName" text NOT NULL,
 "guestPhone" text NOT NULL,
 "createdAt" timestamptz NOT NULL DEFAULT now(),
 "expiresAt" timestamptz NOT NULL DEFAULT (now() + interval '60 minutes'),
 "confirmedReservationId" uuid NULL REFERENCES reservations(id),
 "releasedAt" timestamptz NULL,
 CONSTRAINT marina_hold_valid_range CHECK ("checkOut" > "checkIn"),
 CONSTRAINT marina_hold_valid_expiration CHECK ("expiresAt" > "createdAt")
);
CREATE INDEX IF NOT EXISTS marina_holds_expiry_active_idx
 ON marina_reservation_holds ("expiresAt") WHERE "releasedAt" IS NULL AND "confirmedReservationId" IS NULL;
CREATE INDEX IF NOT EXISTS marina_holds_property_idx ON marina_reservation_holds ("propertyId", "roomId");
