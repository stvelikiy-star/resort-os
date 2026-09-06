# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Version: 5.0
Date: 2026-09-06
Status: RESORT OS 0.61.0 INTERNAL RC FROZEN / EXTERNAL CUTOVER STOP
Canonical: YES

This document separates repository/CI evidence from real external staging/production evidence. It must never be used to imply that Resort OS is already live on the hotel infrastructure.

## 1. Frozen release boundary

Repository: `stvelikiy-star/resort-os`.
Release: `0.61.0`.
Accepted release source PR: `#116` — `audit/full-project-fixes-20260905 -> main`.
Accepted executable head: `e1ac7003abe7f63bd306778edd50a1c63dab6f17`.
Observed tree-equivalent main merge: `8e43893c5fd6ba7f997ab7126d0d1dc5b80729e9`.
Post-merge truth reference: `8e43893c5fd6ba7f997ab7126d0d1dc5b80729e9`.

Evidence:

- exact PR #116 head: **59/59 pull-request workflows SUCCESS, 0 failures**;
- accepted head -> observed main merge: **0 changed files**;
- observed main merge: **38 successful product/security/migration/staging workflows**;
- `Release RC Truth CI` and `Launch Acceptance CI` failed closed on the product merge only because the previous frozen manifest still described 0.60.0. This 0.61.0 release-hygiene refreeze must restore those gates without disabling or bypassing them.

The machine-readable release boundary is `release/current-rc.json`, guarded by `scripts/release_rc_truth_guard.py`.
Production source branch is `main`. Repository evidence is not external staging evidence and is not production evidence.

## 2. Product authority boundary

Canonical architecture:

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`.

OWNER/MANAGER retain reservation and payment authority. AI/n8n may qualify leads and create bounded requests/messages but may not:

- confirm payment;
- guarantee a Reservation;
- invent a fixed prepayment percentage/payment route;
- check a guest in/out;
- refund money;
- mutate hotel finance directly;
- bypass Core availability/pricing;
- write generic business truth directly to PostgreSQL.

Growth outbound authority remains `NONE_AUTOMATIC`.
NFC acquiring/wallet remains deferred outside active V1.
Real bank/TTLock provider activation remains fail-closed until real contracts/credentials/hardware E2E are verified.

## 3. Canonical database release contract

The frozen 0.61.0 release contains **22 committed migrations**:

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

The shared release contract fingerprints **87 critical domain constraints** through `scripts/release_contract.py`.

External staging and production migration mechanism:

```bash
cd packages/database
npm ci
npx prisma validate
npx prisma migrate deploy
cd ../..
```

Do not use `prisma db push` for external staging or production.

Repository acceptance verifies the current migration/constraint contract on clean PostgreSQL and the canonical seed:

- 84 rooms;
- 12 room categories;
- 48 rate rows.

Real-target production evidence still requires a fresh actual-host migration record, backup and restore proof.

## 4. Physical room contract

Physical-room data collection is closed. Do not ask the owner for the room register again.

Canonical authority:

- `data-intake/rooms.csv` — 84 physical rooms / 12 mapped categories;
- checksum-bound owner approval evidence;
- 48 rate rows in the accepted property seed;
- rooms 501/502 are owner-approved two-person basement inventory above the laundry, not the superseded mansard/single mapping.

Remaining external room gate:

`real staging DB -> importer dry-run -> exact diff review -> safe apply -> final zero-diff evidence`.

## 5. Repository/CI verified product surface

The accepted release contains regression-gated contracts for:

- Public Site RU/KG/EN truth and CMS published-only runtime;
- Transfer before Tours;
- Core availability/pricing and ReservationRequest boundary;
- PMS chessboard, move/resize/Split Stay, stale/conflict protection and realtime;
- Reception RBAC and CLEAN check-in gate;
- Stay / RoomAssignment lifecycle;
- Room QR / Guest PIN / HttpOnly GuestSession;
- Guest OS requests, Marketplace and manager-controlled offers;
- Guest CRM history/preferences;
- MAID / TECHNICIAN / DINING staff operations;
- Kitchen Admin, menu publication, stop-list, table reservations and visual Dining Floor;
- Stay-linked Dining Sessions and Kitchen order lifecycle;
- active-table uniqueness and Dining production snapshot integrity;
- atomic group booking;
- guest folio charges separated from actual Payments;
- Payment idempotency including normalized actual `paid_at`;
- debt/remaining/overpaid views and owner analytics;
- Service Point QR without Guest/Stay/Reservation/Payment leakage;
- unified messaging inbox and provider-evidence semantics;
- n8n/Core authority boundary;
- fail-closed provider environment validation;
- backup/restore tooling and release linkage tooling;
- production package build contract;
- fail-closed launch verifier;
- production `DATABASE_URL` fail-closed behavior;
- housekeeping latest-due catch-up semantics;
- NFC deferred boundary.

This does **not** prove the real Beget host, real devices, real provider delivery, real monitoring, branch protection, Drive permission remediation, backups or rollback readiness.

## 6. Mandatory governance gates before final GO

### GitHub branch protection — issue #91

Current state: **NOT VERIFIED**.

Current metadata after PR #116 merge still reports `main` as `protected:false` with required status-check enforcement off.

Before production GO require:

- `main` protected against force push/deletion;
- PR/check discipline enforced for release changes;
- required checks configured for the accepted release boundary;
- fresh GitHub metadata proving protection is active;
- a test PR proving required checks still execute normally.

### Google Drive launch-control permissions — issue #100

Current state: **NOT VERIFIED**.

Latest verified audit found public writer access on the Three Crowns top-level hierarchy. Before production GO require removal/downgrade of `anyone:writer`, named editors only where appropriate, and fresh permission metadata proving current control/operational surfaces are not publicly writable.

Neither governance gate may be treated as fixed without external metadata evidence.

## 7. External hard blockers

Production cutover remains **STOP** until all required evidence is real and current:

1. VERIFIED GitHub branch protection / required checks on `main`;
2. VERIFIED Google Drive launch-control permission hardening;
3. actual Beget host/account/network non-destructive preflight;
4. verified rollback package for the currently live legacy `3korony.com` target;
5. restore rehearsal / rollback gate success;
6. isolated external HTTPS/WSS staging;
7. exact accepted SHA/image linkage on staging;
8. external public-truth probe;
9. real staging room reconciliation to 84 rooms / 12 categories;
10. real iPhone / Android / desktop / Staff / Kitchen acceptance;
11. real E2E for every provider enabled at launch;
12. real monitoring/alerting evidence;
13. fresh pre-cutover backup and verified off-site copy;
14. exact DNS rollback capture;
15. explicit owner GO for production/DNS switch.

No GitHub CI result by itself authorizes production DNS changes.

## 8. Repository gates

Release truth:

```bash
python scripts/release_rc_truth_guard.py
```

Repository launch structure:

```bash
python scripts/verify_launch_acceptance.py --mode repository
```

Final structural cutover evidence validator, only after real external evidence exists:

```bash
python scripts/verify_launch_acceptance.py \
  --mode cutover \
  --manifest /secure/path/launch-evidence.json \
  --release-sha e1ac7003abe7f63bd306778edd50a1c63dab6f17
```

The verifier validates supplied evidence metadata. It does not manufacture external proof.

## 9. External staging order

After authorized Beget/SSH execution exists, execute in order and stop on any failed gate.

### Phase 0 — exact release source

```bash
git fetch origin
git checkout main
git pull --ff-only
python scripts/release_rc_truth_guard.py
python scripts/beget_deployment_guard.py
```

Build/deploy the exact `accepted_executable_head` from `release/current-rc.json`, not an unpinned moving branch.

### Phase 1 — host/env preflight

```bash
bash scripts/host_preflight.sh
python scripts/beget_env_preflight.py \
  --env-file /secure/path/.env.staging \
  --allow-staging \
  --network
```

No live routing/DNS change is allowed in this phase.

### Phase 2 — legacy rollback evidence

Capture real live web root/source, DNS/TTL, DB presence/absence, uploads/media, proxy/runtime config, checksums, timestamps, off-site copy and rollback ownership. Require the rollback verifier/gate to be green before risky cutover work.

### Phase 3 — isolated external staging

- provision staging-only secrets and persistent storage;
- start private PostgreSQL 16;
- apply all **22** committed migrations with `prisma migrate deploy`;
- perform canonical room reconciliation dry-run -> review -> safe apply;
- load approved factual baseline only;
- deploy exact accepted SHA `e1ac7003abe7f63bd306778edd50a1c63dab6f17`;
- start Core, Public, Admin/PMS, Staff/Kitchen and required n8n services;
- verify HTTPS/WSS/cookies/CORS/persistence/private DB;
- record exact image/runtime revision labels.

### Phase 4 — external acceptance

Run external staging acceptance against real staging URLs and retain evidence. Then complete real-device, provider, monitoring, backup and restore acceptance.

## 10. Acceptance matrix

### Public / Booking

Verify RU/KG/EN rendered truth, availability/pricing through Core and `ReservationRequest` creation without automatic Reservation/Payment confirmation.

### PMS / Reception

Verify:

`ReservationRequest -> manager decision/payment fact -> Reservation -> chessboard -> CLEAN check-in -> Stay/RoomAssignment -> optional move/Split Stay -> checkout -> DIRTY -> housekeeping`.

Also verify stale/conflict rejection, realtime, TECH_BLOCK, group booking, finance RBAC and payment idempotency.

### Guest OS / CRM

Verify Room QR, PIN/session, requests, relocation, repeated guest history, checkout session revocation, factual RoomAssignment and manager-controlled offers without automatic commercial/payment truth.

### Kitchen / Dining

Verify Dining Staff access, menu publish/stop-list, table layout/reservations/waiter assignment, Stay-linked Dining Sessions, Guest OS orders, server totals, order lifecycle, arrival linkage, active-table uniqueness, production snapshot integrity and no automatic Hotel Payment side effects.

### Service Point QR

Verify anonymous point QR routing without private Guest/Stay/Reservation/Payment leakage. Real paid access is enabled only when its real provider E2E is separately verified. NFC remains outside active V1.

### Finance / Owner

Verify factual Payment ledger, folio separation, remaining/overpaid/debt including checked-out debt, group-booking commercial boundaries and owner dashboards.

### Staff / AI / messaging

Verify real mobile MAID/TECHNICIAN/DINING flows and provider authenticity/idempotency only for providers actually enabled at launch.

## 11. Production preflight and observability

The actual target must pass `scripts/production_preflight.py` with real environment/database evidence.

Require real evidence for:

- health/readiness monitoring;
- HTTP 5xx visibility;
- container restart visibility;
- PostgreSQL disk/storage monitoring;
- backup age/checksum/off-site presence;
- backup-failure alerts;
- TLS expiry monitoring;
- AuditLog retention;
- exact deployed Git SHA/image identity.

## 12. Controlled cutover

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

Until explicit owner GO and every prerequisite above are complete, status remains **EXTERNAL PRODUCTION CUTOVER STOP**.
