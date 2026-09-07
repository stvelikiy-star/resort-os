# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Version: 6.2  
Date: 2026-09-07  
Status: RESORT OS 0.62.2 INTERNAL RC FROZEN / REPOSITORY VERIFIED / EXTERNAL CUTOVER STOP

This runbook defines controlled external deployment. It is not evidence that deployment has happened.

Canonical state: `knowledge/04_CURRENT_STATE.md`.  
Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md`.  
Canonical machine manifest: `release/current-rc.json`.

## 1. Release boundary

Release: `0.62.2`.  
Accepted source PR: `#135`.  
Accepted executable/release-boundary head: `d851c5c64a103ab263b977b3b07c970f29676783`.  
Observed tree-equivalent main merge: `b477e76a32b7fc0fdf8a349cda400c7fa12bc297`.  
Production source branch: `main`.

Evidence: accepted head **22/22 SUCCESS**; observed merge **20/20 applicable non-truth workflows SUCCESS**. The additional failed push workflow was the expected `Release RC Truth CI` fail-close against the previous frozen boundary. Runtime remains 0.62.2.

## 2. Approved topology

Single-server V1: Caddy HTTPS/WSS edge, PostgreSQL 16 private Docker network, FastAPI Resort Core, Public Next.js, Admin/PMS Next.js, Staff/Kitchen PWA, pinned n8n when enabled, persistent database/media/n8n storage and local + off-site verified backup.

Authority: `PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`.

## 3. Host preflight

Before mutating a real host run `bash scripts/host_preflight.sh`. Do not proceed on `BLOCKED`. Recommended initial target remains Ubuntu 24.04 LTS, 4 vCPU, 8 GB RAM, 120–160 GB SSD/NVMe, static IPv4, sudo/root SSH, Docker Engine + Compose plugin. PostgreSQL must never be publicly exposed.

## 4. Persistent layout

Use `/srv/three-crowns` with persistent PostgreSQL, n8n, public/private media and backups. Repository checkout may be replaced; persistent data/backups must not be deleted with it.

## 5. Preserve legacy production first

Before DNS/apex or web-server changes: record DNS/IP/TTL, capture current web root/config, archive files/media, dump legacy DB if present, checksum artifacts, verify off-site copy, document rollback action/owner and keep current live site serving until staging acceptance passes.

## 6. Environment and secrets

Create `.env.production` only on the server from the example. Generate independent strong secrets. Never commit production secrets. Keep n8n pinned. Mutating CI/demo utilities are not deployment tools.

## 7. Database contract

Release boundary: **22 migrations / 87 critical constraints / 84 rooms / 12 categories / 48 rates**.

Apply only committed migrations:

```bash
cd packages/database
npm ci
npx prisma validate
npx prisma migrate deploy
npx prisma migrate status
cd ../..
```

Never use `prisma db push` for external staging/production.

## 8. First external staging sequence

1. check out `main` and confirm 0.62.2 manifest;
2. run `python scripts/release_rc_truth_guard.py`;
3. run host/environment preflight;
4. preserve verified legacy rollback package;
5. create persistent directories and staging secrets;
6. validate Compose graph and start private PostgreSQL;
7. apply all 22 migrations;
8. run production/database preflight;
9. reconcile canonical 84-room register to zero diff;
10. build exact accepted SHA `d851c5c64a103ab263b977b3b07c970f29676783`;
11. start Core/Public/Admin/Staff/Kitchen in isolated staging;
12. start n8n only after Core readiness;
13. route staging HTTPS/WSS and verify TLS, secure cookies, exact CORS and private PostgreSQL;
14. run external staging acceptance and real-device/provider checks;
15. run the guarded k6 baseline from `docs/LOAD_TESTING.md`; only increase to 25→100→250 VUs after resource headroom is observed;
16. take fresh backup and perform clean restore/off-site verification.

## 9. Load-test boundary

The repository now contains a k6 read-pressure harness. It explicitly blocks `3korony.com` / `www.3korony.com`, requires `LOAD_TEST_ENV=ci|test|staging`, and does not mutate reservations, payments, stays or providers. Repository CI validates the harness itself; **actual Beget capacity is not proven until an isolated external staging run records latency, failure rate, CPU, RAM, PostgreSQL connections and recovery health.**

## 10. Required acceptance

Prove canonical site compatibility, Admin/PMS, Staff/Kitchen, Core readiness, WSS, server-authoritative reservation/pricing state, CLEAN check-in gate, checkout→DIRTY→housekeeping, Kitchen RBAC/menu/order/table lifecycle, active API route uniqueness, private PostgreSQL, guarded load thresholds, backup→clean restore and executable legacy rollback.

## 11. Current blockers

Before production cutover: protect GitHub `main`, remove/downgrade public Google Drive writer grants, obtain authorized Beget/VPS execution, prove live rollback, external HTTPS/WSS, real devices/providers, monitoring, actual load evidence, backup/restore/off-site copy, immutable release/image/deployment linkage and DNS rollback.

## 12. Production cutover gate

Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until all actual-target evidence exists and explicit owner GO is recorded. No CI success alone authorizes DNS switching or provider activation.
