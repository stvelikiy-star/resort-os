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
Accepted source PR: `#127`.  
Accepted executable head: `b79e22ee56c43e5f9146df7597d4c9e5e4124afa`.  
Observed tree-equivalent main merge: `731e81c2d2a4ccc91fae319b73f0d4b8eb9979b5`.  
Production source branch: `main`.

Evidence: accepted head **41/41 SUCCESS**; observed merge **32/32 eligible SUCCESS**; the only additional failed push workflow was expected `Release RC Truth CI` fail-close against the previous 0.62.1 executable boundary.

## 2. Approved topology

Single-server V1: Caddy HTTPS/WSS edge, PostgreSQL 16 private Docker network, FastAPI Resort Core, Public Next.js, Admin/PMS Next.js, Staff/Kitchen PWA, pinned n8n when enabled, persistent database/media/n8n storage and local + off-site verified backup.

Authority: `PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`.

## 3. Host preflight

Before mutating a real host:

```bash
bash scripts/host_preflight.sh
```

Do not proceed on `BLOCKED`. Recommended initial target remains Ubuntu 24.04 LTS, 4 vCPU, 8 GB RAM, 120–160 GB SSD/NVMe, static IPv4, sudo/root SSH, Docker Engine + Compose plugin. PostgreSQL must never be publicly exposed.

## 4. Persistent layout

Use `/srv/three-crowns` with:
- `/srv/three-crowns/data/postgres`
- `/srv/three-crowns/data/n8n`
- `/srv/three-crowns/data/media/public`
- `/srv/three-crowns/data/media/private`
- `/srv/three-crowns/backups`

Repository checkout may be replaced; persistent data/backups must not be deleted with it.

## 5. Preserve legacy production first

Before DNS/apex or web-server changes: record DNS/IP/TTL, capture current web root/config, archive files/media, dump legacy DB if present, checksum artifacts, verify off-site copy, document rollback action/owner and keep current live site serving until staging acceptance passes.

## 6. Environment and secrets

Create `.env.production` only on the server from `.env.production.example`. Generate independent strong secrets. Never commit production secrets. Keep n8n pinned; do not replace with `latest` without a tested release change.

## 7. Database contract

Release boundary: **22 migrations / 87 critical constraints / 84 rooms / 12 categories / 48 rates**.

Canonical 22-migration ledger:
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

## 8. First external staging sequence — deferred until final Beget/VPS phase

1. check out `main` and confirm 0.62.2 manifest;
2. run `python scripts/release_rc_truth_guard.py`;
3. run host/environment preflight;
4. preserve verified legacy rollback package;
5. create persistent directories and staging secrets;
6. validate Compose graph and start private PostgreSQL;
7. apply all 22 migrations;
8. run production/database preflight;
9. reconcile canonical room register to zero diff;
10. build exact accepted SHA `b79e22ee56c43e5f9146df7597d4c9e5e4124afa`;
11. start Core/Public/Admin/Staff/Kitchen in isolated staging;
12. start n8n only after Core readiness;
13. route staging HTTPS/WSS and verify TLS, secure cookies, exact CORS and private PostgreSQL;
14. run external staging acceptance and real-device/provider checks;
15. take fresh backup and perform clean restore verification.

## 9. Required acceptance

Prove canonical site compatibility, Admin/PMS, Staff/Kitchen, Core readiness, WSS, server-authoritative reservation/pricing state, CLEAN check-in gate, checkout→DIRTY→housekeeping, Kitchen RBAC/menu/order/table lifecycle, active API route uniqueness, private PostgreSQL, backup→clean restore and executable legacy rollback.

## 10. Backups and rollback

A backup is not verified until restore is tested. For every release: fresh backup → record running SHA/images → fetch accepted release → migrations/preflight → build → replace containers → health/smoke → retain previous release and backup until acceptance. Application rollback and database rollback are separate decisions; never improvise destructive reverse SQL.

## 11. Current plan boundary

GitHub branch protection and Google Drive permission hardening are advisory/deferred by owner decision. Beget/VPS is the final phase, not the current one.

## 12. Production cutover gate

Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until actual-target rollback, staging, device/provider, monitoring, backup/restore/off-site and DNS rollback evidence exists and explicit owner GO is recorded. No CI success alone authorizes DNS switching or provider activation.
