# RESORT OS — CURRENT STATE

Version: 3.1
Date: 2026-09-01
Status: INTERNAL RELEASE CANDIDATE / CI-LOCAL STAGING VERIFIED / EXTERNAL PRODUCTION EVIDENCE INCOMPLETE / NOT LIVE
Canonical: YES
Authority: factual implementation reality only

**TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Audited executable boundary

Repository: `stvelikiy-star/resort-os`.
Integration branch: `integration/site-pms-cms-20260827`.
Current integration head: `42798b3fd360b5f5a6a4eb2124b1231702c99eea`.
Latest tested exact PR head: `da3cc80f3c13973f799c01ddd8ad64ed79c17f6f`.

The current merge commit has **0 changed files** versus that tested PR head. The exact PR head completed **20/20 triggered workflow contours successfully**, including Resort Core, Full Staging Gate, Single Server Production Package, Public Browser Acceptance, Public Site Truth, dependency security, realtime, operations, backup/restore and the dedicated Site Content Runtime regression.

Earlier closed gates retain their own exact-head CI evidence, including canonical 84-room PMS acceptance, Security #42 and physical room import gate #38.

The current merge commit contains the reviewed tree; it is not evidence of external production deployment.

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
- Admin fail-closed role boundary: only OWNER / MANAGER / RECEPTION / MAID / TECHNICIAN enter Admin/PMS; other operational roles remain in Staff PWA.

The canonical 84-room import contract is closed. External target reconciliation remains a deployment evidence step, not a data-collection blocker.

## Stay / Guest OS / CRM

Implemented and CI-verified:

- canonical `Stay` and `RoomAssignment` lifecycle;
- permanent Room QR using server-side token hash;
- PIN verification and HttpOnly GuestSession;
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
- dependency security inspection: VERIFIED;
- production package build: VERIFIED IN CI;
- CI-local Full Staging: VERIFIED;
- Beget hardening logic: VERIFIED IN CI only;
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

Production remains **STOP** until every required external evidence gate is VERIFIED. The room-register approval gate itself is already closed; the external manifest requires target reconciliation evidence instead. CI success alone does not authorize DNS switch, provider activation or production declaration.

## Extension rule

Extend rather than rewrite the verified Resort Core/PostgreSQL/PMS/Stay/Guest OS/Guest CRM/OperationalTask/Finance/Owner analytics/Inbox/Audit/RBAC boundaries. Do not activate NFC or automatic commercial/payment authority as a side effect of launch work.
