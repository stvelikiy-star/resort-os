# THREE CROWNS — DEMO / ACCEPTANCE RUNBOOK

Date: 2026-08-26
Scope: Resort OS V1 delivery/demo
Status: DEVELOPMENT RELEASE CANDIDATE

This document is a presentation and acceptance checklist, not evidence that production cutover has already happened.

## 1. Product boundary to present

Show one connected system:

`PUBLIC SITE / PMS / STAFF / n8n CONTRACT -> RESORT CORE -> POSTGRESQL`

Core owns hotel truth. Do not present n8n, ManyChat or API Green as the hotel database.

Client-channel architecture:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- website -> Resort Core directly;
- n8n qualifies a hot client and hands the request to management.

Manager owns prepayment decision/collection. Resort OS only records manager-confirmed internal facts.

NFC is deferred and must not be presented as a required V1 feature.

## 2. What the demo must prove

The demo is successful when the audience can see this continuous scenario:

1. Website shows the resort and 12 room categories.
2. Guest chooses dates and guest count.
3. Website receives live availability/pricing from Resort Core.
4. Guest submits a ReservationRequest.
5. PMS receives the request.
6. Manager selects/quotes the category and records the payment fact they actually accepted.
7. Core atomically creates Reservation + InventoryBlock + Payment.
8. Reservation appears in the chessboard.
9. Manager moves/resizes the reservation with preview before commit.
10. Conflict attempt does not corrupt the original reservation.
11. Manager checks the guest in only to a CLEAN room.
12. In-stay relocation preserves already-lived room history.
13. Immediate relocation marks the vacated room DIRTY and creates/reuses housekeeping.
14. Checkout releases future inventory and marks the actually vacated room DIRTY.
15. Housekeeping can move through inspection to CLEAN.
16. Website availability reflects the changed inventory without a separate synchronization process.

## 3. Local startup

Requirements:
- Docker;
- Node.js 22+;
- Python 3.12+.

From repository root:

```bash
docker compose up -d postgres
cp .env.example .env
set -a && source .env && set +a
```

Development schema:

```bash
cd packages/database
npm install
npx prisma validate
npx prisma db push
cd ../..
```

Core dependencies/data:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r services/api/requirements.txt
python scripts/apply_core_constraints.py
python scripts/seed_from_intake.py
python scripts/bootstrap_owner.py
```

Start Core:

```bash
python -m uvicorn app.app_entry:app --app-dir services/api --host 127.0.0.1 --port 8000
```

Start apps in separate terminals:

```bash
cd apps/web && npm install && npm run dev
```

```bash
cd apps/admin && npm install && npm run dev
```

```bash
cd apps/staff && npm install && npm run dev
```

Expected local endpoints:
- website: http://127.0.0.1:3000
- PMS: http://127.0.0.1:3001
- staff PWA: http://127.0.0.1:3002
- Core: http://127.0.0.1:8000

## 4. Optional synthetic presentation data

Only in development/staging:

```bash
python scripts/prepare_demo_showcase.py
```

The script:
- aborts when `APP_ENV=production`;
- creates records through real Resort Core APIs;
- marks all synthetic guests/requests/payments as `DEMO_SHOWCASE` / `DEMO_MANUAL`;
- does not bypass availability, quote, booking or inventory constraints.

Never describe demo payment records as real money.

## 5. PMS demo sequence

### A. Main dashboard

Show:
- room condition snapshot;
- arrivals/departures;
- requests;
- housekeeping/maintenance visibility;
- manager-recorded internal payment visibility.

Do not describe internal finance as accounting profit or tax reporting.

### B. Chessboard V2

Show:
- 7 / 14 / 31 day windows;
- room/category/state search/filtering;
- quick modes: arrivals today, departures today, in-house, free today;
- room state badges;
- one continuous reservation bar per room segment;
- click room -> room detail;
- click booking -> booking/stay workspace.

### C. Move a future booking

Drag a simple GUARANTEED booking to another room/date.

Expected behavior:
- browser does not silently commit;
- server preview opens;
- conflicts are visible;
- stored booking value is not silently changed;
- manager confirms explicitly;
- after commit, old active InventoryBlock is replaced atomically;
- website inventory truth changes immediately from the same Core data.

### D. Resize dates

Drag the outer left/right reservation edge or use the date editor.

Expected behavior:
- server preview first;
- Core shows deterministic tariff suggestion/delta;
- stored commercial total does not silently change;
- invalid/conflicting schedule does not partially save.

### E. Relocate checked-in guest

Use `Переселить с даты`.

Expected behavior:
- already-lived room history cannot be rewritten;
- for immediate relocation, target room must be CLEAN;
- old room becomes DIRTY;
- housekeeping task is created/reused inside the same transaction;
- one Reservation remains one Reservation with multiple contiguous room segments.

### F. Check-in / check-out

Check-in expectations:
- Reservation must be GUARANTEED;
- local hotel date must be inside its room schedule;
- assigned room must be CLEAN.

Checkout expectations:
- Reservation must be CHECKED_IN;
- the currently/finally occupied room is selected schedule-aware;
- early checkout releases future inventory;
- stored commercial total is not silently recalculated;
- vacated room becomes DIRTY;
- housekeeping is created/reused.

## 6. Booking/guest workspace

From a booking show:
- guest/contact;
- current room;
- complete room-move schedule;
- stay dates/status;
- internal manager-recorded payments;
- outstanding balance derived from stored facts;
- active room tasks;
- audit history.

Record an additional internal payment only as a fact already accepted by the manager.

Expected idempotency:
- retry with the same idempotency key on the same reservation replays safely;
- the same key on another reservation must return `409 IDEMPOTENCY_CONFLICT`.

## 7. Staff operations

Housekeeping flow:

`OPEN -> IN_PROGRESS -> IN_INSPECTION -> DONE`

Operational room flow:

`DIRTY -> IN_INSPECTION -> CLEAN`

Maintenance:
- room-linked maintenance can set `TECH_BLOCK`;
- technician sees/claims own allowed tasks;
- manager sees assignment/history.

Do not invent a mandatory housekeeping checklist that has not been approved.

## 8. Website demo

Show:
- premium hero;
- own beach / 150 m pier / SPA / massage / 15×8 outdoor pool;
- 12 room-category structure;
- booking search;
- live Core price and availability;
- tariff-derived meal statement;
- no hard-coded automatic prepayment percentage;
- request form;
- clear statement that request is not yet a confirmed reservation;
- mobile sticky booking CTA.

Current presentation limitation:
- own final Three Crowns photo package still needs to replace temporary media sources before production visual acceptance.

## 9. n8n boundary to demonstrate/explain

n8n is allowed to:
- read hotel facts;
- read deterministic availability/pricing;
- create/read ReservationRequest;
- read reservation/payment status facts that exist in Core;
- hand hot qualified leads to management.

n8n must not:
- write PostgreSQL directly;
- create GUARANTEED Reservation directly;
- confirm/collect payment;
- decide prepayment amount/method;
- check-in/check-out/refund;
- invent price, availability or policy.

## 10. Delivery blockers / items not to misrepresent

Do not claim production-ready until all gates are satisfied:
- own final photography;
- real Prisma migration baseline;
- proven current-schema backup -> clean restore;
- current-main build/E2E evidence;
- staging acceptance;
- monitoring/alerts;
- rollback rehearsal;
- DNS/cutover owner gate.

Current GitHub Actions infrastructure symptom:
- workflow runs are created;
- jobs complete almost immediately as failure;
- job `steps` are null;
- job logs are unavailable;
- this is not valid evidence of a code-test failure because no workflow step executed.

For delivery, run the local release check and retain its output as evidence while the GitHub runner issue is unresolved.

## 11. Final acceptance wording

Use precise status language:
- `VERIFIED` only when there is executed evidence;
- `IMPLEMENTED / LOCALLY VERIFIED` when local release check passes;
- `IMPLEMENTED / NOT CI-VERIFIED` when GitHub Actions did not execute steps;
- `NOT PRODUCTION READY` until production gates are complete.
