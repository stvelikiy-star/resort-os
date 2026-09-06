# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Version: 5.0
Date: 2026-09-06
Status: RESORT OS 0.61.0 INTERNAL RC FROZEN / REPOSITORY VERIFIED / EXTERNAL CUTOVER STOP

This runbook defines controlled external deployment and cutover. It is **not evidence that production deployment has happened**.

Canonical implementation state: `knowledge/04_CURRENT_STATE.md`.
Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md`.
Canonical release manifest: `release/current-rc.json`.

**CI VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## 1. Current release boundary

Repository: `stvelikiy-star/resort-os`.
Release: `0.61.0`.
Accepted release source PR: `#116`.
Exact accepted executable head: `e1ac7003abe7f63bd306778edd50a1c63dab6f17`.
Observed tree-equivalent main merge: `8e43893c5fd6ba7f997ab7126d0d1dc5b80729e9`.
Post-merge truth reference: `8e43893c5fd6ba7f997ab7126d0d1dc5b80729e9`.

Evidence:

- exact PR #116 head: **59/59 pull-request workflows SUCCESS, 0 failures**;
- merge used an expected-head SHA guard;
- accepted head and observed main merge are tree-equivalent with **0 changed files**;
- observed main merge: **38 successful product/security/migration/staging workflows**;
- `Release RC Truth CI` and `Launch Acceptance CI` failed closed on the product merge because the previous release manifest still pointed to 0.60.0. The 0.61.0 refreeze is the controlled correction and must restore both gates.

Production source branch is `main`. This does **not** authorize external cutover.

## 2. Deployment topology

Approved V1 topology:

- Caddy HTTPS/WSS edge;
- PostgreSQL 16 private to deployment network;
- FastAPI Resort Core;
- public Next.js site;
- Resort OS Admin/PMS;
- Staff PWA including Kitchen/Dining surfaces;
- Guest OS routes/contracts;
- pinned n8n runtime when automation is enabled;
- persistent PostgreSQL/media/n8n state;
- local backup directory plus verified off-site copy.

Canonical authority:

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`.

NFC acquiring/wallet remains outside active V1 runtime. Real bank/TTLock activation remains external/provider-gated.

## 3. Database release contract

The frozen 0.61.0 committed migration chain contains **22 migrations**:

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
11. `z10_service_point_paid_access`
12. `z11_owner_corrections_20260905`
13. `z12_guest_service_settings_20260905`
14. `z13_housekeeping_charges_20260905`
15. `z14_dining_entitlements_20260905`
16. `z15_group_bookings_20260905`
17. `z16_site_media_20260905`
18. `z17_dining_floor_layout_20260905`
19. `z18_site_media_slots_20260905`
20. `z19_dining_table_status_guard_20260905`
21. `z20_dining_active_table_unique_20260906`
22. `z21_dining_production_snapshots_20260906`

The shared release contract fingerprints **87 critical domain constraints** in `scripts/release_contract.py`.

Production/staging migration mechanism:

```bash
npx prisma migrate deploy
```

Do **not** use `prisma db push` for production migration.

Canonical property baseline:

- 84 rooms;
- 12 categories;
- 48 rate rows;
- rooms 501/502 are owner-approved two-person basement inventory above the laundry.

Real-target production evidence must still capture exact release SHA/image set, backup before migration, migration command/result, exact 22-migration ledger, readiness/smoke result, tested restore path and off-site backup evidence.

## 4. Business authority boundary

`ReservationRequest != Reservation`.

OWNER/MANAGER retain reservation confirmation and payment fact authority.
AI/n8n must not guarantee a Reservation, confirm payment, invent prepayment/payment route, bypass Core pricing/availability or write generic business state directly to PostgreSQL.

Kitchen/Dining amounts do **not** automatically create Hotel `Payment` or silently alter accommodation commercial truth. Guest folio charges are separate from actual Payments.

Growth outbound authority remains `NONE_AUTOMATIC`.

## 5. Hard external production blockers

Physical room intake is closed at the canonical **84-room / 12-category** register. Do not collect the room register again.

Production cutover remains **STOP** while any required external evidence is missing:

1. GitHub branch protection / required checks on `main`;
2. Google Drive launch-control permission remediation;
3. real target room reconciliation;
4. actual Beget host/account non-destructive preflight;
5. verified rollback backup of current live `3korony.com`;
6. isolated external HTTPS/WSS staging;
7. external public-truth probe;
8. real iPhone/Android/desktop/Staff/Kitchen acceptance;
9. provider E2E for every launch-enabled provider;
10. real monitoring/alerting evidence;
11. fresh pre-cutover DB backup and off-site copy;
12. exact DNS rollback capture;
13. explicit final owner cutover approval.

No GitHub CI result by itself authorizes DNS switch or provider activation.

## 6. Fail-closed launch evidence

Template: `release/launch-evidence.example.json`.

Repository gates:

```bash
python scripts/release_rc_truth_guard.py
python scripts/verify_launch_acceptance.py --mode repository
```

Final structural evidence gate:

```bash
python scripts/verify_launch_acceptance.py \
  --mode cutover \
  --manifest /secure/path/launch-evidence.json \
  --release-sha e1ac7003abe7f63bd306778edd50a1c63dab6f17
```

The verifier validates evidence metadata; it does not manufacture external evidence.

## 7. Preserve the current live target first

Before replacing anything on the actual host, require a fail-closed legacy rollback package:

- provider/account identified;
- current DNS/TTL captured;
- live source/web root archived;
- legacy DB dumped if applicable;
- uploads/media archived;
- reverse-proxy/runtime configuration captured;
- checksum/size/timestamp recorded;
- restore target/procedure and rollback owner recorded;
- off-site copy verified.

A public HTML crawl is not a rollback backup.

## 8. External staging sequence

Use an isolated staging hostname; never point the live apex at an unaccepted release.

1. check out `main` and verify `release/current-rc.json`;
2. run `python scripts/release_rc_truth_guard.py`;
3. verify legacy rollback package;
4. run actual-host preflight;
5. provision secrets out-of-band;
6. provision persistent storage;
7. start private PostgreSQL 16;
8. apply all **22** migrations with `prisma migrate deploy`;
9. run canonical room reconciliation dry-run, review exact diff, then safe apply;
10. load only approved factual data;
11. bootstrap authorized users out-of-band;
12. build/deploy exact accepted SHA `e1ac7003abe7f63bd306778edd50a1c63dab6f17`;
13. verify runtime/image revision labels match that SHA;
14. start edge, Core, Public, Admin, Staff/Kitchen and required n8n services;
15. verify HTTPS, WSS, cookies, CORS, persistence and private PostgreSQL;
16. run unified external staging acceptance and retain checksum-backed evidence.

## 9. Acceptance matrix

### Public / Booking

Verify RU/KG/EN rendered truth, Core availability/pricing and `ReservationRequest` creation without automatic Reservation/Payment confirmation.

### PMS / Reception

Verify:

`ReservationRequest -> manager decision/payment fact -> Reservation -> chessboard -> CLEAN check-in -> Stay/RoomAssignment -> optional move/Split Stay -> checkout -> DIRTY -> housekeeping`.

Also verify stale/conflict rejection, realtime, TECH_BLOCK, group booking, finance RBAC and payment idempotency.

### Guest OS / CRM

Verify Room QR, PIN/session, requests, relocation, repeated guest history, checkout session revocation, factual RoomAssignment and manager-controlled offers.

### Kitchen / Dining

Verify Dining Staff access, menu publication, stop-list, table reservations, waiter assignment, visual floor, Stay-linked Dining Sessions, Guest OS orders, server-derived totals, `NEW -> ACCEPTED -> COOKING -> READY -> SERVED`, active-table uniqueness, Dining production snapshot integrity and no automatic Hotel Payment side effects.

### Service Point QR

Verify anonymous point QR routing without Guest/Stay/Reservation/Payment leakage. Real paid-access provider behavior is launch-enabled only after real provider E2E. NFC remains absent from active V1.

### Finance / Owner

Verify factual Payment ledger, folio separation, remaining/overpaid/debt including checked-out debt, owner dashboards and group-booking commercial boundaries.

### Staff / AI / messaging

Verify real MAID/TECHNICIAN/DINING flows and provider authenticity/idempotency only for providers enabled at launch.

## 10. Production preflight and observability

The actual target must pass `scripts/production_preflight.py` with real environment/database evidence.

Require real evidence for health/readiness, HTTP 5xx, container restarts, PostgreSQL disk/storage, backup age/checksum/off-site presence, backup-failure alerts, TLS expiry, AuditLog retention and exact deployed Git SHA/image identity.

## 11. Controlled cutover

Only after all required launch-evidence gates are VERIFIED:

1. reconfirm frozen RC manifest and exact accepted SHA;
2. take fresh pre-cutover backup and verify off-site copy;
3. verify legacy rollback/DNS rollback target;
4. rerun host and production preflight;
5. confirm staging/device/provider evidence;
6. obtain explicit owner approval;
7. deploy exact accepted image set;
8. run readiness/smoke before public switch;
9. switch DNS/routing in a controlled window;
10. rerun Public/Booking/PMS/Guest OS/Staff/Kitchen smoke;
11. monitor errors/database/containers;
12. roll back if acceptance criteria fail.

Database rollback uses the rehearsed backup/restore path; do not improvise destructive reverse SQL.

## 12. Current GO / STOP

### GO — internal release engineering

Resort OS 0.61.0 is the intended refrozen candidate based on accepted executable head `e1ac7003abe7f63bd306778edd50a1c63dab6f17` and tree-equivalent main merge `8e43893c5fd6ba7f997ab7126d0d1dc5b80729e9`.

### STOP — external production declaration

External Beget/production remains **NOT VERIFIED / EXTERNAL CUTOVER STOP** until all governance and real-world launch evidence is collected. Do not claim `PRODUCTION READY`, `LIVE` or `VERIFIED IN PRODUCTION` solely from repository/CI success.
