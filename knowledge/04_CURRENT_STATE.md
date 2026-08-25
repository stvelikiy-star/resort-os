# RESORT OS — CURRENT STATE

Version: 0.6
Date: 2026-08-25
Status: ACTIVE DEVELOPMENT / CURRENT MAIN PARTIALLY NOT CI-VERIFIED
Canonical: YES
Document Type: Evidence-Based Current System State

Critical rule: **TARGET ≠ CURRENT. IMPLEMENTED ≠ VERIFIED. DEVELOPMENT VERIFIED ≠ PRODUCTION READY.**

---

# 1. CANONICAL REPOSITORY

STATUS: VERIFIED FACT

Repository: `stvelikiy-star/resort-os`

Canonical implementation currently contains:
- PostgreSQL + Prisma domain schema;
- FastAPI Resort Core;
- Three Crowns room/rate seed baseline;
- Next.js PMS/admin;
- Next.js public booking site;
- Next.js staff/Telegram-oriented PWA;
- authentication/RBAC;
- reservation/payment management flow;
- stays/check-in/check-out;
- housekeeping/maintenance tasks;
- realtime PMS WebSocket;
- guarded automation service API;
- provider-neutral Unified Inbox core;
- owner/manager Command Center;
- container/deployment scaffolding;
- dormant NFC implementation retained as deferred code only.

No production DNS cutover, production payment activation or irreversible production migration is recorded.

---

# 2. ACTIVE EXECUTION PLAN

STATUS: ACTIVE / CANONICAL

Canonical plan: `knowledge/07_EXECUTION_PLAN_THREE_CROWNS.md`.

NFC / wristband / internal-wallet work is **DEFERRED** and excluded from the active engineering queue until the owner explicitly reactivates it.

Current active order:
1. PMS daily management and reception visibility;
2. housekeeping/maintenance operational control;
3. Unified Inbox and response control;
4. channel adapters;
5. AI Sales & Concierge over controlled Core tools;
6. Whisper/audio staff intake;
7. real hotel payment provider after provider selection;
8. public-site production completion;
9. dining/store/QR/access/billiards/LED only after exact rules/equipment are known;
10. production hardening/cutover.

Unknown business rules must remain UNKNOWN / DECISION REQUIRED rather than being invented.

---

# 3. PROPERTY DATA

STATUS: VERIFIED AS SEEDABLE DEVELOPMENT BASELINE

Development baseline reconciles:
- 84 rooms;
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

Core domain includes property, room/rate, guest, ReservationRequest, Reservation, InventoryBlock, Payment, staff/auth, operational tasks, communication/inbox entities, automation inbound events and AuditLog.

Critical implemented hotel invariants include:
- `ReservationRequest != Reservation`;
- valid date ranges;
- nonnegative reservation totals;
- positive payment amounts;
- active inventory blocks for the same room cannot overlap.

Dormant NFC tables/functions remain in the repository as deferred implementation evidence but are not part of the active engineering plan.

---

# 5. CORE API

STATUS: IMPLEMENTED

Key routes/modules include:
- health/readiness;
- booking availability and reservation requests;
- PMS grid;
- booking administration;
- reservation detail;
- stays/check-in/check-out;
- operations;
- Telegram staff authentication;
- guarded automation;
- provider-neutral communication ingest;
- manager Unified Inbox;
- realtime PMS;
- owner/manager Command Center.

Current business truth:
**A REQUEST IS NOT A GUARANTEED RESERVATION.**

AI/n8n does not have a route that can directly confirm payment, create a guaranteed reservation, check a guest in/out or mutate money.

---

# 6. AUTHENTICATION / RBAC

STATUS: IMPLEMENTED / VERIFIED IN LAST CONFIRMED BASELINE

Implemented:
- username/password authentication;
- Argon2 verification;
- hashed PostgreSQL sessions;
- expiry/revocation;
- secure cookie configuration;
- server-side role checks;
- Telegram Mini App signature validation and staff linking.

Production secrets are not committed.

---

# 7. BOOKING / PAYMENT-CONVERSION FLOW

STATUS: IMPLEMENTED CONTROLLED MANAGEMENT FLOW / EXTERNAL ACQUIRING NOT ACTIVATED

Implemented:
- manager request queue;
- deterministic quote from Core rates/availability;
- configurable prepayment percentage in development configuration;
- controlled payment confirmation endpoint;
- atomic Guest + GUARANTEED Reservation + inventory block + Payment creation;
- conversion of the request to `CONVERTED`;
- audit/idempotency boundaries;
- no AI permission for final conversion.

Not production-integrated:
- real MBank / Optima / PayBox adapter;
- provider signature verification;
- provider reconciliation/refunds.

Business note: the exact live prepayment rule must follow the owner’s current policy when production payment integration is selected; old website text is not authoritative.

---

# 8. PMS / RECEPTION

STATUS: IMPLEMENTED DEVELOPMENT CONTROL CENTER / RECENT EXTENSIONS NOT CI-VERIFIED

Canonical source: `apps/admin/`.

Current active areas include:
- **Главная / Command Center** — real Core-derived KPIs for room state, arrivals/departures, requests, tasks, payment visibility and communication response control;
- **Шахматка** — real Core data, date navigation, search/filters, sticky room/state columns, reservation/maintenance/manual blocks;
- **Заявки** — ReservationRequest workspace and controlled conversion flow;
- **Брони** — reception workspace with search, arrivals today, departures today, currently staying guests, reservation/guest/room detail, confirmed payments, outstanding balance, room tasks and audit history;
- **Операции** — housekeeping/maintenance/guest-request tasks;
- **Сообщения** — Unified Inbox response-control workspace.

PMS is no longer a deterministic mock.

Advanced historical filter requirements that were not recovered remain backlog items and must not be invented.

---

# 9. STAYS / HOUSEKEEPING / MAINTENANCE

STATUS: IMPLEMENTED BASELINE

Implemented:
- `GUARANTEED -> CHECKED_IN`;
- `CHECKED_IN -> CHECKED_OUT`;
- checkout moves room to `DIRTY`;
- checkout creates/reuses housekeeping task;
- housekeeping lifecycle through `IN_INSPECTION` and manager acceptance;
- maintenance tasks and `TECH_BLOCK`;
- staff task claiming/assignment/status transitions;
- staff PWA.

Physical room states remain separate from reservation/stay state.

Photo-proof/checklist completion is not recorded as fully implemented/verified yet.

---

# 10. UNIFIED INBOX

STATUS: IMPLEMENTED PROVIDER-NEUTRAL CORE / NOT YET CONNECTED TO LIVE CHANNELS / NOT CI-VERIFIED ON CURRENT MAIN

Implemented domain:
- CommunicationChannel;
- Conversation;
- ConversationMessage;
- manager assignment;
- link from conversation to ReservationRequest;
- normalized provider-neutral inbound/outbound message ingestion;
- idempotency through automation inbound events;
- manager conversation read/control API;
- response-control state based on actual inbound/outbound timestamps;
- internal notes;
- manager Inbox UI;
- Command Center metrics for conversations needing a response and longest actual waiting time.

Important truth:
- no fake external-send button is exposed;
- live Telegram/WhatsApp/Instagram outbound delivery is not yet connected;
- no invented SLA threshold is applied.

A dedicated Unified Inbox CI workflow has been added but current GitHub Actions execution remains unavailable for verification.

---

# 11. AI / AUTOMATION BOUNDARY

STATUS: CORE TOOL BOUNDARY IMPLEMENTED / MAJOR BASELINE VERIFIED

Protected automation capabilities include reservation-request creation, structured staff intake and normalized Inbox ingestion.

Authentication uses `X-Resort-Service-Key` with constant-time comparison.

Automation inbound events use database idempotency tracking.

Explicitly forbidden to AI/n8n:
- payment confirmation;
- guaranteed reservation creation;
- check-in;
- check-out;
- refund;
- NFC charge.

Truth rule: **tool failure or unknown result must never be described as success.**

---

# 12. n8n / CHANNEL AUTOMATION

STATUS: CORE BRIDGE TEMPLATES IMPLEMENTED / LIVE CHANNELS NOT DEPLOYED

Inactive importable normalized-input templates exist under `automation/n8n/`.

They do not contain production credentials and do not connect directly to PostgreSQL.

Still required:
- Telegram Sales adapter;
- WhatsApp adapter;
- Instagram adapter;
- provider outbound delivery/retry handling;
- OpenAI extraction/reply orchestration;
- Whisper audio transcription adapter.

Provider-specific behavior must be implemented only from actual provider contracts/credentials.

---

# 13. REALTIME PMS

STATUS: IMPLEMENTED / VERIFIED IN LAST CONFIRMED BASELINE

WebSocket: `/ws/pms/grid`.

Verified baseline behavior:
- authenticated manager connection;
- initial PMS snapshot;
- PostgreSQL state change;
- updated snapshot on the same WebSocket without manual refresh.

---

# 14. PUBLIC SITE

STATUS: IMPLEMENTED / VERIFIED DEVELOPMENT BASELINE

Canonical source: `apps/web/`.

Implemented:
- real availability query;
- Core price data;
- room-category selection;
- guest contact capture;
- ReservationRequest creation;
- explicit communication that a request is not yet a guaranteed reservation.

Production blockers:
- temporary/hotlinked media must be replaced with owned Three Crowns media;
- final room content must be completed;
- full acceptance/rollback gate must precede DNS cutover.

No `3korony.com` cutover to the canonical rebuild is recorded.

---

# 15. DEPLOYMENT / OPERATIONS PACK

STATUS: IMPLEMENTED SCAFFOLD / NOT PRODUCTION DEPLOYED / NOT CI-VERIFIED ON CURRENT MAIN

Implemented after the last confirmed green baseline:
- liveness/readiness probes;
- Docker images for Core, public web, PMS and staff PWA;
- production-oriented compose topology;
- production environment contract/template;
- explicit Core URL build arguments for Next.js images;
- staged deployment and rollback runbook;
- reduced container build context.

Production gate:
- establish a real migration baseline rather than relying on `prisma db push` as the permanent production strategy;
- prove backup/restore;
- run current-main verification;
- perform staging acceptance before cutover.

---

# 16. DEFERRED NFC

STATUS: DEFERRED / DORMANT

The repository retains previously implemented NFC code as evidence and optional future capability.

Per the active owner direction:
- no further NFC engineering;
- no NFC UX expansion;
- no NFC production activation;
- no NFC payment-provider work;
- no NFC business-rule decisions are part of the active queue.

Do not use NFC as a dependency for current Three Crowns V1.

---

# 17. CONFIRMED SCOPE / RULES STILL REQUIRED

Confirmed future modules include:
- dining/cafeteria management;
- store management;
- entrance/access;
- QR service points/toilet scenario;
- billiards/resource booking;
- LED screen management.

Do not invent exact accounting, pricing, hardware or workflow rules that were not recovered/confirmed.

Beach bar/cafe payment remains outside the hotel’s central payment contour under the current project direction.

---

# 18. CI / VERIFICATION STATE

## Last explicitly confirmed full green baseline

Commit: `7038818db41756b94e8d5235410404b9b6172c1e`

Confirmed successful workflows on that commit:
- Resort Core CI — SUCCESS;
- Automation Contract CI — SUCCESS;
- Realtime PMS CI — SUCCESS;
- NFC Beach Payment CI — SUCCESS.

The NFC result above is historical verification only; NFC is now deferred.

## Current Actions blocker

Later on 2026-08-25, multiple workflows began terminating before workflow steps executed. Earlier failed jobs showed empty/null steps and no usable step logs.

For current recent commits, available GitHub checks/runs do not provide new successful verification evidence.

Therefore commits after the last confirmed green baseline remain **IMPLEMENTED / NOT CI-VERIFIED** unless another explicit evidence source verifies them.

Do not classify an infrastructure-level Actions failure as a code/test failure without step/log evidence.

---

# 19. CURRENT ENGINEERING ORDER

Completed/established active foundation:

`PROPERTY DATA -> POSTGRESQL -> CORE -> AUTH/RBAC -> BOOKING REQUEST -> CONTROLLED CONVERSION -> PMS -> STAYS -> STAFF OPS -> REALTIME -> GUARDED AUTOMATION -> COMMAND CENTER -> RECEPTION DETAIL -> UNIFIED INBOX CORE -> DEPLOYMENT SCAFFOLD`

Immediate next sequence:
1. keep current-state evidence synchronized and restore/diagnose CI verification;
2. implement Telegram Sales adapter into the normalized Inbox contract;
3. add real outbound-channel adapter boundary with explicit delivery result/retry state;
4. implement AI Sales/Concierge orchestration over allowed Core tools only;
5. implement Whisper/audio staff intake;
6. add WhatsApp and Instagram adapters only from their actual integration contracts;
7. integrate real hotel payment provider after provider selection/credentials;
8. finish public site owned media/content and staging acceptance;
9. specify remaining dining/store/access/QR/billiards/LED rules before implementation;
10. production hardening, backup/restore, monitoring, staging, rollback and cutover.
