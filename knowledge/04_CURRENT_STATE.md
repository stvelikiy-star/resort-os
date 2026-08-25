# RESORT OS — CURRENT STATE

Version: 0.8
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
- reservation/payment internal management flow;
- stays/check-in/check-out;
- housekeeping/maintenance tasks;
- realtime PMS WebSocket;
- guarded n8n/service API;
- provider-neutral communication/audit core;
- owner/manager Command Center;
- staff-control and room-detail extensions;
- internal hotel-finance reporting API;
- deployment/production scaffolding;
- dormant NFC code retained as deferred evidence only.

No production DNS cutover, automated acquiring activation or irreversible production migration is recorded.

---

# 2. ACTIVE OWNER ARCHITECTURE

STATUS: ACTIVE / CANONICAL

Canonical execution plan: `knowledge/07_EXECUTION_PLAN_THREE_CROWNS.md`.

## Hotel system boundary

**Resort OS is the source of hotel operational truth.**

It owns:
- rooms/categories/rates;
- deterministic availability and pricing;
- ReservationRequest / Reservation / manager-confirmed Payment facts;
- PMS/reception;
- stay lifecycle;
- housekeeping/maintenance/personnel tasks;
- internal finance visibility;
- owner analytics;
- controlled automation APIs;
- public website booking integration.

## Client automation boundary

Owner-selected V1 path:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- Telegram/other client channels may also be orchestrated through n8n;
- public website -> Resort Core directly.

n8n owns conversation orchestration and provider delivery. n8n must not write PostgreSQL or reimplement hotel business truth.

## Sales handoff boundary

Owner decision:
- automation goal = **hot qualified client**;
- n8n/AI collects dates, guest count, contact details and client intent;
- n8n/AI uses Core for actual availability and current price facts;
- n8n creates/reads `ReservationRequest` and hands the qualified client to a manager;
- **the manager decides and collects prepayment manually**;
- automation does not choose the prepayment amount, payment terms or payment method;
- automation does not create payment links/QR or collect money as part of V1;
- automation may only state payment/reservation success when manager-confirmed facts exist in Core.

Direct Telegram/provider adapter code already present in the repository is optional/reference implementation and is **not an active V1 dependency**.

## Explicit freeze

NFC / wristband / internal-wallet work is **DEFERRED** and excluded from the active engineering queue.

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

Known source caveats remain qualified rather than guessed.

---

# 4. DATABASE / CORE

STATUS: IMPLEMENTED; MAJOR BASELINE VERIFIED BEFORE CURRENT ACTIONS BLOCKER

Core domain includes property, rooms/rates, Guest, ReservationRequest, Reservation, InventoryBlock, Payment, staff/auth, OperationalTask, communication/audit entities, automation events and AuditLog.

Critical implemented invariants include:
- `ReservationRequest != Reservation`;
- valid date ranges;
- nonnegative reservation totals;
- positive payments;
- no overlapping active blocks for one room;
- idempotency boundaries for automation/payment-management workflows.

Physical room condition remains separate from reservation/stay state.

---

# 5. BOOKING / RESERVATION / PREPAYMENT TRUTH

STATUS: IMPLEMENTED CONTROLLED INTERNAL FLOW / AUTOMATED PAYMENT COLLECTION OUT OF V1 SCOPE

Implemented:
- deterministic availability;
- deterministic rate calculation;
- public/n8n ReservationRequest creation;
- manager request queue;
- internal manager-controlled payment confirmation path;
- atomic Guest + Reservation + InventoryBlock + Payment conversion when management records/uses that flow;
- check-in/check-out;
- audit/idempotency.

Owner rules currently active:
- automation stops at hot-lead qualification and handoff;
- manager decides and collects prepayment manually;
- without manager-confirmed prepayment/reservation fact, automation must not tell the guest that the room is booked;
- an unpaid ReservationRequest does not hold room inventory;
- the old site statement about an unpaid preliminary booking being held for two days is stale and must not drive automation;
- n8n must not infer a global prepayment percentage/amount or payment method.

Automated acquiring/payment-link/webhook integration is **not required for current V1** unless the owner explicitly reactivates that scope later.

---

# 6. PMS / RECEPTION

STATUS: IMPLEMENTED DEVELOPMENT CONTROL CENTER / RECENT EXTENSIONS NOT CI-VERIFIED

Canonical source: `apps/admin/`.

Current working areas:
- **Главная / Command Center** — Core-derived room, arrival/departure, request, task, internal payment and communication visibility;
- **Шахматка** — real Core data, date navigation, search/filters, sticky room/state columns, reservation/maintenance/manual blocks;
- **Заявки** — ReservationRequest processing and manager handoff workspace;
- **Брони** — search, arrivals today, departures today, staying guests, reservation/guest/room detail, manager-confirmed payments, balance, room tasks and audit history;
- **Операции** — housekeeping/maintenance/guest-request tasks, assignment and task history;
- **Персонал** — staff roles, task visibility, Telegram link visibility and internal session facts;
- **Сообщения** — optional provider-neutral communication/audit workspace.

Recent room-detail implementation exposes stored room metadata plus relevant reservation/block/task history without inventing missing attributes.

PMS is not a mock.

Advanced historical filter requirements that were not recovered remain backlog items and must not be invented.

---

# 7. STAFF / HOUSEKEEPING / MAINTENANCE

STATUS: IMPLEMENTED BASELINE / RECENT CONTROL EXTENSIONS NOT CI-VERIFIED

Implemented:
- `GUARANTEED -> CHECKED_IN`;
- `CHECKED_IN -> CHECKED_OUT`;
- checkout -> room `DIRTY`;
- checkout -> housekeeping task;
- housekeeping -> `IN_INSPECTION` -> manager acceptance -> `CLEAN`;
- maintenance task -> `TECH_BLOCK` where appropriate;
- task claim/assignment/status transitions;
- manager assignment/reassignment for housekeeping/maintenance;
- task action history from AuditLog;
- owner/manager staff-control view;
- staff PWA;
- Telegram Mini App identity/linking;
- voice-maintenance adapter code with conservative room matching.

Voice-maintenance behavior implemented after last confirmed green baseline:
- only linked active staff accounts are accepted;
- exact single room match can create a room-linked maintenance task;
- ambiguous/no room match creates a review task without blocking a guessed room;
- short room codes such as 1-6 require explicit room context;
- automated urgency remains `NORMAL` until severity rules are approved.

Photo/checklist evidence is not recorded as fully completed/verified yet.

---

# 8. N8N / AUTOMATION CONTRACT

STATUS: ACTIVE ARCHITECTURE / CORE BOUNDARY IMPLEMENTED / RECENT READ LAYER NOT CI-VERIFIED

Service authentication:
- `X-Resort-Service-Key`;
- constant-time secret comparison;
- n8n never writes PostgreSQL directly.

Existing write boundaries:
- `POST /api/v1/automation/reservation-requests`;
- `POST /api/v1/automation/staff-intake`;
- optional normalized communication/audit ingest.

Stable read-only truth layer:
- `GET /api/v1/automation/read/hotel-facts`;
- `GET /api/v1/automation/read/reservation-requests/{request_id}`;
- `GET /api/v1/automation/read/reservations/{booking_number}`.

Date-specific availability/pricing remains:
- `GET /api/v1/booking/check-availability`.

The hotel-facts response explicitly states the V1 handoff policy:
- automation goal = `HOT_QUALIFIED_LEAD`;
- manager handles prepayment;
- automation does not collect prepayment;
- automation does not decide prepayment amount or payment method.

Explicitly forbidden to AI/n8n:
- collect/confirm prepayment;
- decide prepayment amount/terms/method;
- create guaranteed reservation directly;
- check-in;
- check-out;
- refund;
- mutate hotel money;
- write PostgreSQL;
- invent price/availability/policy.

Truth rule: **tool failure or unknown result must never be described as success.**

Canonical n8n boundary documentation: `automation/n8n/README.md`.

---

# 9. CLIENT CHANNELS

STATUS: OWNER ROUTING DECISION CONFIRMED / PRODUCTION CONNECTIONS NOT RECORDED

Active architecture:
- Instagram client work: ManyChat -> n8n;
- WhatsApp client work: API Green -> n8n;
- Telegram may be handled through n8n where useful;
- website remains direct to Resort Core.

Resort OS no longer needs provider-specific Instagram/WhatsApp business logic as a V1 priority.

Client automation is considered successful when it produces a qualified handoff package such as:
`dates + guests + contact + category/intent + current Core price + ReservationRequest id -> manager`.

Existing direct Telegram Sales inbound/outbound adapter code remains optional/reference code and is not required for the main client architecture.

---

# 10. AI SALES / CONCIERGE

STATUS: MANAGER-DRAFT IMPLEMENTATION EXISTS / V1 ORCHESTRATION MOVES TO N8N / NOT CI-VERIFIED ON CURRENT MAIN

Existing Resort Core AI draft code:
- can prepare an internal manager-review draft;
- cannot auto-send;
- excludes internal notes from model context;
- supplies stored request/reservation/payment facts separately;
- explicitly forbids invented availability, price, payment or reservation state.

Under the owner-selected architecture, production client AI orchestration should primarily run in n8n and call the controlled Resort Core truth APIs.

V1 AI objective is qualification and hot-lead handoff, not automated closing/payment collection.

Resort Core AI draft code may remain as an optional manager-assist capability but is not the central client-channel orchestrator.

---

# 11. PUBLIC SITE

STATUS: IMPLEMENTED DEVELOPMENT BASELINE / RECENT CONTENT-SEO EXTENSIONS NOT CI-VERIFIED

Canonical source: `apps/web/`.

Implemented:
- real availability query;
- Core pricing;
- 12 real room-category presentation structure;
- guest contact capture;
- ReservationRequest creation;
- explicit statement that a request is not yet a valid reservation without manager confirmation;
- guest-facing copy instead of internal implementation terminology;
- tariff-derived meal visibility;
- canonical metadata/OpenGraph/structured data;
- sitemap and robots configuration;
- confirmed property contact data where authoritative.

Current production blockers:
- replace temporary/hotlinked media with owned Three Crowns photography;
- finish approved room/category content where authoritative values exist;
- mobile/SEO/analytics acceptance;
- staging verification;
- rollback gate before DNS cutover.

No `3korony.com` cutover to the canonical rebuild is recorded.

---

# 12. COMMAND CENTER / ANALYTICS

STATUS: IMPLEMENTED BASELINE / CONTINUES AS ACTIVE PRIORITY

Owner/manager Command Center derives values from Core entities rather than demo numbers.

Current direction is to expand cross-module operational visibility without inventing business thresholds:
- occupancy/inventory state;
- arrivals/departures;
- requests/reservations/internal payment visibility;
- dirty/inspection/tech-block rooms;
- housekeeping/maintenance workload;
- unassigned work and staff visibility;
- operational exceptions;
- later automation conversion metrics when source facts are normalized.

---

# 13. INTERNAL HOTEL FINANCE

STATUS: INTERNAL REPORTING API IMPLEMENTED / UI IN PROGRESS / NOT ACCOUNTING

Owner decision: finance in V1 is **internal hotel control only**.

Implemented backend reporting can derive from stored manager-confirmed facts:
- received payment totals by selected period;
- payment count/status snapshots;
- received amounts by recorded payment method;
- received amounts by day;
- active reservation value / received / outstanding snapshot;
- requests awaiting prepayment snapshot when management uses that status/data;
- all-time refunded-status snapshot;
- recent internal payment records.

Important boundaries:
- Resort OS does not collect prepayment automatically in V1;
- manager decides/collects prepayment manually;
- finance screens report what management has recorded/confirmed in Core;
- these reports are not accounting profit, tax or revenue-recognition statements;
- automated acquiring/provider webhooks are not a V1 requirement.

---

# 14. DEPLOYMENT / PRODUCTION HARDENING

STATUS: IMPLEMENTED SCAFFOLD / ACTIVE WORK / NOT PRODUCTION DEPLOYED

Implemented:
- Core liveness/readiness;
- Docker images for Core, web, PMS and staff;
- production-oriented compose topology;
- env templates;
- explicit Next.js Core URL build args;
- staged deployment/rollback runbook;
- privacy-safe request-id structured logging;
- production preflight script;
- backup + manifest tooling;
- restore-verification tooling and CI scaffold;
- documented migration-baseline procedure.

Production preflight checks include:
- `APP_ENV=production`;
- secure cookie configuration;
- PostgreSQL connection/property data;
- critical DB constraints;
- migration history;
- cleared bootstrap password;
- automation key sanity;
- verified backup marker.

Remaining production gates:
- real migration baseline instead of permanent `prisma db push`;
- execute/prove backup -> restore on current schema;
- current-main verification;
- staging acceptance;
- monitoring/alerts;
- rollback rehearsal;
- DNS/cutover.

---

# 15. DEFERRED NFC

STATUS: DEFERRED / DORMANT

Existing NFC code stays in the repository as optional future evidence only.

Per owner direction:
- no further NFC engineering;
- no NFC UX work;
- no NFC production activation;
- no NFC provider work;
- NFC is not a dependency for V1.

---

# 16. FUTURE HOTEL MODULES REQUIRING EXACT RULES

Confirmed broader scope still includes:
- dining/cafeteria;
- store;
- entrance/access;
- QR service points/toilet scenario;
- billiards/resource usage;
- LED content management.

Do not invent exact accounting, pricing, hardware or workflow rules.

Beach bar/cafe own payment remains outside the central hotel payment contour under the current direction.

---

# 17. CI / VERIFICATION STATE

## Last explicitly confirmed full green baseline

Commit: `7038818db41756b94e8d5235410404b9b6172c1e`

Confirmed successful workflows on that commit:
- Resort Core CI — SUCCESS;
- Automation Contract CI — SUCCESS;
- Realtime PMS CI — SUCCESS;
- NFC Beach Payment CI — SUCCESS (historical only; NFC now deferred).

## Current Actions blocker

Later workflows began terminating before workflow steps executed; earlier evidence showed empty/null step execution and no usable test logs.

Recent commits therefore remain **IMPLEMENTED / NOT CI-VERIFIED** unless explicit test/build/runtime evidence exists.

Do not classify an infrastructure Actions failure as a code failure without step/log evidence.

---

# 18. CURRENT ENGINEERING ORDER

Established foundation:

`PROPERTY DATA -> POSTGRESQL -> CORE -> AUTH/RBAC -> AVAILABILITY/PRICING -> RESERVATION REQUEST -> MANAGER HANDOFF -> PMS -> STAYS -> STAFF OPS -> REALTIME -> COMMAND CENTER -> N8N SERVICE BOUNDARY -> PUBLIC SITE -> DEPLOYMENT SCAFFOLD`

Immediate active sequence:
1. finish internal PMS finance UI from manager-recorded facts;
2. strengthen Command Center links/exceptions and daily reception workflows;
3. strengthen housekeeping/maintenance/staff operations and evidence capture without inventing checklists;
4. keep n8n/Core contracts stable for hot-lead qualification and manager handoff;
5. improve website using authoritative room/rate/property data while waiting for owned photography;
6. establish migration baseline + backup/restore + production preflight/observability;
7. restore current-main CI verification;
8. staging acceptance and site/system cutover;
9. specify dining/store/access/QR/billiards/LED rules before implementation.

Automated payment-provider integration is not in the active V1 sequence unless the owner explicitly reactivates it later.

Development rule:

`KNOWLEDGE -> CURRENT STATE -> GAP -> PRIORITY -> IMPLEMENT -> TEST -> EVIDENCE -> VERIFIED / NOT VERIFIED -> CURRENT STATE UPDATE`
