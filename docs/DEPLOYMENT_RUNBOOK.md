# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Version: 6.7  
Date: 2026-09-18  
Status: RESORT OS 0.62.2 INTERNAL RC FROZEN / FULL_NO_PAYMENTS / INTERNAL CI GREEN / EXTERNAL CUTOVER STOP

This runbook defines controlled external deployment. It is not evidence that real hotel production cutover has happened.

Canonical state: `knowledge/04_CURRENT_STATE.md`.  
Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md`.  
Canonical machine manifest: `release/current-rc.json`.

## 1. Release boundary

Release: `0.62.2`.  
Launch profile: `FULL_NO_PAYMENTS`.  
Accepted executable source PR: `#176`.  
Exact tested PR #176 head: `a3ff4c847c66cd64a7cca92ccec613f23917f62d`.  
Accepted executable/release-boundary head: `a53850983d8fc6e1f1997199049a5b071511ed80`.  
Current governance/main head: `b20ea27d9fd7950e0a22f164413156e8b62355ec` (PR #177 controlled refreeze).  
Production source branch: `main`.

Evidence:
- PR #176: **29/29 workflows SUCCESS**;
- first main push for accepted executable: **25/26 SUCCESS**; only `Release RC Truth CI` correctly failed closed against the previous frozen boundary;
- PR #177 release/governance refreeze: **25/25 PR workflows SUCCESS**;
- post-refreeze main: **24/24 SUCCESS**, including Release RC Truth and Resort OS Release Gate.

The product runtime boundary is `a5385098...`. Later governance/docs-only merges do not replace that executable boundary unless a controlled refreeze explicitly says so.

## 2. Approved topology

Single-server V1: Caddy HTTPS/WSS edge, PostgreSQL 16 private network, FastAPI Resort Core, Public Next.js, Admin/PMS Next.js, Staff/Kitchen PWA, pinned n8n when enabled, persistent database/media/n8n storage and local + restricted off-site verified backup.

Authority:

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Authenticated browser realtime must remain same-origin on Admin/Staff hosts. PostgreSQL must remain private. Production runtime images must use exact audited pins; floating `latest` is not release evidence.

Production hostname plan:
- `3korony.com` — Public;
- `api.3korony.com` — Resort Core;
- `admin.3korony.com` — Admin/PMS;
- `staff.3korony.com` — Staff/Kitchen;
- `automation.3korony.com` — n8n when enabled.

## 3. Launch capability contract

External staging/production for this release must preserve `FULL_NO_PAYMENTS`.

Required enabled contours:
- Public Web;
- PMS / Reception;
- CRM / Agents / Marketing;
- Staff / housekeeping / maintenance / voice;
- Guest OS;
- Kitchen / Dining;
- automation / AI sales within authority limits;
- realtime / WebSocket.

Required fail-closed contours:
- payment mutation routes;
- bank/provider acquiring;
- Service Point payment QR operations;
- MKassa;
- NFC wallet/acquiring.

Guest OS room QR/PIN remains allowed as a non-payment guest-service surface. It is not a payment QR and not a physical smart-lock credential.

TTLock/TTHotel provider authorization is deferred under issue #154 and is not an active launch gate for `FULL_NO_PAYMENTS`.

Never enable dormant payment/provider code merely to make a staging check pass.

## 4. Host preflight

Before mutating a real host run:

```bash
bash scripts/host_preflight.sh
```

Do not proceed on `BLOCKED`.

Recommended initial target remains Ubuntu 24.04 LTS, 4 vCPU, 8 GB RAM, 120–160 GB SSD/NVMe, static IPv4, sudo/root SSH, Docker Engine + Compose plugin. PostgreSQL must never be publicly exposed.

Secure host access must be authorized and must keep private keys/passwords/secrets outside chat and source control.

## 5. Persistent layout and rollback

Use `/srv/three-crowns` with persistent PostgreSQL, n8n, public/private media and backups. Repository checkout may be replaced; persistent data/backups must not be deleted with it.

Before DNS or web-server changes, two independent rollback evidence sets are mandatory:
1. legacy site rollback package (`legacy_rollback_capture.py` -> restore rehearsal -> `legacy_rollback_gate.py`) covering current web root/config/media/database and legacy DNS state;
2. production DNS rollback package covering all five planned production hostnames, including previously absent records.

Capture DNS immediately before routing changes:

```bash
python scripts/dns_rollback_capture.py \
  --output-dir /secure/path/dns-rollback-$(date -u +%Y%m%dT%H%M%SZ) \
  --offsite-dir /mounted/restricted-offsite-copy \
  --rollback-owner OWNER
```

Then require:

```bash
python scripts/dns_rollback_gate.py \
  /secure/path/dns-rollback-YYYYMMDDTHHMMSSZ \
  --max-age-hours 24 \
  --output /secure/path/dns-rollback-evidence.json
```

`DNS_ROLLBACK_GATE_GREEN` is required before any production DNS mutation. The capture/gate never changes DNS.

Keep the current live site serving until external acceptance passes. Do not edit DNS merely to test rollback tooling.

## 6. Environment and secrets

Create `.env.production` only on the server from `.env.production.example`. Generate independent strong secrets. Never commit production secrets.

Required launch flags for this release:

```dotenv
LAUNCH_PROFILE=FULL_NO_PAYMENTS
ENABLE_PUBLIC_SITE=true
ENABLE_PMS=true
ENABLE_CRM=true
ENABLE_STAFF=true
ENABLE_GUEST_OS=true
ENABLE_KITCHEN=true
ENABLE_AUTOMATION=true
ENABLE_AI_SALES=true
ENABLE_PAYMENT_OPERATIONS=false
ENABLE_SERVICE_POINT_QR=false
ENABLE_MKASSA=false
```

Keep NFC wallet/acquiring disabled.

Do not broaden `COOKIE_DOMAIN` to make realtime work. Keep host-only sessions, same-origin Admin/Staff WebSocket routing, Origin enforcement and request-body limits.

## 7. Database contract

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

Historical migration names containing payment/service-point tables do not enable those runtime capabilities.

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

## 8. Product acceptance required after deployment

At minimum verify:
- `GET /api/v1/runtime/capabilities` reports launch profile `FULL_NO_PAYMENTS` and required operational contours enabled;
- payment mutation/provider routes are absent or fail-closed under the launch profile;
- Admin payment-mutation UI is hidden/blocked while historical/control finance reads remain available;
- Public booking request shows exactly `Заявка отправлена. Номер заявки <id>. Менеджер свяжется с вами для согласования условий и предоплаты.` only after the server accepts the request, and still states that the request is not yet a confirmed reservation;
- Public submission does not create a fake payment or provider payment QR;
- Admin contains **Маркетинг** and **Агенты**;
- PMS drag/drop does not commit before explicit schedule confirmation;
- extra beds are rejected by Core for `DOUBLE_STANDARD_BASEMENT`, `DOUBLE_IMPROVED`, `TWO_ROOM_STANDARD` and recalculate for allowed room types;
- returning guest with prior `CHECKED_OUT` stay receives automatic 10% accommodation discount;
- Reception filters by agent and agent reports separate booked amount from actual received-payment history;
- Reception can create dated maintenance/manual holds for owner/staff/guest/service/other use;
- Admin/Staff date-only hotel workflows use `Asia/Bishkek` business date semantics;
- Guest OS, Staff/housekeeping/maintenance, Kitchen/Dining and realtime pass their acceptance flows;
- Guest OS room QR/PIN remains non-payment and is not presented as a physical lock credential.

## 9. Internal operational evidence

Current internal release evidence proves:
- clean 24-migration / 93-constraint database contract;
- canonical 84/12/48 seed;
- Core compile and active-route uniqueness;
- Admin/Public/Staff builds;
- Site/PMS/CMS smoke;
- full-domain E2E;
- Dining/Kitchen acceptance;
- root control-center verification;
- backup/restore mechanism CI;
- release truth and launch acceptance;
- hotel business-date contract;
- `FULL_NO_PAYMENTS` route-surface contract.

These results guide external deployment but must be re-observed on the actual hotel target.

## 10. First external production-like staging sequence

1. use a clean product checkout pinned to accepted executable `a53850983d8fc6e1f1997199049a5b071511ed80`;
2. use a separate current ops/governance checkout only where release/readiness tooling requires it;
3. run `python scripts/release_rc_truth_guard.py`;
4. verify GitHub branch-protection and Drive-integrity launch gates;
5. run host/environment preflight;
6. preserve, checksum, restore-rehearse and off-site-copy the legacy live rollback package;
7. create persistent directories and server-side secrets;
8. start private PostgreSQL;
9. apply all **24** migrations;
10. run production/database preflight;
11. reconcile canonical **84 rooms / 12 categories / 48 rates** to zero unexplained diff;
12. build/deploy API/Web/Admin/Staff images from exact accepted executable `a5385098...`;
13. start Core/Public/Admin/Staff/Kitchen and n8n only after Core readiness;
14. verify runtime capabilities exactly match `FULL_NO_PAYMENTS`;
15. verify HTTPS/WSS, secure host-only cookies, CORS, WebSocket Origin policy, same-origin realtime and private PostgreSQL;
16. verify request-body limits and media-upload boundary;
17. run business acceptance across Public/PMS/CRM/Agents/Marketing/Guest OS/Staff/Kitchen/Dining/realtime;
18. run real iPhone Safari / Android Chrome / desktop / Staff-Kitchen device acceptance;
19. observe target load/resource behavior without enabling deferred provider/payment contours;
20. prove monitoring/restart/self-healing on the target;
21. take a fresh target backup, make a byte-identical restricted off-site copy, run isolated restore evidence, then require `PRE_CUTOVER_BACKUP_GATE_GREEN`;
22. run DNS rollback capture/gate immediately before routing changes and require `DNS_ROLLBACK_GATE_GREEN`;
23. record immutable accepted executable SHA/image/runtime linkage;
24. run unified technical readiness;
25. only after every required launch gate is VERIFIED and explicit owner GO exists, perform the separately authorized DNS cutover.

The exact backup/restore/off-site command sequence is canonical in `docs/PRODUCTION_DATABASE_MIGRATIONS.md`.

## 11. Unified technical cutover-readiness gate

After external staging is complete and manual governance/device prerequisites are already VERIFIED, run one final **read-only** technical readiness pass from the current ops checkout. Keep a separate clean product checkout pinned to accepted executable SHA `a5385098...`; the gate verifies running API/Web/Admin/Staff images carry that same revision.

Example:

```bash
python scripts/production_cutover_readiness.py \
  --release-sha a53850983d8fc6e1f1997199049a5b071511ed80 \
  --launch-manifest /secure/launch-evidence.json \
  --product-repo-root /srv/three-crowns/product-release \
  --rollback-evidence-dir /secure/legacy-rollback \
  --dns-evidence-dir /secure/dns-rollback \
  --backup-file /secure/pre-cutover/postgres.dump \
  --backup-manifest /secure/pre-cutover/manifest.json \
  --backup-offsite-dir /mounted/restricted-offsite-copy/pre-cutover \
  --restore-evidence /secure/pre-cutover/restore-evidence.json \
  --restore-owner OWNER \
  --env-file /srv/three-crowns/.env.production \
  --backup-dir /srv/three-crowns/backups \
  --disk-path /srv/three-crowns \
  --public-url https://3korony.com \
  --core-url https://api.3korony.com \
  --admin-url https://admin.3korony.com \
  --staff-url https://staff.3korony.com \
  --wss-url wss://api.3korony.com/ws/pms/grid \
  --output-dir /secure/readiness-final
```

The launch manifest must already prove manual/external prerequisites before this command can turn green: GitHub branch protection, Drive permission integrity, room reconciliation, external HTTPS/WSS staging and real-device acceptance.

For `FULL_NO_PAYMENTS`, provider-payment/TTLock acceptance is not required and those capabilities must remain disabled. If a future launch profile enables a provider, that provider's real acceptance becomes mandatory for that future profile.

**Safety boundary:** `owner_cutover_approval` must still be `NOT_VERIFIED` while this gate runs. `PRODUCTION_CUTOVER_TECHNICAL_READINESS_GREEN` means only that technical evidence is ready for owner review. It does not change DNS, enable payments/MKassa/TTLock, write hotel business data or authorize production.

After reviewing generated evidence, and only after explicit owner GO, update launch evidence and run:

```bash
python scripts/verify_launch_acceptance.py \
  --mode cutover \
  --manifest /secure/launch-evidence.json \
  --release-sha a53850983d8fc6e1f1997199049a5b071511ed80
```

Only `STRUCTURAL LAUNCH EVIDENCE COMPLETE` **after explicit owner GO** permits the separately authorized DNS cutover procedure.

## 12. Current blockers

Before production cutover:
- enable real GitHub `main` branch protection/required checks (#91);
- verify/remediate Google Drive permissions (#100);
- obtain authorized real Beget/VPS execution path (#72);
- prove isolated external target runtime (#28);
- prove target rollback and exact migration/room reconciliation (#8);
- prove final production HTTPS/WSS and real-device behavior;
- execute fresh actual-target backup/clean-restore/restricted off-site gate;
- execute authoritative DNS rollback capture/gate on the real zone immediately before routing changes;
- record immutable accepted executable deployment linkage (#40);
- run unified technical cutover-readiness gate and review evidence;
- record explicit owner GO only after every preceding item is complete.

Deferred payment/MKassa/NFC/TTLock work is not a blocker for the current `FULL_NO_PAYMENTS` profile.

## 13. Production cutover gate

Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until all actual-target evidence exists and explicit owner GO is recorded.

No CI success, synthetic Full Test result or technical readiness script alone authorizes DNS switching or provider activation.
