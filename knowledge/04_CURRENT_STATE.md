# RESORT OS — CURRENT STATE

Version: 0.2
Date: 2026-08-25
Status: IMPLEMENTATION STARTED
Canonical: YES
Document Type: Evidence-Based Current System State

Critical rule: TARGET ≠ CURRENT. This file records implementation evidence only.

---

# 1. REPOSITORY

STATUS: VERIFIED FACT

Canonical repository:
`stvelikiy-star/resort-os`

Repository now contains:
- canonical knowledge;
- recovery artifacts;
- evidence-backed Three Crowns room/rate intake;
- first PostgreSQL/Prisma Core schema;
- first FastAPI Core implementation;
- seed/bootstrap scripts;
- CI definition.

---

# 2. THREE CROWNS DATA BASELINE

STATUS: PARTIAL / EVIDENCE-BACKED INPUT

Evidence:
- `data-intake/rooms.csv`
- `data-intake/rates.csv`
- `data-intake/reservation_rules.md`
- `docs/THREE_CROWNS_SOURCE_RECONCILIATION_2026-08-25.md`

Established input baseline:
- 84 room rows;
- 12 room categories;
- 2026/27 seasonal tariff rows;
- direct-source food and extra-person tariffs;
- unpaid request is NOT an active reservation;
- legacy website rule allowing an unpaid preliminary booking for two days is stale and MUST NOT be implemented.

Known data caveats remain documented in the reconciliation file, including 501/502 category confirmation, building/floor mapping and raw bed abbreviations.

---

# 3. PUBLIC WEBSITE

STATUS: PARTIAL

Evidence from prior Vercel audit:
- production-target V5 prototype exists on Vercel;
- visual public-site skeleton exists;
- its booking interaction is prototype behavior and is not evidence of real availability/reservation functionality;
- V5 source tree has not yet been established inside this canonical repository.

Production DNS cutover to V5 is NOT approved by this status.

---

# 4. PMS GRID

STATUS: PARTIAL / RECOVERED UI PROTOTYPE

Evidence:
`recovery-artifacts/pms-grid/PMSGrid.tsx`

The recovered component:
- is an interactive grid UI prototype;
- contains deterministic mock data;
- is NOT current production PMS;
- can be adapted to the new live Core endpoint once the backend is verified.

New implementation endpoint now exists in source:
`GET /api/v1/pms/grid`

Runtime status of that endpoint:
NOT YET VERIFIED at the time of this update.

---

# 5. DATABASE / INVENTORY / PRICING

STATUS: IMPLEMENTED IN SOURCE / NOT YET VERIFIED

Evidence:
- `packages/database/prisma/schema.prisma`
- `packages/database/sql/001_core_constraints.sql`
- `scripts/seed_from_intake.py`

Implemented source model includes:
- Property;
- RoomType;
- Room;
- RatePlan;
- RatePeriod;
- Guest;
- ReservationRequest;
- Reservation;
- InventoryBlock;
- Payment;
- AuditLog.

Important implementation boundary:
- ReservationRequest and Reservation are separate entities;
- an unpaid request does not create a Reservation;
- rate rows with price 0 are imported as `CONFIRM_REQUIRED`, not as free sale inventory.

Data-integrity implementation includes a PostgreSQL exclusion constraint designed to prevent overlapping active inventory blocks for the same room.

Database migration/constraint execution and concurrency behavior remain NOT VERIFIED until CI/runtime evidence succeeds.

---

# 6. CORE API

STATUS: IMPLEMENTED IN SOURCE / NOT YET VERIFIED

Evidence:
- `services/api/app/main.py`
- `services/api/app/db.py`
- `services/api/requirements.txt`

Implemented source routes:
- `GET /health`
- `GET /api/v1/booking/check-availability`
- `POST /api/v1/booking/requests`
- `GET /api/v1/pms/grid`

Current booking rule enforced by source intent:
`REQUEST -> availability/price -> payment/confirmation flow -> RESERVATION`

The current request endpoint explicitly returns that the created object is not a reservation.

Authentication/RBAC is NOT implemented yet and the API MUST NOT be treated as production-public until authorization boundaries exist.

---

# 7. CI / TESTING

STATUS: IMPLEMENTED DEFINITION / EXECUTION NOT YET VERIFIED

Evidence:
`.github/workflows/core-ci.yml`

The workflow is designed to verify:
- Prisma schema validity;
- PostgreSQL schema creation;
- Python compilation;
- critical DB constraints;
- real 84-room/12-category seed;
- API health;
- availability endpoint smoke test;
- PMS grid smoke test.

No successful workflow run is claimed until GitHub Actions returns execution evidence.

---

# 8. AUTHENTICATION / RBAC

STATUS: UNKNOWN / TODO P0-P1

No working server-side authentication or RBAC implementation is currently established.

Target property roles previously specified include OWNER/MANAGER/MAID/TECHNICIAN and other operational roles, but target role documentation is not implementation evidence.

---

# 9. HOUSEKEEPING / MAINTENANCE

STATUS: PLANNED / NOT IMPLEMENTED

Business workflows are defined at target level, but working task/housekeeping/maintenance modules are not yet established in source.

The current Room operational-state schema includes:
- UNKNOWN;
- CLEAN;
- DIRTY;
- IN_INSPECTION;
- TECH_BLOCK.

This enum alone does not mean the staff workflow is implemented.

---

# 10. COMMUNICATIONS / AI / AUTOMATION

STATUS: NOT IMPLEMENTED IN CURRENT CORE

No working evidence yet for production:
- Instagram integration;
- WhatsApp integration;
- Telegram sales integration;
- unified inbox;
- AI Sales & Concierge tool calling;
- n8n production workflows;
- Whisper staff flow.

These remain future modules over the controlled Core API.

---

# 11. DINING / STORE / QR / ACCESS / BILLIARDS / LED

STATUS: REQUIREMENTS ESTABLISHED / IMPLEMENTATION NOT YET ESTABLISHED

These modules are in the Three Crowns Master Specification but no working implementation is claimed yet.

Beach bar and beach cafe payments are outside the hotel financial ledger in current scope.

---

# 12. NFC

STATUS: DEFERRED

NFC/wristband finance is not a foundation dependency and is intentionally not part of the current Core implementation milestone.

---

# 13. CURRENT P0

Current engineering objective:

`REAL ROOM/RATE DATA -> VERIFIED DATABASE -> VERIFIED AVAILABILITY -> VERIFIED RESERVATION REQUEST -> LIVE PMS GRID -> SITE INTEGRATION`

Immediate blockers before public production use:
- successful CI/runtime verification;
- authentication/RBAC;
- final payment/prepayment amount rule;
- production payment flow;
- cancellation/refund/no-show rules;
- final site-to-Core integration;
- production deployment/security/backup/observability evidence.

---

# 14. TRUTH SUMMARY

IMPLEMENTED IN SOURCE:
- Core data model;
- rate/inventory seed path;
- double-booking DB constraint definition;
- availability API source;
- reservation-request API source;
- PMS grid API source;
- CI definition.

PARTIAL:
- public site V5;
- PMS UI prototype;
- property data baseline.

NOT YET VERIFIED:
- database boot;
- seed execution;
- API runtime;
- endpoint behavior;
- double-booking constraint under runtime concurrency.

NOT YET IMPLEMENTED / UNKNOWN:
- auth/RBAC;
- confirmed payment workflow;
- staff apps;
- communications integrations;
- AI automation;
- dining/store/QR/access/billiards/LED operational modules.
