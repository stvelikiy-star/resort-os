-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateEnum
CREATE TYPE "RoomOperationalState" AS ENUM ('UNKNOWN', 'CLEAN', 'DIRTY', 'IN_INSPECTION', 'TECH_BLOCK');

-- CreateEnum
CREATE TYPE "RateSaleStatus" AS ENUM ('OPEN', 'CLOSED', 'CONFIRM_REQUIRED');

-- CreateEnum
CREATE TYPE "ReservationRequestStatus" AS ENUM ('NEW', 'QUOTED', 'AWAITING_PREPAYMENT', 'CONVERTED', 'REJECTED', 'CANCELLED', 'EXPIRED');

-- CreateEnum
CREATE TYPE "ReservationStatus" AS ENUM ('GUARANTEED', 'CHECKED_IN', 'CHECKED_OUT', 'CANCELLED', 'NO_SHOW');

-- CreateEnum
CREATE TYPE "PaymentStatus" AS ENUM ('PENDING', 'RECEIVED', 'FAILED', 'REFUNDED', 'CANCELLED');

-- CreateEnum
CREATE TYPE "InventoryBlockType" AS ENUM ('RESERVATION', 'MAINTENANCE', 'MANUAL');

-- CreateEnum
CREATE TYPE "StaffRole" AS ENUM ('OWNER', 'MANAGER', 'MAID', 'TECHNICIAN', 'BEACH_PARTNER');

-- CreateEnum
CREATE TYPE "OperationalTaskType" AS ENUM ('HOUSEKEEPING', 'MAINTENANCE', 'GUEST_REQUEST');

-- CreateEnum
CREATE TYPE "OperationalTaskStatus" AS ENUM ('OPEN', 'IN_PROGRESS', 'IN_INSPECTION', 'DONE', 'CANCELLED');

-- CreateEnum
CREATE TYPE "OperationalTaskPriority" AS ENUM ('LOW', 'NORMAL', 'HIGH', 'URGENT');

-- CreateEnum
CREATE TYPE "NfcWalletStatus" AS ENUM ('ACTIVE', 'BLOCKED', 'CLOSED');

-- CreateEnum
CREATE TYPE "NfcBraceletStatus" AS ENUM ('ACTIVE', 'BLOCKED', 'LOST', 'RETURNED');

-- CreateEnum
CREATE TYPE "NfcTransactionStatus" AS ENUM ('COMPLETED', 'REVERSED');

-- CreateEnum
CREATE TYPE "CommunicationChannelKind" AS ENUM ('WEBSITE', 'TELEGRAM', 'WHATSAPP', 'INSTAGRAM', 'OTHER');

-- CreateEnum
CREATE TYPE "ConversationStatus" AS ENUM ('OPEN', 'WAITING_GUEST', 'WAITING_STAFF', 'RESOLVED', 'ARCHIVED');

-- CreateEnum
CREATE TYPE "MessageDirection" AS ENUM ('INBOUND', 'OUTBOUND', 'INTERNAL');

-- CreateEnum
CREATE TYPE "MessageDeliveryStatus" AS ENUM ('RECEIVED', 'QUEUED', 'SENT', 'DELIVERED', 'FAILED', 'UNKNOWN');

-- CreateTable
CREATE TABLE "properties" (
    "id" UUID NOT NULL,
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "timezone" TEXT NOT NULL DEFAULT 'Asia/Bishkek',
    "currency" TEXT NOT NULL DEFAULT 'KGS',
    "beachCommissionBps" INTEGER NOT NULL DEFAULT 500,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "properties_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "room_types" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "capacityAdults" INTEGER NOT NULL,
    "capacityChildren" INTEGER,
    "areaLabel" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "room_types_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "rooms" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "roomTypeId" UUID NOT NULL,
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "buildingOrZone" TEXT,
    "floorLabel" TEXT,
    "bedConfiguration" TEXT,
    "areaLabel" TEXT,
    "operationalState" "RoomOperationalState" NOT NULL DEFAULT 'UNKNOWN',
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "rooms_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "rate_plans" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "currency" TEXT NOT NULL DEFAULT 'KGS',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "rate_plans_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "rate_periods" (
    "id" UUID NOT NULL,
    "ratePlanId" UUID NOT NULL,
    "roomTypeId" UUID NOT NULL,
    "label" TEXT NOT NULL,
    "validFrom" DATE NOT NULL,
    "validTo" DATE NOT NULL,
    "priceKgs" INTEGER NOT NULL,
    "mealIncluded" TEXT NOT NULL,
    "saleStatus" "RateSaleStatus" NOT NULL DEFAULT 'OPEN',
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "rate_periods_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "guests" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "firstName" TEXT,
    "lastName" TEXT,
    "phone" TEXT,
    "email" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "guests_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "reservation_requests" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "status" "ReservationRequestStatus" NOT NULL DEFAULT 'NEW',
    "source" TEXT,
    "guestName" TEXT NOT NULL,
    "phone" TEXT NOT NULL,
    "email" TEXT,
    "checkIn" DATE NOT NULL,
    "checkOut" DATE NOT NULL,
    "adults" INTEGER NOT NULL,
    "children" INTEGER NOT NULL DEFAULT 0,
    "desiredRoomTypeId" UUID,
    "quotedTotalKgs" INTEGER,
    "requiredPrepaymentKgs" INTEGER,
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "reservation_requests_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "reservations" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "requestId" UUID,
    "bookingNumber" TEXT NOT NULL,
    "primaryGuestId" UUID,
    "status" "ReservationStatus" NOT NULL DEFAULT 'GUARANTEED',
    "checkIn" DATE NOT NULL,
    "checkOut" DATE NOT NULL,
    "adults" INTEGER NOT NULL,
    "children" INTEGER NOT NULL DEFAULT 0,
    "totalKgs" INTEGER NOT NULL,
    "notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "reservations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "inventory_blocks" (
    "id" UUID NOT NULL,
    "roomId" UUID NOT NULL,
    "reservationId" UUID,
    "blockType" "InventoryBlockType" NOT NULL,
    "startDate" DATE NOT NULL,
    "endDate" DATE NOT NULL,
    "active" BOOLEAN NOT NULL DEFAULT true,
    "reason" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "inventory_blocks_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "payments" (
    "id" UUID NOT NULL,
    "requestId" UUID,
    "reservationId" UUID,
    "amountKgs" INTEGER NOT NULL,
    "method" TEXT NOT NULL,
    "status" "PaymentStatus" NOT NULL DEFAULT 'PENDING',
    "provider" TEXT,
    "externalRef" TEXT,
    "idempotencyKey" TEXT,
    "metadata" JSONB,
    "paidAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "payments_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "staff_users" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "username" TEXT NOT NULL,
    "displayName" TEXT NOT NULL,
    "passwordHash" TEXT NOT NULL,
    "role" "StaffRole" NOT NULL,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "telegramUserId" TEXT,
    "telegramUsername" TEXT,
    "telegramLinkedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "staff_users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "auth_sessions" (
    "id" UUID NOT NULL,
    "userId" UUID NOT NULL,
    "tokenHash" TEXT NOT NULL,
    "expiresAt" TIMESTAMP(3) NOT NULL,
    "revokedAt" TIMESTAMP(3),
    "lastSeenAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "auth_sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "operational_tasks" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "roomId" UUID,
    "type" "OperationalTaskType" NOT NULL,
    "status" "OperationalTaskStatus" NOT NULL DEFAULT 'OPEN',
    "priority" "OperationalTaskPriority" NOT NULL DEFAULT 'NORMAL',
    "title" TEXT NOT NULL,
    "description" TEXT,
    "assignedToId" UUID,
    "createdByType" TEXT NOT NULL,
    "createdById" TEXT,
    "source" TEXT,
    "completedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "operational_tasks_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "automation_inbound_events" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "source" TEXT NOT NULL,
    "idempotencyKey" TEXT NOT NULL,
    "eventType" TEXT NOT NULL,
    "payloadJson" JSONB NOT NULL,
    "resultResource" TEXT,
    "resultResourceId" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "automation_inbound_events_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "communication_channels" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "code" TEXT NOT NULL,
    "kind" "CommunicationChannelKind" NOT NULL,
    "displayName" TEXT NOT NULL,
    "externalAccountId" TEXT,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "metadata" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "communication_channels_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "conversations" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "channelId" UUID NOT NULL,
    "externalConversationId" TEXT,
    "externalContactId" TEXT,
    "contactName" TEXT,
    "contactPhone" TEXT,
    "contactUsername" TEXT,
    "status" "ConversationStatus" NOT NULL DEFAULT 'OPEN',
    "assignedToId" UUID,
    "reservationRequestId" UUID,
    "lastInboundAt" TIMESTAMP(3),
    "lastOutboundAt" TIMESTAMP(3),
    "firstResponseAt" TIMESTAMP(3),
    "resolvedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "conversations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "conversation_messages" (
    "id" UUID NOT NULL,
    "conversationId" UUID NOT NULL,
    "direction" "MessageDirection" NOT NULL,
    "externalMessageId" TEXT,
    "senderType" TEXT NOT NULL,
    "senderExternalId" TEXT,
    "text" TEXT,
    "contentType" TEXT NOT NULL DEFAULT 'TEXT',
    "deliveryStatus" "MessageDeliveryStatus" NOT NULL DEFAULT 'UNKNOWN',
    "rawPayload" JSONB,
    "sentAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "conversation_messages_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "nfc_wallets" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "reservationId" UUID NOT NULL,
    "guestId" UUID NOT NULL,
    "balanceKgs" INTEGER NOT NULL DEFAULT 0,
    "status" "NfcWalletStatus" NOT NULL DEFAULT 'ACTIVE',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "nfc_wallets_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "nfc_bracelets" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "walletId" UUID NOT NULL,
    "uidHash" TEXT NOT NULL,
    "status" "NfcBraceletStatus" NOT NULL DEFAULT 'ACTIVE',
    "label" TEXT,
    "issuedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "returnedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "nfc_bracelets_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "nfc_transactions" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "walletId" UUID NOT NULL,
    "braceletId" UUID NOT NULL,
    "partnerStaffUserId" UUID NOT NULL,
    "amountKgs" INTEGER NOT NULL,
    "hotelCommissionKgs" INTEGER NOT NULL,
    "partnerNetKgs" INTEGER NOT NULL,
    "commissionBps" INTEGER NOT NULL,
    "status" "NfcTransactionStatus" NOT NULL DEFAULT 'COMPLETED',
    "idempotencyKey" TEXT NOT NULL,
    "description" TEXT,
    "externalRef" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "nfc_transactions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "nfc_ledger_entries" (
    "id" UUID NOT NULL,
    "walletId" UUID NOT NULL,
    "transactionId" UUID,
    "entryType" TEXT NOT NULL,
    "deltaKgs" INTEGER NOT NULL,
    "balanceBeforeKgs" INTEGER NOT NULL,
    "balanceAfterKgs" INTEGER NOT NULL,
    "note" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "nfc_ledger_entries_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "audit_logs" (
    "id" UUID NOT NULL,
    "propertyId" UUID,
    "actorType" TEXT NOT NULL,
    "actorId" TEXT,
    "action" TEXT NOT NULL,
    "resource" TEXT NOT NULL,
    "resourceId" TEXT,
    "source" TEXT,
    "result" TEXT NOT NULL,
    "beforeJson" JSONB,
    "afterJson" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "audit_logs_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "properties_code_key" ON "properties"("code");

-- CreateIndex
CREATE UNIQUE INDEX "room_types_propertyId_code_key" ON "room_types"("propertyId", "code");

-- CreateIndex
CREATE UNIQUE INDEX "room_types_propertyId_name_key" ON "room_types"("propertyId", "name");

-- CreateIndex
CREATE INDEX "rooms_propertyId_roomTypeId_idx" ON "rooms"("propertyId", "roomTypeId");

-- CreateIndex
CREATE UNIQUE INDEX "rooms_propertyId_code_key" ON "rooms"("propertyId", "code");

-- CreateIndex
CREATE UNIQUE INDEX "rate_plans_propertyId_code_key" ON "rate_plans"("propertyId", "code");

-- CreateIndex
CREATE INDEX "rate_periods_roomTypeId_validFrom_validTo_idx" ON "rate_periods"("roomTypeId", "validFrom", "validTo");

-- CreateIndex
CREATE UNIQUE INDEX "rate_periods_ratePlanId_roomTypeId_validFrom_validTo_key" ON "rate_periods"("ratePlanId", "roomTypeId", "validFrom", "validTo");

-- CreateIndex
CREATE INDEX "guests_propertyId_phone_idx" ON "guests"("propertyId", "phone");

-- CreateIndex
CREATE INDEX "reservation_requests_propertyId_createdAt_idx" ON "reservation_requests"("propertyId", "createdAt");

-- CreateIndex
CREATE INDEX "reservation_requests_status_idx" ON "reservation_requests"("status");

-- CreateIndex
CREATE UNIQUE INDEX "reservations_requestId_key" ON "reservations"("requestId");

-- CreateIndex
CREATE UNIQUE INDEX "reservations_bookingNumber_key" ON "reservations"("bookingNumber");

-- CreateIndex
CREATE INDEX "reservations_propertyId_checkIn_checkOut_idx" ON "reservations"("propertyId", "checkIn", "checkOut");

-- CreateIndex
CREATE INDEX "inventory_blocks_roomId_startDate_endDate_idx" ON "inventory_blocks"("roomId", "startDate", "endDate");

-- CreateIndex
CREATE UNIQUE INDEX "payments_idempotencyKey_key" ON "payments"("idempotencyKey");

-- CreateIndex
CREATE INDEX "payments_requestId_idx" ON "payments"("requestId");

-- CreateIndex
CREATE INDEX "payments_reservationId_idx" ON "payments"("reservationId");

-- CreateIndex
CREATE UNIQUE INDEX "payments_provider_externalRef_key" ON "payments"("provider", "externalRef");

-- CreateIndex
CREATE INDEX "staff_users_propertyId_role_idx" ON "staff_users"("propertyId", "role");

-- CreateIndex
CREATE UNIQUE INDEX "staff_users_propertyId_username_key" ON "staff_users"("propertyId", "username");

-- CreateIndex
CREATE UNIQUE INDEX "staff_users_propertyId_telegramUserId_key" ON "staff_users"("propertyId", "telegramUserId");

-- CreateIndex
CREATE UNIQUE INDEX "auth_sessions_tokenHash_key" ON "auth_sessions"("tokenHash");

-- CreateIndex
CREATE INDEX "auth_sessions_userId_expiresAt_idx" ON "auth_sessions"("userId", "expiresAt");

-- CreateIndex
CREATE INDEX "auth_sessions_expiresAt_idx" ON "auth_sessions"("expiresAt");

-- CreateIndex
CREATE INDEX "operational_tasks_propertyId_status_type_idx" ON "operational_tasks"("propertyId", "status", "type");

-- CreateIndex
CREATE INDEX "operational_tasks_roomId_status_idx" ON "operational_tasks"("roomId", "status");

-- CreateIndex
CREATE INDEX "operational_tasks_assignedToId_status_idx" ON "operational_tasks"("assignedToId", "status");

-- CreateIndex
CREATE INDEX "automation_inbound_events_propertyId_eventType_createdAt_idx" ON "automation_inbound_events"("propertyId", "eventType", "createdAt");

-- CreateIndex
CREATE UNIQUE INDEX "automation_inbound_events_propertyId_source_idempotencyKey_key" ON "automation_inbound_events"("propertyId", "source", "idempotencyKey");

-- CreateIndex
CREATE INDEX "communication_channels_propertyId_kind_isActive_idx" ON "communication_channels"("propertyId", "kind", "isActive");

-- CreateIndex
CREATE UNIQUE INDEX "communication_channels_propertyId_code_key" ON "communication_channels"("propertyId", "code");

-- CreateIndex
CREATE INDEX "conversations_propertyId_status_updatedAt_idx" ON "conversations"("propertyId", "status", "updatedAt");

-- CreateIndex
CREATE INDEX "conversations_assignedToId_status_idx" ON "conversations"("assignedToId", "status");

-- CreateIndex
CREATE INDEX "conversations_reservationRequestId_idx" ON "conversations"("reservationRequestId");

-- CreateIndex
CREATE UNIQUE INDEX "conversations_channelId_externalConversationId_key" ON "conversations"("channelId", "externalConversationId");

-- CreateIndex
CREATE INDEX "conversation_messages_conversationId_createdAt_idx" ON "conversation_messages"("conversationId", "createdAt");

-- CreateIndex
CREATE UNIQUE INDEX "conversation_messages_conversationId_externalMessageId_key" ON "conversation_messages"("conversationId", "externalMessageId");

-- CreateIndex
CREATE UNIQUE INDEX "nfc_wallets_reservationId_key" ON "nfc_wallets"("reservationId");

-- CreateIndex
CREATE INDEX "nfc_wallets_propertyId_status_idx" ON "nfc_wallets"("propertyId", "status");

-- CreateIndex
CREATE INDEX "nfc_wallets_guestId_idx" ON "nfc_wallets"("guestId");

-- CreateIndex
CREATE INDEX "nfc_bracelets_walletId_status_idx" ON "nfc_bracelets"("walletId", "status");

-- CreateIndex
CREATE UNIQUE INDEX "nfc_bracelets_propertyId_uidHash_key" ON "nfc_bracelets"("propertyId", "uidHash");

-- CreateIndex
CREATE INDEX "nfc_transactions_walletId_createdAt_idx" ON "nfc_transactions"("walletId", "createdAt");

-- CreateIndex
CREATE INDEX "nfc_transactions_partnerStaffUserId_createdAt_idx" ON "nfc_transactions"("partnerStaffUserId", "createdAt");

-- CreateIndex
CREATE UNIQUE INDEX "nfc_transactions_propertyId_idempotencyKey_key" ON "nfc_transactions"("propertyId", "idempotencyKey");

-- CreateIndex
CREATE UNIQUE INDEX "nfc_ledger_entries_transactionId_key" ON "nfc_ledger_entries"("transactionId");

-- CreateIndex
CREATE INDEX "nfc_ledger_entries_walletId_createdAt_idx" ON "nfc_ledger_entries"("walletId", "createdAt");

-- CreateIndex
CREATE INDEX "audit_logs_propertyId_createdAt_idx" ON "audit_logs"("propertyId", "createdAt");

-- AddForeignKey
ALTER TABLE "room_types" ADD CONSTRAINT "room_types_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "rooms" ADD CONSTRAINT "rooms_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "rooms" ADD CONSTRAINT "rooms_roomTypeId_fkey" FOREIGN KEY ("roomTypeId") REFERENCES "room_types"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "rate_plans" ADD CONSTRAINT "rate_plans_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "rate_periods" ADD CONSTRAINT "rate_periods_ratePlanId_fkey" FOREIGN KEY ("ratePlanId") REFERENCES "rate_plans"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "rate_periods" ADD CONSTRAINT "rate_periods_roomTypeId_fkey" FOREIGN KEY ("roomTypeId") REFERENCES "room_types"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "guests" ADD CONSTRAINT "guests_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "reservation_requests" ADD CONSTRAINT "reservation_requests_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "reservation_requests" ADD CONSTRAINT "reservation_requests_desiredRoomTypeId_fkey" FOREIGN KEY ("desiredRoomTypeId") REFERENCES "room_types"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "reservations" ADD CONSTRAINT "reservations_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "reservations" ADD CONSTRAINT "reservations_requestId_fkey" FOREIGN KEY ("requestId") REFERENCES "reservation_requests"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "reservations" ADD CONSTRAINT "reservations_primaryGuestId_fkey" FOREIGN KEY ("primaryGuestId") REFERENCES "guests"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "inventory_blocks" ADD CONSTRAINT "inventory_blocks_roomId_fkey" FOREIGN KEY ("roomId") REFERENCES "rooms"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "inventory_blocks" ADD CONSTRAINT "inventory_blocks_reservationId_fkey" FOREIGN KEY ("reservationId") REFERENCES "reservations"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payments" ADD CONSTRAINT "payments_requestId_fkey" FOREIGN KEY ("requestId") REFERENCES "reservation_requests"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payments" ADD CONSTRAINT "payments_reservationId_fkey" FOREIGN KEY ("reservationId") REFERENCES "reservations"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "staff_users" ADD CONSTRAINT "staff_users_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "auth_sessions" ADD CONSTRAINT "auth_sessions_userId_fkey" FOREIGN KEY ("userId") REFERENCES "staff_users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "operational_tasks" ADD CONSTRAINT "operational_tasks_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "operational_tasks" ADD CONSTRAINT "operational_tasks_roomId_fkey" FOREIGN KEY ("roomId") REFERENCES "rooms"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "operational_tasks" ADD CONSTRAINT "operational_tasks_assignedToId_fkey" FOREIGN KEY ("assignedToId") REFERENCES "staff_users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "automation_inbound_events" ADD CONSTRAINT "automation_inbound_events_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "communication_channels" ADD CONSTRAINT "communication_channels_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "conversations" ADD CONSTRAINT "conversations_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "conversations" ADD CONSTRAINT "conversations_channelId_fkey" FOREIGN KEY ("channelId") REFERENCES "communication_channels"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "conversations" ADD CONSTRAINT "conversations_assignedToId_fkey" FOREIGN KEY ("assignedToId") REFERENCES "staff_users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "conversations" ADD CONSTRAINT "conversations_reservationRequestId_fkey" FOREIGN KEY ("reservationRequestId") REFERENCES "reservation_requests"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "conversation_messages" ADD CONSTRAINT "conversation_messages_conversationId_fkey" FOREIGN KEY ("conversationId") REFERENCES "conversations"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "nfc_wallets" ADD CONSTRAINT "nfc_wallets_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "nfc_wallets" ADD CONSTRAINT "nfc_wallets_reservationId_fkey" FOREIGN KEY ("reservationId") REFERENCES "reservations"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "nfc_wallets" ADD CONSTRAINT "nfc_wallets_guestId_fkey" FOREIGN KEY ("guestId") REFERENCES "guests"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "nfc_bracelets" ADD CONSTRAINT "nfc_bracelets_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "nfc_bracelets" ADD CONSTRAINT "nfc_bracelets_walletId_fkey" FOREIGN KEY ("walletId") REFERENCES "nfc_wallets"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "nfc_transactions" ADD CONSTRAINT "nfc_transactions_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "nfc_transactions" ADD CONSTRAINT "nfc_transactions_walletId_fkey" FOREIGN KEY ("walletId") REFERENCES "nfc_wallets"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "nfc_transactions" ADD CONSTRAINT "nfc_transactions_braceletId_fkey" FOREIGN KEY ("braceletId") REFERENCES "nfc_bracelets"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "nfc_transactions" ADD CONSTRAINT "nfc_transactions_partnerStaffUserId_fkey" FOREIGN KEY ("partnerStaffUserId") REFERENCES "staff_users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "nfc_ledger_entries" ADD CONSTRAINT "nfc_ledger_entries_walletId_fkey" FOREIGN KEY ("walletId") REFERENCES "nfc_wallets"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "nfc_ledger_entries" ADD CONSTRAINT "nfc_ledger_entries_transactionId_fkey" FOREIGN KEY ("transactionId") REFERENCES "nfc_transactions"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "audit_logs" ADD CONSTRAINT "audit_logs_propertyId_fkey" FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE SET NULL ON UPDATE CASCADE;



-- ================================================================
-- Resort OS custom PostgreSQL invariants reviewed separately from Prisma DSL.
-- Source at generation time: packages/database/sql/001_core_constraints.sql
-- ================================================================
-- Resort OS critical PostgreSQL constraints not expressible in Prisma schema.
-- Apply after Prisma migration.

CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE "rate_periods"
  ADD CONSTRAINT rate_period_valid_dates CHECK ("validFrom" <= "validTo"),
  ADD CONSTRAINT rate_period_nonnegative_price CHECK ("priceKgs" >= 0);

ALTER TABLE "reservation_requests"
  ADD CONSTRAINT reservation_request_valid_dates CHECK ("checkIn" < "checkOut"),
  ADD CONSTRAINT reservation_request_positive_adults CHECK (adults > 0),
  ADD CONSTRAINT reservation_request_nonnegative_children CHECK (children >= 0);

ALTER TABLE "reservations"
  ADD CONSTRAINT reservation_valid_dates CHECK ("checkIn" < "checkOut"),
  ADD CONSTRAINT reservation_positive_adults CHECK (adults > 0),
  ADD CONSTRAINT reservation_nonnegative_children CHECK (children >= 0),
  ADD CONSTRAINT reservation_nonnegative_total CHECK ("totalKgs" >= 0);

ALTER TABLE "inventory_blocks"
  ADD CONSTRAINT inventory_block_valid_dates CHECK ("startDate" < "endDate");

-- One room cannot have two active inventory blocks for overlapping nights.
-- This is the primary database-level double-booking protection.
ALTER TABLE "inventory_blocks"
  ADD CONSTRAINT no_overlapping_active_room_blocks
  EXCLUDE USING gist (
    "roomId" WITH =,
    daterange("startDate", "endDate", '[)') WITH &&
  ) WHERE (active = true);

ALTER TABLE "payments"
  ADD CONSTRAINT payment_positive_amount CHECK ("amountKgs" > 0),
  ADD CONSTRAINT payment_has_context CHECK ("requestId" IS NOT NULL OR "reservationId" IS NOT NULL);
