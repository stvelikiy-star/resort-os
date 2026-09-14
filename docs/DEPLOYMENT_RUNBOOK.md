# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Version: 6.4  
Date: 2026-09-14  
Status: RESORT OS 0.62.2 INTERNAL RC REFROZEN / FULL TEST VERIFIED / EXTERNAL CUTOVER STOP

This runbook defines controlled external deployment. It is not evidence that real hotel production cutover has happened.

Canonical state: `knowledge/04_CURRENT_STATE.md`.  
Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md`.  
Canonical machine manifest: `release/current-rc.json`.

## 1. Release boundary

Release: `0.62.2`.  
Accepted source PR: `#157`.  
Accepted executable/release-boundary head: `7ae394bbb549bb6200c84e9c46d47ed5cd45499a`.  
Observed tree-equivalent main merge: `b13bacad3f2e923f51354b1839371d07179b2e8c`.  
Production source branch: `main`.

Evidence: accepted PR head **52/52 SUCCESS**. First merge push produced **37/39 SUCCESS**; `Release RC Truth CI` and `Launch Acceptance CI` intentionally failed closed against the old frozen boundary and are corrected by this same-version refreeze. Runtime remains 0.62.2.

Railway `Three Crowns Full Test` is deployed from merge SHA `b13bacad3f2e923f51354b1839371d07179b2e8c` for API/Web/Admin/Staff. This is integration/staging evidence only.

## 2. Approved topology

Single-server V1: Caddy HTTPS/WSS edge, PostgreSQL 16 private network, FastAPI Resort Core, Public Next.js, Admin/PMS Next.js, Staff/Kitchen PWA, pinned n8n when enabled, persistent database/media/n8n storage and local + off-site verified backup.

Authority: `PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`.

Authenticated browser realtime must remain same-origin on Admin/Staff hosts. PostgreSQL must remain private. Production runtime images must use exact audited pins; floating `latest` is not release evidence.

## 3. Host preflight

Before mutating a real host run `bash scripts/host_preflight.sh`. Do not proceed on `BLOCKED`. Recommended initial target remains Ubuntu 24.04 LTS, 4 vCPU, 8 GB RAM, 120–160 GB SSD/NVMe, static IPv4, sudo/root SSH, Docker Engine + Compose plugin. PostgreSQL must never be publicly exposed.

## 4. Persistent layout and rollback

Use `/srv/three-crowns` with persistent PostgreSQL, n8n, public/private media and backups. Repository checkout may be replaced; persistent data/backups must not be deleted with it.

Before DNS/apex or web-server changes: record DNS/IP/TTL, capture current web root/config, archive files/media, dump legacy DB if present, checksum artifacts, verify off-site copy, document rollback action/owner and keep current live site serving until acceptance passes.

## 5. Environment and secrets

Create `.env.production` only on the server from the example. Generate independent strong secrets. Never commit production secrets. Keep audited runtime pins. Mutating CI/demo utilities are not deployment tools.

Do not broaden `COOKIE_DOMAIN` to make realtime work. Keep host-only sessions, same-origin Admin/Staff WebSocket routing, Origin enforcement and request-body limits.

## 6. Database contract

Release boundary: **24 migrations / 93 critical constraints / 84 rooms / 12 categories / 48 rates**.

Canonical 24-migration ledger:
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
23. `z99_marketing_consent_attribution_20260912`
24. `zz100_owner_ops_corrections_20260914`

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

## 7. Product acceptance required after deployment

At minimum verify:
- Public booking request returns a server-confirmed success state;
- Admin contains **Маркетинг** and **Агенты**;
- PMS drag/drop does not commit before explicit schedule confirmation;
- extra beds are rejected by Core for `DOUBLE_STANDARD_BASEMENT`, `DOUBLE_IMPROVED`, `TWO_ROOM_STANDARD` and recalculate for allowed room types;
- returning guest with prior `CHECKED_OUT` stay receives automatic 10% accommodation discount;
- Reception filters by agent and agent reports separate booked amount from actual received payments;
- Reception can create dated maintenance/manual holds for owner/staff/guest/service/other use;
- Guest OS, Staff/housekeeping/maintenance, Kitchen/Dining, Finance and realtime still pass their acceptance flows;
- no fake payment is created by reservation creation.

## 8. First external production-like staging sequence

1. check out `main` and verify release `0.62.2`, accepted head `7ae394bbb549bb6200c84e9c46d47ed5cd45499a` and merge `b13bacad3f2e923f51354b1839371d07179b2e8c`;
2. run `python scripts/release_rc_truth_guard.py`;
3. verify GitHub/Drive launch-security gates;
4. run host/environment preflight;
5. preserve and checksum the live rollback package;
6. create persistent directories and staging secrets;
7. start private PostgreSQL;
8. apply all **24** migrations;
9. run production/database preflight;
10. reconcile canonical 84-room register to zero diff;
11. build the accepted executable tree;
12. start Core/Public/Admin/Staff/Kitchen and n8n only after Core readiness;
13. verify HTTPS/WSS, secure host-only cookies, CORS, WebSocket Origin policy, same-origin realtime and private PostgreSQL;
14. verify request-body limits and media-upload boundary;
15. run business acceptance, including Marketing/Agents/room holds/pricing corrections;
16. run real-device/provider checks;
17. run guarded load baseline with resource observations;
18. prove monitoring/restart/self-healing;
19. take fresh backup and perform clean restore plus off-site verification;
20. record immutable SHA/image/runtime linkage and DNS rollback evidence.

## 9. Current Full Test result

Railway Full Test already proved the integrated merge can start with all four application services on one SHA. API successfully applied `z99_marketing_consent_attribution_20260912` and `zz100_owner_ops_corrections_20260914`, found all **24** migrations and returned readiness HTTP 200. This does not replace real production backup, rollback, device/provider or DNS evidence.

## 10. Current blockers

Before production cutover:
- protect GitHub `main` and require release/security checks;
- remove/downgrade public Google Drive writer grants;
- obtain an authorized real production execution path;
- prove target rollback and 24-migration/room reconciliation;
- prove external HTTPS/WSS and real-device/provider behavior;
- prove actual load capacity and monitoring;
- prove actual-target backup/restore/off-site evidence;
- record immutable deployment linkage and DNS rollback.

## 11. Production cutover gate

Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until all actual-target evidence exists and explicit owner GO is recorded. No CI or Railway Full Test success alone authorizes DNS switching or provider activation.
