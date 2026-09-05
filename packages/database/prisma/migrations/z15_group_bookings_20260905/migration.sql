CREATE TABLE booking_groups (
    id uuid PRIMARY KEY,
    "propertyId" uuid NOT NULL,
    code text NOT NULL,
    name text NOT NULL,
    "contactGuestId" uuid,
    "contactName" text NOT NULL,
    "contactPhone" text NOT NULL,
    "contactEmail" text,
    "checkIn" date NOT NULL,
    "checkOut" date NOT NULL,
    status text NOT NULL DEFAULT 'ACTIVE',
    notes text,
    "createdById" uuid,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT booking_groups_property_fkey FOREIGN KEY ("propertyId") REFERENCES properties(id) ON DELETE CASCADE,
    CONSTRAINT booking_groups_contact_guest_fkey FOREIGN KEY ("contactGuestId") REFERENCES guests(id) ON DELETE SET NULL,
    CONSTRAINT booking_groups_created_by_fkey FOREIGN KEY ("createdById") REFERENCES staff_users(id) ON DELETE SET NULL,
    CONSTRAINT booking_groups_dates_check CHECK ("checkOut" > "checkIn"),
    CONSTRAINT booking_groups_status_check CHECK (status IN ('ACTIVE','CANCELLED','COMPLETED'))
);
CREATE UNIQUE INDEX booking_groups_property_code_key ON booking_groups ("propertyId",code);
CREATE INDEX booking_groups_property_dates_idx ON booking_groups ("propertyId","checkIn","checkOut",status);

CREATE TABLE booking_group_members (
    id uuid PRIMARY KEY,
    "groupId" uuid NOT NULL,
    "reservationId" uuid NOT NULL,
    "roomId" uuid NOT NULL,
    "memberLabel" text,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT booking_group_members_group_fkey FOREIGN KEY ("groupId") REFERENCES booking_groups(id) ON DELETE CASCADE,
    CONSTRAINT booking_group_members_reservation_fkey FOREIGN KEY ("reservationId") REFERENCES reservations(id) ON DELETE CASCADE,
    CONSTRAINT booking_group_members_room_fkey FOREIGN KEY ("roomId") REFERENCES rooms(id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX booking_group_members_reservation_key ON booking_group_members ("reservationId");
CREATE UNIQUE INDEX booking_group_members_group_room_key ON booking_group_members ("groupId","roomId");
CREATE INDEX booking_group_members_group_idx ON booking_group_members ("groupId");
