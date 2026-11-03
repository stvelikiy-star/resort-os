# Shared authentication: isolated staging slice

Status: implementation and test preparation, not production approval.

The default single-property login is unchanged. The new mode is opt-in with
`MARINA_SHARED_AUTH_PREVIEW_ENABLED=true`, `APP_ENV=staging` and
`MARINA_TENANT_CONTEXT_ENABLED=true`. Existing MARINA_DEMO/MARINA_HOTEL01 runtimes
are refused. It belongs in a separate synthetic staging database.

The login accepts `tenant_code`, `property_code`, `username` and `password`. Codes
are selectors, not authority: the database must resolve that active tenant and
property, then verify the staff account in that property. No public list of
hotels/accounts or trust in X-Tenant-Id/X-Property-Id/X-Role is introduced.

Sessions use the existing auth_sessions table without a schema migration. The
entire random contextual token is hashed for the DB lookup. Embedded tenant and
property UUIDs are compared with the currently authenticated staff membership
after the DB lookup; they cannot grant authority on their own. Changed tenant
membership, revoked/expired session, inactive user or inactive tenant is refused.
The preview and legacy session formats cannot be used interchangeably.

The ASGI boundary permits auth login/logout/me/mode and health endpoints.
In an isolated staging-only review branch, it additionally permits the tenant-scoped
read-only GET `/api/v1/admin/dashboard` and GET `/api/v1/pms/grid` endpoints.
This reviewed staff-management slice additionally permits GET `/api/v1/admin/staff/overview`,
POST `/api/v1/admin/staff` and PATCH `/api/v1/admin/staff/{staff_uuid}` with existing
owner-only mutation rights, signed hotel sessions and server-side property scoping.
A further narrow PMS stage permits POST `/api/v1/admin/pms/reservations/new/preview`,
POST `/api/v1/admin/pms/reservations/new/commit`, and POST
`/api/v1/admin/pms/reservations/{reservation_uuid}/cancel` (only unpaid,
not checked-in, PMS-origin bookings). The booking commit is transactional,
uses server-trusted hotel ID and validates the quoted price, and the room
inventory exclusion constraint prevents concurrent double booking.
The shared PMS endpoints are API-only in this staging slice; the Admin UI
still displays a read-only grid, without booking mutation controls.
An additional narrowly reviewed stay-operation slice allows only POST
`/api/v1/admin/stays/reservations/{reservation_uuid}/check-in` and
POST `/check-out` for authenticated OWNER/MANAGER/RECEPTION according to
server-managed section permissions. Existing handlers verify property ownership,
hotel-local dates, assigned room readiness, stay and booking state; check-in
issues a one-time visible guest access PIN and creates a non-financial kitchen
arrival task. Check-out revokes the guest PIN and sessions, closes occupancy,
releases unused future nights only when valid, marks the vacated room DIRTY and
creates housekeeping work. The core route logic stays on the same backend for
web and future mobile clients. These are test-only API permissions: there is no
production shared staff/guest app rollout or general guest-service activation.

The next reviewed financial slice composes only internal manual booking payment
records in shared staging even when legacy ENABLE_PAYMENT_OPERATIONS is false,
then explicitly allows authenticated OWNER/MANAGER GET
`/api/v1/admin/booking/reservations/{reservation_uuid}/acquiring-readiness`,
GET `/cancellation-finance-review`, and POST `/payments`.
Payments are restricted to internal manual CASH/CARD/CARD_POS/BANK_TRANSFER/OTHER
entries, require unique idempotency keys, and in shared mode ALWAYS enforce
the actual outstanding financial balance with the reservation locked.
This does **not** connect a bank, initiate acquiring, verify funds receipt,
issue a payment link, provide online checkout or perform refunds. The
receipts are staff-recorded internal facts only; third-party payment,
service-point QR and MKassa entry points remain gated off. The shared
Admin UI does not offer these payment actions in this staging slice.

The shared reservation schedule slice also permits GET
`/api/v1/admin/pms/reservations/{reservation_uuid}/schedule` and POST to
`/schedule/preview` and `/schedule/commit` under existing OWNER/MANAGER PMS
authorization. The schedule mutator was changed to resolve the property ID from
the DB-validated authenticated session instead of looking up the displayed hotel
code. Both schedule preview and commit clear only that property's expired HOLDs
inside a transaction before checking room conflicts. The commit retains the
reservation's stored amount, checks its expected version, logs the date move and
refuses overlapping inventory. It does **not** recalculate or collect payments,
and the shared Admin page still has no date-edit UI in this isolated stage.

A reviewed shared HOLD slice additionally permits GET/POST
`/api/v1/admin/pms/holds` and GET/DELETE
`/api/v1/admin/pms/holds/{hold_uuid}` for OWNER/MANAGER.
HOLD ownership, dates and room inventory are checked on the server against
the verified hotel context. The 60-minute expiration sweep now visits each
database-linked hotel with a separate transaction and uses row-level
SKIP LOCKED to avoid duplicate releases in multi-process runs. Ordinary
booking preview and commit also clear expired HOLDs for their authenticated
hotel before checking availability; the periodic sweep is not the sole
enforcement of expiration. Guest-facing/public availability remains a
separate verification gate; no claim that all OTA or background consumers
already implement the same expiry/availability contract is made.
All other HTTP routes return 503 and WebSockets are closed before their handlers
run. Payments, stay check-in/out, shared onboarding and providers remain
blocked. Shared HOLD and booking API changes do NOT establish a complete
production-ready PMS; Admin shared UI is still read-only for these actions. The gate is installed in the canonical app;
real PostgreSQL + canonical ASGI route acceptance is required before integration.

The regular Admin root checks the server authentication mode first. Only in
isolated `shared_auth_preview` staging it routes to `/shared-auth-preview`,
which requires the verified tenant and property codes at login. The page exposes
only reviewed read-only dashboard/PMS grid, a hotel-scoped staff overview, and
owner-only staff creation/activation controls through the existing Core API.
Other modules and PMS mutations are **not enabled**. It is NOT the general
Admin/PMS interface or proof of a production-ready shared platform. In legacy
single-property mode the existing Admin login and DEMO workflow are unchanged.
The separate Staff/mobile app and deployment files remain untouched.
Browser acceptance uses synthetic intercepted API responses; PostgreSQL/canonical
ASGI isolation is accepted independently in the shared-auth CI.

Known-workspace attempts retain database-backed throttling, scoped by the hotel
selector. A bounded per-process IP limiter covers all attempts, including unknown
selectors. It is not a production-wide distributed limiter. Tenant onboarding,
member selection across multiple hotels, recovery, remaining route isolation,
per-hotel provider secrets and operational workspaces remain separate steps.

Validation consists of local API tests with simulated DB state, legacy regression
tests, and a dedicated real PostgreSQL CI scenario against committed migrations.
The CI runner requires an explicit confirmation and only accepts the disposable
localhost database marina_shared_auth_ci. Until its result is observed, do not
claim that PostgreSQL acceptance passed or that the platform is deployed.
