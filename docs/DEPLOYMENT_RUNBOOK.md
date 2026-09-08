# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Version: 6.3  
Date: 2026-09-08  
Status: RESORT OS 0.62.2 INTERNAL RC FROZEN / REPOSITORY VERIFIED / EXTERNAL CUTOVER STOP

This runbook defines controlled external deployment. It is not evidence that deployment has happened.

Canonical state: `knowledge/04_CURRENT_STATE.md`.  
Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md`.  
Canonical machine manifest: `release/current-rc.json`.

## 1. Release boundary

Release: `0.62.2`.  
Accepted source PR: `#143`.  
Accepted executable/release-boundary head: `ac1a45e4cf3ef0e40a7fea6be75c81999e9af0b4`.  
Observed tree-equivalent main merge: `c931b7e12973ecb62b8f9595d60f0d7947e7ad8e`.  
Production source branch: `main`.

Evidence: accepted head **24/24 SUCCESS**; observed merge **23/23 applicable non-truth workflows SUCCESS**. The additional failed push workflow was the expected `Release RC Truth CI` fail-close against the previous frozen boundary. Runtime remains 0.62.2.

## 2. Approved topology

Single-server V1: Caddy HTTPS/WSS edge, PostgreSQL 16 private Docker network, FastAPI Resort Core, Public Next.js, Admin/PMS Next.js, Staff/Kitchen PWA, pinned n8n when enabled, persistent database/media/n8n storage and local + off-site verified backup.

Authority: `PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`.

Authenticated browser realtime must remain same-origin on Admin/Staff hosts. PostgreSQL must remain private. Production runtime images must use the exact audited pins encoded by the release configuration; floating `latest` is not release evidence.

## 3. Host preflight

Before mutating a real host run `bash scripts/host_preflight.sh`. Do not proceed on `BLOCKED`. Recommended initial target remains Ubuntu 24.04 LTS, 4 vCPU, 8 GB RAM, 120–160 GB SSD/NVMe, static IPv4, sudo/root SSH, Docker Engine + Compose plugin. PostgreSQL must never be publicly exposed.

## 4. Persistent layout

Use `/srv/three-crowns` with persistent PostgreSQL, n8n, public/private media and backups. Repository checkout may be replaced; persistent data/backups must not be deleted with it.

## 5. Preserve legacy production first

Before DNS/apex or web-server changes: record DNS/IP/TTL, capture current web root/config, archive files/media, dump legacy DB if present, checksum artifacts, verify off-site copy, document rollback action/owner and keep current live site serving until staging acceptance passes.

## 6. Environment and secrets

Create `.env.production` only on the server from the example. Generate independent strong secrets. Never commit production secrets. Keep exact audited runtime pins. Mutating CI/demo utilities are not deployment tools.

Do not broaden `COOKIE_DOMAIN` to make realtime work. The accepted topology uses host-only sessions and same-origin Admin/Staff WebSocket routing. Do not remove WebSocket Origin enforcement or Caddy body-size boundaries.

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

## 8. First external staging sequence

1. check out `main` and confirm the 0.62.2 manifest;
2. run `python scripts/release_rc_truth_guard.py`;
3. verify GitHub/Drive launch-security gates and record any unresolved STOP items;
4. run host/environment preflight;
5. preserve and checksum the live legacy rollback package;
6. create persistent directories and staging secrets;
7. validate Compose graph and start private PostgreSQL;
8. apply all 22 migrations;
9. run production/database preflight;
10. reconcile canonical 84-room register to zero diff;
11. build exact accepted SHA `ac1a45e4cf3ef0e40a7fea6be75c81999e9af0b4`;
12. start Core/Public/Admin/Staff/Kitchen in isolated staging;
13. start n8n only after Core readiness;
14. route staging HTTPS/WSS and verify TLS, secure host-only cookies, exact CORS, WebSocket Origin policy, same-origin realtime and private PostgreSQL;
15. verify edge request-body limits: Telegram webhook 1 MB, generic public/admin/staff/API 2 MB, CMS media upload 8 MB;
16. run external business acceptance and real-device/provider checks;
17. run the guarded k6 baseline from `docs/LOAD_TESTING.md`; only increase pressure after resource headroom is observed;
18. prove monitoring/restart/self-healing;
19. take a fresh backup and perform clean restore plus off-site verification;
20. record immutable SHA/image/runtime linkage and DNS rollback evidence.

## 9. Load-test boundary

The repository contains a k6 read-pressure harness. It explicitly blocks `3korony.com` / `www.3korony.com`, requires `LOAD_TEST_ENV=ci|test|staging`, and does not mutate reservations, payments, stays or providers. Repository CI validates the harness itself; **actual Beget/VPS capacity is not proven until an isolated external staging run records latency, failure rate, CPU, RAM, PostgreSQL connections and recovery health.**

## 10. Required acceptance

Prove canonical site compatibility, Admin/PMS, Staff/Kitchen, Core readiness, secure HTTPS/WSS, same-origin authenticated realtime, request-body limits, server-authoritative reservation/pricing state, CLEAN check-in gate, checkout→DIRTY→housekeeping, Kitchen RBAC/menu/order/table lifecycle, active API route uniqueness, private PostgreSQL, guarded load thresholds, monitoring/restart recovery, backup→clean restore and executable legacy rollback.

## 11. Current blockers

Before production cutover:
- protect GitHub `main` and require the release/security checks;
- remove/downgrade public Google Drive writer grants;
- obtain an authorized Beget/VPS execution path;
- prove live rollback and target migration/reconciliation;
- prove external HTTPS/WSS and real-device/provider behavior;
- prove actual load capacity and monitoring;
- prove backup/restore/off-site evidence;
- record immutable deployment linkage and DNS rollback.

## 12. Production cutover gate

Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until all actual-target evidence exists and explicit owner GO is recorded. No CI success alone authorizes DNS switching or provider activation.
