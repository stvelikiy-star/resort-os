# RESORT OS — CURRENT STATE

Version: 1.2
Date: 2026-08-26
Status: DELIVERY RELEASE CANDIDATE / LATEST MAIN NOT CI-VERIFIED
Canonical: YES
Document Type: Evidence-Based Current System State

Critical rule: **TARGET != CURRENT. IMPLEMENTED != VERIFIED. DEVELOPMENT VERIFIED != PRODUCTION READY.**

---

## 1. Canonical architecture

Repository: `stvelikiy-star/resort-os`.

Current owner-approved V1 architecture:

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Canonical runtime entrypoint: `app.app_entry:app`.
Current composed app version: `0.29.0`.

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
- AuditLog.

Client channels are orchestrated outside Resort Core:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- website -> Resort Core directly.

n8n objective = **HOT QUALIFIED LEAD**. It must not write PostgreSQL, confirm payment, create guaranteed Reservation directly, check-in/out/refund or invent price/availability/policy.

### NFC owner freeze

NFC is **DEFERRED / DORMANT** and excluded from active V1 runtime/work.

Current enforcement:
- NFC source/schema artifacts may remain as historical/dormant implementation;
- `app.app_entry:app` does **not** compose NFC/beach payment routers;
- normal hotel checkout no longer queries or mutates NFC tables;
- active Staff PWA no longer imports/renders the beach terminal branch;
- `scripts/release_scope_guard.py` fails if NFC/beach routes are accidentally composed again.

Do not reactivate NFC without an explicit owner instruction.

---

## 2. Prepayment / finance truth

Owner-approved V1 rule:
- manager decides prepayment amount, terms and payment method;
- manager collects prepayment manually;
- no global `PREPAYMENT_PERCENT` exists in the active contract;
- automation does not generate/collect/approve prepayment;
- Resort OS records manager-confirmed internal payment facts only;
- `ReservationRequest != Reservation`;
- unpaid request does not hold inventory;
- automation cannot say a room is booked until manager-confirmed Reservation truth exists.

Current booking flow:

`ReservationRequest -> manager quote of stay value -> manager records accepted payment fact -> atomic Guest + Reservation + InventoryBlock + Payment`.

Booking conversion and additional reservation payments have idempotency protection. A global idempotency key cannot be replayed against another request/reservation; such misuse returns `409 IDEMPOTENCY_CONFLICT`.

Internal finance is operational control, **not accounting profit/tax/revenue recognition**.

---

## 3. PMS Chessboard V2 — primary product surface

STATUS: **IMPLEMENTED / NOT CI-VERIFIED ON LATEST MAIN**.

Server-authoritative mutation contract:
- `GET /api/v1/admin/pms/reservations/{id}/schedule`;
- `POST /api/v1/admin/pms/reservations/{id}/schedule/preview`;
- `POST /api/v1/admin/pms/reservations/{id}/schedule/commit`.

Implemented capabilities:
- one spanning reservation bar per room/date segment;
- move a future simple reservation to another room;
- drag future simple reservation to another room and start date while preserving duration;
- direct outer-edge pointer resize for check-in/check-out dates;
- explicit date editor for touch/tablet;
- split one Reservation into contiguous room-assignment segments;
- relocate CHECKED_IN guest from an effective date without rewriting already-lived history;
- server pricing preview/delta without silently modifying stored commercial total;
- explicit manager confirmation before commit;
- stale-version protection;
- conflict preview and race rollback;
- PostgreSQL exclusion constraint as final double-booking guard;
- TECH_BLOCK rejection;
- immediate relocation requires CLEAN target room;
- immediate relocation marks old room DIRTY and creates/reuses housekeeping inside the same transaction;
- AuditLog before/after evidence;
- realtime PMS snapshots.

Concurrency hardening:
- Reservation is locked before mutation;
- active reservation InventoryBlocks are locked separately;
- room rows are then locked in deterministic sorted order;
- joined room rows are not accidentally locked earlier by the schedule query;
- this reduces deadlock risk when two managers mutate schedules concurrently.

Daily quick views:
- all rooms;
- arrivals today;
- departures today;
- in-house;
- free today.

Recent UI hardening:
- guaranteed/future Reservation bars are blue;
- checked-in/current stay bars are green;
- maintenance and manual blocks have distinct legend colors;
- bar subtitle includes booking number + human stay state;
- booking workspace uses human status labels rather than raw enums;
- checked-in workspace explains that check-in date/already-lived nights are immutable;
- check-in/check-out actions require explicit manager confirmation.

Intermediate relocation segment boundaries are not treated as hotel arrival/departure boundaries.

---

## 4. Reception / reservation workspace

STATUS: **IMPLEMENTED / NOT CI-VERIFIED ON LATEST MAIN**.

Schedule-aware behavior:
- one row per Reservation even when stay uses several rooms;
- current/working room is resolved from complete schedule and hotel-local date/status;
- booking detail returns the complete room route;
- room tasks are collected across every room used by the stay;
- guest/contact, notes and source request are visible;
- internal payments, paid amount and outstanding balance are visible;
- recent AuditLog events are visible.

Reception list now shows without opening the card:
- human stay status;
- guest and room;
- dates;
- manager-recorded paid / total amount;
- remaining balance or `Оплачено полностью`.

Check-in/out failures are translated to operator-facing messages for room readiness/date schedule conflicts. Both actions require confirmation in UI.

Chessboard booking modal embeds quick facts and manager actions so reception can work without jumping between many tabs.

Additional internal payment endpoint:
- `POST /api/v1/admin/booking/reservations/{id}/payments`;
- manager-entered positive amount/method/reference/note;
- provider stored as `MANAGER_MANUAL`;
- same-reservation retries are idempotent;
- same idempotency key used by another Reservation returns `409 IDEMPOTENCY_CONFLICT`;
- payment fact is audited.

---

## 5. Stay / room-condition safety

STATUS: **IMPLEMENTED / NOT CI-VERIFIED ON LATEST MAIN**.

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

## 6. Housekeeping / maintenance transition safety

STATUS: **IMPLEMENTED / NOT CI-VERIFIED ON LATEST MAIN**.

Core now enforces a transition matrix rather than accepting arbitrary task-state jumps.

HOUSEKEEPING:
- `OPEN -> IN_PROGRESS`;
- `IN_PROGRESS -> IN_INSPECTION`;
- manager acceptance: `IN_INSPECTION -> DONE`;
- manager rejection/rework: `IN_INSPECTION -> IN_PROGRESS`;
- manager may cancel active work;
- DONE/CANCELLED are terminal.

Room-condition path with rework:

`DIRTY -> IN_INSPECTION -> DIRTY -> IN_INSPECTION -> CLEAN`.

Safety rules:
- skipped transitions return `409 INVALID_TASK_TRANSITION`;
- line staff must claim/own tasks before changing status;
- only OWNER/MANAGER decides housekeeping inspection acceptance/rework;
- housekeeping going to inspection does not overwrite `TECH_BLOCK`;
- housekeeping DONE is allowed only when physical room state is `IN_INSPECTION`;
- a TECH_BLOCK room therefore cannot be silently turned CLEAN by a housekeeping task;
- maintenance DONE changes room to DIRTY for subsequent housekeeping;
- AuditLog status changes include previous/new states.

Admin Operations UI includes:
- assignment/reassignment;
- `Принять номер → готов`;
- `Вернуть на доработку`;
- active-task cancellation;
- action history.

Staff PWA active roles:
- OWNER;
- MANAGER;
- MAID;
- TECHNICIAN.

MAID flow: unassigned/own housekeeping -> claim -> IN_PROGRESS -> IN_INSPECTION.
TECHNICIAN flow: maintenance -> claim -> IN_PROGRESS -> DONE.

BEACH_PARTNER terminal flow is not active in current Staff PWA.

Photo/checklist evidence remains future work because exact mandatory checklist rules have not been approved.

---

## 7. PMS/admin areas

Current manager navigation:
- **Главная** — Command Center;
- **Шахматка** — primary daily operating surface;
- **Заявки** — ReservationRequest manager handoff;
- **Брони** — reception / stays;
- **Финансы** — internal manager-recorded payment visibility;
- **Операции** — housekeeping / maintenance / task control;
- **Персонал** — roles, task load, Telegram/session operational facts;
- **Аудит сообщений** — optional communication/audit workspace; n8n remains the client orchestrator.

Command Center drill-down navigates into the corresponding operational areas rather than acting only as a passive report.

Recent UX hardening:
- laptop/tablet-safe horizontally scrollable admin navigation;
- room detail and task history;
- manager assignment/reassignment;
- chessboard booking quick facts and payment form;
- reservation paid/outstanding visibility directly in reception list.

PMS is not a mock.

---

## 8. Internal hotel finance

STATUS: **API + PMS UI IMPLEMENTED / NOT CI-VERIFIED ON LATEST MAIN**.

Finance UI derives only from stored manager-confirmed facts:
- received amount/count for a selected period;
- active Reservation booked total / received / outstanding;
- received amounts by recorded method;
- received amounts by day;
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

STATUS: **IMPLEMENTED BASELINE; RECENT EXTENSIONS NOT CI-VERIFIED**.

Implemented:
- staff PWA for active hotel roles;
- task claim/assignment/reassignment;
- strict housekeeping/maintenance status transitions;
- task action history;
- Telegram Mini App staff identity/linking;
- conservative voice-maintenance adapter code.

Voice safety:
- linked active staff only;
- exact single real-room match can create a room-linked task;
- ambiguous/no room match becomes review task without blocking a guessed room;
- short room numbers require explicit room context;
- automatic urgency remains NORMAL until exact severity rules are approved.

---

## 10. n8n automation boundary

STATUS: **IMPLEMENTED CORE CONTRACT / LATEST CHANGES NOT CI-VERIFIED**.

Protected by `X-Resort-Service-Key`.

Approved n8n/Core capabilities include:
- hotel facts;
- deterministic availability/pricing;
- create/read ReservationRequest;
- request/reservation/payment status facts that exist in Core;
- structured staff intake where applicable.

Canonical n8n documentation: `automation/n8n/README.md`.

Direct Telegram/provider adapters retained in Core are optional/reference code, not an active V1 dependency.

---

## 11. Public sales site

STATUS: **IMPLEMENTED DELIVERY BASELINE / OWNED MEDIA STILL REQUIRED FOR PRODUCTION VISUAL ACCEPTANCE**.

Current `apps/web` includes:
- premium guest-facing hero/sections;
- 12 category structure;
- confirmed resort facts: own beach, 150 m pier, SPA/massage, outdoor pool 15×8, Cholpon-Ata;
- confirmed contacts;
- live Core availability/pricing;
- tariff-derived meal information;
- sellable-first/price-sorted availability results;
- mobile-friendly date/guest search;
- selected-room request flow;
- real ReservationRequest creation;
- explicit request-not-yet-booking wording;
- manager confirmation/prepayment boundary;
- metadata/OpenGraph/JSON-LD/sitemap/robots;
- sticky mobile booking CTA.

Recent public-copy audit removed unconfirmed sauna/conference/restaurant claims and internal development wording.

Remaining visual blocker:
- replace temporary/hotlinked media with owned Three Crowns photography before production cutover.

Website and PMS read the same InventoryBlock truth; no separate availability synchronization job is required.

Existing Vercel project `three-crowns-resort-preview` was inspected and is a legacy static mock with fake availability text; it must not be presented as the current canonical Resort OS.

---

## 12. Deployment / release candidate

STATUS: **DELIVERY TOOLING IMPLEMENTED / PRODUCTION GATES OPEN**.

Implemented:
- API/admin/web/staff Dockerfiles;
- production compose;
- canonical `/health/live` and `/health/ready` probes plus legacy aliases;
- environment templates aligned with manager-owned prepayment;
- privacy-safe request-id logging;
- production preflight;
- backup/manifest and restore-verification tooling;
- migration-baseline generation helper/procedure;
- updated README;
- `docs/DEMO_ACCEPTANCE_2026-08-26.md`;
- development-only `scripts/prepare_demo_showcase.py`;
- `scripts/release_scope_guard.py`;
- `scripts/release_operations_smoke.py`;
- `scripts/release_candidate_check.sh`.

Current local RC check has 13 areas:
1. PostgreSQL availability;
2. Prisma validation/development schema;
3. Python compile + active route/scope guard;
4. critical PostgreSQL constraints + 84/12 seed + synthetic RC maid;
5. admin typecheck/build;
6. web typecheck/build;
7. Staff PWA typecheck/build;
8. Core health/readiness 84/12;
9. auth + protected PMS + 84 unique rooms;
10. availability + ReservationRequest not-a-reservation truth;
11. manager quote/payment -> GUARANTEED Reservation -> chessboard schedule;
12. existing-reservation payment idempotency;
13. housekeeping inspection/rework lifecycle smoke.

The operations smoke proves:

`DIRTY -> IN_PROGRESS -> IN_INSPECTION -> DIRTY -> IN_INSPECTION -> CLEAN`.

`RC_SEED_DEMO=1` can prepare synthetic presentation records after the release checks.

This local script is a delivery/staging verifier, **not production readiness evidence**.

---

## 13. Production database migration status

STATUS: **PROCESS + GENERATION HELPER IMPLEMENTED / BASELINE NOT YET EXECUTED AND VERIFIED**.

`docs/PRODUCTION_DATABASE_MIGRATIONS.md` defines the gate.
`scripts/generate_migration_baseline.sh` can generate an initial Prisma migration from the current canonical schema and append reviewed active core PostgreSQL constraints.

Still required before production:
- generate baseline in a controlled workspace;
- review SQL;
- apply to clean staging DB;
- verify schema/constraints;
- establish `_prisma_migrations` history correctly;
- backup -> restore rehearsal.

Do not use `prisma db push` as permanent production migration strategy.

Dormant NFC schema artifacts must not drive active V1 feature scope.

---

## 14. Production gates still open

Do not claim production-ready until these are completed:
1. generated/reviewed/applied Prisma migration baseline/history rather than permanent `db push`;
2. current-schema backup -> clean restore proof;
3. accepted current-main executed build/E2E evidence;
4. owned public-site photography;
5. staging acceptance;
6. production secrets/HTTPS/hostnames;
7. monitoring/alerts;
8. rollback rehearsal;
9. explicit DNS/cutover owner gate.

Automated payment-provider integration is **not** a V1 gate under the current manager-manual prepayment workflow.

---

## 15. CI / verification state

Last explicitly confirmed full green historical baseline:

`7038818db41756b94e8d5235410404b9b6172c1e`

Historical successful workflows included Resort Core, Automation Contract and Realtime PMS. Historical NFC success is irrelevant to active V1 because NFC is deferred.

Current GitHub Actions symptom remains explicitly confirmed on current work. Example:
- Hotel Operations CI run `32923329835`;
- head commit `648e7d75946486d831c6d15e16ef7e8e001db508`;
- job id `98041117598`;
- conclusion `failure`;
- `steps=null`;
- no job log URL/content.

Therefore that run did **not execute the workflow steps** and is not evidence that the code/tests failed.

Latest changes remain **IMPLEMENTED / NOT CI-VERIFIED** until `scripts/release_candidate_check.sh`, staging, or restored Actions execution evidence is captured.

---

## 16. Immediate delivery order

1. Run `bash scripts/release_candidate_check.sh` and preserve `/tmp/three-crowns-rc` output.
2. Fix only locally reproduced build/runtime failures.
3. Optionally create clearly marked development demo reservations with `RC_SEED_DEMO=1`.
4. Execute `docs/DEMO_ACCEPTANCE_2026-08-26.md` end-to-end.
5. Replace site media when owned photography is available.
6. For production: migration baseline -> backup/restore proof -> staging -> monitoring/rollback -> cutover gate.

Do not spend delivery time on NFC, direct Instagram/WhatsApp provider code, automated acquiring, or unspecified dining/store/access/QR/billiards/LED business rules.

Development rule:

`KNOWLEDGE -> CURRENT STATE -> GAP -> PRIORITY -> IMPLEMENT -> TEST -> EVIDENCE -> VERIFIED / NOT VERIFIED -> CURRENT STATE UPDATE`
