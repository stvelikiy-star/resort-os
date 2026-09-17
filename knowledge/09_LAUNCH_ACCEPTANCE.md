# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Version: 6.7  
Date: 2026-09-18  
Status: RESORT OS 0.62.2 INTERNAL RC FROZEN / FULL_NO_PAYMENTS / INTERNAL CI GREEN / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

Repository/CI evidence is not real hotel production evidence.

## 1. Frozen release boundary

Repository: `stvelikiy-star/resort-os`.  
Release: `0.62.2`.  
Launch profile: `FULL_NO_PAYMENTS`.  
Accepted executable source PR: `#176`.  
Exact tested PR #176 head: `a3ff4c847c66cd64a7cca92ccec613f23917f62d`.  
Accepted executable/release-boundary head: `a53850983d8fc6e1f1997199049a5b071511ed80`.  
Current governance/main head: `b20ea27d9fd7950e0a22f164413156e8b62355ec` (PR #177 controlled refreeze).  
Production source branch: `main`.

Evidence:
- PR #176: **29/29 workflows SUCCESS, 0 failures**;
- first main push for accepted executable boundary: **25/26 SUCCESS**; only `Release RC Truth CI` failed closed against the previous frozen boundary;
- PR #177 release/governance refreeze: **25/25 PR workflows SUCCESS**;
- post-refreeze `main` at `b20ea27d...`: **24/24 SUCCESS**, including `Release RC Truth CI` and `Resort OS Release Gate`;
- executable boundary remains `a5385098...`; later governance/docs merge commits do not replace the accepted product runtime boundary.

Machine truth: `release/current-rc.json`. Guard: `scripts/release_rc_truth_guard.py`.

## 2. Product authority boundary

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`. OWNER/MANAGER retain reservation and factual payment authority. AI/n8n cannot confirm payment/reservation, invent policy, check guests in/out, refund or bypass Core pricing/availability.

The accepted contour includes:
- Public booking request and exact server-confirmed request-sent copy;
- PMS/Reception and explicit confirmation before schedule commit after drag/drop;
- CRM / Agents / Marketing;
- server-enforced extra-bed rules;
- returning-guest 10% accommodation discount;
- dated maintenance/manual room holds;
- Guest OS;
- Staff / housekeeping / maintenance / voice;
- Kitchen / Dining;
- realtime/WebSocket;
- hotel business-date handling using `Asia/Bishkek` for Admin/Staff date-only flows.

## 3. Launch capability contract

Required operational capabilities for `FULL_NO_PAYMENTS`:
- Public Web: ON;
- PMS / Reception: ON;
- CRM / Agents / Marketing: ON;
- Staff: ON;
- Guest OS: ON;
- Kitchen / Dining: ON;
- automation / AI sales within authority limits: ON;
- realtime: ON.

Required fail-closed capabilities:
- payment mutation routes: OFF;
- bank/provider acquiring: OFF;
- Service Point payment QR: OFF;
- MKassa: OFF;
- NFC wallet/acquiring: OFF.

Guest OS room QR/PIN remains permitted as a guest-service surface; it is not a payment QR and not a physical smart-lock credential.

Dormant provider/payment source code may remain in the repository but must not be exposed in the launch route surface unless a later separately approved launch profile explicitly enables it.

TTLock/TTHotel issue #154 is deferred and is not a current `FULL_NO_PAYMENTS` launch gate.

## 4. Database/property contract

Frozen release boundary: **24 committed migrations / 93 critical domain constraints**.  
Canonical property seed: **84 rooms / 12 categories / 48 rate rows**.

The final migrations remain:
- `z99_marketing_consent_attribution_20260912`;
- `zz100_owner_ops_corrections_20260914`.

External staging/production migration uses only `npx prisma migrate deploy`; `prisma db push` is never staging/production release evidence.

Historical migration names containing service-point/payment functionality do not make those runtime capabilities launch-enabled.

## 5. Repository/internal verification

Current verification covers:
- PMS/chessboard, Rates/Seasons, Reception, CRM, Agents, Marketing;
- Guest OS/Services/Offers;
- housekeeping/maintenance;
- Finance historical/control surfaces;
- Reports/Analytics;
- Staff/RBAC;
- Kitchen/Dining;
- Inbox and automation contracts;
- realtime;
- backup/restore mechanism;
- production package, release and staging gates;
- active-route uniqueness;
- mutating-CI safety;
- hotel-business-date contract;
- `FULL_NO_PAYMENTS` route-surface contract.

The current Release Gate proves migrations, Core, Admin/Public/Staff builds, Site/PMS/CMS smoke, full-domain E2E, Dining/Kitchen and root control-center on the accepted internal contour.

These are internal results, not production cutover evidence.

## 6. Remaining external launch gate

Production cutover remains **STOP** until real evidence exists for:
- platform-level protected GitHub `main` with required checks (#91);
- Google Drive permission integrity (#100);
- authorized real Beget/VPS execution path (#72);
- isolated external hotel staging/runtime acceptance (#28);
- actual legacy-live rollback package plus restore rehearsal (#8);
- target room/rate reconciliation to exact 84/12/48;
- final production HTTPS/WSS on hotel domains;
- real iPhone/Android/desktop/Staff/Kitchen acceptance against the actual target;
- production monitoring/alert delivery and restart/self-healing;
- fresh actual-target backup -> clean restore plus verified restricted off-site copy;
- exact immutable accepted executable SHA/image/runtime linkage (#40);
- authoritative tested DNS rollback;
- unified production-cutover technical readiness GREEN on the real target;
- explicit owner GO.

Payment-provider/MKassa/NFC/TTLock E2E is required only if a future launch profile explicitly enables those capabilities. It is not part of the current `FULL_NO_PAYMENTS` acceptance gate.

## 7. Repository gates

```bash
python scripts/release_rc_truth_guard.py
python scripts/verify_launch_acceptance.py --mode repository
```

Final structural cutover evidence check must use the accepted executable SHA:

```bash
python scripts/verify_launch_acceptance.py \
  --mode cutover \
  --manifest /secure/path/launch-evidence.json \
  --release-sha a53850983d8fc6e1f1997199049a5b071511ed80
```

## 8. Final external sequence

1. verify release `0.62.2`, launch profile `FULL_NO_PAYMENTS`, accepted executable `a5385098...` and current machine manifest;
2. verify GitHub protection and Drive integrity gates;
3. run release truth, host and environment preflight;
4. preserve/checksum current legacy rollback and prove restore ownership;
5. create persistent storage and private PostgreSQL;
6. apply all **24** migrations using `prisma migrate deploy`;
7. reconcile canonical **84 rooms / 12 categories / 48 rates** to zero diff;
8. deploy images from exact accepted executable boundary `a5385098...` to isolated production-like HTTPS/WSS staging;
9. verify runtime capabilities report `FULL_NO_PAYMENTS` and payment mutation surfaces remain absent;
10. verify Core/Public/Admin/Staff/Kitchen, Marketing/Agents, secure sessions and realtime boundaries;
11. run real-device acceptance for Public/Admin/Staff/Kitchen;
12. re-run target load/resource observation where appropriate;
13. prove target monitoring/restart/self-healing;
14. take fresh backup, prove isolated clean restore and restricted off-site copy;
15. record immutable SHA/image/runtime linkage and authoritative DNS rollback;
16. run `scripts/production_cutover_readiness.py` and require technical readiness GREEN;
17. only after explicit owner GO prepare controlled production/DNS switch.

**EXTERNAL PRODUCTION CUTOVER STOP** remains in force.
