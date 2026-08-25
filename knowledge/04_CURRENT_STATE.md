# RESORT OS — CURRENT STATE

Version: 0.5
Date: 2026-08-25
Status: ACTIVE DEVELOPMENT / LAST FULLY CONFIRMED CI BASELINE RECORDED
Canonical: YES
Document Type: Evidence-Based Current System State

Critical rule: **TARGET ≠ CURRENT. IMPLEMENTED ≠ VERIFIED. DEVELOPMENT VERIFIED ≠ PRODUCTION READY.**

---

# 1. CANONICAL REPOSITORY

STATUS: VERIFIED FACT

Repository:
`stvelikiy-star/resort-os`

Canonical implementation contains:
- PostgreSQL + Prisma domain schema;
- critical PostgreSQL SQL invariants/functions;
- FastAPI Resort Core;
- real Three Crowns room/rate seed baseline;
- Next.js PMS/admin;
- Next.js public booking site;
- Next.js staff/Telegram-oriented PWA;
- auth/RBAC;
- reservation/payment management flow;
- stays/check-in/check-out;
- housekeeping/maintenance operational tasks;
- realtime PMS WebSocket;
- guarded automation service API;
- NFC wallet/beach payment subsystem;
- recovery evidence and canonical knowledge.

No DNS cutover, production payment activation or irreversible production migration is recorded here.

---

# 2. PROPERTY DATA

STATUS: VERIFIED AS SEEDABLE DEVELOPMENT BASELINE

Current development baseline reconciles:
- 84 rooms;
- 12 room categories;
- 2026/27 rate input.

Evidence:
- `data-intake/rooms.csv`
- `data-intake/rates.csv`
- `docs/THREE_CROWNS_SOURCE_RECONCILIATION_2026-08-25.md`

Known source caveats remain qualified rather than guessed.

---

# 3. DATABASE CORE

STATUS: IMPLEMENTED; MAJOR BASELINE VERIFIED IN CI

Current Prisma/domain schema includes:
- Property;
- RoomType / Room;
- RatePlan / RatePeriod;
- Guest;
- ReservationRequest;
- Reservation;
- InventoryBlock;
- Payment;
- StaffUser / AuthSession;
- OperationalTask;
- AutomationInboundEvent;
- NfcWallet / NfcBracelet / NfcTransaction / NfcLedgerEntry;
- AuditLog.

Critical implemented invariants include:
- `ReservationRequest != Reservation`;
- valid stay/rate date ranges;
- nonnegative reservation totals;
- positive payment amounts;
- active inventory blocks for the same room cannot overlap;
- NFC wallet balance cannot be negative;
- NFC transaction split must equal amount;
- NFC ledger balance arithmetic must reconcile;
- beach commission is bounded to 0..10000 bps.

Added after the last fully confirmed CI baseline:
- `packages/database/sql/003_nfc_lifecycle.sql`;
- partial unique index enforcing no more than one `ACTIVE` bracelet per NFC wallet.

This latest lifecycle SQL is IMPLEMENTED but currently NOT CI-VERIFIED because GitHub Actions jobs are not starting workflow steps (see section 16).

---

# 4. CORE API

STATUS: IMPLEMENTED; CORE BASELINE VERIFIED IN CI

Public/core routes include:
- `GET /health`;
- `GET /api/v1/booking/check-availability`;
- `POST /api/v1/booking/requests`;
- `GET /api/v1/pms/grid`.

Domain modules composed by `services/api/app/app_entry.py` include:
- booking admin;
- operations;
- stays;
- Telegram authentication;
- automation;
- realtime;
- NFC;
- NFC reporting.

Current business truth:
**WITHOUT THE CONTROLLED PAYMENT/MANAGEMENT CONVERSION FLOW THERE IS NO GUARANTEED RESERVATION.**

AI/n8n does not receive a route that can directly confirm payment or create a guaranteed reservation.

---

# 5. AUTHENTICATION / RBAC

STATUS: IMPLEMENTED / VERIFIED IN THE LAST CONFIRMED BASELINE

Implemented:
- server-side username/password authentication;
- Argon2 password verification;
- hashed session tokens stored in PostgreSQL;
- session expiry/revocation model;
- secure-cookie configuration including optional shared cookie domain;
- server-side role checks;
- roles: `OWNER`, `MANAGER`, `MAID`, `TECHNICIAN`, `BEACH_PARTNER`;
- Telegram Mini App `initData` signature validation;
- Telegram account linking to an existing staff user;
- automatic Telegram login after linking.

Production credentials/tokens are not committed.

---

# 6. RESERVATION REQUEST -> PAYMENT -> GUARANTEED RESERVATION

STATUS: IMPLEMENTED CONTROLLED MANAGEMENT FLOW / EXTERNAL ACQUIRING NOT ACTIVATED

Implemented:
- manager request queue;
- deterministic quote against Core room/rate data;
- configurable prepayment percentage (`PREPAYMENT_PERCENT`, current project default 30);
- controlled payment confirmation endpoint;
- atomic creation of Guest + GUARANTEED Reservation + reservation inventory block + received Payment;
- request conversion to `CONVERTED`;
- idempotency/audit boundaries used by the management flow;
- no AI permission to execute this conversion.

Not yet production-integrated:
- MBank / Optima / PayBox acquiring/webhook credentials;
- provider signature verification;
- automated provider reconciliation/refund flows.

No production merchant keys are recorded in the repository.

---

# 7. PMS ADMIN

STATUS: IMPLEMENTED DEVELOPMENT CONTROL CENTER

Canonical source:
`apps/admin/`

Current major areas:
- **Шахматка** — real Core data, date windows/navigation, search and filters, sticky room/state columns, reservation/maintenance/manual blocks;
- **Заявки** — ReservationRequest workspace and controlled conversion flow;
- **Брони** — guaranteed reservations, check-in/check-out, NFC issuance/management;
- **Операции** — housekeeping/maintenance/guest-request tasks;
- **Финансы NFC** — added after last fully confirmed baseline; read-only transaction/partner reporting.

PMS is no longer a deterministic mock.

Advanced filter requirements beyond currently recovered/implemented filters must remain an explicit backlog item; do not invent unrecovered historical filter specifications.

---

# 8. STAYS / HOUSEKEEPING / MAINTENANCE

STATUS: IMPLEMENTED BASELINE

Implemented:
- controlled `GUARANTEED -> CHECKED_IN`;
- controlled `CHECKED_IN -> CHECKED_OUT`;
- checkout changes physical room state to `DIRTY`;
- checkout creates/reuses housekeeping task;
- housekeeping task lifecycle including `IN_INSPECTION`;
- manager acceptance flow;
- maintenance tasks;
- maintenance intake can move a room to `TECH_BLOCK`;
- staff assignment/claiming and task status transitions;
- staff PWA for operational workers.

Room physical states remain:
- `UNKNOWN`;
- `CLEAN`;
- `DIRTY`;
- `IN_INSPECTION`;
- `TECH_BLOCK`.

Photo-proof workflow is not recorded as fully implemented/verified yet.

---

# 9. STAFF / TELEGRAM PWA

STATUS: IMPLEMENTED DEVELOPMENT BASELINE

Canonical source:
`apps/staff/`

Implemented roles/interfaces:
- MAID task interface;
- TECHNICIAN task interface;
- BEACH_PARTNER NFC terminal;
- Telegram Mini App bootstrapping and automatic identity attempt;
- first-login Telegram linking fallback;
- manual login fallback.

BEACH_PARTNER terminal supports:
- bracelet UID scan/input;
- balance lookup;
- charge amount;
- commission preview/result;
- idempotent retry behavior through Core;
- Web NFC when supported by the client environment;
- manual UID fallback when Web NFC is unavailable.

Browser/WebView NFC hardware compatibility still requires real-device testing.

---

# 10. REALTIME PMS

STATUS: IMPLEMENTED / VERIFIED IN LAST CONFIRMED BASELINE

Implemented WebSocket contract:
`/ws/pms/grid`

Verified baseline behavior before the current Actions infrastructure blocker:
- authenticated manager connection;
- initial PMS snapshot;
- PostgreSQL state change;
- same WebSocket receives an updated snapshot without manual refresh.

Current implementation observes PostgreSQL state and can later be optimized to `LISTEN/NOTIFY` without changing the external WebSocket contract.

---

# 11. AI / AUTOMATION SERVICE BOUNDARY

STATUS: CORE TOOL BOUNDARY IMPLEMENTED / VERIFIED IN LAST CONFIRMED BASELINE

Implemented protected service routes:
- `GET /api/v1/automation/capabilities`;
- `POST /api/v1/automation/reservation-requests`;
- `POST /api/v1/automation/staff-intake`.

Authentication:
`X-Resort-Service-Key` validated with constant-time comparison.

Automation inbound events have database idempotency tracking.

Explicit AI/n8n forbidden operations include:
- payment confirmation;
- guaranteed reservation creation;
- check-in;
- check-out;
- refund;
- NFC charge.

Truth rule:
**tool failure or unknown result must never be described as success.**

---

# 12. n8n / CHANNEL AUTOMATION

STATUS: CORE BRIDGE TEMPLATES IMPLEMENTED / NOT DEPLOYED

Added after the last fully confirmed CI baseline:
- `automation/n8n/README.md`;
- `automation/n8n/reservation-intake-core.json`;
- `automation/n8n/staff-intake-core.json`.

These are inactive, importable orchestration templates for **normalized structured input** only.

They do not contain provider credentials and do not connect directly to PostgreSQL.

NOT YET IMPLEMENTED/DEPLOYED:
- production n8n instance configuration;
- Instagram adapter;
- WhatsApp adapter;
- Telegram sales adapter;
- unified inbox/response-control dashboard;
- OpenAI extraction/reply layer;
- Whisper audio transcription adapter;
- outbound provider reply delivery and retry/DLQ logic.

---

# 13. NFC CASHLESS SYSTEM

STATUS: CORE PAYMENT BASELINE VERIFIED; LIFECYCLE/FINANCE EXTENSIONS IMPLEMENTED BUT CURRENTLY NOT CI-VERIFIED

Verified before current Actions blocker:
- NFC wallet issuance only after `CHECKED_IN`;
- raw bracelet UID is not stored; Core stores a peppered SHA-256 hash;
- `BEACH_PARTNER` RBAC;
- PostgreSQL `process_nfc_payment`;
- wallet locking using `FOR UPDATE`;
- idempotency;
- idempotency replay bound to the same partner;
- immutable transaction + ledger write;
- property commission config, Three Crowns current default 500 bps (5%);
- insufficient-funds rejection;
- concurrency test proving simultaneous charges cannot overdraw wallet.

Implemented after last fully confirmed baseline:
- reception NFC issue modal;
- wallet summary in reservation workspace;
- bracelet states using schema-confirmed values `ACTIVE/BLOCKED/LOST/RETURNED`;
- controlled bracelet retirement;
- atomic bracelet replacement preserving wallet balance;
- database invariant: max one ACTIVE bracelet per wallet;
- checkout freezes ACTIVE NFC wallet/bracelet to `BLOCKED` while preserving remaining balance;
- manager NFC transaction report;
- partner commission summary;
- admin `Финансы NFC` tab;
- beach-partner own transaction reporting API.

IMPORTANT UNKNOWN / BUSINESS DECISION REQUIRED:
what happens to a nonzero remaining NFC balance after checkout (refund, transfer, other settlement policy). Current safe behavior freezes access and preserves the balance; it does not silently zero or refund money.

---

# 14. CANONICAL PUBLIC SITE

STATUS: IMPLEMENTED / VERIFIED DEVELOPMENT BASELINE

Canonical source:
`apps/web/`

Implemented:
- real availability query;
- real Core price data;
- room-category selection;
- guest contact capture;
- `POST /api/v1/booking/requests`;
- explicit message that a request is not yet a guaranteed reservation.

Recovered V5 remains reference evidence only.

Current media limitation:
temporary/hotlinked images remain a production-cutover blocker until owned resort media replaces them.

No `3korony.com` DNS cutover to the canonical rebuild is recorded.

---

# 15. DINING / STORE / QR / ACCESS / BILLIARDS / LED / UNIFIED INBOX

STATUS: CONFIRMED PROJECT SCOPE / IMPLEMENTATION TODO UNLESS SEPARATELY EVIDENCED

Confirmed required modules include:
- dining/cafeteria management;
- shop/payment control;
- beach bar;
- beach cafe;
- entrance/access;
- QR toilet scenario;
- billiards;
- LED screen management;
- unified control of incoming messages/replies across platforms.

Detailed historical business rules for several of these modules were not recovered. Do not invent them. They require explicit domain contracts before financial/access-control implementation.

---

# 16. CI / VERIFICATION STATE

## Last explicitly confirmed full green baseline

Commit:
`7038818db41756b94e8d5235410404b9b6172c1e`

Confirmed successful workflows on that commit:
- Resort Core CI — SUCCESS;
- Automation Contract CI — SUCCESS;
- Realtime PMS CI — SUCCESS;
- NFC Beach Payment CI — SUCCESS.

The verified NFC CI at that baseline covered 5% commission, idempotent retry, insufficient funds, raw UID hashing and concurrent-charge no-overdraft behavior.

## Current GitHub Actions blocker

Starting later on 2026-08-25, multiple independent workflows began failing approximately 4–5 seconds after scheduling, before any workflow step executed.

Observed evidence on failed jobs:
- job conclusion `failure`;
- `steps = null` / empty step list;
- no decoded job log available.

Therefore the exact infrastructure cause is **UNKNOWN**.

Do NOT classify these runs as code/test failures without a workflow step/log proving such a failure.

All commits after the last fully confirmed baseline must be classified as one of:
- IMPLEMENTED / NOT CI-VERIFIED, or
- VERIFIED by another explicit evidence source.

---

# 17. CURRENT ENGINEERING ORDER

Completed/established foundation:

`PROPERTY DATA -> POSTGRESQL -> CORE -> AUTH/RBAC -> BOOKING REQUEST -> CONTROLLED PAYMENT CONVERSION -> PMS -> STAYS -> STAFF OPS -> REALTIME -> GUARDED AUTOMATION TOOLS -> NFC CORE`

Immediate next sequence:

1. restore/diagnose GitHub Actions runner execution and re-verify current `main`;
2. add provider/channel adapters around the guarded n8n Core bridge;
3. implement Whisper/audio intake adapter for technicians/staff;
4. implement unified inbox + response-control state model;
5. integrate a real payment provider only after provider credentials/contracts are explicitly selected;
6. define NFC checkout balance settlement policy before any refund/close automation;
7. specify and implement dining/store/beach cafe/bar accounting domain;
8. specify entrance/QR toilet/billiards access/resource domain;
9. specify LED screen device/content protocol;
10. replace public-site temporary media with owned assets and perform production cutover only after full acceptance/rollback planning.
