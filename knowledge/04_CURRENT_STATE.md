# RESORT OS — CURRENT STATE

Version: 3.5
Date: 2026-09-02
Status: INTERNAL RELEASE CANDIDATE / CI-LOCAL STAGING UNDER FINAL REGRESSION / EXTERNAL PRODUCTION EVIDENCE INCOMPLETE / NOT LIVE
Canonical: YES
Authority: factual implementation reality only

**TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Audited executable boundary

Repository: `stvelikiy-star/resort-os`.
Integration branch: `integration/site-pms-cms-20260827`.

The canonical integration branch is the only release integration source. `main` is not a production source and must not be used for Beget deployment or cutover while stale relative to integration.

Earlier accepted product heads retain their exact-head CI evidence. The current Kitchen/Admin extension is accepted only after its own exact-head regression is fully green and merged tree-equivalent into integration.

The canonical machine-readable RC boundary is `release/current-rc.json`, guarded by `scripts/release_rc_truth_guard.py`. It must be refrozen after the current product merge; an older RC pointer must not be presented as the latest release.

The database toolchain remains deterministic and separately security-gated: `prisma` and `@prisma/client` are exactly pinned to `6.12.0`, `packages/database/package-lock.json` is committed, clean `npm ci` is required, and the database npm audit must have zero HIGH/CRITICAL findings before acceptance.

Earlier closed gates retain their own exact-head CI evidence, including canonical 84-room PMS acceptance, Security #42 and physical room import gate #38.

Repository/CI evidence is not evidence of external production deployment.

## Authority

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`.

OWNER/MANAGER retain reservation and payment authority. AI/n8n cannot confirm payment, guarantee a Reservation, invent a fixed prepayment percentage/payment route or bypass Core availability/pricing. Sheets, reports, analytics and inbox surfaces are not parallel transaction truth.

NFC acquiring/wallet remains deferred and outside active V1 composition.

## Database release contract

Committed migration chain:

`0_init -> 1_site_content -> 2_guest_service_tasks -> 3_owner_analytics_snapshots -> 4_guest_engagements -> 5_guest_os_core -> 6_service_point_qr_operations -> 7_kitchen_operations`.

Exact eight-migration ledger, 27 critical hotel/payment domain constraints, clean migration deployment and backup -> clean restore are release gates. Kitchen-specific constraints are additionally checked by the migration and Kitchen Operations contours.

Canonical room intake/import gate #38 is **CLOSED / COMPLETED** at 84 rooms / 12 mapped categories with fail-closed importer, drift protection and reviewed import contract. No new owner room questionnaire is required. On a real external staging database, reconciliation must still be run as dry-run -> diff review -> safe apply evidence.

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
- successful check-in surfaces the one-time six-digit Guest OS PIN without changing the Core response contract;
- OWNER/MANAGER/RECEPTION can reissue a lost/expired Guest OS PIN only for a CHECKED_IN reservation with an ACTIVE stay; plaintext is returned once, only the PBKDF2 hash is persisted and the action is audited;
- Admin fail-closed role boundary: only OWNER / MANAGER / RECEPTION / MAID / TECHNICIAN enter Admin/PMS; other operational roles remain in Staff PWA;
- global admin locale selector for RU/KG/EN and operational label/status/audit rendering.

The canonical 84-room import contract is closed. External target reconciliation remains a deployment evidence step, not a data-collection blocker.

## Stay / Guest OS / CRM

Implemented and regression-gated:

- canonical `Stay` and `RoomAssignment` lifecycle;
- permanent Room QR using server-side token hash;
- PIN verification and HttpOnly GuestSession;
- one-time six-digit PIN issuance at check-in and fail-closed reissue for active stays;
- session revocation at checkout;
- Guest OS service requests;
- factual Guest CRM history across repeated stays and relocations;
- safe manager-confirmed guest preferences;
- GuestHistoryEvent and AuditLog trails.

Room QR / GuestSession is separate from anonymous Service Point QR.

## Kitchen / Dining

Current Kitchen domain is an extension of Resort Core/PostgreSQL, not a parallel accounting system.

Implemented in the current Kitchen release candidate and subject to exact-head regression before merge:

- dedicated Kitchen Admin surface for `DINING_STAFF`, OWNER and MANAGER;
- editable RU/KG/EN draft menu with server-side prices and active/draft controls;
- factual table register managed from Kitchen Admin rather than fabricated room data;
- table states `AVAILABLE / RESERVED / OCCUPIED / CLEANING / OUT_OF_SERVICE`;
- KitchenOrder + KitchenOrderItem lifecycle `NEW -> ACCEPTED -> COOKING -> READY -> SERVED/CANCELLED`;
- table, room, Stay and Reservation context where appropriate;
- Guest OS Kitchen order API through existing GuestSession authority;
- successful PMS check-in creates an idempotent Dining arrival card in the same PostgreSQL transaction, with repair sync as a fallback;
- Dining arrival card excludes sensitive guest/payment data;
- Kitchen totals are isolated operational amounts: **no automatic Hotel Payment creation and no automatic Reservation.totalKgs mutation**;
- Kitchen order actions and check-in routing are audited.

The provisional menu is intentionally replaceable from Kitchen Admin. Real table layout/count is entered operationally and is not guessed in code.

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
- public `/p/{token}` surface without Guest/Stay/Reservation/Payment data;
- payload-safe idempotency and replay mismatch rejection;
- ServicePoint-linked OperationalTask with no room/stay/reservation context;
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

Real provider credentials/live provider E2E remain external evidence and are not inferred from CI.

## Deployment state

Repository/CI release gates include:

- migration baseline;
- backup -> restore;
- frontend/backend dependency security inspection;
- deterministic Prisma dependency/lockfile checks;
- production package build;
- CI-local Full Staging;
- Beget hardening logic;
- exact Git SHA -> deployed application image linkage contract;
- staging mutation safety guard;
- unified external staging acceptance orchestration contract;
- physical room import gate #38;
- fail-closed launch verifier.

All of these must be green at the final exact release head before internal RC freeze. The RC truth guard must then bind `release/current-rc.json` to that exact integration SHA.

External/production remains separate:

- actual Beget host/account preflight: NOT VERIFIED;
- full rollback backup of currently live legacy site: NOT VERIFIED;
- external HTTPS/WSS staging: NOT VERIFIED;
- external rendered public-truth probe: NOT VERIFIED;
- real staging room reconciliation against canonical 84-room register: NOT VERIFIED;
- real iPhone/Android/desktop/Telegram acceptance: NOT VERIFIED;
- launch-enabled provider E2E: NOT VERIFIED or NOT REQUIRED if providers stay disabled;
- real monitoring/alerting evidence: NOT VERIFIED;
- fresh pre-cutover backup/DNS rollback evidence: NOT VERIFIED;
- explicit owner cutover approval: NOT GIVEN;
- production/DNS cutover: NOT EXECUTED.

## Launch rule

Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md` and `scripts/verify_launch_acceptance.py`.
Canonical RC manifest: `release/current-rc.json`.

Production remains **STOP** until every required external evidence gate is VERIFIED. The room-register approval gate itself is already closed; the external manifest requires target reconciliation evidence instead. CI success alone does not authorize DNS switch, provider activation or production declaration.

## Extension rule

Extend rather than rewrite the verified Resort Core/PostgreSQL/PMS/Stay/Guest OS/Guest CRM/OperationalTask/Finance/Owner analytics/Inbox/Audit/RBAC boundaries. Kitchen remains a Core-backed operational domain. Do not activate NFC or automatic commercial/payment authority as a side effect of launch work.
