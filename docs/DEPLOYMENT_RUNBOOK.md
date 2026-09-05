# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Version: 4.0
Date: 2026-09-05
Status: RESORT OS 0.60.0 MERGED / REPOSITORY VERIFIED / EXTERNAL CUTOVER STOP

This runbook defines controlled external deployment and cutover. It is **not evidence that production deployment has happened**.

Canonical implementation state: `knowledge/04_CURRENT_STATE.md`.
Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md`.
Canonical frozen external-production manifest: `release/current-rc.json`.

**CI VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

---

## 1. Current release boundary

Repository: `stvelikiy-star/resort-os`.

Release PR: `#112`.
Exact tested PR head: `c8db446d367284465853850136c31274c8e39370`.
Merged `main` commit: `e5efe074abb4a277c032b017ae5fb02c5d0d5039`.

Evidence:

- PR head: **46/46 checks SUCCESS, 0 failures**;
- merge used an expected-head SHA guard;
- resulting `main`: **35/35 triggered checks SUCCESS, 0 failures**.

Repository release engineering is green. External deployment remains a separate gate.

The frozen `release/current-rc.json` has not yet been deliberately refrozen to this new merged boundary. Do not treat the old manifest as proof that 0.60 has been externally accepted.

---

## 2. Deployment topology

Approved V1 topology:

- Caddy HTTPS/WSS edge;
- PostgreSQL 16 private to deployment network;
- FastAPI Resort Core;
- public Next.js site;
- Resort OS Admin/PMS;
- Staff PWA including Kitchen/Dining staff surfaces;
- Guest OS routes/contracts served through the product stack;
- pinned n8n runtime when automation is enabled;
- persistent PostgreSQL/media/n8n state;
- local backup directory plus verified off-site copy.

Canonical authority:

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`.

NFC acquiring/wallet remains outside active V1 runtime.

---

## 3. Database release contract

The current committed migration chain contains **20 migrations**:

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

The shared release contract currently fingerprints **81 critical domain constraints** in `scripts/release_contract.py`.

Production/staging migration mechanism:

```bash
npx prisma migrate deploy
```

Do **not** use `prisma db push` for production migration.

Production-like acceptance has already proven on clean PostgreSQL 16 that:

- all 20 migrations apply successfully;
- migration status is current;
- the canonical property seed produces 84 rooms / 12 categories / 48 rate rows;
- release smoke/E2E and backup/restore contracts pass on the tested release tree.

Production evidence must still capture the real target result:

- exact release SHA/image set;
- backup before migration;
- migration command/result;
- exact 20-migration ledger;
- readiness/smoke result;
- tested restore path;
- off-site backup evidence.

---

## 4. Business authority boundary

`ReservationRequest != Reservation`.

OWNER/MANAGER retain reservation confirmation and payment fact authority.

AI/n8n must not guarantee a Reservation, confirm payment, invent a fixed prepayment percentage/payment route, bypass Core pricing/availability or write generic business state directly to PostgreSQL.

Kitchen/Dining is Core-backed. Kitchen/Dining operational amounts do **not** automatically create Hotel `Payment` or silently alter accommodation commercial truth.

Guest folio charges are separate from actual Payments.

Growth outbound authority remains `NONE_AUTOMATIC`.

---

## 5. Hard external production blockers

Physical room intake is already closed at the canonical **84-room / 12-category** register. Do not collect the room register again.

Production cutover remains **STOP** while any required external evidence is missing:

1. GitHub branch protection / required-check enforcement for the actual production source branch;
2. Google Drive launch-control permission remediation and verification;
3. real target room reconciliation against the canonical register;
4. actual Beget host/account non-destructive preflight;
5. verified rollback backup of the currently live legacy target;
6. isolated external HTTPS/WSS staging;
7. external public-truth probe;
8. real iPhone/Android/desktop/Telegram/Staff/Kitchen acceptance;
9. provider E2E for every provider enabled at launch;
10. real monitoring/alerting evidence;
11. fresh pre-cutover database backup and off-site copy;
12. exact DNS rollback capture;
13. deliberate RC refreeze to the exact accepted release boundary;
14. explicit final owner cutover approval.

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
5. start private PostgreSQL 16;
6. apply all 20 committed migrations with `prisma migrate deploy`;
7. run canonical room reconciliation dry-run against staging, review the exact diff, then safely reconcile;
8. load only approved factual data;
9. bootstrap authorized users out-of-band;
10. build/deploy the exact accepted release SHA;
11. verify runtime/image revision labels match that SHA;
12. start edge, Core, public, Admin, Staff/Kitchen and required n8n services;
13. verify HTTPS, WSS, cookies, CORS, persistence and private PostgreSQL;
14. run unified external staging acceptance and retain checksum-backed evidence.

---

## 9. Acceptance matrix

### Public / Booking

Verify RU/KG/EN rendered truth, availability/pricing through Core and `ReservationRequest` creation without automatic Reservation/Payment confirmation.

### PMS / Reception

Verify:

`ReservationRequest -> manager decision/payment fact -> Reservation -> chessboard -> CLEAN check-in -> Stay/RoomAssignment -> optional move/Split Stay -> checkout -> DIRTY -> housekeeping`.

Also verify stale/conflict rejection, realtime, TECH_BLOCK, group booking flows and RBAC.

### Guest OS / CRM

Verify Room QR, PIN/session, requests, relocation, repeated guest history, checkout session revocation, factual room assignment and manager-controlled offers without automatic payment/commercial truth.

### Kitchen / Dining

Verify:

- Dining Staff access;
- factual table creation/editing;
- visual floor layout;
- draft menu editing/disable/reprice;
- hotel-local daily publication by meal type;
- stop-list / restore;
- table reservation capacity/time-conflict protection;
- waiter assignment;
- Stay-linked Dining Sessions;
- Guest OS order reaches Kitchen;
- server-derived totals;
- `NEW -> ACCEPTED -> COOKING -> READY -> SERVED`;
- successful check-in Dining arrival linkage;
- repair sync does not duplicate arrival data;
- completed table/session state invariants;
- no automatic Hotel Payment from Kitchen/Dining operations.

### Service Point QR

Verify anonymous point QR routing without Guest/Stay/Reservation/Payment leakage. NFC must remain absent from active V1 runtime.

### Finance / Owner

Verify factual Payment ledger, guest folio separation, remaining/overpaid/debt including checked-out debt, owner dashboards and group-booking commercial boundaries.

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
2. deliberately refreeze the external-production RC manifest to the accepted boundary;
3. take fresh pre-cutover backup and verify off-site copy;
4. verify legacy rollback/DNS rollback target;
5. rerun host and production preflight;
6. confirm staging/device/provider evidence;
7. obtain explicit owner approval;
8. deploy exact accepted image set;
9. run readiness/smoke before public switch;
10. switch DNS/routing in a controlled window;
11. rerun external public/booking/PMS/Guest OS/Staff/Kitchen smoke;
12. monitor errors/database/containers;
13. roll back if acceptance criteria fail.

Database rollback uses the rehearsed backup/restore path; do not improvise destructive reverse SQL.

---

## 12. Current GO / STOP

### GO — internal release engineering

Resort OS 0.60.0 is merged to `main` at `e5efe074abb4a277c032b017ae5fb02c5d0d5039`. The exact PR head passed 46/46 checks and the merged main commit passed 35/35 triggered checks.

### STOP — external production declaration

External Beget/production remains **NOT VERIFIED** until all governance and real-world launch evidence is collected. Do not claim `PRODUCTION READY`, `LIVE` or `VERIFIED IN PRODUCTION` solely from repository/CI success.
