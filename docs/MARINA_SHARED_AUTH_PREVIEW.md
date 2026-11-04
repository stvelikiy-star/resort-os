# MARINA SMART — shared-auth staging boundary (RC2)

**Status: isolated synthetic staging, NOT external staging or production approval.**
Source reference: reviewed application `62a2caec856e8fe32801c9156d90de655298ad33`.
Candidate details and blockers: [RC2 handoff](MARINA_SMART_RC2_HANDOFF_20261104.md).

## Runtime isolation and authentication

Shared preview requires all of `MARINA_SHARED_AUTH_PREVIEW_ENABLED=true`,
`MARINA_TENANT_CONTEXT_ENABLED=true` and `APP_ENV=staging` against a
**separate disposable database**. The runtime refuses MARINA_DEMO and old
MARINA_HOTEL01. Single-property login and existing production configuration
remain unchanged.

Login requires tenant, property, username and password. Selectors are not
authority; tenant/property membership and active staff role are resolved
from the database. Session context is checked on each operation; untrusted
`X-Tenant-Id`, `X-Property-Id`, or `X-Role` headers cannot select another
hotel. Preview and legacy sessions cannot be interchanged. Session tokens
are hashed for storage and revoked/expired memberships are rejected.
Default non-allowlisted HTTP routes fail with 503; WebSockets are closed.
This is a narrow staging security boundary, not an all-module shared runtime.

## Available shared Admin screens

The dedicated `/shared-auth-preview` interface has only four sections
conditioned on *server-provided* role and module grants:

- OWNER/MANAGER: dashboard, hotel-local grid, reservations, and staff overview
  when the corresponding modules are enabled. The reviewed grid provides
  real room/date/price preview + explicit booking commit and a separate
  60-minute HOLD list/create/release panel.
- RECEPTION: grid and reservation list as granted, with real check-in/check-out;
  no owner-only booking/mutation controls.
- AGENT: grid only where granted.
- MAID, TECHNICIAN, COOK, WAITER and other operational roles: **no complete
  shared working cabinet yet**. Their API/legacy or separate staff workspaces
  do not prove the shared preview is ready for daily operations.

Staff overview/add/activate actions are restricted by backend role/permissions.
Changing a label, hiding a button, or forging a hotel selector does not grant
API access. All actions remain property-scoped on the server.

## Accepted narrow PMS contracts

- `POST /api/v1/admin/pms/reservations/new/preview` and `/new/commit`:
  server-owned room/price, transaction and inventory conflict checks. Creating
  a booking does **not** collect money.
- `GET/POST /api/v1/admin/pms/holds`, `GET/DELETE /holds/{uuid}`:
  OWNER/MANAGER, hotel-specific inventory, 60-minute TTL and explicit release.
  The periodic expiry sweep and booking preview also expire old holds. Public
  website/OTA inventory parity is a **separate unverified gate**.
- `GET /api/v1/admin/pms/reservations/{uuid}/schedule`,
  `POST /schedule/preview` and `POST /schedule/commit`:
  limited one-segment date change in shared UI with explicit version match.
  The stored commercial total is **not automatically repriced**. Complex
  multi-room/multi-segment date changes are not covered by this screen.
- `GET /api/v1/admin/booking/reservations/{uuid}/cancellation-finance-review`
  then `POST /api/v1/admin/pms/reservations/{uuid}/cancel`:
  only eligible unpaid, non-stayed, PMS-origin bookings. A cancellation is
  **not a refund**.
- `GET /api/v1/admin/booking/reservations/{uuid}/acquiring-readiness` and
  `POST /payments`: OWNER/MANAGER internal records of **already received**
  CASH/CARD/CARD_POS/BANK_TRANSFER/OTHER money, server-enforced balance,
  idempotency and explicit employee confirmation. No acquiring, payment link,
  bank verification or automatic charge is connected.
- `GET /api/v1/admin/reception/reservations` and `/{uuid}` and
  `POST /api/v1/admin/stays/reservations/{uuid}/check-in`, `/check-out`:
  OWNER/MANAGER/RECEPTION by granted permissions. Check-in issues a volatile
  one-time guest PIN; the blocking PIN window must be acknowledged before
  further operations. Check-out revokes PIN/sessions, marks the room DIRTY,
  creates housekeeping work and trims valid unused nights without altering
  the stored booking total.

All these are **opt-in shared staging** routes. The legacy shared-preview
read-only description before RC2 is obsolete; this document reflects the
reviewed RC2 source. It does not establish real property/customer readiness.

## Verified CI evidence and unsatisfied launch gates

An isolated real Chromium -> Next.js -> FastAPI -> PostgreSQL 16 test created
and mutated bookings for **two distinct hotels**, checked PIN/checkout/HOLD,
manual payment records, audit and housekeeping, and denied cross-tenant
read/write on the tested PMS routes:
https://github.com/stvelikiy-star/resort-os/actions/runs/41711228040

The RC2 metadata head must independently pass **19 core workflows plus this
real-browser workflow** at one exact SHA before source-acceptance is declared.
CI on the *previous* application source SHA does not satisfy that condition.
Target/external staging, target DB restore/rollback, full operational staff
workspaces, shared guest QR/requests, third-hotel onboarding and live
per-hotel WhatsApp/AI/handoff remain unverified. In particular, the existing
GREEN-API QR provisioning binds a single PROPERTY_CODE and rejects
`MARINA_TENANT_CONTEXT_ENABLED=true`, so it is not the shared per-hotel
WhatsApp solution.

## Source and deployment safety

No changes to the DEMO, MARINA_HOTEL01 data, other hotels/sites, mobile app,
Ubuntu/server deployments, DNS or payment providers are implied or authorized
by this branch. The candidate manifest preserves
`production_cutover_authorized=false`, `external_staging_verified=false`
and `backup_restore_target_verified=false`.
