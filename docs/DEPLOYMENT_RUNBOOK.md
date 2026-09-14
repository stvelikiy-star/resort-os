# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Version: 6.5  
Date: 2026-09-14  
Status: RESORT OS 0.62.2 INTERNAL RC REFROZEN / FULL TEST VERIFIED / EXTERNAL CUTOVER STOP

This runbook defines controlled external deployment. It is not evidence that real hotel production cutover has happened.

Canonical state: `knowledge/04_CURRENT_STATE.md`.  
Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md`.  
Canonical machine manifest: `release/current-rc.json`.

## 1. Release boundary

Release: `0.62.2`.  
Accepted source PR: `#164`.  
Accepted executable/release-boundary head: `61bd40d7592e842a4d52cfb343483065afb378cb`.  
Observed main merge: `94c849a0833079627b47db1e25869096191424bc`.  
Production source branch: `main`.

PR #164 head passed **26/26 workflows**. Its first main push passed **25/26**; only `Release RC Truth CI` failed closed because the frozen manifest still pointed at the prior executable boundary. The head and merge differ only by the exact already-accepted PR #163 operational merge-guard files. Runtime remains `0.62.2`.

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

Migration authority: `docs/PRODUCTION_DATABASE_MIGRATIONS.md`.

Canonical migration ledger, in exact deployment order:
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
- Public booking request shows exactly `Заявка отправлена. Номер заявки <id>. Менеджер свяжется с вами для согласования условий и предоплаты.` only after the server accepts the request, and still states that the request is not yet a confirmed reservation;
- Admin contains **Маркетинг** and **Агенты**;
- PMS drag/drop does not commit before explicit schedule confirmation;
- extra beds are rejected by Core for `DOUBLE_STANDARD_BASEMENT`, `DOUBLE_IMPROVED`, `TWO_ROOM_STANDARD` and recalculate for allowed room types;
- returning guest with prior `CHECKED_OUT` stay receives automatic 10% accommodation discount;
- Reception filters by agent and agent reports separate booked amount from actual received payments;
- Reception can create dated maintenance/manual holds for owner/staff/guest/service/other use;
- Guest OS, Staff/housekeeping/maintenance, Kitchen/Dining, Finance and realtime pass their acceptance flows;
- no fake payment is created by reservation creation.

## 8. Verified Full Test operational evidence

Railway `Three Crowns Full Test` has already proved:
- API/Public/Admin/Staff external HTTPS and WSS-path reachability;
- daily Chromium acceptance and 6-hour external smoke;
- explicit `ON_FAILURE` self-healing for application services;
- read-only k6 load through 50 VU: **32,229 HTTP requests, 0% failures, overall p95 38.49 ms, availability p95 42.25 ms**;
- recovery after the load test with observed API/PostgreSQL resource headroom;
- repository PostgreSQL backup -> clean restore CI.

These results guide sizing and procedure but must be re-observed on the actual production host.

## 9. First external production-like staging sequence

1. check out `main` and verify release `0.62.2`, accepted head `61bd40d7592e842a4d52cfb343483065afb378cb` and observed merge `94c849a0833079627b47db1e25869096191424bc`;
2. run `python scripts/release_rc_truth_guard.py`;
3. verify GitHub/Drive launch-security gates;
4. run host/environment preflight;
5. preserve and checksum the live rollback package;
6. create persistent directories and staging secrets;
7. start private PostgreSQL;
8. apply all **24** migrations;
9. run production/database preflight;
10. reconcile canonical **84 rooms / 12 categories / 48 rates** to zero diff;
11. build/deploy the accepted product boundary plus exact accepted ops-only merge drift;
12. start Core/Public/Admin/Staff/Kitchen and n8n only after Core readiness;
13. verify HTTPS/WSS, secure host-only cookies, CORS, WebSocket Origin policy, same-origin realtime and private PostgreSQL;
14. verify request-body limits and media-upload boundary;
15. run business acceptance, including Marketing/Agents/room holds/pricing corrections and exact Public confirmation copy;
16. run real-device/provider checks;
17. re-run guarded load baseline with target resource observations;
18. prove monitoring/restart/self-healing on the target;
19. take fresh target backup and perform clean restore plus off-site verification;
20. record immutable SHA/image/runtime linkage and DNS rollback evidence.

## 10. Current blockers

Before production cutover:
- enable real GitHub `main` branch protection/required checks; the current CI merge guard is not a platform protection substitute;
- verify/remediate public Google Drive writer grants if present;
- obtain an authorized real production execution path;
- prove target rollback and exact migration/room reconciliation;
- prove final production HTTPS/WSS and real-device/provider behavior;
- prove actual-target backup/restore/off-site evidence;
- record immutable deployment linkage and tested DNS rollback.

## 11. Production cutover gate

Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until all actual-target evidence exists and explicit owner GO is recorded. No CI or Railway Full Test success alone authorizes DNS switching or provider activation.
