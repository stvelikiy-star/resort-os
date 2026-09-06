# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Version: 6.0  
Date: 2026-09-07  
Status: RESORT OS 0.62.0 INTERNAL RC FROZEN / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

Repository/CI evidence is not external staging or production evidence.

## 1. Frozen release boundary

Repository: `stvelikiy-star/resort-os`.
Release: `0.62.0`.
Accepted source PR: `#122` — `chore/management-final-acceptance-20260906 -> main`.
Accepted executable head: `609a309c97f30b5f95828956188507fc35ed3d0d`.
Observed tree-equivalent main merge: `bccc491ea24c94668ef1bea4d86fb61a5b8e6f3d`.
Post-merge truth reference: `bccc491ea24c94668ef1bea4d86fb61a5b8e6f3d`.
Production source branch: `main`.

Evidence:

- accepted PR #122 head: **21/21 workflows SUCCESS, 0 failures**;
- accepted head and observed merge share the same tree;
- observed main merge: **20 product/security/migration/staging workflows SUCCESS**;
- the only failed push workflow was `Release RC Truth CI`, which failed closed because the previous manifest still described 0.61.0; this 0.62.0 refreeze is the controlled correction.

Machine truth: `release/current-rc.json`. Guard: `scripts/release_rc_truth_guard.py`.

## 2. Product authority boundary

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`.
OWNER/MANAGER retain reservation and payment authority. AI/n8n may create bounded requests/messages but may not confirm payment, guarantee a Reservation, invent payment rules, check guests in/out, refund, bypass Core pricing/availability or write generic business truth directly to PostgreSQL.

Real bank/TTLock activation remains fail-closed. NFC acquiring/wallet remains outside active V1.

## 3. Database and property contract

Frozen release boundary: **22 committed migrations / 87 critical domain constraints**.
Canonical property seed: **84 rooms / 12 categories / 48 rate rows**.
Rooms 501/502 remain the owner-approved two-person basement inventory above the laundry.

External staging/production migration uses only:

```bash
cd packages/database
npm ci
npx prisma validate
npx prisma migrate deploy
npx prisma migrate status
cd ../..
```

Do not use `prisma db push` for staging or production.

## 4. Repository-verified management contour

0.62.0 includes the accepted management closure:

- PMS/supershakhmatka, pricing/seasons, Reception, CRM and group booking;
- CLEAN check-in gate, Stay/RoomAssignment lifecycle and checkout -> DIRTY -> housekeeping;
- MAID/TECHNICIAN operations and TECH_BLOCK protection;
- Guest Services, Guest OS, PIN/session, offers and Guest CRM history;
- Kitchen/Dining production management, OWNER/MANAGER menu creation/publish/price control, DINING_STAFF operational access, table/session/order lifecycle and production snapshots;
- Finance/folio/payment idempotency and owner analytics;
- Room/Service Point QR boundaries;
- Unified Inbox, Telegram/n8n/AI contract boundaries;
- backup/restore tooling, production package and final management acceptance.

The public website source remained frozen during PR #122.

## 5. Mandatory external blockers

Production cutover remains **STOP** until current real evidence exists for all required gates:

1. GitHub `main` branch protection and required checks;
2. Google Drive launch-control permission hardening;
3. actual target host/account/network preflight;
4. verified rollback package for current live `3korony.com`;
5. restore rehearsal / rollback verification;
6. isolated external HTTPS/WSS staging;
7. exact accepted SHA/image linkage on staging;
8. real staging room reconciliation to 84 rooms / 12 categories;
9. external public-truth probe;
10. real iPhone / Android / desktop / Staff / Kitchen acceptance;
11. real E2E for every provider enabled at launch;
12. monitoring/alerting evidence;
13. fresh pre-cutover backup and verified off-site copy;
14. exact DNS rollback capture;
15. explicit owner GO for production/DNS switch.

No GitHub CI result alone authorizes DNS cutover.

## 6. Repository gates

```bash
python scripts/release_rc_truth_guard.py
python scripts/verify_launch_acceptance.py --mode repository
```

Final structural cutover evidence check, only after real evidence exists:

```bash
python scripts/verify_launch_acceptance.py \
  --mode cutover \
  --manifest /secure/path/launch-evidence.json \
  --release-sha 609a309c97f30b5f95828956188507fc35ed3d0d
```

## 7. External staging order

1. `git fetch origin && git checkout main && git pull --ff-only`.
2. Verify `release/current-rc.json` and run release guard.
3. Run `bash scripts/host_preflight.sh`.
4. Run environment preflight with staging secrets only.
5. Preserve and checksum the legacy-site rollback package.
6. Provision persistent PostgreSQL/media/n8n storage.
7. Apply all 22 migrations.
8. Reconcile canonical room register: dry-run -> exact diff review -> safe apply -> zero diff.
9. Build/deploy exact accepted SHA `609a309c97f30b5f95828956188507fc35ed3d0d`.
10. Start Core/Public/Admin/Staff/Kitchen and required n8n services.
11. Verify HTTPS, WSS, secure cookies, exact CORS, private PostgreSQL and persistent storage.
12. Run full external staging acceptance and real-device checks.
13. Create and verify fresh backup/restore evidence.
14. Only then prepare controlled production cutover.

## 8. Production preflight and observability

Actual target must pass `scripts/production_preflight.py` with real environment/database evidence. Require monitoring for readiness, HTTP 5xx, container restarts, PostgreSQL disk/storage, backup age/failure, TLS expiry, AuditLog retention and exact deployed SHA/image identity.

## 9. Controlled cutover

Only after every external gate is VERIFIED:

1. reconfirm 0.62.0 frozen RC and exact accepted SHA;
2. take fresh backup and verify off-site copy;
3. confirm legacy/DNS rollback target;
4. rerun host and production preflight;
5. confirm device/provider/monitoring evidence;
6. obtain explicit owner approval;
7. deploy exact accepted image set;
8. run readiness/smoke before public switch;
9. switch DNS/routing in a controlled window;
10. rerun Public/Booking/PMS/Guest OS/Staff/Kitchen smoke;
11. monitor; roll back if acceptance criteria fail.

**EXTERNAL PRODUCTION CUTOVER STOP** remains in force until all prerequisites above are verified.
