# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Version: 3.8
Date: 2026-09-02
Status: INTERNAL RC FROZEN / EXTERNAL CUTOVER STOP
Canonical: YES

This document separates repository/CI evidence from external production evidence. It must never be used to imply that the new Resort OS is live.

## 1. Current repository boundary

Repository: `stvelikiy-star/resort-os`.
Integration branch: `integration/site-pms-cms-20260827`.
Accepted executable head: `ab6b649d91df5e9698253d43788cc657ca7040c9`.
Observed integration merge: `c4a2b9584e9e6222ae7b213a6bf87ba3cd6f97e4`.

The exact PR #107 product/security head completed **20/20 applicable non-RC workflows successfully, 0 failures**. `Release RC Truth CI` intentionally failed before refreeze because the previous RC manifest still pointed at the prior accepted release.

The observed PR #107 integration merge has **0 changed files** versus the tested product head.

PR #107 is a narrow provider-environment and final launch-governance hardening delta. It does not enable any provider and does not change PMS/Kitchen business logic, room inventory, pricing, payment authority, database schema or NFC scope.

Previous accepted product evidence remains part of the same tree:

- PR #102 customer-facing AI truth hardening: 17/17 applicable non-RC workflows SUCCESS;
- PR #98 Kitchen/Core release baseline: 43/43 non-RC workflows SUCCESS.

The machine-readable release boundary is `release/current-rc.json`, guarded by `scripts/release_rc_truth_guard.py`.

`main` is not a production source. Stale `main` must not be used for Beget deployment or DNS cutover.

Repository/CI evidence is not external staging evidence and is not production evidence.

## 2. Current AI / messaging truth boundary

Customer-facing automation reads hotel facts from Resort Core. The accepted facts require:

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

Provider success belongs to provider evidence. QUEUED/UNKNOWN/timeout is not delivery success.

## 3. Provider environment security boundary

Providers remain optional. When a provider/model path is configured, repository preflight now fails closed on obvious placeholder or structurally weak configuration:

- Telegram Sales: real/non-placeholder token; webhook secret real/non-placeholder and at least 24 characters;
- GREEN API: both ID and token real/non-placeholder; webhook secret real/non-placeholder and at least 24 characters;
- OpenAI: any configured Resort OS OpenAI model requires a real/non-placeholder `OPENAI_API_KEY`;
- Staff Voice: real Telegram bot token plus real/non-placeholder staff webhook secret at least 24 characters when transcription is configured.

Obvious placeholder forms such as `CHANGE_ME`, `REPLACE_ME`, `PLACEHOLDER`, `YOUR_*`, `NOT_SET` and related markers are rejected.

The exact PR #107 head passed the deterministic provider-security matrix and the Beget preflight integration cases. This is configuration-hygiene evidence only; it is **not provider launch E2E** and does not prove any provider is live.

## 4. Canonical database release contract

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

## 5. Canonical physical-room contract

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

## 6. What is repository/CI verified

The accepted tree contains verified contracts for:

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
- provider environment fail-closed validation;
- backup -> clean restore contract;
- dependency security checks;
- production package build contract;
- CI-local staging;
- exact Git SHA -> deployed image linkage verifier;
- external staging acceptance orchestrator;
- fail-closed launch verifier;
- NFC deferred scope.

These checks do not prove external Beget networking, real devices, real provider delivery, actual monitoring, branch protection, Drive permission remediation or current live rollback readiness.

## 7. Mandatory governance gates before final GO

The final structural cutover verifier now requires both of these gates to be `VERIFIED`:

### GitHub branch protection — issue #91

Current factual state: **NOT VERIFIED**.

The canonical integration branch currently reports `protected:false`; required status-check enforcement is off. Before production GO require evidence of the approved protection/PR/check/force-push policy and a fresh metadata read proving the policy is active.

### Google Drive launch-control permissions — issue #100

Current factual state: **NOT VERIFIED**.

Permission audit on 2026-09-02 found **13/13 top-level Three Crowns project folders expose `anyone with link -> writer`**, including the hierarchy containing current control Docs/Sheets. Before production GO public writer access must be removed/downgraded project-wide, named editors retained, any public links reader-only/disabled, and fresh metadata must prove no current operational/control surface retains `anyone:writer`.

The connected toolset cannot safely mutate either external governance control, so neither gate is claimed fixed.

## 8. External hard blockers

Production cutover remains **STOP** until all required evidence below is real and current:

1. VERIFIED GitHub branch protection / required-check enforcement;
2. VERIFIED Google Drive launch-control permission hardening;
3. actual Beget host/account/network non-destructive preflight;
4. verified rollback package for the currently live legacy `3korony.com` target;
5. restore rehearsal / rollback gate success;
6. isolated external HTTPS/WSS staging;
7. exact accepted SHA/image linkage on that staging deployment;
8. external public-truth probe;
9. real staging room reconciliation to the canonical 84-room register;
10. real iPhone/Android/desktop/Telegram/Staff/Kitchen acceptance;
11. real E2E for every provider enabled at launch;
12. real monitoring/alerting evidence;
13. fresh pre-cutover backup and verified off-site copy;
14. exact DNS rollback capture;
15. explicit owner GO for the production/DNS switch.

No GitHub CI result by itself authorizes production DNS changes.

## 9. Fail-closed repository checks

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

The final manifest structurally requires `github_branch_protection` and `drive_launch_control_permissions` in addition to the other external gates. The verifier validates supplied evidence; it does not manufacture external proof.

Never commit credentials, provider tokens, database passwords or production secrets into launch evidence.

## 10. Mandatory external staging order

After authorized Beget/SSH access exists, execute in this order and stop on any failed gate.

### Phase 0 — release source and governance

Before deployment work, require VERIFIED #91 and #100 evidence in the launch-control process. Then on the canonical integration branch:

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

Do not change live routing/DNS here. Provider credentials may remain absent while those providers are disabled; any configured provider path must pass the fail-closed secret validation.

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

Templates, mocks, static credential validation and CI do not replace this phase.

## 11. Final cutover sequence

Only after every required external/governance gate is VERIFIED:

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

Until explicit owner GO and every prerequisite above are complete, status remains **EXTERNAL PRODUCTION CUTOVER STOP**.
