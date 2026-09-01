# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Date: 2026-09-02
Status: INTERNAL RELEASE CANDIDATE / EXTERNAL CUTOVER STOP
Canonical: YES

This document separates repository/CI evidence from external production evidence. It must not be used to imply that the system is live.

## 1. Current repository boundary

Integration branch: `integration/site-pms-cms-20260827`.
Accepted executable head: `3787e8729b84e1ecc41133ab846a909943458306`.
Observed integration merge: `102a46ef721ee880647ecd6f81024bd744458170`.

The accepted executable head is the exact PR #95 product head after Guest OS PIN presentation/reissue and admin RU/KG/EN/contrast hardening and completed **35/35 executable acceptance/security/regression contours successfully, 0 failures**. The separate RC-truth workflow intentionally failed on that product head because the previous release was frozen; this document and `release/current-rc.json` perform the controlled refreeze after the actual tree-equivalent integration merge existed.

The successful product contours include Resort Core, Full Staging, Production Package, PMS Final Acceptance, PMS grid/mutation, Guest OS Core/Access/Requests, Admin Runtime Truth, the dedicated Admin Guest PIN and i18n build/contract gate, frontend/backend/database dependency security, realtime, operations, payment idempotency, backup/restore, AI/n8n and communications contracts.

The observed integration merge has **0 changed files** versus the tested executable head. The machine-readable RC boundary is `release/current-rc.json`, guarded by `scripts/release_rc_truth_guard.py`.

`main` is not a production source. It is stale relative to the accepted integration RC and must not be used for Beget deployment or DNS cutover.

Earlier closed product gates retain their own exact-head evidence. A tree-equivalent merge commit is not a substitute for independent external acceptance.

## 2. Canonical database release contract

Exact committed migration ledger:

1. `0_init`
2. `1_site_content`
3. `2_guest_service_tasks`
4. `3_owner_analytics_snapshots`
5. `4_guest_engagements`
6. `5_guest_os_core`
7. `6_service_point_qr_operations`

Production migration mechanism: `npx prisma migrate deploy`.

Critical PostgreSQL constraint fingerprint is maintained in `scripts/release_contract.py` and currently contains 27 constraints.

The database Node toolchain is also part of the release security boundary: `prisma` and `@prisma/client` are pinned exactly to `6.12.0`, `packages/database/package-lock.json` is committed, deterministic `npm ci` is required, and `Database Dependency Security CI` gates HIGH/CRITICAL npm findings plus Prisma schema validation/client generation.

## 3. What is repository/CI verified

The repository contains and CI exercises:

- public site truth and RU/KG/EN browser acceptance;
- CMS -> Core -> public runtime with locale-safe fallback/ownership;
- ReservationRequest/Core boundary;
- compact owner PMS grid and full PMS mutation lifecycle;
- Reception/Admin RBAC;
- canonical Stay and RoomAssignment lifecycle;
- Room QR / PIN / GuestSession access;
- one-time Guest OS PIN surfaced at check-in and secure PIN reissue for active checked-in stays;
- global Admin RU/KG/EN locale runtime for operational labels/status/audit presentation and high-contrast dashboard override;
- Guest OS requests and Staff role routing;
- Guest CRM factual Stay/relocation/history/preferences;
- Guest Services Center;
- Finance & operational control;
- Owner Intelligence / Control / Growth / Dashboard analytics;
- unified inbox, AI draft authority boundary and n8n contracts;
- anonymous Service Point QR operations;
- migration baseline and backup -> clean restore;
- frontend/backend dependency security inspections;
- database Prisma dependency security, exact pins and deterministic lockfile;
- single-server production package and CI-local Full Staging;
- exact Git SHA -> deployed image linkage contract;
- mutating staging acceptance production-safety guard;
- unified external staging acceptance orchestration contract;
- NFC deferred scope: NFC payment routes remain outside active V1 composition.

Physical room import gate #38 is **CLOSED / COMPLETED** for the canonical 84-room / 12-category register and safe importer contract. This is not external staging reconciliation evidence.

CI verification is not external production evidence.

## 4. External hard blockers

Production cutover remains STOP until all required items below have real evidence:

- room reconciliation on the actual external staging database against the closed #38 canonical register: importer dry-run -> diff review -> safe apply/result evidence;
- non-destructive preflight on the actual Beget host/account/network;
- verified rollback backup of the currently live `3korony.com` target, including DNS/config/data/media where applicable;
- isolated external HTTPS/WSS staging on the real network;
- external public-truth probe against that staging deployment;
- real-device acceptance on iPhone, Android, desktop and Telegram/staff surfaces;
- real provider E2E for every messaging provider that will be enabled at launch;
- monitoring/alerting evidence on real infrastructure;
- fresh pre-cutover backup evidence;
- exact DNS rollback capture;
- explicit final owner approval for the production/DNS switch.

Do **not** reopen room-data collection as a launch requirement. The remaining room gate is real-target reconciliation only.

## 5. Fail-closed launch evidence

Template: `release/launch-evidence.example.json`.
Verifier: `scripts/verify_launch_acceptance.py`.
Unified external staging runner: `scripts/external_staging_acceptance.py`.
RC truth manifest: `release/current-rc.json`.

Repository check:

```bash
python scripts/verify_launch_acceptance.py --mode repository
python scripts/release_rc_truth_guard.py
```

Cutover check after real evidence has been collected into a separate non-secret manifest:

```bash
python scripts/verify_launch_acceptance.py \
  --mode cutover \
  --manifest /secure/path/launch-evidence.json \
  --release-sha <exact-accepted-release-sha>
```

Required external room evidence key is `room_reconciliation`. Historical `owner_room_register` is obsolete and rejected by the verifier because #38 is already closed.

The verifier validates supplied evidence metadata and fails closed on missing gates. It does not manufacture, infer or independently observe external evidence.

Do not commit credentials, provider tokens, database passwords or other production secrets into the evidence manifest.

### 5A. External Beget operator sequence — mandatory order

This is the approved fail-closed execution order after authorized Beget/SSH access exists. Stop immediately on any non-zero exit code. Do not skip forward and do not treat warnings as production approval.

**Phase 0 — source boundary.** Work only from the accepted integration RC. Never deploy stale `main`.

```bash
python scripts/release_rc_truth_guard.py
python scripts/beget_deployment_guard.py
```

**Phase 1 — non-destructive host and managed-infrastructure preflight.** These checks must run before changing the live site, DNS or application services.

```bash
bash scripts/host_preflight.sh
python scripts/beget_env_preflight.py \
  --env-file /secure/path/.env.staging \
  --allow-staging \
  --network
```

A host preflight `FAIL` blocks deployment. A host preflight warning must be explicitly resolved/accepted before production cutover; it is not equivalent to production readiness.

**Phase 2 — legacy rollback capture and restore proof.** Use the actual live web root and actual evidence decisions. Do not invent paths or declare DB/uploads/config absent unless that absence has been verified. Secrets stay in environment variables or protected files, never command history/evidence manifests.

Example shape when those real facts have been established:

```bash
python scripts/legacy_rollback_capture.py \
  --web-root <ACTUAL_LIVE_WEB_ROOT> \
  --output-dir <NEW_EMPTY_LOCAL_EVIDENCE_DIR> \
  --domain 3korony.com \
  --dns-snapshot-file <AUTHORITATIVE_DNS_JSON> \
  --authoritative-dns-reviewed \
  --offsite-dir <MOUNTED_OR_OFFSITE_DESTINATION> \
  --rollback-owner <RESPONSIBLE_ROLE_OR_PERSON> \
  <REAL_DB_OPTION> \
  <REAL_UPLOADS_OPTION> \
  <REAL_CONFIG_OPTION>
```

For the three decision placeholders above, use exactly one factual branch where required: `--database-url-env <ENV_NAME>` **or** `--database-absent-confirmed`; repeat `--uploads <PATH>` **or** use `--uploads-absent-confirmed`; repeat `--config <PATH>` **or** use `--config-absent-confirmed`.

Then rehearse and verify the captured rollback package using the committed verifier, and only after the rehearsal is marked verified run the final rollback gate:

```bash
python scripts/legacy_rollback_verify.py <ROLLBACK_EVIDENCE_DIR> --mark-verified
python scripts/legacy_rollback_gate.py <ROLLBACK_EVIDENCE_DIR>
```

`legacy_rollback_gate.py` must return `RESULT: CUTOVER_ROLLBACK_PREREQUISITE_GREEN`. Until then, **STOP: do not deploy external staging on any topology that risks the legacy live target and do not switch DNS/routing**.

**Phase 3 — isolated external staging deployment.** Deploy the exact accepted release to staging-only hostnames/configuration. Apply the committed seven migrations with `prisma migrate deploy`, then reconcile the real staging database against the canonical 84-room register with importer dry-run/diff review before any safe apply. This phase must not route public production traffic.

After application containers are running, prove that source checkout and all application images match the exact accepted release:

```bash
python scripts/deployment_release_linkage.py \
  --expected-sha <EXACT_ACCEPTED_RELEASE_SHA> \
  --compose-file compose.beget.yaml \
  --env-file /secure/path/.env.staging \
  --output <NON_SECRET_RELEASE_LINKAGE_JSON>
```

**Phase 4 — one atomic external acceptance run.** Use staging-only HTTPS/WSS URLs. This runner is fail-fast and writes one checksum-bound evidence manifest/log set.

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

The required result is `RESULT: EXTERNAL STAGING ACCEPTANCE GREEN`. A RED result blocks further launch work and its evidence directory must be retained for diagnosis.

**Phase 5 — external-only acceptance not replaced by scripts.** After Phase 4 is green, perform and record real iPhone Safari, Android Chrome, desktop and launch-enabled Telegram/provider tests, real monitoring/alert delivery and required restore evidence. These are not inferred from CI.

**Phase 6 — final launch gate.** Only after #8, #28, branch protection #91, required device/provider evidence and explicit owner GO are all green, create the final non-secret launch evidence manifest and run `verify_launch_acceptance.py --mode cutover`. DNS/public routing changes remain forbidden before this point.

## 6. Production authority boundary

`ReservationRequest != Reservation`.

OWNER/MANAGER retain reservation and payment authority. AI/n8n cannot guarantee a Reservation, confirm payment, invent a fixed prepayment percentage or bypass Core availability/pricing.

NFC acquiring/wallet remains deferred and must not be activated as a side effect of launch acceptance.

## 7. Cutover sequence

After all external blockers are VERIFIED:

1. freeze exact accepted release SHA/image set;
2. take fresh pre-cutover backup;
3. confirm legacy rollback package and DNS rollback target;
4. rerun host/preflight and production preflight;
5. confirm external staging, room reconciliation and device/provider evidence;
6. obtain explicit owner cutover approval;
7. deploy exact accepted release;
8. run readiness/smoke before public switch;
9. switch routing/DNS in the approved window;
10. run public truth, booking, PMS, Guest OS, Staff and WSS smoke checks;
11. monitor errors, database and containers;
12. roll back immediately if acceptance criteria fail.

Until step 6 is complete, status remains `PRODUCTION CUTOVER STOP`.
