# RESORT OS — CURRENT STATE

Version: 0.3
Date: 2026-08-25
Status: CORE BASELINE VERIFIED IN CI
Canonical: YES
Document Type: Evidence-Based Current System State

Critical rule: TARGET ≠ CURRENT. Production readiness is not implied by development CI verification.

---

# 1. CANONICAL REPOSITORY

STATUS: VERIFIED FACT

Repository:
`stvelikiy-star/resort-os`

Current repository contains canonical knowledge, recovery artifacts, real Three Crowns intake data and the first working Resort Core implementation.

---

# 2. THREE CROWNS PROPERTY DATA

STATUS: VERIFIED AS SEEDABLE DEVELOPMENT BASELINE

Evidence:
- `data-intake/rooms.csv`
- `data-intake/rates.csv`
- `data-intake/reservation_rules.md`
- `docs/THREE_CROWNS_SOURCE_RECONCILIATION_2026-08-25.md`
- `docs/CORE_IMPLEMENTATION_EVIDENCE_2026-08-25.md`

CI successfully seeded:
- 84 room rows;
- 12 room categories;
- current 2026/27 rate input.

Known source caveats remain explicitly documented and are not silently converted to facts.

---

# 3. DATABASE CORE

STATUS: VERIFIED IN DEVELOPMENT CI

Evidence:
- `packages/database/prisma/schema.prisma`
- `packages/database/sql/001_core_constraints.sql`
- CI run `32834872750`, conclusion `success`.

Verified in PostgreSQL 16 CI:
- Prisma schema validation;
- schema creation;
- custom constraint application;
- evidence-backed seed execution.

Implemented core entities:
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

Verified design boundary:
`ReservationRequest ≠ Reservation`.

Current business rule encoded in implementation intent:
An unpaid request is not an active reservation.

Critical database definition exists and applies successfully:
active inventory blocks for one room cannot overlap by date range.

NOT YET VERIFIED:
parallel concurrency stress/race behavior beyond successful constraint installation.

---

# 4. CORE API

STATUS: VERIFIED DEVELOPMENT SMOKE BASELINE

Evidence:
- `services/api/app/main.py`
- `services/api/app/db.py`
- CI run `32834872750`.

Verified runtime routes:
- `GET /health`
- `GET /api/v1/booking/check-availability`
- `POST /api/v1/booking/requests` exists in source and compiles; dedicated POST behavioral assertion is still TODO.
- `GET /api/v1/pms/grid`

CI successfully started FastAPI against the seeded PostgreSQL database and received successful HTTP responses from health, availability and PMS grid endpoints.

The API is NOT approved for open production exposure because authentication/RBAC is not implemented yet.

---

# 5. PRICING

STATUS: PARTIAL / DEVELOPMENT BASELINE VERIFIED

Seasonal rate data loads successfully and availability can read pricing from the database.

Safety behavior in seed:
legacy/off-season rate rows with `0 KGS` become `CONFIRM_REQUIRED`; they are not interpreted as free-sale prices.

NOT YET VERIFIED:
- exhaustive price assertions at every seasonal boundary;
- manual discounts;
- extra-person price engine;
- final production prepayment amount.

---

# 6. PUBLIC WEBSITE

STATUS: PARTIAL / VISUAL PROTOTYPE

A V5 public-site skeleton exists on Vercel from prior project work.

Known limitation from audit:
its previous booking UI did not use the now-verified Resort Core API.

The public-site source is not yet established as a canonical application tree inside this repository.

Next required implementation:
connect the existing visual booking flow to Core availability and ReservationRequest APIs after the site source is canonicalized.

---

# 7. PMS UI

STATUS: PARTIAL

Recovered evidence:
`recovery-artifacts/pms-grid/PMSGrid.tsx`

That component is a UI prototype using mock data and is not production PMS.

The backend endpoint it conceptually required now exists and has passed smoke verification:
`GET /api/v1/pms/grid`.

Next required implementation:
create canonical admin application and replace mock generation with live API data.

---

# 8. AUTHENTICATION / RBAC

STATUS: NOT IMPLEMENTED

No verified server-side login/RBAC exists yet.

This is a blocker for any public/admin production deployment.

---

# 9. HOUSEKEEPING / MAINTENANCE

STATUS: BUSINESS REQUIREMENTS ESTABLISHED / IMPLEMENTATION TODO

Room operational-state enum exists:
- UNKNOWN;
- CLEAN;
- DIRTY;
- IN_INSPECTION;
- TECH_BLOCK.

This does not yet constitute a staff task workflow.

---

# 10. COMMUNICATIONS / AI / AUTOMATION

STATUS: NOT IMPLEMENTED IN CURRENT CORE

No production evidence yet for:
- Instagram;
- WhatsApp;
- Telegram sales integration;
- unified inbox;
- n8n workflows;
- AI Sales & Concierge tool calling;
- Whisper staff workflow.

These remain downstream modules over the Core API.

---

# 11. DINING / STORE / QR / ACCESS / BILLIARDS / LED

STATUS: REQUIREMENTS ESTABLISHED / IMPLEMENTATION TODO

Beach bar and beach cafe payments remain outside the hotel financial ledger in current scope.

---

# 12. NFC

STATUS: DEFERRED

NFC finance is not a dependency for current V1.

---

# 13. TEST EVIDENCE

Latest verified baseline:

Workflow: `Resort Core CI`
Run: `32834872750`
Job: `97761394147`
Commit verified: `1bc6531a55c5522ad65d60e6a5254988ece9a1cb`
Conclusion: `success`

Successful steps include PostgreSQL boot, Prisma validation/schema creation, Python compilation, critical DB constraints, 84-room seed, API start, health smoke, availability smoke and PMS grid smoke.

Full detail:
`docs/CORE_IMPLEMENTATION_EVIDENCE_2026-08-25.md`.

---

# 14. CURRENT ENGINEERING ORDER

1. Canonical live PMS admin UI over `/api/v1/pms/grid`.
2. Add authentication/RBAC before external/admin production exposure.
3. Canonicalize existing V5 site source.
4. Connect site booking UI to availability + ReservationRequest.
5. Implement paid-request -> guaranteed Reservation transaction after final prepayment rules/provider are confirmed.
6. Add housekeeping and maintenance task engine.
7. Add communications/unified inbox and AI tools.
8. Add dining/store/QR/access/billiards/LED modules.

Current verified foundation:

`REAL DATA -> POSTGRESQL -> AVAILABILITY -> PMS GRID API`

Next target:

`LIVE PMS UI -> AUTH -> SITE INTEGRATION`.
