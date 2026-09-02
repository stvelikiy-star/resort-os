# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Version: 3.7
Date: 2026-09-02
Status: INTERNAL RC FROZEN / EXTERNAL CUTOVER STOP
Canonical: YES

This document separates repository/CI evidence from external production evidence. It must never be used to imply that the new Resort OS is live.

## 1. Current repository boundary

Repository: `stvelikiy-star/resort-os`.
Integration branch: `integration/site-pms-cms-20260827`.
Accepted executable head: `ce2d8ecde43c294162a782f7912425ced5258f99`.
Observed integration merge: `05777f3371bd42b4c4cc9a8d6d68fa9b482b238c`.

The exact PR #102 product head completed **17/17 applicable non-RC workflows successfully, 0 failures**. `Release RC Truth CI` intentionally failed before refreeze because the previous RC manifest still pointed at the prior accepted release.

The observed PR #102 integration merge has **0 changed files** versus the tested product head.

PR #102 is a narrow customer-facing AI truth hardening delta. The previous PR #98 Kitchen/Core release baseline retains its separate **43/43 non-RC** product, acceptance, security, migration, backup/restore, staging and packaging evidence.

The current machine-readable boundary is `release/current-rc.json`, guarded by `scripts/release_rc_truth_guard.py`.

`main` is not a production source. Stale `main` must not be used for Beget deployment or DNS cutover.

Repository/CI evidence is not external staging evidence and is not production evidence.

## 2. Current AI / messaging truth boundary

Customer-facing automation reads hotel facts from Resort Core. The current accepted facts now require:

- check-in `14:00`;
- checkout `12:00`;
- gym absent;
- sports grounds absent;
- laundry not promoted until normalized;
- conference halls not promoted until normalized;
- sauna winter-only, 5,000 KGS/hour, approximately 4–5 people;
- billiards 500 KGS/hour;
- table tennis free for staying guests;
- parking approximately 20–30 cars, free for staying guests;
- no unverified payment-method enumeration in customer-facing AI context;
- public payment methods/providers remain `NOT_VERIFIED_FOR_LAUNCH` until real manager/provider evidence exists.

`ReservationRequest != Reservation`.

AI/n8n may qualify a lead and create a `ReservationRequest`; it must not confirm payment, create a guaranteed Reservation, invent a fixed prepayment percentage, choose a payment route, check a guest in/out, refund money, mutate hotel finance or write PostgreSQL directly.

Provider success is provider evidence. QUEUED/UNKNOWN/timeout is not delivery success.

## 3. Canonical database release contract

Exact committed migration ledger:

1. `0_init`
2. `1_site_content`
3. `2_guest_service_tasks`
4. `3_owner_analytics_snapshots`
5. `4_guest_engagements`
6. `5_guest_os_core`
7. `6_service_point_qr_operations`
8. `7_kitchen_operations`

External staging and production migration mechanism:

```bash
cd packages/database
npm ci
npx prisma validate
npx prisma migrate deploy
cd ../..
```

`prisma db push` is not the external staging or production migration mechanism.

The shared release contract maintains 27 critical hotel/payment PostgreSQL constraints. Kitchen migration/domain checks add their own menu/table/order/item invariants.

`prisma` and `@prisma/client` remain pinned exactly to `6.12.0`; deterministic lockfile install and database dependency security are release gates.

## 4. Canonical physical-room contract

Physical-room data collection is closed. Do not ask the owner for the room register again.

Canonical authority:

- `data-intake/rooms.csv` — exactly 84 physical rooms / 12 mapped categories;
- `data-intake/room-register-owner-approval.json` — checksum-bound owner approval;
- `data-intake/owner-room-checklist.json` — provenance/history.

The old mutable Google `ROOMS_IMPORT` spreadsheet is provenance only and must not become a parallel production source.

Remaining external room gate:

```text
real staging DB -> importer dry-run -> exact diff review -> safe apply -> final zero diff evidence
```

`scripts/import_physical_rooms.py` is dry-run by default, preserves existing runtime room operational state, does not change rates/reservations/payments/inventory blocks, and refuses unsafe apply conditions.

## 5. What is repository/CI verified

The accepted baseline plus the PR #102 truth-hardening delta contain verified contracts for:

- public site truth and RU/KG/EN rendering;
- Transfer before Tours;
- Core availability/pricing;
- website `ReservationRequest` boundary;
- PMS chessboard, move/resize/Split Stay, stale/conflict protection and realtime;
- Reception RBAC and CLEAN check-in gate;
- Stay / RoomAssignment lifecycle;
- Guest OS Room QR / PIN / HttpOnly session / requests;
- Guest CRM factual history/preferences;
- MAID / TECHNICIAN operations and staff voice;
- Kitchen Admin, editable provisional menu, factual table register and Kitchen order lifecycle;
- transactional check-in -> Dining arrival card;
- Kitchen finance isolation from Hotel Payment/accommodation total;
- Service Point QR without Guest/Stay/Reservation/Payment leakage;
- Payment fact/idempotency and owner finance/analytics boundaries;
- unified inbox and provider-evidence semantics;
- n8n/Core authority boundary;
- backup -> clean restore contract;
- dependency security checks;
- production package build contract;
- CI-local staging;
- exact Git SHA -> deployed image linkage verifier;
- external staging acceptance orchestrator;
- fail-closed launch verifier;
- NFC deferred scope.

These checks do not prove external Beget networking, real devices, real provider delivery, actual monitoring or current live rollback readiness.

## 6. External hard blockers

Production cutover remains **STOP** until all required evidence below is real and current:

1. repository branch protection / required checks enforcement for the release source;
2. actual Beget host/account/network non-destructive preflight;
3. verified rollback package for the currently live legacy `3korony.com` target;
4. restore rehearsal / rollback gate success;
5. isolated external HTTPS/WSS staging;
6. exact accepted SHA/image linkage on that staging deployment;
7. external public-truth probe;
8. real staging room reconciliation to the canonical 84-room register;
9. real iPhone/Android/desktop/Telegram/Staff/Kitchen acceptance;
10. real E2E for every provider enabled at launch;
11. real monitoring/alerting evidence;
12. fresh pre-cutover backup and verified off-site copy;
13. exact DNS rollback capture;
14. explicit owner GO for the production/DNS switch.

No GitHub CI result by itself authorizes production DNS changes.

## 7. Fail-closed repository checks

Repository release truth:

```bash
python scripts/release_rc_truth_guard.py
python scripts/verify_launch_acceptance.py --mode repository
```

Final cutover evidence verifier, only after real external evidence exists:

```bash
python scripts/verify_launch_acceptance.py \
  --mode cutover \
  --manifest /secure/path/launch-evidence.json \
  --release-sha <EXACT_ACCEPTED_RELEASE_SHA>
```

The verifier validates supplied evidence. It does not manufacture external proof.

Never commit credentials, provider tokens, database passwords or production secrets into launch evidence.

## 8. Mandatory external staging order

After authorized Beget/SSH access exists, execute in this order and stop on any failed gate.

### Phase 0 — release source

On the canonical integration branch:

```bash
git fetch origin
git checkout integration/site-pms-cms-20260827
git pull --ff-only
python scripts/release_rc_truth_guard.py
python scripts/beget_deployment_guard.py
```

Read `accepted_executable_head` from `release/current-rc.json`. Build/deploy the exact accepted SHA, not an unpinned moving branch.

### Phase 1 — host preflight

```bash
bash scripts/host_preflight.sh
python scripts/beget_env_preflight.py \
  --env-file /secure/path/.env.staging \
  --allow-staging \
  --network
```

Do not change live routing/DNS here.

### Phase 2 — legacy rollback capture and proof

Capture the actual live web root, authoritative DNS, real database presence/absence, uploads/media, runtime/reverse-proxy configuration, checksums, timestamps, off-site copy and responsible rollback owner.

Then verify/rehearse and require:

```bash
python scripts/legacy_rollback_verify.py <ROLLBACK_EVIDENCE_DIR> --mark-verified
python scripts/legacy_rollback_gate.py <ROLLBACK_EVIDENCE_DIR>
```

Required result:

`RESULT: CUTOVER_ROLLBACK_PREREQUISITE_GREEN`

No external deployment path may risk the legacy live target before this gate is green.

### Phase 3 — isolated external staging

- provision staging-only secrets and persistent storage;
- provision private PostgreSQL;
- apply all eight migrations with `prisma migrate deploy`;
- load approved factual baseline only;
- run canonical room dry-run -> review -> safe apply;
- deploy exact accepted SHA;
- start Core, Public, Admin/PMS, Staff/Kitchen and required n8n services;
- verify HTTPS, WSS, cookies, CORS, persistence and private database topology.

### Phase 4 — release linkage

```bash
python scripts/deployment_release_linkage.py \
  --expected-sha <EXACT_ACCEPTED_RELEASE_SHA> \
  --compose-file compose.beget.yaml \
  --env-file /secure/path/.env.staging \
  --output <NON_SECRET_RELEASE_LINKAGE_JSON>
```

Dirty checkout, missing service, stopped service, missing revision label or SHA mismatch is a hard failure.

### Phase 5 — atomic external acceptance

```bash
STAGING_ACCEPTANCE_MUTATIONS=I_UNDERSTAND_SYNTHETIC_WRITES \
APP_ENV=staging \
python scripts/external_staging_acceptance.py \
  --expected-sha <EXACT_ACCEPTED_RELEASE_SHA> \
  --rollback-evidence-dir <ROLLBACK_EVIDENCE_DIR> \
  --public-url https://<PUBLIC_STAGING_HOST>/ \
  --core-url https://<API_STAGING_HOST> \
  --admin-url https://<ADMIN_STAGING_HOST>/ \
  --staff-url https://<STAFF_STAGING_HOST>/ \
  --ws-url wss://<API_STAGING_HOST> \
  --compose-file compose.beget.yaml \
  --env-file /secure/path/.env.staging \
  --backup-dir <REAL_BACKUP_DIR> \
  --disk-path <REAL_APP_DISK_PATH> \
  --output-dir <NEW_EMPTY_EXTERNAL_ACCEPTANCE_DIR>
```

Required result:

`RESULT: EXTERNAL STAGING ACCEPTANCE GREEN`

The runner requires staging hostnames and does not perform production DNS switch.

### Phase 6 — real devices/providers/monitoring

After scripted staging acceptance is green, record real evidence for:

- iPhone Safari;
- Android Chrome;
- desktop;
- Telegram Mini App where enabled;
- PMS realtime/reconnect;
- Staff MAID/TECHNICIAN;
- Kitchen/DINING_STAFF;
- Guest OS;
- provider delivery/idempotency for each provider enabled at launch;
- actual alert delivery, backup age/off-site copy and restore evidence.

Templates, mocks and CI do not replace this phase.

## 9. Final cutover sequence

Only after every required external gate is VERIFIED:

1. freeze exact accepted SHA/image set;
2. take fresh pre-cutover backup and verify off-site copy;
3. confirm legacy rollback package and DNS rollback target;
4. rerun host and production preflight;
5. confirm staging/room/device/provider evidence;
6. obtain explicit owner GO;
7. deploy exact accepted release image set;
8. run readiness/smoke before public switch;
9. change routing/DNS in the controlled window;
10. smoke public truth, booking, PMS, Guest OS, Staff, Kitchen and WSS;
11. monitor errors/database/containers;
12. roll back immediately if acceptance criteria fail.

Database rollback uses the rehearsed backup/restore path. Do not improvise destructive reverse SQL.

Until explicit owner GO and every prerequisite above are complete, status remains **PRODUCTION CUTOVER STOP**.
