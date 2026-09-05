# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Version: 3.2
Date: 2026-09-05
Status: RELEASE-CANDIDATE HANDOFF / CI-LOCAL VERIFICATION REQUIRED / EXTERNAL CUTOVER STOP

This runbook defines controlled external deployment and cutover. It is **not evidence that production deployment has happened**.

Canonical implementation state: `knowledge/04_CURRENT_STATE.md`.
Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md`.
Canonical release manifest: `release/current-rc.json`.

**CI VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

---

## 1. Release authority

Repository: `stvelikiy-star/resort-os`.
Integration branch: `integration/site-pms-cms-20260827`.

Only an exact integration SHA whose full applicable regression and release gates are green may be frozen as the internal RC. Historical Vercel previews and stale `main` are not release authority.

The merge tree must be compared against the exact tested PR head. A non-empty tested-head -> merge diff invalidates the evidence and requires another regression cycle.

---

## 2. Deployment topology

Approved V1 topology:

- Caddy HTTPS/WSS edge;
- PostgreSQL 16 private to deployment network;
- FastAPI Resort Core;
- public Next.js site;
- Resort OS admin/PMS;
- staff PWA, including Kitchen Admin;
- pinned n8n runtime when automation is enabled;
- persistent PostgreSQL/media/n8n state;
- local backup directory plus verified off-site copy.

Canonical authority:

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`.

NFC acquiring/wallet remains outside active V1 runtime.

---

## 3. Database release contract

Committed migration chain:

1. `0_init`
2. `1_site_content`
3. `2_guest_service_tasks`
4. `3_owner_analytics_snapshots`
5. `4_guest_engagements`
6. `5_guest_os_core`
7. `6_service_point_qr_operations`
8. `7_kitchen_operations`
9. `8_dining_service_control`
10. `9_guest_offer_campaigns`

Production/staging migration mechanism:

```bash
npx prisma migrate deploy
```

Do **not** use `prisma db push` for production migration.

The shared release contract maintains 37 critical hotel/payment/operations domain constraints. Kitchen/Dining/Guest Offer migration/domain gates additionally verify menu/table/order/item constraints, daily publication, table reservation, waiter assignment, offer targeting/actions/events and the unique GuestTask -> KitchenOrder link.

Production evidence must capture:

- exact release SHA/image set;
- backup before migration;
- migration command/result;
- exact ten-migration ledger;
- readiness/smoke result;
- tested restore path.

---

## 4. Business authority boundary

`ReservationRequest != Reservation`.

OWNER/MANAGER retain reservation confirmation and payment fact authority.

AI/n8n must not guarantee a Reservation, confirm payment, invent a fixed prepayment percentage/payment route, bypass Core pricing/availability or write generic business state directly to PostgreSQL.

Kitchen is also Core-backed. `KitchenOrder.totalKgs` is an operational amount and does **not** automatically create `Payment` or change `Reservation.totalKgs`.

Growth outbound authority remains `NONE_AUTOMATIC`.

---

## 5. Hard external production blockers

Physical room import gate #38 is already closed at the canonical 84-room / 12-category register. Do not collect the room register again.

Production cutover remains **STOP** while any required external evidence is missing:

1. real target room reconciliation against the canonical register;
2. actual Beget host/account non-destructive preflight;
3. verified rollback backup of the currently live legacy target;
4. isolated external HTTPS/WSS staging;
5. external public-truth probe;
6. real iPhone/Android/desktop/Telegram/staff/Kitchen acceptance;
7. provider E2E for every provider enabled at launch;
8. real monitoring/alerting evidence;
9. fresh pre-cutover database backup and off-site copy;
10. exact DNS rollback capture;
11. explicit final owner cutover approval.

No GitHub CI result by itself authorizes production DNS switch or provider activation.

---

## 6. Fail-closed launch evidence

Template: `release/launch-evidence.example.json`.

Repository gate:

```bash
python scripts/verify_launch_acceptance.py --mode repository
```

Final structural evidence gate:

```bash
python scripts/verify_launch_acceptance.py \
  --mode cutover \
  --manifest /secure/path/launch-evidence.json \
  --release-sha <exact-accepted-release-sha>
```

The verifier validates evidence metadata. It does not manufacture external evidence.

---

## 7. Preserve the current live target first

Before replacing anything on the actual host, require the fail-closed legacy rollback package:

- provider/account identified;
- current DNS captured;
- live source/web root archived;
- legacy DB dumped if applicable;
- uploads/media archived;
- reverse-proxy/runtime configuration captured;
- checksum/size/timestamp recorded;
- restore target/procedure and rollback owner recorded;
- off-site copy verified.

A public HTML crawl is not a rollback backup.

---

## 8. External staging sequence

Use an isolated staging hostname; never point the live apex at an unaccepted release.

1. verify legacy rollback package;
2. run actual-host preflight;
3. provision secrets out-of-band;
4. provision persistent storage;
5. start private PostgreSQL;
6. apply all ten committed migrations;
7. run canonical room importer dry-run against staging, review the exact diff, then safely reconcile;
8. load only approved factual data;
9. bootstrap authorized users out-of-band;
10. build/deploy the exact accepted release SHA;
11. verify image revision labels match that SHA;
12. start edge, Core, public, Admin, Staff/Kitchen and required n8n services;
13. verify HTTPS, WSS, cookies, CORS, persistence and private PostgreSQL;
14. run the unified external staging acceptance runner and retain its checksum-backed evidence manifest.

---

## 9. Acceptance matrix

### Public / Booking

Verify RU/KG/EN rendered truth, availability/pricing through Core and `ReservationRequest` creation without automatic Reservation/Payment confirmation.

### PMS / Reception

Verify:

`ReservationRequest -> manager decision/payment fact -> Reservation -> chessboard -> CLEAN check-in -> Stay/RoomAssignment -> optional move/Split Stay -> checkout -> DIRTY -> housekeeping`.

Also verify stale/conflict rejection, realtime, TECH_BLOCK and RBAC.

### Guest OS / CRM

Verify Room QR, PIN/session, requests, relocation, repeated guest history, checkout session revocation and factual room assignment. For the in-stay Marketplace, verify only manager-configured active offers are surfaced and that offer actions do not create payment/commercial truth automatically.

### Kitchen / Dining

Verify:

- Dining Staff opens Kitchen Admin;
- factual tables can be created/edited without code changes;
- draft menu can be edited/disabled/repriced;
- current hotel-local day menu is explicitly published by meal type before Guest OS can order it;
- stop-list and restore affect guest availability fail-closed;
- table reservations enforce capacity/time conflicts;
- waiter assignment and READY -> SERVED handoff work;
- table order and room/Stay order use server-derived totals;
- Guest OS order reaches Kitchen;
- `NEW -> ACCEPTED -> COOKING -> READY -> SERVED` works;
- successful check-in creates exactly one Dining arrival card;
- repair sync does not duplicate it;
- Kitchen order does not create Hotel `Payment` or alter `Reservation.totalKgs`;
- completed table orders free the table when no other active order remains.

### Service Point QR

Verify anonymous point QR routing without Guest/Stay/Reservation/Payment leakage. NFC must remain absent.

### Finance / Owner

Verify factual Payment ledger, remaining/overpaid/debt including checked-out debt, owner dashboards and no automatic Kitchen posting into accommodation finance.

### Staff / AI / messaging

Verify real mobile MAID/TECHNICIAN/DINING flows and provider authenticity/idempotency for any messaging provider actually enabled at launch.

---

## 10. Production preflight and observability

The actual target must pass `scripts/production_preflight.py` with real target environment/database evidence.

Before cutover require real evidence for:

- health/readiness monitoring;
- HTTP 5xx visibility;
- container restart visibility;
- PostgreSQL disk/storage monitoring;
- backup age/checksum/off-site presence;
- backup-failure alerting;
- TLS expiry monitoring;
- AuditLog retention;
- exact deployed Git SHA/image identity.

---

## 11. Controlled cutover

Only after all required launch-evidence gates are VERIFIED:

1. freeze exact accepted SHA;
2. take fresh pre-cutover backup and verify off-site copy;
3. verify legacy rollback/DNS rollback target;
4. rerun host and production preflight;
5. confirm staging/device/provider evidence;
6. obtain explicit owner approval;
7. deploy exact accepted image set;
8. run readiness/smoke before public switch;
9. switch DNS/routing in a controlled window;
10. rerun external public/booking/PMS/Guest OS/Staff/Kitchen smoke;
11. monitor errors/database/containers;
12. roll back if acceptance criteria fail.

Database rollback uses the rehearsed backup/restore path; do not improvise destructive reverse SQL.

---

## 12. Current GO / STOP

### GO — internal release engineering

The repository has a mature Core/PMS/Guest OS/Finance/Staff/Kitchen stack and fail-closed release tooling. The final internal RC is valid only after the current exact-head full regression is green and the RC truth manifest is refrozen to the resulting integration SHA.

### STOP — external production declaration

External Beget/production remains **NOT VERIFIED** until the real evidence in section 5 is collected. Do not claim `PRODUCTION READY`, `LIVE` or `VERIFIED IN PRODUCTION` solely from repository/CI success.
