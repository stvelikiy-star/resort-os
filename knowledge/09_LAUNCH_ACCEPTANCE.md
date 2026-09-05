# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Version: 4.0
Date: 2026-09-05
Status: RESORT OS 0.60.0 INTERNAL RC FROZEN / EXTERNAL CUTOVER STOP
Canonical: YES

This document separates repository/CI evidence from external production evidence. It must never be used to imply that Resort OS is already live on the real hotel infrastructure.

## 1. Frozen release boundary

Repository: `stvelikiy-star/resort-os`.
Release: `0.60.0`.
Release PR: `#112` — `feature/owner-corrections-20260905 -> main`.
Accepted executable head: `c8db446d367284465853850136c31274c8e39370`.
Observed main merge: `e5efe074abb4a277c032b017ae5fb02c5d0d5039`.
Post-merge truth-only head: `00fdb8d1b583cf418e1c39709fb79ca248e462e4`.

Evidence:

- exact PR #112 head: **46/46 checks SUCCESS, 0 failures**;
- accepted executable head and observed main merge are tree-equivalent;
- observed main merge: **35/35 triggered main checks SUCCESS, 0 failures**;
- post-merge truth-only head: **4/4 triggered checks SUCCESS, 0 failures**;
- the post-merge truth delta contains documentation only and no executable product drift.

The machine-readable release boundary is `release/current-rc.json`, guarded by `scripts/release_rc_truth_guard.py`.

The production source branch is `main` because the accepted 0.60.0 executable tree is merged there. This is a source-of-release statement only: production cutover remains unauthorized until all external/governance evidence gates are green.

Repository/CI evidence is not external staging evidence and is not production evidence.

## 2. Product authority boundary

Canonical architecture:

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`.

OWNER/MANAGER retain reservation and payment authority. AI/n8n may qualify leads and create bounded requests, but may not:

- confirm payment;
- guarantee a Reservation;
- invent a fixed prepayment percentage or payment route;
- check a guest in/out;
- refund money;
- mutate hotel finance directly;
- bypass Core availability/pricing;
- write generic business truth directly to PostgreSQL.

Growth outbound authority remains `NONE_AUTOMATIC`.

NFC acquiring/wallet remains deferred outside active V1.

## 3. Canonical database release contract

The frozen 0.60.0 release contains **20 committed migrations**:

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

The shared release contract fingerprints **81 critical domain constraints** through `scripts/release_contract.py`.

External staging and production migration mechanism:

```bash
cd packages/database
npm ci
npx prisma validate
npx prisma migrate deploy
cd ../..
```

Do not use `prisma db push` for external staging or production migration.

The production-like acceptance run on clean PostgreSQL 16 proved:

- all 20 committed migrations apply cleanly;
- Prisma migration status is current;
- canonical seed = 84 rooms / 12 room categories / 48 rate rows;
- Core, Public Web, Admin and Staff/Kitchen release contours pass;
- the release E2E and database invariants pass.

## 4. Physical room contract

Physical-room data collection is closed. Do not ask the owner for the room register again.

Canonical authority:

- `data-intake/rooms.csv` — 84 physical rooms / 12 mapped categories;
- checksum-bound owner approval evidence in the repository;
- 48 rate rows in the accepted property seed.

Remaining external room gate:

`real staging DB -> importer dry-run -> exact diff review -> safe apply -> final zero-diff evidence`.

## 5. Repository/CI verified product surface

The frozen release contains regression-gated contracts for:

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
- atomic group booking;
- guest folio charges separated from actual Payments;
- Payment idempotency, debt/remaining/overpaid views and owner analytics;
- Service Point QR without Guest/Stay/Reservation/Payment leakage;
- unified messaging inbox and provider-evidence semantics;
- n8n/Core authority boundary;
- provider environment fail-closed validation;
- backup/restore tooling and release linkage tooling;
- production package build contract;
- fail-closed launch verifier;
- NFC deferred boundary.

This does not prove the real Beget host, real devices, real provider delivery, real monitoring, branch protection, Drive permission remediation, backups or current-live rollback readiness.

## 6. Mandatory governance gates before final GO

### GitHub branch protection — issue #91

Current state: **NOT VERIFIED**.

The actual production source branch is now `main`. Before production GO require:

- `main` protected against force push/deletion;
- PR/check discipline enforced for release changes;
- required checks configured for the accepted release boundary;
- fresh GitHub metadata proving protection is active;
- a test PR proving required checks still execute normally.

### Google Drive launch-control permissions — issue #100

Current state: **NOT VERIFIED**.

The last verified permission audit found public writer access on the top-level Three Crowns project hierarchy. Before production GO require removal/downgrade of `anyone:writer`, named editors only where appropriate, and a fresh permission audit proving current operational/control surfaces are not publicly writable.

Neither governance gate may be treated as fixed without external metadata evidence.

## 7. External hard blockers

Production cutover remains **STOP** until all required evidence below is real and current:

1. VERIFIED GitHub branch protection / required-check enforcement on `main`;
2. VERIFIED Google Drive launch-control permission hardening;
3. actual Beget host/account/network non-destructive preflight;
4. verified rollback package for the currently live legacy `3korony.com` target;
5. restore rehearsal / rollback gate success;
6. isolated external HTTPS/WSS staging;
7. exact accepted SHA/image linkage on staging;
8. external public-truth probe;
9. real staging room reconciliation to 84 rooms / 12 categories;
10. real iPhone / Android / desktop / Telegram / Staff / Kitchen acceptance;
11. real E2E for every provider enabled at launch;
12. real monitoring/alerting evidence;
13. fresh pre-cutover backup and verified off-site copy;
14. exact DNS rollback capture;
15. explicit owner GO for the production/DNS switch.

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
  --release-sha c8db446d367284465853850136c31274c8e39370
```

The verifier validates supplied evidence metadata. It does not manufacture external proof.

## 9. External staging order

After authorized Beget/SSH access exists, execute in this order and stop on any failed gate.

### Phase 0 — exact release source

```bash
git fetch origin
git checkout main
git pull --ff-only
python scripts/release_rc_truth_guard.py
python scripts/beget_deployment_guard.py
```

Read `accepted_executable_head` from `release/current-rc.json` and build/deploy that exact SHA, not an unpinned moving branch.

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

Capture real live web root/source, DNS/TTL, database presence/absence, uploads/media, proxy/runtime config, checksums, timestamps, off-site copy and rollback ownership.

Then require the repository rollback verifier/gate to be green before any risky cutover action.

### Phase 3 — isolated external staging

- provision staging-only secrets and persistent storage;
- start private PostgreSQL 16;
- apply all 20 migrations with `prisma migrate deploy`;
- perform canonical room reconciliation dry-run -> review -> safe apply;
- load approved factual baseline only;
- deploy exact accepted SHA `c8db446d367284465853850136c31274c8e39370`;
- start Core, Public, Admin/PMS, Staff/Kitchen and required n8n services;
- verify HTTPS/WSS/cookies/CORS/persistence/private database;
- record exact image/runtime revision labels.

### Phase 4 — external acceptance

Run the external staging acceptance tooling against real staging URLs and retain evidence. Then complete real-device, provider, monitoring, backup and restore acceptance.

## 10. Final cutover sequence

Only after every required external/governance gate is VERIFIED:

1. reconfirm frozen RC manifest and exact accepted SHA;
2. take fresh pre-cutover backup and verify off-site copy;
3. confirm legacy rollback package and DNS rollback target;
4. rerun host and production preflight;
5. confirm staging/room/device/provider evidence;
6. obtain explicit owner GO;
7. deploy exact accepted release image set;
8. run readiness/smoke before public switch;
9. change routing/DNS in a controlled window;
10. smoke Public Site, booking, PMS, Guest OS, Staff, Kitchen and WSS;
11. monitor errors/database/containers;
12. roll back immediately if acceptance criteria fail.

Database rollback uses the rehearsed backup/restore path; do not improvise destructive reverse SQL.

Until explicit owner GO and every prerequisite above are complete, status remains **EXTERNAL PRODUCTION CUTOVER STOP**.
