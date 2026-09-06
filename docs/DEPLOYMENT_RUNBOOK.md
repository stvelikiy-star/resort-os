# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Version: 6.0  
Date: 2026-09-07  
Status: RESORT OS 0.62.0 INTERNAL RC FROZEN / REPOSITORY VERIFIED / EXTERNAL CUTOVER STOP

This runbook defines controlled external deployment. It is not evidence that deployment has happened.

Canonical state: `knowledge/04_CURRENT_STATE.md`.  
Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md`.  
Canonical machine manifest: `release/current-rc.json`.

## 1. Release boundary

Release: `0.62.0`.
Accepted source PR: `#122`.
Accepted executable head: `609a309c97f30b5f95828956188507fc35ed3d0d`.
Observed tree-equivalent main merge: `bccc491ea24c94668ef1bea4d86fb61a5b8e6f3d`.
Production source branch: `main`.

Evidence: accepted head **21/21 SUCCESS**; observed merge **20 eligible product/security/migration/staging SUCCESS**; the only failed push workflow was the expected fail-closed `Release RC Truth CI` caused by the previous 0.61.0 manifest.

## 2. Approved topology

Single-server V1:

- Caddy HTTPS/WSS edge;
- PostgreSQL 16 private to Docker network;
- FastAPI Resort Core;
- Public Next.js site;
- Admin/PMS Next.js;
- Staff PWA / Kitchen;
- n8n pinned production runtime when enabled;
- persistent PostgreSQL/media/n8n storage;
- local backup directory plus verified off-site copy.

Authority: `PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`.

## 3. Host preflight

Before mutating a real host:

```bash
bash scripts/host_preflight.sh
```

Do not proceed on `BLOCKED`. Existing listeners on 80/443 are a warning because the legacy site may still be live.

Recommended initial target: Ubuntu 24.04 LTS, 4 vCPU, 8 GB RAM, 120–160 GB SSD/NVMe, static IPv4, sudo/root SSH, Docker Engine + Compose plugin.

PostgreSQL must never be publicly exposed.

## 4. Persistent layout

Use `/srv/three-crowns` with separate persistent data and backups:

- `/srv/three-crowns/data/postgres`;
- `/srv/three-crowns/data/n8n`;
- `/srv/three-crowns/data/media/public`;
- `/srv/three-crowns/data/media/private`;
- `/srv/three-crowns/backups`.

Repository checkout may be replaced; persistent data/backups must not be deleted with it.

## 5. Preserve legacy production first

Before DNS/apex or web-server changes:

1. record current DNS/IP/TTL;
2. capture current web root/source and web-server config;
3. archive site files and media;
4. dump legacy DB if present;
5. checksum every rollback artifact;
6. verify off-site copy;
7. document exact rollback action and owner;
8. keep the current site serving until staging acceptance completes.

## 6. Environment and secrets

Create `.env.production` only on the server from `.env.production.example`.
Generate independent strong values for PostgreSQL, automation service key, n8n encryption and enabled provider secrets.
Never commit production secrets or include `.env.production` in ordinary backups.

Production baseline keeps the tested pinned n8n image; never replace it with `latest` without a tested release change.

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

1. check out `main` and confirm manifest 0.62.0;
2. run `python scripts/release_rc_truth_guard.py`;
3. run host/environment preflight;
4. preserve verified legacy rollback package;
5. create persistent directories with restricted permissions;
6. provision staging secrets;
7. validate Docker Compose graph;
8. start private PostgreSQL only;
9. apply all 22 migrations;
10. run production/database preflight;
11. reconcile canonical room register: dry-run -> exact diff review -> safe apply -> zero diff;
12. build exact accepted SHA `609a309c97f30b5f95828956188507fc35ed3d0d`;
13. start Core/Public/Admin/Staff in isolated staging contour;
14. start n8n only after Core readiness;
15. route Caddy staging hostnames and verify TLS/WSS;
16. run external staging acceptance;
17. complete iPhone/Android/desktop/Staff/Kitchen tests;
18. take fresh backup and perform clean restore verification.

## 9. Required staging acceptance

Prove:

- canonical site is served on staging;
- Admin/PMS and Staff/Kitchen are the accepted interfaces;
- Core `/health/ready` succeeds through HTTPS;
- secure cookies and exact CORS work;
- WSS upgrades work;
- Core remains pricing/availability authority;
- website creates `ReservationRequest`, not guaranteed Reservation;
- PMS stale/conflict/move/resize/Split Stay protections remain server-authoritative;
- CLEAN check-in gate and checkout -> DIRTY -> housekeeping work;
- Kitchen menu/order/table lifecycle works with correct RBAC;
- PostgreSQL is not publicly reachable;
- NFC routes remain outside active V1;
- backup -> clean restore evidence is current;
- legacy rollback remains executable.

## 10. Backups

Use repository backup tooling and verify every backup by clean restore. Initial policy: nightly local backups, at least 14 daily restore points, provider snapshot capability and an off-site copy.

A backup is not verified until restore is tested.

## 11. Update/rollback

For every release: fresh backup -> record running SHA/images -> fetch accepted release -> migration/preflight -> build -> replace containers -> health/smoke -> retain previous release and backup until acceptance.

Application rollback and database rollback are separate decisions. Never improvise destructive reverse SQL.

## 12. Production cutover gate

Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until all required external evidence in `knowledge/09_LAUNCH_ACCEPTANCE.md` is verified, including branch protection, Drive permissions, real host/staging/device/provider/monitoring/backup/DNS rollback evidence and explicit owner GO.

No CI success alone authorizes DNS switching or provider activation.
