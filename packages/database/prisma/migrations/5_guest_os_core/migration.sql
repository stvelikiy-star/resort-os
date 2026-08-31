-- Extend staff roles required by the operational baseline.
ALTER TYPE "StaffRole" ADD VALUE IF NOT EXISTS 'RECEPTION';
ALTER TYPE "StaffRole" ADD VALUE IF NOT EXISTS 'STORE_STAFF';
ALTER TYPE "StaffRole" ADD VALUE IF NOT EXISTS 'DINING_STAFF';
ALTER TYPE "StaffRole" ADD VALUE IF NOT EXISTS 'CONTENT_MANAGER';

-- Guest OS / stay lifecycle enums.
CREATE TYPE "StayStatus" AS ENUM ('PENDING', 'ACTIVE', 'CHECKED_OUT', 'CANCELLED');
CREATE TYPE "RoomQrStatus" AS ENUM ('ACTIVE', 'REVOKED');
CREATE TYPE "GuestSessionStatus" AS ENUM ('ACTIVE', 'REVOKED', 'EXPIRED');

-- Actual stay lifecycle. Reservation remains the commercial booking authority.
CREATE TABLE "stays" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "reservationId" UUID NOT NULL,
    "guestId" UUID NOT NULL,
    "status" "StayStatus" NOT NULL DEFAULT 'PENDING',
    "actualCheckInAt" TIMESTAMP(3),
    "actualCheckOutAt" TIMESTAMP(3),
    "guestAccessPinHash" TEXT,
    "guestAccessPinIssuedAt" TIMESTAMP(3),
    "guestAccessPinExpiresAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "stays_pkey" PRIMARY KEY ("id")
);

-- Physical room placement during a stay. A stay may have many historical assignments.
CREATE TABLE "room_assignments" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "stayId" UUID NOT NULL,
    "roomId" UUID NOT NULL,
    "startedAt" TIMESTAMP(3) NOT NULL,
    "endedAt" TIMESTAMP(3),
    "source" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "room_assignments_pkey" PRIMARY KEY ("id")
);

-- Permanent room QR credentials. Only hashes of opaque public tokens are persisted.
CREATE TABLE "room_qrs" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "roomId" UUID NOT NULL,
    "tokenHash" TEXT NOT NULL,
    "status" "RoomQrStatus" NOT NULL DEFAULT 'ACTIVE',
    "label" TEXT,
    "issuedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "revokedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "room_qrs_pkey" PRIMARY KEY ("id")
);

-- Authorized guest-device sessions. Only hashed session tokens are stored.
CREATE TABLE "guest_sessions" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "stayId" UUID NOT NULL,
    "guestId" UUID NOT NULL,
    "roomQrId" UUID,
    "tokenHash" TEXT NOT NULL,
    "status" "GuestSessionStatus" NOT NULL DEFAULT 'ACTIVE',
    "verificationMethod" TEXT NOT NULL DEFAULT 'PIN',
    "verifiedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expiresAt" TIMESTAMP(3) NOT NULL,
    "revokedAt" TIMESTAMP(3),
    "lastSeenAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "guest_sessions_pkey" PRIMARY KEY ("id")
);

-- Durable guest timeline events that are not safely represented by a mutable current-state row.
CREATE TABLE "guest_history_events" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "guestId" UUID NOT NULL,
    "stayId" UUID,
    "eventType" TEXT NOT NULL,
    "source" TEXT,
    "payloadJson" JSONB,
    "occurredAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "guest_history_events_pkey" PRIMARY KEY ("id")
);

-- Explicit, staff-approved guest preferences. History itself remains derived from stays/tasks/events.
CREATE TABLE "guest_preferences" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "guestId" UUID NOT NULL,
    "key" TEXT NOT NULL,
    "valueText" TEXT,
    "metadata" JSONB,
    "source" TEXT,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "guest_preferences_pkey" PRIMARY KEY ("id")
);

-- Tie operational requests to the exact stay while preserving current reservation/room links.
ALTER TABLE "operational_tasks" ADD COLUMN "stayId" UUID;

-- Uniques.
CREATE UNIQUE INDEX "stays_reservationId_key" ON "stays"("reservationId");
CREATE UNIQUE INDEX "room_qrs_tokenHash_key" ON "room_qrs"("tokenHash");
CREATE UNIQUE INDEX "guest_sessions_tokenHash_key" ON "guest_sessions"("tokenHash");
CREATE UNIQUE INDEX "guest_preferences_guestId_key_key" ON "guest_preferences"("guestId", "key");

-- At most one current room assignment for a stay and at most one active stay assignment in a room.
CREATE UNIQUE INDEX "room_assignments_one_open_per_stay_idx" ON "room_assignments"("stayId") WHERE "endedAt" IS NULL;
CREATE UNIQUE INDEX "room_assignments_one_open_per_room_idx" ON "room_assignments"("roomId") WHERE "endedAt" IS NULL;

-- At most one active physical QR credential per room.
CREATE UNIQUE INDEX "room_qrs_one_active_per_room_idx" ON "room_qrs"("roomId") WHERE "status" = 'ACTIVE';

-- Query indexes.
CREATE INDEX "stays_propertyId_status_idx" ON "stays"("propertyId", "status");
CREATE INDEX "stays_guestId_createdAt_idx" ON "stays"("guestId", "createdAt");
CREATE INDEX "room_assignments_propertyId_roomId_startedAt_endedAt_idx" ON "room_assignments"("propertyId", "roomId", "startedAt", "endedAt");
CREATE INDEX "room_assignments_stayId_startedAt_idx" ON "room_assignments"("stayId", "startedAt");
CREATE INDEX "room_qrs_propertyId_roomId_status_idx" ON "room_qrs"("propertyId", "roomId", "status");
CREATE INDEX "guest_sessions_propertyId_stayId_status_idx" ON "guest_sessions"("propertyId", "stayId", "status");
CREATE INDEX "guest_sessions_guestId_createdAt_idx" ON "guest_sessions"("guestId", "createdAt");
CREATE INDEX "guest_sessions_expiresAt_status_idx" ON "guest_sessions"("expiresAt", "status");
CREATE INDEX "guest_history_events_propertyId_guestId_occurredAt_idx" ON "guest_history_events"("propertyId", "guestId", "occurredAt");
CREATE INDEX "guest_history_events_stayId_occurredAt_idx" ON "guest_history_events"("stayId", "occurredAt");
CREATE INDEX "guest_preferences_propertyId_guestId_isActive_idx" ON "guest_preferences"("propertyId", "guestId", "isActive");
CREATE INDEX "operational_tasks_stayId_status_idx" ON "operational_tasks"("stayId", "status");

-- Foreign keys.
ALTER TABLE "stays" ADD CONSTRAINT "stays_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "stays" ADD CONSTRAINT "stays_reservationId_fkey" FOREIGN KEY ("reservationId") REFERENCES "reservations"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "stays" ADD CONSTRAINT "stays_guestId_fkey" FOREIGN KEY ("guestId") REFERENCES "guests"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "room_assignments" ADD CONSTRAINT "room_assignments_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "room_assignments" ADD CONSTRAINT "room_assignments_stayId_fkey" FOREIGN KEY ("stayId") REFERENCES "stays"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "room_assignments" ADD CONSTRAINT "room_assignments_roomId_fkey" FOREIGN KEY ("roomId") REFERENCES "rooms"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "room_qrs" ADD CONSTRAINT "room_qrs_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "room_qrs" ADD CONSTRAINT "room_qrs_roomId_fkey" FOREIGN KEY ("roomId") REFERENCES "rooms"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "guest_sessions" ADD CONSTRAINT "guest_sessions_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "guest_sessions" ADD CONSTRAINT "guest_sessions_stayId_fkey" FOREIGN KEY ("stayId") REFERENCES "stays"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "guest_sessions" ADD CONSTRAINT "guest_sessions_guestId_fkey" FOREIGN KEY ("guestId") REFERENCES "guests"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "guest_sessions" ADD CONSTRAINT "guest_sessions_roomQrId_fkey" FOREIGN KEY ("roomQrId") REFERENCES "room_qrs"("id") ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE "guest_history_events" ADD CONSTRAINT "guest_history_events_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "guest_history_events" ADD CONSTRAINT "guest_history_events_guestId_fkey" FOREIGN KEY ("guestId") REFERENCES "guests"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "guest_history_events" ADD CONSTRAINT "guest_history_events_stayId_fkey" FOREIGN KEY ("stayId") REFERENCES "stays"("id") ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE "guest_preferences" ADD CONSTRAINT "guest_preferences_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "guest_preferences" ADD CONSTRAINT "guest_preferences_guestId_fkey" FOREIGN KEY ("guestId") REFERENCES "guests"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "operational_tasks" ADD CONSTRAINT "operational_tasks_stayId_fkey" FOREIGN KEY ("stayId") REFERENCES "stays"("id") ON DELETE SET NULL ON UPDATE CASCADE;