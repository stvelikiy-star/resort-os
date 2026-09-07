# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Version: 6.1  
Date: 2026-09-07  
Status: RESORT OS 0.62.1 INTERNAL RC FROZEN / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

Repository/CI evidence is not external staging or production evidence.

## 1. Frozen release boundary

Repository: `stvelikiy-star/resort-os`.
Release: `0.62.1`.
Accepted source PR: `#125` — `audit/internal-hardening-20260907 -> main`.
Accepted executable head: `b3bb0c1be4c522d765509796ddd1d32e8606dc89`.
Observed tree-equivalent main merge: `7f689458b2cf507d76a8c54fbe164e9492f79aca`.
Post-merge truth reference: `7f689458b2cf507d76a8c54fbe164e9492f79aca`.
Production source branch: `main`.

Evidence:

- accepted PR #125 head: **28/28 workflows SUCCESS, 0 failures**;
- accepted head and observed merge share the same tree;
- observed main merge: **23 eligible product/security/migration/staging workflows SUCCESS**;
- `Release RC Truth CI` failed closed exactly because the previous 0.62.0 manifest detected executable drift after hardening; this 0.62.1 refreeze is the controlled correction;
- final post-merge Resort OS Release Gate completed successfully through migration, seed, Admin/Public/Staff builds, Core startup, domain E2E, Dining/Kitchen checks and root control-center verification.

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

0.62.1 contains the accepted management closure plus strict hardening:

- PMS/supershakhmatka, pricing/seasons, Reception, CRM and group booking;
- CLEAN check-in gate, Stay/RoomAssignment lifecycle and checkout -> DIRTY -> housekeeping;
- MAID/TECHNICIAN operations and TECH_BLOCK protection;
- Guest Services, Guest OS, PIN/session, offers and Guest CRM history;
- Kitchen/Dining production management, OWNER/MANAGER menu creation/publish/price control, DINING_STAFF operational access, table/session/order lifecycle and production snapshots;
- historical `/admin/demo` fail-closed to 404;
- Kitchen draft bootstrap denied to DINING_STAFF and fail-closed in production;
- Finance/folio/payment idempotency and owner analytics;
- Room/Service Point QR boundaries;
- Unified Inbox, Telegram/n8n/AI contract boundaries;
- backup/restore tooling, production package and final management acceptance;
- dedicated internal hardening suite with 100+ release/data/auth/Kitchen/external-gate assertions.

The public website source remained frozen during PR #125: **0 files under `apps/web/**` changed**.

## 5. External phase

Per owner plan, GitHub branch protection and Google Drive permission hardening are recommendations/deferred controls, not blockers for the current internal release. Beget/VPS is intentionally the final external phase.

Production cutover remains **STOP** until the final external phase verifies the applicable live evidence:

1. actual target host/account/network preflight;
2. verified rollback package for current live `3korony.com`;
3. restore rehearsal / rollback verification;
4. isolated external HTTPS/WSS staging;
5. exact accepted SHA/image linkage on staging;
6. real staging room reconciliation to 84 rooms / 12 categories;
7. external public-truth probe;
8. real iPhone / Android / desktop / Staff / Kitchen acceptance;
9. real E2E for every provider enabled at launch;
10. monitoring/alerting evidence;
11. fresh pre-cutover backup and verified off-site copy;
12. exact DNS rollback capture;
13. explicit owner GO for production/DNS switch.

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
  --release-sha b3bb0c1be4c522d765509796ddd1d32e8606dc89
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
9. Build/deploy exact accepted SHA `b3bb0c1be4c522d765509796ddd1d32e8606dc89`.
10. Start Core/Public/Admin/Staff/Kitchen and required n8n services.
11. Verify HTTPS, WSS, secure cookies, exact CORS, private PostgreSQL and persistent storage.
12. Run full external staging acceptance and real-device checks.
13. Create and verify fresh backup/restore evidence.
14. Only then prepare controlled production cutover.

## 8. Production preflight and observability

Actual target must pass `scripts/production_preflight.py` with real environment/database evidence. Require monitoring for readiness, HTTP 5xx, container restarts, PostgreSQL disk/storage, backup age/failure, TLS expiry, AuditLog retention and exact deployed SHA/image identity.

## 9. Controlled cutover

Only after every applicable external gate is VERIFIED:

1. reconfirm 0.62.1 frozen RC and exact accepted SHA;
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

**EXTERNAL PRODUCTION CUTOVER STOP** remains in force until the final external phase is completed and owner GO is explicit.
