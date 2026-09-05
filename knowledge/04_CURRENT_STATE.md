# RESORT OS — CURRENT STATE

Version: 3.9-working
Date: 2026-09-05
Status: WORKING PR #110 / ACCEPTED RC STILL FROZEN / EXTERNAL PRODUCTION EVIDENCE INCOMPLETE / NOT LIVE
Canonical: YES
Authority: factual implementation reality only

**TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Audited executable boundary

Repository: `stvelikiy-star/resort-os`.
Integration branch: `integration/site-pms-cms-20260827`.
Accepted executable head: `ab6b649d91df5e9698253d43788cc657ca7040c9`.
Observed integration merge: `c4a2b9584e9e6222ae7b213a6bf87ba3cd6f97e4`.

The exact PR #107 product/security head completed **20/20 applicable non-RC workflows successfully, 0 failures**. `Release RC Truth CI` intentionally failed before refreeze because the previous RC manifest still pointed to the prior accepted executable boundary.

The observed PR #107 integration merge has **0 changed files** versus the tested PR head. Therefore the merged product tree is identical to the exact tree that passed the applicable PR #107 regression contours.

PR #107 is a narrow release-security/governance delta on top of the accepted product stack. It does not change PMS/Kitchen business logic, room inventory, pricing, payment authority, database schema, NFC scope or provider enablement.

Earlier accepted product evidence remains part of the same tree:

- PR #102 customer-facing automation truth hardening: **17/17 applicable non-RC workflows SUCCESS**;
- PR #98 Kitchen/Core release baseline: **43/43 non-RC workflows SUCCESS**.

The current working delta is draft PR #110 on `ux/management-kitchen-guest-v1-20260905`. It extends management UX, Reception readiness, Kitchen/Dining, Guest Marketplace and manager-controlled Guest Offer campaigns. It is **not** the accepted RC and must not be treated as merged, refrozen or production-authorized until its required regression/acceptance gates are complete.

The canonical integration branch is the only release integration source. `main` is not a production source and must not be used for Beget deployment or cutover while stale relative to integration.

The canonical machine-readable RC boundary is `release/current-rc.json`, guarded by `scripts/release_rc_truth_guard.py`.

Repository/CI evidence is not evidence of external production deployment.

## Authority

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`.

OWNER/MANAGER retain reservation and payment authority. AI/n8n cannot confirm payment, guarantee a Reservation, invent a fixed prepayment percentage/payment route or bypass Core availability/pricing. Sheets, reports, analytics and inbox surfaces are not parallel transaction truth.

NFC acquiring/wallet remains deferred and outside active V1 composition.

## Database release contract

Committed migration chain on the current working branch:

`0_init -> 1_site_content -> 2_guest_service_tasks -> 3_owner_analytics_snapshots -> 4_guest_engagements -> 5_guest_os_core -> 6_service_point_qr_operations -> 7_kitchen_operations -> 8_dining_service_control -> 9_guest_offer_campaigns`.

Exact ten-migration ledger, 37 critical hotel/payment/operations domain constraints, clean migration deployment and backup -> clean restore are release gates. External staging/production migration uses `npx prisma migrate deploy`.

`prisma` and `@prisma/client` remain exactly pinned to `6.12.0`; deterministic lockfile install and zero HIGH/CRITICAL database dependency findings are release gates.

Canonical room intake/import gate #38 is **CLOSED / COMPLETED** at 84 rooms / 12 mapped categories with checksum-bound owner approval, fail-closed importer, drift protection and reviewed import contract. No new owner room questionnaire is required. On a real external staging database, reconciliation still requires dry-run -> exact diff review -> safe apply -> final zero-diff evidence.

## Public site

Verified in repository/CI:

- owner-approved public truth guard;
- RU/KG/EN browser acceptance;
- Transfer before Tours;
- Core availability/pricing and ReservationRequest boundary;
- no fixed 30% prepayment claim;
- no automatic reservation/payment confirmation;
- current approved contact/service facts;
- CMS -> Core -> public runtime linkage;
- locale-safe CMS fallback and CMS ownership after RU/KG/EN localization.

External rendered production truth is not yet verified on a real staging/production host.

## PMS / Reception

Canonical PMS includes:

- compact room × night owner grid;
- single-night click and multi-night drag selection;
- Core pricing preview/commit;
- move/resize/Split Stay;
- stale/conflict/race rejection;
- TECH_BLOCK protection;
- CLEAN check-in gate;
- realtime/audit;
- factual RoomAssignment relocation;
- checkout -> DIRTY/housekeeping lifecycle;
- Reception read/check-in/check-out/QR authority without financial/commercial mutation authority;
- one-time six-digit Guest OS PIN on successful check-in;
- audited PIN reissue only for CHECKED_IN reservation with ACTIVE stay; plaintext returned once, PBKDF2 hash persisted;
- Admin fail-closed role boundary for OWNER / MANAGER / RECEPTION / MAID / TECHNICIAN;
- RU/KG/EN admin locale selector and operational rendering.

PR #110 adds a narrow audited Reception -> Housekeeping readiness handoff for guaranteed arrivals without weakening the Core `CLEAN` check-in gate and without granting RECEPTION unrestricted Operations authority.

The canonical 84-room import contract is closed. External target reconciliation remains a deployment evidence step, not a data-collection blocker.

## Stay / Guest OS / CRM

Implemented and regression-gated baseline:

- canonical `Stay` and `RoomAssignment` lifecycle;
- permanent Room QR using server-side token hash;
- PIN verification and HttpOnly GuestSession;
- session revocation at checkout;
- Guest OS service requests;
- factual Guest CRM history across repeated stays and relocations;
- safe manager-confirmed guest preferences;
- GuestHistoryEvent and AuditLog trails;
- Guest OS Kitchen menu/order API through existing GuestSession authority.

PR #110 adds an authenticated in-stay Marketplace, fail-closed current-day Kitchen menu exposure, verified-facts AI concierge integration and dynamic manager-controlled Guest Offer campaigns. Offer actions remain bounded to real Guest Requests, configured HTTPS destinations or AI prompts and do not create payment/commercial truth automatically.

Room QR / GuestSession remains separate from anonymous Service Point QR.

## Kitchen / Dining

Kitchen remains a Resort Core/PostgreSQL operational domain, not a parallel accounting system.

Accepted baseline implementation includes:

- Kitchen Admin for `DINING_STAFF`, OWNER and MANAGER;
- editable RU/KG/EN provisional menu with server-side prices and active/draft controls;
- factual table register;
- table states `AVAILABLE / RESERVED / OCCUPIED / CLEANING / OUT_OF_SERVICE`;
- `KitchenOrder` lifecycle `NEW -> ACCEPTED -> COOKING -> READY -> SERVED/CANCELLED`;
- table, room, Stay and Reservation context where appropriate;
- Guest OS Kitchen orders through GuestSession authority;
- idempotent Dining arrival card created transactionally on successful PMS check-in, with repair sync fallback;
- no sensitive payment data in the Dining arrival card;
- Kitchen totals isolated from Hotel `Payment` and `Reservation.totalKgs`;
- audited Kitchen/check-in routing.

PR #110 working delta adds:

- dedicated `/kitchen` entry and `/waiter` floor surface using existing `DINING_STAFF` authority;
- hotel-local daily menu publication by meal type;
- stop-list / restore;
- table reservations with capacity/time-conflict guards;
- waiter assignment and READY -> SERVED handoff;
- Guest OS visibility only for active, non-draft, explicitly published, available and not-sold-out items.

The provisional menu and real table layout/count remain operationally editable and are not fabricated in code.

## Staff / Guest Services

Implemented and regression-gated:

- MAID / TECHNICIAN workflows;
- Reception and Dining role access where defined;
- unified Guest Services Center over canonical OperationalTask;
- role-based request routing;
- in-stay requests do not automatically change room state or create Payment;
- staff voice contract;
- anonymous Service Point QR -> OperationalTask routing for common areas.

## Service Point QR

Implemented and CI-verified:

- separate `ServicePoint`, request options and QR lifecycle;
- opaque display-once QR token, SHA-256 hash stored server-side;
- issue / rotate / revoke;
- public `/p/{token}` without Guest/Stay/Reservation/Payment data;
- payload-safe idempotency and replay mismatch rejection;
- ServicePoint-linked OperationalTask without room/stay/reservation context;
- PostgreSQL constraints preventing context mixing;
- NFC endpoint remains absent.

## Finance / Owner management

Implemented and regression-gated:

- Payment fact/idempotency controls;
- Reservation ledger, remaining/overpaid and debtors including checked-out debt;
- explicit manager prepayment requirement without fixed percentage;
- local `Asia/Bishkek` financial day handling;
- Owner Intelligence / Control / Growth / Dashboard analytics;
- factual operational KPIs and recurring-fault views;
- no statistical forecast claim where history is insufficient;
- Growth outbound authority remains `NONE_AUTOMATIC`;
- Kitchen operational totals do not silently post to Hotel Payment or accommodation total.

These are operational/management metrics, not statutory accounting.

## AI / n8n / communications

Implemented and CI-verified contracts:

- unified inbox for messaging channels;
- payload-safe provider idempotency;
- `Conversation <-> ReservationRequest` linkage;
- provider delivery evidence;
- AI draft authority boundary;
- n8n Resort Core contract;
- website direct-Core booking boundary.

Customer-facing Core guest facts remain synchronized with owner-approved truth:

- check-in `14:00`, checkout `12:00`;
- gym and sports grounds absent;
- laundry and conference halls `UNKNOWN_DO_NOT_PROMOTE`;
- sauna winter-only, 5,000 KGS/hour, approximately 4–5 people;
- billiards 500 KGS/hour;
- table tennis free for staying guests;
- parking approximately 20–30 cars, free for staying guests;
- no unverified payment-method enumeration in customer-facing AI context;
- public launch payment methods/providers remain `NOT_VERIFIED_FOR_LAUNCH` until real manager/provider launch evidence exists.

PR #107 adds shared fail-closed provider environment validation used by Beget and production preflight:

- Telegram Sales token may not be an obvious placeholder and its webhook secret must be real/non-placeholder and at least 24 characters when enabled;
- GREEN API ID/token must both be real/non-placeholder and webhook secret must be real/non-placeholder and at least 24 characters when enabled;
- any configured Resort OS OpenAI model requires a real/non-placeholder `OPENAI_API_KEY`;
- Staff Voice Telegram/transcription configuration requires a real bot token and real/non-placeholder staff webhook secret at least 24 characters;
- obvious placeholder forms such as `CHANGE_ME`, `REPLACE_ME`, `PLACEHOLDER`, `YOUR_*`, `NOT_SET` and similar are rejected;
- deterministic provider-security matrix and Beget integration checks passed on the exact accepted head.

No provider is enabled or proven live by this static validation. Real launch-enabled provider E2E remains external evidence.

## Release governance hardening

PR #107 makes two already-real P0 gates structurally mandatory in the final `verify_launch_acceptance.py --mode cutover` manifest:

1. `github_branch_protection` must be VERIFIED;
2. `drive_launch_control_permissions` must be VERIFIED.

Current factual status:

- integration branch protection: **NOT VERIFIED / currently `protected:false`, required-check enforcement off**; issue #91 OPEN;
- Google Drive permission audit: **13/13 top-level project folders expose `anyone with link -> writer`**; issue #100 OPEN;
- the connected tools cannot safely mutate either control, so neither is claimed fixed.

The final cutover verifier now fails closed while either governance gate remains unverified.

## Deployment state

Repository release engineering on the current working branch has:

- prior 43/43 Kitchen/Core release baseline;
- PR #102 AI truth-hardening delta with 17/17 applicable non-RC success;
- PR #107 provider/governance security delta with 20/20 applicable non-RC success;
- exact ten-migration database ledger through `8_dining_service_control` and `9_guest_offer_campaigns`;
- 37-constraint shared release fingerprint;
- backup -> clean restore contract verified against the ten-migration boundary;
- frontend/backend/database dependency security inspection;
- deterministic Prisma dependency/lockfile checks;
- production package build contract;
- CI-local Full Staging contract, with the current PR gate required to pass before acceptance;
- Beget hardening contract and provider-secret security matrix;
- exact Git SHA -> deployed application image linkage contract;
- staging mutation safety guard;
- unified external staging acceptance orchestration contract;
- physical room import gate #38;
- fail-closed launch verifier with GitHub/Drive governance gates;
- Kitchen/PMS/Guest OS/Finance/Staff/AI/automation regression contours.

The accepted RC remains the PR #107 boundary: tested head `ab6b649d91df5e9698253d43788cc657ca7040c9` bound to tree-equivalent integration merge `c4a2b9584e9e6222ae7b213a6bf87ba3cd6f97e4`. PR #110 must not replace that RC until its exact-head acceptance is complete and a deliberate refreeze occurs.

External/production remains separate:

- GitHub branch protection / required-check enforcement: NOT VERIFIED;
- Google Drive launch-control permissions: NOT VERIFIED; 13/13 top-level folders currently public-writer;
- actual Beget host/account preflight: NOT VERIFIED;
- full rollback backup of currently live legacy site: NOT VERIFIED;
- external HTTPS/WSS staging: NOT VERIFIED;
- external rendered public-truth probe: NOT VERIFIED;
- real staging room reconciliation against canonical 84-room register: NOT VERIFIED;
- real iPhone/Android/desktop/Telegram/Kitchen acceptance: NOT VERIFIED;
- launch-enabled provider E2E: NOT VERIFIED or NOT_REQUIRED if providers remain disabled;
- real monitoring/alerting evidence: NOT VERIFIED;
- fresh pre-cutover backup/DNS rollback evidence: NOT VERIFIED;
- explicit owner cutover approval: NOT GIVEN;
- production/DNS cutover: NOT EXECUTED.

## Launch rule

Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md` and `scripts/verify_launch_acceptance.py`.
Canonical RC manifest: `release/current-rc.json`.

Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until every required external/governance evidence gate is VERIFIED. CI success alone does not authorize DNS switch, provider activation or production declaration.

## Extension rule

Extend rather than rewrite the verified Resort Core/PostgreSQL/PMS/Stay/Guest OS/Guest CRM/OperationalTask/Finance/Owner analytics/Inbox/Audit/RBAC boundaries. Kitchen remains a Core-backed operational domain. Do not activate NFC or automatic commercial/payment authority as a side effect of launch work.
