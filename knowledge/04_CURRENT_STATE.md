# RESORT OS — CURRENT STATE

Version: 0.9
Date: 2026-08-25
Status: ACTIVE DEVELOPMENT / CURRENT MAIN PARTIALLY NOT CI-VERIFIED
Canonical: YES
Document Type: Evidence-Based Current System State

Critical rule: **TARGET != CURRENT. IMPLEMENTED != VERIFIED. DEVELOPMENT VERIFIED != PRODUCTION READY.**

---

# 1. CANONICAL REPOSITORY

STATUS: VERIFIED FACT

Repository: `stvelikiy-star/resort-os`

Canonical implementation contains:
- PostgreSQL + Prisma hotel domain;
- FastAPI Resort Core;
- Three Crowns room/rate development seed baseline;
- Next.js PMS/admin;
- Next.js public booking site;
- Next.js staff PWA;
- authentication/RBAC;
- reservation/internal payment management;
- stay lifecycle;
- housekeeping/maintenance operations;
- realtime PMS WebSocket;
- guarded n8n/service API;
- owner/manager Command Center;
- internal hotel finance reporting;
- deployment/production scaffolding;
- dormant NFC code retained as deferred evidence only.

No production DNS cutover, automated acquiring activation or irreversible production migration is recorded.

---

# 2. ACTIVE OWNER PRODUCT PRIORITY

STATUS: ACTIVE / CANONICAL

Canonical execution plan: `knowledge/07_EXECUTION_PLAN_THREE_CROWNS.md`.

Current product priority is explicit:

1. **PMS chessboard is the primary daily operating surface.**
2. **Admin/PMS must be highly usable and multifunctional.**
3. **Public website must be a polished sales site using the same live Resort Core truth.**
4. **n8n owns client conversation automation and hands hot qualified clients to management.**

Website, PMS and n8n must not keep separate copies of price, availability or booking truth.

NFC is DEFERRED and excluded from the active engineering queue.

Unknown business rules remain UNKNOWN / DECISION REQUIRED rather than being invented.

---

# 3. PROPERTY DATA

STATUS: VERIFIED AS SEEDABLE DEVELOPMENT BASELINE

Current reconciled development baseline:
- 84 room positions;
- 12 room categories;
- 2026/27 rate input.

Evidence:
- `data-intake/rooms.csv`;
- `data-intake/rates.csv`;
- `docs/THREE_CROWNS_SOURCE_RECONCILIATION_2026-08-25.md`.

---

# 4. DATABASE / CORE SAFETY

STATUS: IMPLEMENTED; MAJOR BASELINE VERIFIED BEFORE CURRENT ACTIONS BLOCKER

Core domain includes Property, RoomType, Room, RatePlan/RatePeriod, Guest, ReservationRequest, Reservation, InventoryBlock, Payment, staff/auth, OperationalTask, automation events and AuditLog.

Critical invariants include:
- `ReservationRequest != Reservation`;
- unpaid ReservationRequest does not hold inventory;
- valid date ranges;
- nonnegative reservation totals;
- positive manager-recorded payments;
- no overlapping active blocks for one room;
- automation/payment idempotency boundaries;
- physical room condition is separate from commercial reservation/stay state.

PostgreSQL exclusion constraint `no_overlapping_active_room_blocks` remains the final double-booking guard.

---

# 5. CLIENT SALES / PREPAYMENT BOUNDARY

STATUS: OWNER DECISION IMPLEMENTED IN ACTIVE PLAN AND CURRENT BOOKING FLOW

Client architecture:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- Telegram/other channels may use n8n where useful;
- public website -> Resort Core directly.

Automation objective = **HOT QUALIFIED LEAD**.

n8n/AI may:
- collect dates, guest count and contact details;
- read approved hotel facts;
- call deterministic availability/pricing;
- create/read ReservationRequest;
- hand the qualified request to management.

Manager boundary:
- **manager decides prepayment amount/terms/method manually**;
- manager collects prepayment manually;
- Resort OS records internal manager-confirmed payment/reservation facts;
- n8n does not generate payment links/QR, collect money or decide whether prepayment is sufficient;
- without manager-confirmed reservation fact, automation must not tell the guest that a room is booked.

Current booking-admin correction:
- quote calculates stay value only;
- no fixed 30% rule is applied by Core;
- quote stores `requiredPrepaymentKgs = NULL` until management acts;
- manager-confirmed positive payment amount can be recorded through the controlled PMS conversion flow;
- resulting Reservation + InventoryBlock + Payment creation remains atomic/idempotent.

Automated acquiring/payment-provider integration is not required for current V1.

---

# 6. PMS CHESSBOARD V2 — PRIMARY P0

STATUS: TRANSACTIONAL BACKEND + FIRST V2 INTERACTION UI IMPLEMENTED / NOT CI-VERIFIED

Detailed contract: `docs/PMS_CHESSBOARD_MUTATION_CONTRACT.md`.

## Server mutation engine

Implemented protected endpoints:
- `GET /api/v1/admin/pms/reservations/{reservation_id}/schedule`;
- `POST /api/v1/admin/pms/reservations/{reservation_id}/schedule/preview`;
- `POST /api/v1/admin/pms/reservations/{reservation_id}/schedule/commit`.

One Reservation may own multiple contiguous active Reservation InventoryBlock segments. This supports room relocation without creating a fake second booking.

Implemented mutation capabilities:
- move a future reservation to another room for the same dates;
- change/cut/extend future reservation dates;
- split a stay into contiguous room segments;
- relocate a CHECKED_IN guest from an effective date;
- preserve already-lived room assignment history;
- deterministic pricing preview/delta without silently changing stored reservation value;
- optimistic concurrency with reservation version token;
- conflict preview before commit;
- transactional conflict rollback;
- AuditLog before/after evidence.

Safety behavior:
- Reservation is locked before commit;
- active reservation blocks are locked;
- current/proposed rooms are locked;
- room overlap is rechecked inside the transaction;
- PostgreSQL exclusion constraint remains final race guard;
- stale manager screen returns `409 STALE_RESERVATION`;
- TECH_BLOCK target is rejected;
- CHECKED_IN past room nights cannot be rewritten;
- if checked-in guest is relocated **today**, target room must be CLEAN;
- successful immediate relocation marks the vacated room DIRTY and creates/reuses a housekeeping task inside the same transaction;
- failure leaves original schedule unchanged.

## Chessboard V2 UI

Active admin chessboard now uses `PMSGridV2`.

Implemented UI direction:
- one reservation segment is rendered as one spanning bar across its date range rather than duplicated cell-by-cell;
- split/relocated stay renders as multiple room/date bars;
- click room -> room detail;
- click reservation -> stay-management modal;
- future GUARANTEED reservation can be dragged onto another room row;
- drop opens server-backed move preview rather than committing silently;
- left/right edge controls open date-cut/resize workflow;
- explicit modes: `Перенести бронь`, `Изменить даты`, `Переселить с даты`;
- preview shows target schedule, conflicts, stored total, suggested Core tariff and delta;
- explicit confirmation is required before commit;
- GUARANTEED -> check-in and CHECKED_IN -> check-out actions are available from the reservation workspace;
- touch/tablet remains usable through explicit controls without requiring precision drag gestures.

True direct pointer-drag resizing of the bar edge is still a follow-up UX enhancement; the safe date-resize workflow already exists through edge controls/modal.

---

# 7. RECEPTION / RESERVATION DETAIL

STATUS: SCHEDULE-AWARE EXTENSION IMPLEMENTED / NOT CI-VERIFIED

A new reception list returns exactly one row per Reservation even when the stay has several room segments.

Displayed room is selected by reservation state and hotel-local date:
- GUARANTEED -> first/check-in room;
- CHECKED_IN -> current room segment;
- CHECKED_OUT -> final room segment.

Reception card/detail now supports:
- guest/contact;
- dates and status;
- current/working room;
- complete room-move schedule;
- manager-recorded internal payment facts and balance;
- tasks across all rooms used by the stay;
- audit history;
- check-in/check-out.

Stay lifecycle was made room-schedule aware so check-out selects the actually occupied/final room segment rather than blindly using the first block after a relocation.

---

# 8. OTHER PMS / ADMIN AREAS

STATUS: IMPLEMENTED DEVELOPMENT CONTROL CENTER / RECENT EXTENSIONS NOT CI-VERIFIED

Current areas:
- **Главная / Command Center** — room, arrival/departure, request, task and internal payment visibility;
- **Шахматка V2** — primary operating surface;
- **Заявки** — hot-lead/ReservationRequest manager handoff and manual prepayment confirmation;
- **Брони / Ресепшен** — one-row-per-reservation schedule-aware workspace;
- **Операции** — housekeeping/maintenance/guest request tasks, assignment and history;
- **Персонал** — staff/task/Telegram/session visibility;
- **Карточка номера** — stored metadata, reservation/block/task history;
- **Аудит сообщений** — optional provider-neutral communication history; n8n remains client orchestrator.

PMS is not a mock.

---

# 9. STAFF / HOUSEKEEPING / MAINTENANCE

STATUS: IMPLEMENTED BASELINE / RECENT CONTROL EXTENSIONS NOT CI-VERIFIED

Implemented:
- checkout -> actual vacated room DIRTY;
- checkout -> housekeeping task;
- immediate in-stay relocation -> vacated room DIRTY + housekeeping in same transaction;
- housekeeping -> IN_INSPECTION -> manager acceptance -> CLEAN;
- maintenance -> TECH_BLOCK where appropriate;
- task claim/assignment/reassignment/status transitions;
- task action history;
- owner/manager staff-control view;
- staff PWA;
- Telegram identity/linking;
- conservative voice-maintenance intake.

Photo/checklist evidence remains a future enhancement; exact checklists must not be invented.

---

# 10. N8N / AUTOMATION CONTRACT

STATUS: ACTIVE ARCHITECTURE / CORE BOUNDARY IMPLEMENTED / RECENT READ LAYER NOT CI-VERIFIED

Protected service boundary uses `X-Resort-Service-Key`.

Stable truth/actions include:
- `GET /api/v1/automation/read/hotel-facts`;
- `GET /api/v1/booking/check-availability`;
- `POST /api/v1/automation/reservation-requests`;
- request/reservation status reads;
- structured staff intake where applicable.

n8n must never write PostgreSQL directly or mutate booking/payment/stay truth outside approved Core routes.

Canonical n8n boundary: `automation/n8n/README.md`.

---

# 11. PUBLIC SALES SITE

STATUS: IMPLEMENTED DEVELOPMENT BASELINE / VISUAL PRODUCTION WORK REMAINS

Canonical source: `apps/web/`.

Implemented:
- real Core availability;
- real Core pricing;
- 12 real category presentation structure;
- guest contact capture;
- ReservationRequest creation;
- guest-facing sales copy;
- tariff-derived meal visibility;
- canonical metadata/OpenGraph/structured data;
- sitemap/robots;
- confirmed property contacts.

Important system linkage:
- website availability reads the same InventoryBlock truth mutated by PMS chessboard;
- successful room/date move therefore changes website sellability without a separate sync job.

Main remaining site work:
- replace temporary/hotlinked media with owned Three Crowns photography;
- premium visual polish and category presentation;
- stronger mobile booking UX;
- final approved room content where authoritative values exist;
- analytics/SEO acceptance;
- staging acceptance;
- DNS cutover only after rollback gate.

---

# 12. INTERNAL HOTEL FINANCE

STATUS: INTERNAL REPORTING API IMPLEMENTED / NOT ACCOUNTING

V1 finance is internal control only.

Can derive from stored manager-confirmed facts:
- received payment totals by period;
- payment statuses/methods;
- received amounts by day;
- active reservation value / received / outstanding;
- prepayment snapshots where management records those facts;
- recent internal payment records.

Not in V1 scope:
- automatic acquiring;
- automated payment collection;
- accounting profit/tax/revenue-recognition policy.

---

# 13. DEPLOYMENT / PRODUCTION HARDENING

STATUS: IMPLEMENTED SCAFFOLD / ACTIVE WORK / NOT PRODUCTION DEPLOYED

Implemented:
- liveness/readiness;
- Docker images for Core/web/PMS/staff;
- production-oriented compose;
- env templates;
- privacy-safe request logging;
- production preflight;
- backup + manifest tooling;
- restore-verification tooling;
- documented migration-baseline procedure.

Remaining gates:
- real Prisma migration baseline instead of permanent `db push`;
- execute/prove current-schema backup -> restore;
- current-main build/E2E verification;
- staging acceptance;
- monitoring/alerts;
- rollback rehearsal;
- DNS/cutover.

---

# 14. DEFERRED / UNKNOWN MODULES

NFC: DEFERRED / DORMANT. No active engineering.

Future modules requiring exact owner rules/equipment:
- dining/cafeteria;
- store;
- entrance/access;
- QR service points/toilet scenario;
- billiards/resource usage;
- LED content management.

Do not invent accounting, pricing, hardware or workflow rules for these modules.

---

# 15. CI / VERIFICATION STATE

## Last explicitly confirmed full green baseline

Commit: `7038818db41756b94e8d5235410404b9b6172c1e`

Confirmed successful workflows on that historical baseline:
- Resort Core CI — SUCCESS;
- Automation Contract CI — SUCCESS;
- Realtime PMS CI — SUCCESS;
- historical NFC CI — SUCCESS (NFC now deferred).

## Current Actions blocker

Recent/current commits still return no usable new CI status/step evidence through the available GitHub Actions view.

Dedicated current workflows now include:
- updated Resort Core CI using manager-decided manual prepayment;
- PMS Chessboard Mutation CI for move/split/resize/stale/conflict rollback/audit;
- n8n Core contract CI;
- hotel operations CI;
- backup/restore CI scaffolding.

Until actual workflow execution evidence exists, latest chessboard/reception changes remain **IMPLEMENTED / NOT CI-VERIFIED**.

---

# 16. CURRENT ENGINEERING ORDER

Immediate sequence:

1. **Finish/verify PMS Chessboard V2 transaction safety and interaction UX.**
2. Add true pointer resize handles and faster move/split gestures over the same preview/commit API.
3. Finish reservation/guest side workspace directly from chessboard.
4. Harden schedule-aware check-in/check-out and room-relocation operational side effects.
5. Strengthen daily reception navigation and Command Center drill-downs.
6. Continue staff/housekeeping/maintenance convenience and evidence capture without inventing checklists.
7. Keep n8n/Core hot-lead contract stable.
8. Finish premium public site using the same Core truth; replace media when owned photography arrives.
9. Finish internal-finance UI from manager-recorded facts.
10. Establish migration baseline, backup/restore proof, CI, staging and rollback.
11. Production cutover only after acceptance.
12. Implement dining/store/access/QR/billiards/LED only after exact rules are supplied.

Development rule:

`KNOWLEDGE -> CURRENT STATE -> GAP -> PRIORITY -> IMPLEMENT -> TEST -> EVIDENCE -> VERIFIED / NOT VERIFIED -> CURRENT STATE UPDATE`
