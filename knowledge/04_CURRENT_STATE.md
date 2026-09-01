# RESORT OS — CURRENT STATE

Version: 3.4
Date: 2026-09-02
Status: INTERNAL RELEASE CANDIDATE / CI-LOCAL STAGING VERIFIED / EXTERNAL PRODUCTION EVIDENCE INCOMPLETE / NOT LIVE
Canonical: YES
Authority: factual implementation reality only

**TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Audited executable boundary

Repository: `stvelikiy-star/resort-os`.
Integration branch: `integration/site-pms-cms-20260827`.
Accepted executable head: `3787e8729b84e1ecc41133ab846a909943458306`.
Observed integration merge: `102a46ef721ee880647ecd6f81024bd744458170`.

The accepted executable head is the exact PR #95 product head after Guest OS PIN presentation/reissue and admin locale/contrast hardening and completed **35/35 executable acceptance/security/regression contours successfully, 0 failures**. The separate RC-truth workflow intentionally blocked that product head because the prior RC was frozen; this refreeze follows the actual tree-equivalent integration merge. The successful contours include Resort Core, Full Staging Gate, PMS Final Acceptance, Guest OS Core/Access/Requests, PMS mutation/grid tests, Single Server Production Package, frontend/backend/database dependency security, the dedicated Admin Guest PIN and i18n CI, Admin Runtime Truth, realtime, operations, payment idempotency, backup/restore and AI/n8n contracts.

The observed integration merge has **0 changed files** versus that accepted executable head. The canonical machine-readable RC boundary is `release/current-rc.json`, guarded by `scripts/release_rc_truth_guard.py`.

The database toolchain remains deterministic and separately security-gated: `prisma` and `@prisma/client` are exactly pinned to `6.12.0`, `packages/database/package-lock.json` is committed, clean `npm ci` is required, and the database npm audit must have zero HIGH/CRITICAL findings before acceptance.

`main` is not a production source. The current `main` branch is stale relative to the accepted integration RC and must not be used for Beget deployment or cutover.

Earlier closed gates retain their own exact-head CI evidence, including canonical 84-room PMS acceptance, Security #42 and physical room import gate #38.

The accepted repository tree is not evidence of external production deployment.

## Authority

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`.

OWNER/MANAGER retain reservation and payment authority. AI/n8n cannot confirm payment, guarantee a Reservation, invent a fixed prepayment percentage/payment route or bypass Core availability/pricing. Sheets, reports, analytics and inbox surfaces are not parallel transaction truth.

NFC acquiring/wallet remains deferred and outside active V1 composition.

## Database release contract

Verified committed migration chain:

`0_init -> 1_site_content -> 2_guest_service_tasks -> 3_owner_analytics_snapshots -> 4_guest_engagements -> 5_guest_os_core -> 6_service_point_qr_operations`.

Exact seven-migration ledger, 27 critical domain constraints, clean migration deployment and backup -> clean restore are CI-verified.

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
- global admin locale selector for RU/KG/EN, dynamic rendering translation for operational labels/statuses/audit codes and a final high-contrast blue/white dashboard layer.

The canonical 84-room import contract is closed. External target reconciliation remains a deployment evidence step, not a data-collection blocker.

## Stay / Guest OS / CRM

Implemented and CI-verified:

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

## Staff / Guest Services

Implemented and CI-verified:

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

Implemented and CI-verified:

- Payment fact/idempotency controls;
- Reservation ledger, remaining/overpaid and debtors including checked-out debt;
- explicit manager prepayment requirement without fixed percentage;
- local `Asia/Bishkek` financial day handling;
- Owner Intelligence / Control / Growth / Dashboard analytics;
- factual operational KPIs and recurring-fault views;
- no statistical forecast claim where history is insufficient;
- Growth outbound authority remains `NONE_AUTOMATIC`.

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

Repository/CI:

- migration baseline: VERIFIED;
- backup -> restore: VERIFIED;
- frontend/backend dependency security inspection: VERIFIED;
- database Prisma dependency security + deterministic lockfile: VERIFIED;
- production package build: VERIFIED IN CI;
- CI-local Full Staging: VERIFIED;
- Beget hardening logic: VERIFIED IN CI only;
- exact Git SHA -> deployed application image linkage contract: VERIFIED IN CI;
- staging mutation safety guard: VERIFIED IN CI;
- unified external staging acceptance orchestration contract: VERIFIED IN CI;
- physical room import gate #38: CLOSED / VERIFIED by its own exact-head evidence;
- launch verifier: fail-closed and requires real target room reconciliation rather than repeating room-data approval.

External/production:

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

Extend rather than rewrite the verified Resort Core/PostgreSQL/PMS/Stay/Guest OS/Guest CRM/OperationalTask/Finance/Owner analytics/Inbox/Audit/RBAC boundaries. Do not activate NFC or automatic commercial/payment authority as a side effect of launch work.
