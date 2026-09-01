CREATE TYPE "ServicePointQrStatus" AS ENUM ('ACTIVE', 'REVOKED');

CREATE TABLE "service_points" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "category" TEXT NOT NULL,
    "zoneLabel" TEXT,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "service_points_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "service_point_request_options" (
    "id" UUID NOT NULL,
    "servicePointId" UUID NOT NULL,
    "code" TEXT NOT NULL,
    "label" TEXT NOT NULL,
    "taskType" "OperationalTaskType" NOT NULL,
    "priority" "OperationalTaskPriority" NOT NULL DEFAULT 'NORMAL',
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "service_point_request_options_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "service_point_qrs" (
    "id" UUID NOT NULL,
    "propertyId" UUID NOT NULL,
    "servicePointId" UUID NOT NULL,
    "tokenHash" TEXT NOT NULL,
    "status" "ServicePointQrStatus" NOT NULL DEFAULT 'ACTIVE',
    "label" TEXT,
    "issuedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "revokedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "service_point_qrs_pkey" PRIMARY KEY ("id")
);

ALTER TABLE "operational_tasks" ADD COLUMN "servicePointId" UUID;

CREATE UNIQUE INDEX "service_points_propertyId_code_key" ON "service_points"("propertyId", "code");
CREATE INDEX "service_points_propertyId_category_isActive_idx" ON "service_points"("propertyId", "category", "isActive");
CREATE UNIQUE INDEX "service_point_request_options_servicePointId_code_key" ON "service_point_request_options"("servicePointId", "code");
CREATE INDEX "service_point_request_options_servicePointId_isActive_idx" ON "service_point_request_options"("servicePointId", "isActive");
CREATE UNIQUE INDEX "service_point_qrs_tokenHash_key" ON "service_point_qrs"("tokenHash");
CREATE INDEX "service_point_qrs_propertyId_servicePointId_status_idx" ON "service_point_qrs"("propertyId", "servicePointId", "status");
CREATE UNIQUE INDEX "service_point_qrs_one_active_per_point" ON "service_point_qrs"("servicePointId") WHERE "status"='ACTIVE';
CREATE INDEX "operational_tasks_servicePointId_status_idx" ON "operational_tasks"("servicePointId", "status");

ALTER TABLE "service_points"
    ADD CONSTRAINT "service_points_propertyId_fkey"
    FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "service_point_request_options"
    ADD CONSTRAINT "service_point_request_options_servicePointId_fkey"
    FOREIGN KEY ("servicePointId") REFERENCES "service_points"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "service_point_qrs"
    ADD CONSTRAINT "service_point_qrs_propertyId_fkey"
    FOREIGN KEY ("propertyId") REFERENCES "properties"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "service_point_qrs"
    ADD CONSTRAINT "service_point_qrs_servicePointId_fkey"
    FOREIGN KEY ("servicePointId") REFERENCES "service_points"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "operational_tasks"
    ADD CONSTRAINT "operational_tasks_servicePointId_fkey"
    FOREIGN KEY ("servicePointId") REFERENCES "service_points"("id") ON DELETE SET NULL ON UPDATE CASCADE;
