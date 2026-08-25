# RESORT OS — CURRENT STATE

Version: 1.1
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

NFC is **DEFERRED / DORMANT** and excluded from the active V1 engineering queue.

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

Daily quick views:
- all rooms;
- arrivals today;
- departures today;
- in-house;
- free today.

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
- housekeeping is created/reused.

Housekeeping baseline:
`OPEN -> IN_PROGRESS -> IN_INSPECTION -> DONE`, with room moving back to CLEAN after management acceptance.

Maintenance baseline supports TECH_BLOCK, assignment and history.

---

## 6. PMS/admin areas

Current manager navigation:
- **Главная** — Command Center;
- **Шахматка** — primary daily operating surface;
- **Заявки** — ReservationRequest manager handoff;
- **Брони** — reception / stays;
- **Финансы** — internal manager-recorded payment visibility;
- **Операции** — housekeeping / maintenance / task control;
- **Персонал** — roles, task load, Telegram/session operational facts;
- **Аудит сообщений** — optional communication/audit workspace; n8n remains the client orchestrator.

Recent UX hardening:
- laptop/tablet-safe horizontally scrollable admin navigation;
- room detail and task history;
- manager assignment/reassignment;
- chessboard booking quick facts and payment form.

PMS is not a mock.

---

## 7. Internal hotel finance

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

## 8. Staff / operations

STATUS: **IMPLEMENTED BASELINE; RECENT EXTENSIONS NOT CI-VERIFIED**.

Implemented:
- OWNER / MANAGER / MAID / TECHNICIAN access boundaries;
- staff PWA;
- task claim/assignment/reassignment;
- housekeeping and maintenance status transitions;
- task action history;
- Telegram Mini App staff identity/linking;
- conservative voice-maintenance adapter code.

Voice safety:
- linked active staff only;
- exact single real-room match can create a room-linked task;
- ambiguous/no room match becomes review task without blocking a guessed room;
- short room numbers require explicit room context;
- automatic urgency remains NORMAL until exact severity rules are approved.

Photo/checklist evidence remains future work because exact mandatory checklist rules have not been approved.

---

## 9. n8n automation boundary

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

## 10. Public sales site

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

---

## 11. Deployment / release candidate

STATUS: **DELIVERY TOOLING IMPLEMENTED / PRODUCTION GATES OPEN**.

Implemented:
- API/admin/web/staff Dockerfiles;
- production compose;
- canonical `/health/live` and `/health/ready` probes plus legacy aliases;
- environment templates aligned with manager-owned prepayment;
- privacy-safe request-id logging;
- production preflight;
- backup/manifest and restore-verification tooling;
- migration-baseline procedure documentation;
- updated README;
- `docs/DEMO_ACCEPTANCE_2026-08-26.md`;
- development-only `scripts/prepare_demo_showcase.py`;
- `scripts/release_candidate_check.sh`.

Local RC check verifies:
- PostgreSQL availability;
- Prisma validate + development schema;
- Python compile;
- critical PostgreSQL constraints + 84/12 seed;
- admin/web/staff typecheck and production build;
- Core health/readiness 84/12;
- unauthenticated PMS rejection;
- OWNER authentication;
- 84 unique PMS rooms;
- availability contract;
- ReservationRequest remains not-a-reservation;
- quote calculates stay value with no automatic prepayment amount;
- manager-confirmed payment creates GUARANTEED Reservation and schedule;
- additional internal payment idempotency does not double-count.

This local script is a delivery/staging verifier, **not production readiness evidence**.

---

## 12. Production gates still open

Do not claim production-ready until these are completed:
1. real Prisma migration baseline/history rather than permanent `db push`;
2. current-schema backup -> clean restore proof;
3. accepted current-main execution evidence;
4. owned public-site photography;
5. staging acceptance;
6. production secrets/HTTPS/hostnames;
7. monitoring/alerts;
8. rollback rehearsal;
9. explicit DNS/cutover owner gate.

Automated payment-provider integration is **not** a V1 gate under the current manager-manual prepayment workflow.

---

## 13. CI / verification state

Last explicitly confirmed full green historical baseline:

`7038818db41756b94e8d5235410404b9b6172c1e`

Historical successful workflows included Resort Core, Automation Contract and Realtime PMS. Historical NFC success is irrelevant to active V1 because NFC is deferred.

Current GitHub Actions symptom is now more precisely observed:
- workflow runs are created on latest commits;
- jobs terminate in seconds as failure;
- job payloads contain `steps=null`;
- downloadable job logs are unavailable (`BlobNotFound` observed);
- therefore no workflow test step actually provides failure evidence.

Latest changes remain **IMPLEMENTED / NOT CI-VERIFIED** until local/staging or restored Actions execution evidence is captured.

---

## 14. Immediate delivery order

1. Run `scripts/release_candidate_check.sh` and preserve output.
2. Optionally create clearly marked development demo reservations with `RC_SEED_DEMO=1`.
3. Execute `docs/DEMO_ACCEPTANCE_2026-08-26.md` end-to-end.
4. Fix any locally reproduced build/runtime errors first.
5. Replace site media when owned photography is available.
6. For production: migration baseline -> backup/restore proof -> staging -> monitoring/rollback -> cutover gate.

Do not spend delivery time on NFC, direct Instagram/WhatsApp provider code, automated acquiring, or unspecified dining/store/access/QR/billiards/LED business rules.

Development rule:

`KNOWLEDGE -> CURRENT STATE -> GAP -> PRIORITY -> IMPLEMENT -> TEST -> EVIDENCE -> VERIFIED / NOT VERIFIED -> CURRENT STATE UPDATE`
