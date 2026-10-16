# MARINA SMART multi-tenant rollout

Status: IMPLEMENTATION PLAN / NOT PRODUCTION AUTHORIZATION  
Date: 2026-10-08  
Product: MARINA SMART  
Canonical repository: stvelikiy-star/resort-os

## Decision

MARINA SMART is delivered as one central platform with strict logical isolation:

- one canonical codebase;
- one central production runtime;
- PostgreSQL as the system of record;
- a Tenant for each client organization;
- one or more Properties for each Tenant;
- separate users, memberships and roles;
- no cross-tenant or cross-property visibility.

A client's normal hosting remains the location of the client's public website. It is not the default location for the MARINA database or API.

A private deployment on a dedicated VPS or on-premise server is an optional premium mode. It is not the default onboarding path.

## Current implementation boundary

The current canonical runtime already has:

- `properties`;
- `staff_users.propertyId`;
- session-based staff authentication;
- property-scoped operational queries in many modules;
- role checks and audit logging.

The current runtime is not yet a complete multi-tenant platform because:

- the database has no first-class `tenants` table;
- authentication and several modules still use the deployment-level `PROPERTY_CODE` configuration;
- login does not yet select a property from a trusted tenant/domain context;
- a complete cross-tenant isolation E2E is still required;
- self-service or owner-controlled client provisioning is not implemented.

Do not report multi-tenant production readiness until these gates are verified.

## Target model

```text
Tenant (client organization)
  └── Property (hotel / resort)
       ├── Staff users and memberships
       ├── Rooms, rates and inventory
       ├── Reservations, stays and guests
       ├── CRM, operations and Guest OS
       └── Domains and enabled modules
```

The server must derive tenant/property context from the authenticated session and trusted host/domain mapping. Browser-supplied tenant or property IDs are never an authorization boundary.

## Delivery phases

### Phase 1 — inventory and schema foundation

1. Inventory every global `PROPERTY_CODE` dependency.
2. Add a first-class `tenants` table.
3. Add a required tenant relation to `properties`.
4. Backfill the existing staging property into a deterministic default tenant.
5. Preserve existing property-scoped tables and the compact owner chessboard.
6. Add constraints and indexes for tenant/property uniqueness.

### Phase 2 — trusted authentication context

1. Resolve login target from a trusted property slug, domain mapping or explicit selected property.
2. Store tenant and property context in the server session.
3. Remove deployment-global property checks from request authorization.
4. Keep legacy single-property behavior only as an explicitly marked compatibility mode.
5. Reject cross-tenant and cross-property access with 403/404 according to the endpoint contract.

### Phase 3 — idempotent onboarding

Create an owner-only provisioning flow:

1. create Tenant;
2. create Property;
3. create the initial OWNER;
4. create default modules and settings;
5. import or configure rooms and rates;
6. register the client's domain/subdomain;
7. return separate role links and a first-login password reset flow.

Provisioning must be idempotent and must never copy another hotel's guests, reservations, payments or content.

### Phase 4 — acceptance gates

Required before real customer data:

- two tenants in one database;
- two properties under one tenant;
- duplicate usernames isolated by property where policy allows;
- all roles tested against both properties;
- public site/API requests scoped to the correct property;
- AI context scoped to the authenticated property;
- booking conflict protection remains active;
- backup and restore preserve tenant boundaries;
- audit log records provisioning and access changes.

## Deployment modes

- **MARINA Cloud:** default for standard customers.
- **Private Cloud:** dedicated VPS/database for larger customers.
- **On-premise:** optional later, only when the customer supplies or purchases an always-on managed device and accepts separate support/backup terms.

No production/DNS cutover, payment activation or real-data migration is implied by this document.


## Current implementation slice

The first safe code slice now carries a trusted context in the authenticated session and
in `/api/v1/auth/me`:

- `property_id` is always derived from the joined database property;
- `tenant_id` is read only from `properties.tenantId`;
- `MARINA_TENANT_CONTEXT_ENABLED=false` is the default, so the pre-migration runtime
  remains compatible;
- the existing `PROPERTY_CODE` boundary remains active until every property-scoped
  query is covered by isolation tests;
- the browser cannot select a tenant by sending a custom header.

The rollout order is therefore: apply migration in isolated staging, enable the flag only
there, create two test tenants, verify login/context and cross-tenant read/write denial,
then migrate property/domain resolution. No production deployment is implied by this
document.


## Staging gate before customer onboarding

The first staging gate is intentionally read-only and is implemented in
`scripts/verify_marina_multitenant_staging.py`. It requires:

1. HTTPS staging API readiness and OpenAPI availability;
2. the complete migration ledger including `zz107_marina_tenants_20261008`;
3. two active test tenants and two test properties;
4. every property assigned to a non-null tenant;
5. no duplicate property code inside one tenant;
6. explicit expected property codes supplied by the staging runbook.

This gate does not prove application-level login isolation. After it passes, a separate
two-account E2E must log into both test properties, compare the server-returned
`tenant_id/property_id`, verify role boundaries, and attempt cross-property reads and
writes. Until that E2E and backup/restore are green, customer onboarding and production
deployment remain blocked.
