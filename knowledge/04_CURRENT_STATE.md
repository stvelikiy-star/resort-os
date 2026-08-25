# RESORT OS — CURRENT STATE

Version: 0.4
Date: 2026-08-25
Status: CORE + PMS + CANONICAL SITE BASELINE VERIFIED IN CI
Canonical: YES
Document Type: Evidence-Based Current System State

Critical rule: TARGET ≠ CURRENT. Development verification does not equal production readiness.

---

# 1. CANONICAL REPOSITORY

STATUS: VERIFIED FACT

Repository:
`stvelikiy-star/resort-os`

Canonical implementation now contains:
- PostgreSQL/Prisma Resort Core schema;
- FastAPI Core;
- real Three Crowns room/rate seed;
- Next.js PMS admin application;
- Next.js canonical public site application;
- CI verification;
- recovery evidence and canonical knowledge.

---

# 2. PROPERTY DATA

STATUS: VERIFIED AS SEEDABLE DEVELOPMENT BASELINE

Current CI successfully reconciles and loads:
- 84 rooms;
- 12 room categories;
- current 2026/27 rate input.

Evidence:
- `data-intake/rooms.csv`
- `data-intake/rates.csv`
- `docs/THREE_CROWNS_SOURCE_RECONCILIATION_2026-08-25.md`

Known source caveats remain explicitly qualified rather than guessed.

---

# 3. DATABASE CORE

STATUS: VERIFIED IN DEVELOPMENT CI

Implemented and successfully created on PostgreSQL 16:
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

Critical implemented boundary:
`ReservationRequest != Reservation`.

Critical database constraint successfully applies:
active inventory blocks for the same room cannot overlap by date range.

Zero-price legacy/off-season rate input is not exposed as free sale; it becomes `CONFIRM_REQUIRED`.

NOT YET VERIFIED:
parallel concurrency stress behavior under simultaneous reservation writes.

---

# 4. CORE API

STATUS: VERIFIED DEVELOPMENT BASELINE

Implemented routes:
- `GET /health`
- `GET /api/v1/booking/check-availability`
- `POST /api/v1/booking/requests`
- `GET /api/v1/pms/grid`

Verified runtime behavior includes:
- availability returns successfully against seeded PostgreSQL;
- PMS grid returns successfully against seeded PostgreSQL;
- an unpaid POST creates a request with status `NEW` and explicitly returns `is_reservation = false`.

Current business truth implemented:
WITHOUT CONFIRMED PREPAYMENT THERE IS NO ACTIVE RESERVATION.

The stale legacy website rule about holding an unpaid preliminary booking for two days is not implemented.

---

# 5. PMS ADMIN

STATUS: IMPLEMENTED / VERIFIED BUILD BASELINE

Canonical source:
`apps/admin/`

The admin is no longer based on deterministic mock data.

Implemented current UI:
- live fetch from `/api/v1/pms/grid`;
- real room/category roster from Resort Core;
- 7 / 14 / 31 day windows;
- previous / today / next navigation;
- room/category search;
- room-type filter;
- operational-state filter;
- sticky room and state columns;
- horizontal date scroll;
- physical room state badges;
- reservation / maintenance / manual inventory block rendering;
- current room-state summary.

CI evidence:
- TypeScript check: SUCCESS;
- Next.js production build: SUCCESS.

Authentication/RBAC is still missing, therefore this admin is NOT approved for public production exposure.

---

# 6. CANONICAL PUBLIC SITE

STATUS: IMPLEMENTED / VERIFIED DEVELOPMENT INTEGRATION BASELINE

Canonical source:
`apps/web/`

Recovered V5 remains reference evidence only:
`docs/PUBLIC_SITE_V5_RECOVERY.md`.

The canonical rebuild retains the V5 premium green/gold visual direction but removes the old fake booking behavior.

Implemented current booking experience:
- guest chooses check-in/check-out;
- guest chooses adults/children;
- site calls real `GET /api/v1/booking/check-availability`;
- site shows real room categories returned by Core;
- exact period price is read from Core when sellable;
- guest selects a room category;
- guest enters name / phone / optional email;
- site POSTs to `POST /api/v1/booking/requests`;
- UI explicitly states that the request is not a reservation until confirmed prepayment.

CI evidence:
- public-site TypeScript check: SUCCESS;
- public-site production build: SUCCESS;
- public-site production-mode startup: SUCCESS;
- homepage HTTP smoke: SUCCESS;
- public-site `/core` proxy to availability: SUCCESS.

Current media limitation:
several images are temporary hotlinks inherited from the V5 visual skeleton. They must be replaced with owned media before final production cutover.

The existing V5 Vercel deployment is NOT the canonical source application and no DNS cutover has been performed.

---

# 7. TEST EVIDENCE

Initial Core verification:
- Run `32834872750`
- Job `97761394147`
- conclusion: SUCCESS

PMS + site integration verification:
- Run `32835695344`
- Job `97763917713`
- commit `7f86165aaebaf38bcf68af415c0f9a3a8311678a`
- conclusion: SUCCESS

Full evidence:
- `docs/CORE_IMPLEMENTATION_EVIDENCE_2026-08-25.md`
- `docs/PMS_SITE_INTEGRATION_EVIDENCE_2026-08-25.md`

---

# 8. AUTHENTICATION / RBAC

STATUS: NOT IMPLEMENTED

This is now the immediate P0/P1 engineering blocker before admin deployment.

No server-side login, staff session or permission enforcement is yet verified.

---

# 9. PAYMENT / RESERVATION CONVERSION

STATUS: PARTIAL DOMAIN MODEL / TRANSACTION TODO

Payment entity exists.

Not yet implemented:
- payment provider/acquiring;
- final prepayment amount rule;
- payment verification;
- atomic `paid request -> guaranteed Reservation -> inventory block` transaction;
- refund/cancellation/no-show rules.

No production payment activation has occurred.

---

# 10. HOUSEKEEPING / MAINTENANCE

STATUS: REQUIREMENTS ESTABLISHED / IMPLEMENTATION TODO

Room physical states exist in schema:
- UNKNOWN;
- CLEAN;
- DIRTY;
- IN_INSPECTION;
- TECH_BLOCK.

Task workflows, assignments, SLA, photos and staff mobile UI are not yet implemented.

---

# 11. COMMUNICATIONS / AI / AUTOMATION

STATUS: NOT IMPLEMENTED

No verified working production integration yet for:
- Instagram;
- WhatsApp;
- Telegram sales;
- unified inbox;
- response control;
- AI Sales & Concierge tools;
- n8n production orchestration;
- Whisper staff flow.

These remain downstream of secure Core permissions.

---

# 12. DINING / STORE / QR / ACCESS / BILLIARDS / LED

STATUS: REQUIREMENTS ESTABLISHED / IMPLEMENTATION TODO

These remain confirmed Three Crowns scope modules.

Beach bar and beach cafe customer payments remain outside the hotel financial ledger.

---

# 13. NFC

STATUS: DEFERRED

NFC financial ecosystem is explicitly not a V1 foundation dependency.

---

# 14. CURRENT ENGINEERING ORDER

Verified now:

`REAL PROPERTY DATA -> POSTGRESQL -> CORE API -> PMS ADMIN BUILD`

and:

`PUBLIC SITE -> REAL AVAILABILITY -> RESERVATION REQUEST`

Next engineering sequence:

1. internal authentication / RBAC with no external identity service dependency;
2. protect PMS/admin Core routes;
3. implement manager booking workspace and request queue;
4. finalize current prepayment rule/provider and implement atomic paid-request conversion;
5. add real reservation bars/actions into PMS;
6. housekeeping + maintenance task engine;
7. communications/unified inbox + response-control;
8. AI tools over authorized Core;
9. dining/store/QR/access/billiards/LED.
