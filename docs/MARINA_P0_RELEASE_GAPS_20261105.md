# MARINA SMART — P0 gap register, 2026-11-05

## Verified baseline

Draft PR #367 at SHA `e63b11b1a4f78806c1e5f1dce4f238317ce76ef2`: **100/100 GitHub Actions SUCCESS**. These are CI results, not an external staging or commercial deployment acceptance. A later commit requires its own CI.

This follow-up does not touch frozen RC3 source, migration SQL, DEMO, `apps/mobile`, production database or Ubuntu.

## Source-confirmed blocking gaps

| Surface | Accepted in shared preview | Commercial launch blocker | Evidence |
| --- | --- | --- | --- |
| Auth / roles | 12 roles authenticate in two disposable hotels; owner manages six staff roles | External production-session acceptance and broader staff workspaces missing | `scripts/marina_shared_role_auth_ci.py`, `services/api/app/staff_control.py` |
| RECEPTION | Booking read, check-in/out, tasks | **Cannot create a PMS booking:** canonical create API grants OWNER/MANAGER/AGENT; shared Admin renders booking form only for OWNER/MANAGER | `services/api/app/pms_reservation_create.py`, `apps/admin/app/shared-auth-preview/page.tsx` |
| COOK / WAITER | Accounts exist and authenticate | No accepted shared dining endpoints or working shared staff UI; Staff gateway admits only MAID/TECHNICIAN in shared mode | `services/api/app/shared_auth_preview.py`, `apps/staff/components/StaffRoleGateway.tsx` |
| Other roles | Legacy role enum retained | STORE_STAFF, DINING_STAFF, CONTENT_MANAGER, BEACH_PARTNER lack accepted shared operational cabinets | `docs/MARINA_SHARED_AUTH_MOBILE_CONTRACT_20261104.md` |
| PMS and money | Browser+real PostgreSQL tests cover two-property booking/HOLD/recorded payments/stays | External staging, bank reconciliation and refund settlement **not proven**; manual payments are not acquiring | `scripts/marina_shared_live_browser.mjs`, `docs/MARINA_SHARED_FINANCE_AUDIT_RC_20261104.md` |
| WhatsApp / AI | RC7 webhook and RC8 human outbound synthetic contract PASS | Real two-instance provider delivery, knowledge isolation, reconnect and handoff not verified | `services/api/app/shared_green_rc7.py`, `services/api/app/shared_green_rc8.py` |
| Production | Isolated Compose/staging instructions, PostgreSQL restore rehearsal | Customer-target TLS, backup/restore, rollback, monitoring and production smoke not accepted | `docs/MARINA_SHARED_HTTPS_STAGING.md` |

## Next P0 actions and acceptance

1. Preserve immutable RC3 and migration checksums. Do not bypass source lock; any necessary change to its frozen files requires an explicit separately reviewed versioned rebaseline.
2. Add RECEPTION **core-rate-only** booking to the canonical API and shared Admin, with no manager price override; verify 201/403/404/409 and hotel isolation using real PostgreSQL.
3. Add shared COOK and WAITER role-limited dining workspaces only after two-hotel browser→API→DB tests. Determine separately which other roles must ship at launch.
4. Accept real guest QR requests, live provider WhatsApp receipts and MARINA AI human handoff on isolated external HTTPS staging.
5. Prove third-hotel onboarding, restore/rollback and monitored host before commercial GO. Require required CI PASS on one final SHA.

## Narrow improvements in this change

- Staff browser shared login now requires eight password characters, matching canonical server validation, while legacy single-property six-character UI behavior is unchanged. Chromium HTTPS staff tests enforce this contract.
- Existing booking form already discards its quote on guest-name/phone edits. The Chromium HTTPS PMS test now checks this positive behavior, including renewed quote before the booking commit. No server pricing logic is modified.

## Stage 2 reception slice — implementation pending acceptance

This new candidate introduces **RECEPTION core-rate-only booking** through the existing `/api/v1/admin/pms/reservations/new/preview` and `/commit` routes. The API explicitly forbids staff-set pricing, discounts, extra beds, agent IDs and HOLD conversion and retains the legacy single-property denial. The additive `/shared-reception` page uses authenticated hotel identity and a scoped room list. It is discoverable from the locked shared-auth landing via a new nested layout. No frozen RC3 source was modified.

Coverage added: a Python scope regression and a two-hotel, real Chromium HTTPS browser test that attempts manager overrides (403), foreign room pricing (404), repeated booking (409), and accepts only core-rate 201 with no payment. **These are test requirements, not PASS claims until the final SHA CI has completed.**

Kitchen/waiter shared workspaces, external provider delivery, target restore and production authorisation remain blocking.

## Stage 2 COOK / WAITER shared staging slice — CI acceptance pending

The existing canonical handlers remain authoritative: `GET /api/v1/kitchen/orders`,
`PATCH /api/v1/kitchen/orders/{id}/status` (COOK); `GET /api/v1/dining/floor`,
`PATCH /api/v1/dining/orders/{id}/waiter` (WAITER). Additional exact dining
routes are admitted via an **explicit** stage-only boundary. No menu management,
provider, payments, AI, guest or unreviewed mutations are opened.

- `MARINA_SHARED_DINING_P0_ENABLED` defaults false; activation requires
  `MARINA_SHARED_DINING_P0_CONFIRM=REVIEWED_SHARED_DINING_STAGING_ONLY`,
  secure shared cookies, `APP_ENV=staging` and validated tenant context.
- The default RC3–RC8 ASGI boundary remains unchanged when the feature is off.
  Role and module permissions are still resolved by `require_roles` and the
  active hotel by `trusted_property_id` in the existing canonical endpoints.
- Shared Staff shows a role-specific `SharedDiningShift` only after verifying
  that COOK/WAITER identity has DINING and the server-issued hotel IDs.
- The disposable staging CI creates two synthetic table/order records using
  frozen RC3 database safety guards; browser tests verify COOK transition,
  WAITER self-assignment, property isolation, 403 role denials, foreign 404
  and revoked session on logout.
- Never execute the dining seed against a customer or populated database.
  Do not turn on the stage flag in production or DEMO.

**Evidence requirement:** successful exact-head CI for new kitchen/restaurant
unit gate, Compose HTTPS Chrome staff end-to-end, full source integrity and
relevant regressions. This document is not an acceptance receipt.

## Stage 2 dining handoff — pending exact-head verification

**Gap:** The shared WAITER could self-assign an order but was not authorised to mark
its delivery after the cook prepared it. The canonical kitchen status transition
already implements `READY -> SERVED` atomically, including audit, any guest task
completion, released table status, and `NONE_AUTOMATIC` financial posting.

**Change:** Only the existing `PATCH /api/v1/kitchen/orders/{id}/status`
dependency admits WAITER. A WAITER must request `SERVED` (all other status
changes are 403), must be the server-stored assigned waiter (403 otherwise)
and must pass the shared-dining staging guard. The query is bound to the session's
hotel ID, so foreign order IDs return 404. Existing COOK/manager permissions,
order reads and creation paths remain unchanged; no new API routes or SQL are added.

**Acceptance required:** Real two-property HTTPS Chromium through Staff to
canonical API/PostgreSQL, verifying NEW -> ACCEPTED -> COOKING -> READY ->
assigned WAITER -> SERVED; foreign 404; forbidden 403; duplicate 409; session
logout 401; management read persists SERVED, without automatic charges or payments.

The result is a **staging-only functional slice** until the final SHA CI finishes.
Commercial revenue, real guest orders and production acceptance remain NO-GO.

## Stage 2 reception internal cash ledger — pending final SHA CI

The canonical `GET /api/v1/admin/booking/reservations/{id}/acquiring-readiness`
and `POST /api/v1/admin/booking/reservations/{id}/payments` now permit RECEPTION
**only in explicitly opted-in shared staging**, with both a valid `RESERVATIONS`
module grant and secure shared tenant session. `MANAGER`/`OWNER` authority is
unchanged; cancellation-finance-review stays management-only.

Only `CASH` with no user-supplied payment event time is permitted for
RECEPTION. No provider/QR/card/bank transfer, online acquiring, refunds,
manual rate changes, ledger deletion or elevated financial reporting.
`MARINA_SHARED_RECEPTION_CASH_P0_ENABLED` defaults false and requires
`MARINA_SHARED_RECEPTION_CASH_P0_CONFIRM=REVIEWED_RECEPTION_CASH_STAGING_ONLY`.
The stage-only guard denies DEMO, the old single-hotel runtime, production,
revoked RESERVATIONS module or missing approval before any write.

No new finance endpoint or migration: the existing handler already performs
transactional property-bound reservation locking, balance checks,
`idempotencyKey` replay/conflict handling, and immutable audit metadata
(`recorded_by_staff_id`, `recorded_by_role`, paid and recorded times).
An internal `RECEIVED` row is an **operator's assertion of cash actually
received**, not a bank settlement receipt.

The existing `SharedManualPaymentPanel` was reused with a cash-only mode.
The added shared reception list filters hotel-local reservations and rechecks
the tenant/session before rendering the panel. The booking form refreshes the
list when the server confirms a booking.

**Required evidence:** browser form and real two-property PostgreSQL with
correct internal receipts, denial of foreign hotel (404), manager-only finance
review (403), forbidden card/bank/backdating (403), overbalance (409), repeat
idempotency key returning the *same* payment ID and no double-received amount;
strict role guard unit tests; all mandatory exact-head CI PASS.

Production cutover remains NO-GO. This is a stage-only manual cash ledger, not
a payment-service integration.

## Stage 2 AGENT linked-booking acceptance — PENDING exact-head CI

- The canonical `/admin/pms/reservations/new/preview` and `/commit`
  enforce a server-side, same-property **ACTIVE** `booking_agents` record
  bound to the logged-in `staff_users.bookingAgentId`. The link is rechecked
  for each booking attempt; role enum alone is not permission.
- Reject manual total, extra-bed unit/count, discount and reason, foreign
  agency ID and HOLD explicitly with 403 (no silent dropping).
- Extend existing OWNER-only staff create/PATCH contract to include `AGENT`
  with required `booking_agent_id`. Validate agency activity and property;
  owner cannot attach a foreign or inactive company. Linking and disabling
  an agent account revoke existing sessions, using the existing audit and
  owner-only guard. No new API and no SQL migration.
- Add a separate `/shared-agent` browser booking page using the canonical
  grid and existing shared booking form in CORE_RATE-only mode. Login
  verifies tenant, hotel, role and PMS module. No manual payments/price edits
  are exposed to AGENT.
- Add isolated disposable two-hotel agency fixture with active/inactive/
  unlinked accounts; verify real owner creation, foreign cross-property 422,
  unlinked/inactive 403, booking 201/409, no payment and session revocation.
- Retain the original six-role staff lifecycle test separately; AGENT tests
  cover owner linkage, identity and distinct rights. Legacy unreviewed roles
  remain closed in shared mode.

**This is not production acceptance**. External agency onboarding,
self-service agent account management and production agent settlement remain
separately gated. Do not touch RC3 locked source, customer DB, DEMO, Ubuntu,
mobile or main. Run only necessary target tests and accept final single-SHA CI.

### Agent grid source-level security correction

While accepting the first agent slice, the Chromium test exposed a real
role-boundary defect: the existing `GET /api/v1/pms/grid` checked that
`staff_users.bookingAgentId` was non-null but did not verify that the agency
still had `ACTIVE` status. The PMS booking preview/commit *did* require ACTIVE.
These inconsistent checks must not allow deactivated agencies to see the hotel
calendar.

The follow-up changes the existing **single canonical grid query** to join
`booking_agents` on both bookingAgentId and propertyId with `status='ACTIVE'`.
No new endpoint, new DB column, migration or bypass. The existing agent privacy
mask (foreign guest name, phone, reservation ID) is preserved. A new two-hotel
browser check asserts that disabled/unlinked agent identities get 403 rather
than the room inventory, and that active agents see only their own guest data.
This correction is subject to exact-head HTTPS and regression acceptance.
