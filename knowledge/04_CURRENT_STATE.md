# RESORT OS — CURRENT STATE

Version: 1.6
Date: 2026-08-26
Status: DELIVERY RELEASE CANDIDATE / CURRENT EXECUTABLE BASELINE CI-VERIFIED / NOT PRODUCTION READY
Canonical: YES
Document Type: Evidence-Based Current System State
Authority: **This is the only canonical owner of factual implementation reality.**

Critical rule: **TARGET != CURRENT. IMPLEMENTED != VERIFIED. DEVELOPMENT VERIFIED != PRODUCTION READY.**

Supporting property documents (`06`, `07`, `08`) may describe requirements, plans or decision extracts, but they must not redefine Current State. If they conflict with this document about what actually exists, this document controls until new implementation evidence is captured here.

---

## 1. Verified code baseline and architecture

Repository: `stvelikiy-star/resort-os`.

Current executable code baseline verified in GitHub Actions:

`f68e2ff6428929f4e069d650ff2b8d30a6224599`

This current baseline contains the recovered executable stack, payment-idempotency hardening, Control Center monorepo verification hardening, the security maintenance upgrade of Admin/Public Web/Staff to Next.js 15.5.24 with React/React DOM 19.2.8, the current Three Crowns public-site/catalog implementation, read-only CRM mirror contract, inactive n8n Google Sheets mirror workflow, the standalone presentation-only Admin `/demo` surface, vendor-neutral privacy-safe public booking-funnel analytics, and the fail-closed public-site/privacy truth guard.

The repository-owned AI PROF verification contract remains fail-closed: root `npm test` validates the exact trusted Git blob identities of all three app manifests before running their typechecks/builds and Core/scripts Python compilation. The trusted manifest blobs at this baseline remain:
- `apps/admin/package.json` -> `e29254cc30c879d2e581db42002367a30d850bf7`;
- `apps/web/package.json` -> `abe10c8520756ae0863702f2389bda821a956384`;
- `apps/staff/package.json` -> `85e54aabc4afefc58d1d20b2a92031c4c364a1fa`.

Current owner-approved V1 architecture:

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Canonical runtime entrypoint: `app.app_entry:app`.
Current FastAPI application version declared in `services/api/app/main.py`: `0.2.0`.

Resort Core owns hotel truth:
- 84 room positions / 12 room categories development baseline;
- rate periods, availability and pricing;
- ReservationRequest / Reservation;
- room/date inventory;
- stay lifecycle;
- housekeeping / maintenance;
- staff/RBAC;
- manager-recorded internal payment facts;
- controlled n8n API;
- read-only CRM mirror feed;
- AuditLog.

Client channels are orchestrated outside Resort Core:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- website -> Resort Core directly.

n8n objective = **HOT QUALIFIED LEAD**. It must not write PostgreSQL directly, confirm payment, create guaranteed Reservation directly, check-in/out/refund or invent price/availability/policy.

---

## 2. NFC active-scope truth

NFC is **DEFERRED / DORMANT** and excluded from active V1 runtime/work.

Current enforcement:
- NFC source/schema artifacts may remain as historical/dormant implementation;
- `app.app_entry:app` does **not** compose NFC/beach payment routers;
- normal hotel checkout does not query or mutate NFC tables;
- active Staff PWA does not expose the beach terminal branch;
- `scripts/release_scope_guard.py` fails if NFC/beach routes are accidentally composed again;
- `NFC Deferred Scope CI` is part of the active verification matrix.

Do not reactivate NFC without an explicit owner decision recorded through canonical decision authority.

---

## 3. Prepayment and finance truth

Owner-approved Three Crowns V1 rule:
- manager decides prepayment amount, terms and payment method;
- manager collects prepayment manually;
- no global active `PREPAYMENT_PERCENT` exists in the runtime contract;
- automation does not generate/collect/approve prepayment;
- Resort OS records manager-confirmed internal payment facts only;
- `ReservationRequest != Reservation`;
- unpaid request does not hold inventory;
- automation cannot state that a room is booked until manager-confirmed Reservation truth exists.

Current booking flow:

`ReservationRequest -> manager quote of stay value -> manager records accepted payment fact -> atomic Guest + Reservation + InventoryBlock + Payment`.

Current payment-idempotency behavior is VERIFIED on the executable baseline:
- `payments.idempotencyKey` remains globally unique in PostgreSQL;
- `(provider, externalRef)` remains unique where an external reference exists;
- exact normalized retries are idempotent;
- the same key with changed amount/method/external reference returns `409 IDEMPOTENCY_PAYLOAD_MISMATCH`;
- additional Reservation payments also bind the normalized note to the idempotent payload;
- the same key used for another request/reservation returns `409 IDEMPOTENCY_CONFLICT`;
- a different payment operation against an already converted request returns `409 REQUEST_ALREADY_CONVERTED` rather than a false replay;
- duplicate manager external references return `409 PAYMENT_EXTERNAL_REF_CONFLICT`;
- whitespace-only normalized payment methods are rejected with `422 INVALID_PAYMENT_METHOD`;
- transaction-scoped PostgreSQL advisory locks serialize global idempotency-key/external-reference races;
- focused concurrent tests prove one durable write and deterministic conflict behavior instead of duplicate writes/unique-constraint 500s.

Internal finance is operational control, **not accounting profit/tax/revenue recognition**.

Automated acquiring/payment-provider integration remains outside the active Three Crowns V1 requirement. General Resort OS payment-provider implementation remains a separate VALIDATE decision; the existence of manager-manual recording does not promote a generic provider integration to VERIFIED.

---

## 4. PMS Chessboard V2 — primary product surface

STATUS: **VERIFIED DEVELOPMENT BASELINE**.

Server-authoritative mutation contract:
- `GET /api/v1/admin/pms/reservations/{id}/schedule`;
- `POST /api/v1/admin/pms/reservations/{id}/schedule/preview`;
- `POST /api/v1/admin/pms/reservations/{id}/schedule/commit`.

Verified capabilities include:
- one spanning reservation bar per room/date segment;
- move a future simple reservation to another room;
- drag a future simple reservation to another room/start date while preserving duration;
- outer-edge pointer resize for check-in/check-out dates;
- explicit date editor for touch/tablet;
- split one Reservation into contiguous room-assignment segments;
- relocate a CHECKED_IN guest from an effective date without rewriting already-lived history;
- server pricing preview/delta without silently modifying stored commercial total;
- explicit manager confirmation before commit;
- stale-version protection;
- conflict preview and race rollback;
- PostgreSQL exclusion constraint as final double-booking guard;
- TECH_BLOCK rejection;
- immediate relocation requires CLEAN target room;
- immediate relocation dirties the vacated room and creates/reuses housekeeping in the same transaction;
- AuditLog before/after evidence;
- realtime PMS snapshots.

Concurrency hardening:
- Reservation is locked before mutation;
- active reservation InventoryBlocks are locked separately;
- room rows are locked in deterministic sorted order;
- joined room rows are not accidentally locked earlier by the schedule query.

Daily quick views:
- all rooms;
- arrivals today;
- departures today;
- in-house;
- free today.

UI hardening includes human stay labels, distinct reservation/current-stay/maintenance/manual-block states, quick booking facts, and explicit confirmation for check-in/check-out.

Intermediate relocation segment boundaries are not treated as hotel arrival/departure boundaries.

---

## 5. Reception / reservation workspace

STATUS: **VERIFIED DEVELOPMENT BASELINE**.

Schedule-aware behavior:
- one row per Reservation even when a stay uses several rooms;
- current/working room is resolved from complete schedule and hotel-local date/status;
- booking detail returns the complete room route;
- room tasks are collected across every room used by the stay;
- guest/contact, notes and source request are visible;
- internal payments, paid amount and outstanding balance are visible;
- recent AuditLog events are visible.

Reception list exposes stay status, guest/room, dates, manager-recorded paid/total amount and remaining balance/full-payment state.

Check-in/out failures are translated to operator-facing room-readiness/date-schedule messages. Both actions require explicit confirmation in UI.

Additional internal payment endpoint:
- `POST /api/v1/admin/booking/reservations/{id}/payments`;
- manager-entered positive amount/method/reference/note;
- provider stored as `MANAGER_MANUAL`;
- payload-bound idempotency and conflict behavior described in section 3;
- payment fact is audited.

---

## 6. Stay / room-condition safety

STATUS: **VERIFIED DEVELOPMENT BASELINE**.

Check-in:
- only GUARANTEED Reservation;
- hotel-local date must belong to the reservation room schedule;
- actual room segment must be CLEAN;
- no unsupported early/late commercial charge is invented.

Check-out:
- only CHECKED_IN Reservation;
- room is selected schedule-aware rather than from the first historical block;
- early checkout releases future inventory atomically;
- stored commercial total is not silently recalculated;
- checkout outside schedule requires manager to extend dates first;
- vacated room becomes DIRTY;
- housekeeping is created/reused;
- no NFC dependency exists in the active checkout transaction.

---

## 7. Housekeeping / maintenance transition safety

STATUS: **VERIFIED DEVELOPMENT BASELINE**.

HOUSEKEEPING transition matrix:
- `OPEN -> IN_PROGRESS`;
- `IN_PROGRESS -> IN_INSPECTION`;
- manager acceptance: `IN_INSPECTION -> DONE`;
- manager rejection/rework: `IN_INSPECTION -> IN_PROGRESS`;
- manager may cancel active work;
- DONE/CANCELLED are terminal.

Room-condition rework path:

`DIRTY -> IN_INSPECTION -> DIRTY -> IN_INSPECTION -> CLEAN`.

Safety rules:
- skipped transitions return `409 INVALID_TASK_TRANSITION`;
- line staff must claim/own tasks before changing status;
- only OWNER/MANAGER decides housekeeping inspection acceptance/rework;
- housekeeping inspection does not overwrite `TECH_BLOCK`;
- housekeeping DONE is allowed only when physical room state is `IN_INSPECTION`;
- TECH_BLOCK cannot be silently turned CLEAN by housekeeping;
- maintenance DONE changes room to DIRTY for subsequent housekeeping;
- AuditLog captures status transitions.

Admin Operations includes assignment/reassignment, accept-ready, return-to-rework, active-task cancellation and action history.

Active Staff PWA roles:
- OWNER;
- MANAGER;
- MAID;
- TECHNICIAN.

BEACH_PARTNER terminal flow is not active.

Photo/checklist evidence remains future work because exact mandatory checklist rules have not been approved.

---

## 8. PMS/admin and internal finance areas

STATUS: **VERIFIED DEVELOPMENT BASELINE FOR CURRENT CI-COVERED FLOWS**.

Current manager navigation:
- **Главная** — Command Center;
- **Шахматка** — primary daily operating surface;
- **Заявки** — ReservationRequest manager handoff;
- **Брони** — reception / stays;
- **Финансы** — internal manager-recorded payment visibility;
- **Операции** — housekeeping / maintenance / task control;
- **Персонал** — roles, task load, Telegram/session operational facts;
- **Аудит сообщений** — optional communication/audit workspace; n8n remains the client orchestrator.

Command Center drill-down navigates into operational areas. PMS is not a mock.

A standalone Admin `/demo` presentation route is also present and CI-built:
- it uses explicitly synthetic demonstration data;
- it provides a client-facing chessboard/dashboard showcase without production credentials or a live Core dependency;
- it is presentation-only and does not write to Resort Core/PostgreSQL;
- production `/` remains the authenticated Core-backed operational surface;
- demo data must never be represented as current hotel truth, production occupancy or a production runtime proof.

Finance UI derives only from stored manager-confirmed facts:
- received amount/count for a selected period;
- active Reservation booked total / received / outstanding;
- received amounts by recorded method/day;
- payment status snapshot;
- recent payment records;
- all-time refund-status snapshot where representable by the current Payment model.

Explicitly not included:
- automatic acquiring;
- automatic payment links/QR;
- automatic prepayment percentage;
- tax/profit/revenue-recognition accounting.

---

## 9. Staff / voice / Telegram

STATUS: **VERIFIED DEVELOPMENT BASELINE FOR ACTIVE CI-COVERED CONTRACTS**.

Implemented and exercised by the active matrix:
- staff PWA for active hotel roles;
- task claim/assignment/reassignment;
- strict housekeeping/maintenance transitions;
- task action history;
- Telegram Mini App staff identity/linking;
- conservative voice-maintenance adapter behavior.

Voice safety:
- linked active staff only;
- exact single real-room match can create a room-linked task;
- ambiguous/no room match becomes review work without blocking a guessed room;
- short room numbers require explicit room context;
- automatic urgency remains NORMAL until exact severity rules are approved.

Direct client-provider adapters retained in Core remain optional/reference code and are not an active V1 dependency.

---

## 10. n8n automation and CRM mirror boundary

STATUS: **VERIFIED DEVELOPMENT CORE CONTRACT / CRM MIRROR IMPLEMENTED / LIVE GOOGLE SHEETS SYNC NOT VERIFIED**.

Protected by `X-Resort-Service-Key`.

Current allowed contract includes:
- hotel facts;
- deterministic availability/pricing;
- create/read ReservationRequest;
- request/reservation/payment status facts that exist in Core;
- structured staff intake where applicable;
- protected read-only `GET /api/v1/automation/read/crm-feed` for ReservationRequest, Reservation and Payment mirror data.

CRM mirror authority rules:
- Resort Core remains source of truth;
- the CRM feed is read-only and exposes no Google Sheets -> PostgreSQL write-back route;
- stable Core IDs are used for mirror upserts;
- admin Requests includes a CRM-compatible CSV fallback export;
- committed n8n workflow `automation/n8n/crm-google-sheets-sync.json` is inactive and contains no OAuth/service secrets;
- intended workflow behavior is periodic Core -> Google Sheets upsert for Leads, Bookings and Payments while preserving manager-only CRM fields;
- live Google Sheets OAuth selection, workflow publication, execution against the target sheet and ongoing runtime synchronization are **NOT VERIFIED** by repository evidence alone.

n8n/AI cannot bypass Core authority to create guaranteed reservations, confirm manager payments, check-in/out, refund or mutate hotel money.

Implementation/runbook detail: `automation/n8n/README.md` and `automation/n8n/CRM_GOOGLE_SHEETS_SYNC.md`.

Those runbooks and `knowledge/08_CLIENT_AUTOMATION_N8N_BOUNDARY.md` are supporting implementation/decision documents; none replaces canonical Product/Domain/AI/Current-State authority.

---

## 11. Public sales site

STATUS: **IMPLEMENTED DELIVERY BASELINE; BUILD + PUBLIC-TRUTH/PRIVACY GUARD VERIFIED; FINAL MEDIA COMPLETENESS / VISUAL ACCEPTANCE STILL OPEN**.

Current `apps/web` includes:
- rebuilt premium canonical homepage;
- centralized 12-category `roomCatalog`;
- `/rooms` catalog plus 12 statically generated `/rooms/[slug]` category pages;
- verified room-area and baseline-capacity presentation from current project intake;
- official summer 2026 category price matrix as a reference layer;
- confirmed resort facts: own beach, 150 m pier, SPA/massage, outdoor pool 15×8, Cholpon-Ata;
- confirmed contacts;
- live Core availability/pricing;
- mobile-friendly date/guest search;
- selected-room request flow;
- real ReservationRequest creation;
- explicit request-not-yet-booking / no automatic room-block wording;
- manager confirmation/prepayment boundary;
- metadata/OpenGraph/JSON-LD/sitemap/robots;
- cross-route navigation and mobile browsing;
- vendor-neutral public booking-funnel analytics event bus.

Current analytics truth:
- events cover search started/succeeded/failed, room selection and request started/succeeded/failed;
- analytics payloads contain only event-specific aggregate/commercial fields such as guest counts, nights, room type code, availability counts and quote values;
- guest name, phone, email, free-text notes, request IDs and exact travel dates are intentionally excluded;
- TypeScript event-specific payload types plus runtime allowlists reject unknown/non-scalar payload fields;
- `scripts/public_site_truth_guard.py` additionally checks the analytics allowlist and forbids sensitive keys from being added silently;
- events currently publish to `window.dataLayer` and a local `three-crowns:analytics` CustomEvent;
- no external GTM/GA/other analytics vendor is configured or VERIFIED by this repository evidence.

Current media truth:
- rendered primary public media use repository-local Three Crowns assets;
- current homepage explicitly treats the materialized local photo subset as incomplete for category-specific photography;
- presence of a candidate/source asset does not establish a CURRENT operational service claim;
- `conference.webp`, billiards, laundry and sauna are not allowed to become public CURRENT claims without separate canonical verification.

Fail-closed public truth enforcement:
- `scripts/public_site_truth_guard.py` protects homepage, metadata, room catalog/pages, BookingWidget, roomCatalog and the public analytics module;
- it rejects stale fixed-prepayment rules, the old two-day unpaid hold, fixed first-night prepayment, uncanonicalized conference/billiards/laundry/sauna claims, conference media promotion, remote/hotlinked media and sensitive analytics allowlist keys;
- it requires the live Core availability/request endpoints, explicit request-not-confirmed-booking wording and exactly 12 public categories;
- dedicated `Public Site Truth CI` is active and passed on exact current executable main `f68e2ff6428929f4e069d650ff2b8d30a6224599`.

Website and PMS read the same InventoryBlock truth; no separate availability synchronization job is required.

A Vercel deployment existing under a Three Crowns project name does not by itself prove correspondence to this exact canonical GitHub main. Production deployment correspondence remains a separate runtime/deployment gate until exact source linkage is verified.

---

## 12. Deployment / release tooling

STATUS: **DELIVERY TOOLING IMPLEMENTED / DEVELOPMENT CI VERIFIED / PRODUCTION GATES OPEN**.

Implemented:
- API/admin/web/staff Dockerfiles;
- production compose;
- canonical `/health/live` and `/health/ready` probes plus compatibility aliases;
- environment templates aligned with manager-owned prepayment;
- privacy-safe request-id logging;
- production preflight;
- backup/manifest and restore-verification tooling;
- migration-baseline generation helper/procedure;
- `docs/DEMO_ACCEPTANCE_2026-08-26.md`;
- development-only `scripts/prepare_demo_showcase.py`;
- `scripts/release_scope_guard.py`;
- `scripts/release_operations_smoke.py`;
- `scripts/release_candidate_check.sh`.

The local RC script remains a delivery/staging verifier, not production readiness evidence.

---

## 13. Production database migration status

STATUS: **PROCESS + GENERATION HELPER IMPLEMENTED / PRODUCTION BASELINE NOT YET EXECUTED AND VERIFIED**.

`docs/PRODUCTION_DATABASE_MIGRATIONS.md` defines the gate.
`scripts/generate_migration_baseline.sh` can generate an initial Prisma migration from the current canonical schema and append reviewed active-core PostgreSQL constraints.

Still required before production:
- generate baseline in a controlled workspace;
- review SQL;
- apply it to clean staging DB;
- verify schema/constraints;
- establish `_prisma_migrations` history correctly;
- perform the required production-like backup/restore rehearsal.

Do not use `prisma db push` as the permanent production migration strategy.

Dormant NFC schema artifacts must not drive active V1 feature scope.

---

## 14. Production gates still open

**Development CI verification is satisfied for the current executable baseline. Production readiness is not.**

Do not claim production-ready until the remaining gates are completed:
1. generated/reviewed/applied Prisma migration baseline/history rather than permanent `db push`;
2. production-like current-schema backup -> clean restore proof for the intended deployment procedure;
3. complete/final approved public media pack, category-photo mapping and visual acceptance;
4. staging acceptance;
5. production secrets/HTTPS/hostnames;
6. monitoring/alerts;
7. rollback rehearsal;
8. explicit DNS/cutover owner gate;
9. exact production deployment/source correspondence to the intended canonical main;
10. if Google Sheets CRM is part of go-live scope: OAuth credential binding, workflow publication and live sync acceptance.

Automated payment-provider integration is **not** a Three Crowns V1 gate under the current manager-manual prepayment workflow.

---

## 15. CI / verification evidence

The former GitHub Actions execution blocker (`steps=null` before workflow execution) is **RESOLVED as a current blocker**. It remains historical evidence only.

CI recovery evidence:
- recovery PR #1 exact head `ba9f362e664f631f5369be7ee24e7239fd0e1243` passed 13/13 triggered workflows;
- merge commit `46843ce9d8ddd71b0a3dbb39917f1cbd150966e5` then produced 13/13 completed push workflows on `main`, with no failure/cancellation in the verified matrix;
- this recovery added focused Data Intake Integrity coverage and aligned active NFC scope with the owner freeze.

Payment-integrity evidence:
- finance PR #2 exact head `a0993354b1c002848ac926961fa322baaac28350` passed 14/14 triggered workflows;
- merge commit `9420d48209c8e869a055b2e552e2491c1f19bd63` produced 14/14 completed push workflows on `main`;
- `failure=0`, `cancelled=0` for that exact post-merge SHA;
- `Payment Idempotency CI` passed schema, normalization, real API/PostgreSQL contract tests and concurrent collision tests.

Security-maintenance evidence:
- PR #9 exact head `a7b6bf9db44bf4990bd3d91313b7da40750e0701` upgraded Admin/Public Web/Staff to Next.js 15.5.24 and React/React DOM 19.2.8 while updating the trusted manifest fingerprints rather than weakening verification;
- canonical security baseline commit is `97f69cb5c091b49650bfa4b80beb095def75886b`;
- GitHub Actions reported 7 push-triggered workflow runs for that exact post-merge SHA, all completed successfully, with no failure or cancelled conclusion found.

Public/CRM/demo/analytics baseline lineage after that security baseline includes:
- `e165c9fdeba76f71cef75880ee51f840966ea2c1` — verified Three Crowns 2026 brand/rate/local-media integration;
- `ff688bcdfb46aeb6e659d3c4ad28392c32b01d5c` — rendered primary backgrounds forced to local media; post-merge Resort Core CI #413 and Contract CI #22 succeeded;
- `33c384964e2936533ecdaa3380130dd085ef3abd` — full 2026 public price presentation baseline;
- `fd2946cc1fd3e46331e9c5a56a5a674ddb673e09` — protected read-only Resort Core CRM mirror feed and admin CSV fallback;
- `fe1278fba5ea129b96bc8974d8613c76946b4bce` — inactive importable n8n Google Sheets CRM sync workflow plus JSON/safety CI;
- `7c5cb5e166bac98841467b22515d04c34ac9b570` — canonical public 12-category room catalog and category pages;
- `7f193e9476ba6aa8f13e4e35b8d58a7916543b43` — canonical public homepage rebuilt with unverified CURRENT service claims removed;
- `3023226c025a2f57cc801298e22b892c0862d8c6` — fail-closed public-site truth guard and dedicated CI;
- `402eb4bf0f18df223e7b428ca9e85ba6abac81b4` — docs-only Current State v1.5 synchronization; no executable change was inferred from this docs merge;
- `461fc1ea3ed0d3087eb5fd66bccc15ad3872c7b5` — isolated Admin `/demo` presentation route merge, with post-merge Resort Core CI #432 succeeding;
- current executable main `f68e2ff6428929f4e069d650ff2b8d30a6224599` — privacy-safe public funnel analytics plus strengthened fail-closed privacy/public-truth guard.

Exact current-main Actions evidence:
- query for `head_sha=f68e2ff6428929f4e069d650ff2b8d30a6224599` returned 14 push-triggered runs;
- query for the same exact SHA filtered to `status=success` also returned 14 runs;
- therefore exact post-merge result is **14/14 SUCCESS**;
- `Public Site Truth CI` run #6 completed with `success` on that exact SHA;
- the matrix includes full Resort Core build/lifecycle verification and the Control Center monorepo fail-closed contract.

Active baseline matrix retained from the core implementation includes:
1. Resort Core CI;
2. Hotel Operations CI;
3. PMS Chessboard Mutation CI;
4. Payment Idempotency CI;
5. Automation Contract CI;
6. n8n Resort Core Contract CI;
7. Unified Inbox CI;
8. AI Sales Draft CI;
9. Telegram Sales CI;
10. Staff Voice CI;
11. Realtime PMS CI;
12. PostgreSQL Backup Restore CI;
13. NFC Deferred Scope CI;
14. Data Intake Integrity CI.

Additional focused guards now include:
- Public Site Truth CI, including public analytics privacy allowlist enforcement;
- n8n Workflow JSON/safety CI for committed workflow artifacts.

Interpretation boundary:

**Development CI success proves the exercised development contracts on the exact cited code baselines. It does not prove staging acceptance, production secrets, production migration execution, live Google Sheets synchronization, a live external analytics vendor, monitoring, rollback, exact Vercel source correspondence or DNS cutover.**

---

## 16. Immediate delivery order

Remaining work should now proceed from verified current state, not from historical bootstrap assumptions:

1. production migration baseline generation/review -> clean staging apply/verification;
2. production-like backup/restore rehearsal using the intended migration/deploy procedure;
3. staging acceptance of public site + PMS + Staff + Core + n8n handoff contracts;
4. complete/finalize category-specific public media pack and visual acceptance;
5. verify intended production deployment is built from the intended canonical GitHub baseline;
6. if CRM Sheets is required for launch, bind Google OAuth, publish the inactive workflow and prove live mirror sync without write-back authority;
7. production secrets/HTTPS/hostnames and operational monitoring;
8. rollback rehearsal;
9. explicit owner DNS/cutover gate.

Do not spend active delivery time on deferred NFC, automated acquiring, direct provider-specific CRM write-back logic, or unspecified dining/store/access/QR/billiards/LED business rules unless canonical decision authority changes their scope.

Development rule:

`KNOWLEDGE -> CURRENT STATE -> GAP -> PRIORITY -> IMPLEMENT -> TEST -> EVIDENCE -> VERIFIED / NOT VERIFIED -> CURRENT STATE UPDATE`