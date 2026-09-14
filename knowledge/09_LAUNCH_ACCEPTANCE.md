# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Version: 6.4  
Date: 2026-09-14  
Status: RESORT OS 0.62.2 INTERNAL RC REFROZEN / FULL TEST VERIFIED / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

Repository/CI and Railway Full Test evidence are not real hotel production evidence.

## 1. Frozen release boundary

Repository: `stvelikiy-star/resort-os`.  
Release: `0.62.2`.  
Accepted source PR: `#157` — `feat/owner-ops-corrections-20260914 -> main`.  
Accepted executable/release-boundary head: `7ae394bbb549bb6200c84e9c46d47ed5cd45499a`.  
Observed tree-equivalent main merge: `b13bacad3f2e923f51354b1839371d07179b2e8c`.  
Production source branch: `main`.

Evidence:
- accepted PR #157 head: **52/52 workflows SUCCESS, 0 failures**;
- accepted head and merge are tree-equivalent;
- first main push: **37/39 workflows SUCCESS**;
- `Release RC Truth CI` and `Launch Acceptance CI` failed closed only because the prior 2026-09-07 frozen manifest did not accept the new executable/product boundary; this controlled refreeze updates that truth without bypassing the guard.

Machine truth: `release/current-rc.json`. Guard: `scripts/release_rc_truth_guard.py`.

## 2. Product authority boundary

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`. OWNER/MANAGER retain reservation/payment authority. AI/n8n cannot confirm payment/reservation, invent policy, check guests in/out, refund or bypass Core pricing/availability.

The accepted final contour includes Marketing in Admin/Core, agent CRM/reporting, server-enforced extra-bed rules, returning-guest 10% accommodation discount, dated maintenance/manual room holds and explicit confirmation before schedule commit after booking drag/drop.

Real bank/MKassa/TTLock remains provider-gated until real provider acceptance. NFC remains outside active V1.

## 3. Database/property contract

Frozen release boundary: **24 committed migrations / 93 critical domain constraints**.  
Canonical property seed: **84 rooms / 12 categories / 48 rate rows**.

The final two migrations are:
- `z99_marketing_consent_attribution_20260912`;
- `zz100_owner_ops_corrections_20260914`.

External staging/production migration uses only `npx prisma migrate deploy`; `prisma db push` is never staging/production release evidence.

## 4. Repository and Full Test verification

The accepted 0.62.2 boundary has repository verification for PMS/chessboard, Rates/Seasons, Reception, CRM, Agents, Marketing, Guest OS/Services/Offers, housekeeping/maintenance, Finance, Reports/Analytics, Staff/RBAC, Kitchen/Dining, QR/service points, Inbox, automation contracts, backup/restore, production package, staging/release gates, active-route uniqueness, mutating-CI safety and guarded load testing.

Railway `Three Crowns Full Test` additionally proves the integrated merge SHA `b13bacad3f2e923f51354b1839371d07179b2e8c` can deploy API/Web/Admin/Staff together. API applied all **24** migrations, including Marketing and Owner Operations, and passed readiness. This is Full Test evidence, not production cutover evidence.

## 5. Remaining external launch gate

Production cutover remains **STOP** until real evidence exists for:
- protected GitHub `main` with required checks;
- removal/downgrade of public Google Drive writer grants;
- authorized real production host/runtime path;
- actual legacy-live rollback package plus restore rehearsal;
- target room reconciliation and exact 24 migrations;
- external production HTTPS/WSS;
- real iPhone/Android/desktop/Staff/Kitchen acceptance;
- real launch-enabled bank/MKassa/TTLock provider checks;
- real load/stress run with resource observations;
- monitoring/restart/self-healing acceptance;
- fresh actual-target backup -> clean restore plus off-site copy;
- exact immutable release/image/deployment linkage;
- DNS rollback;
- explicit owner GO.

No CI or Full Test result alone authorizes DNS or provider cutover.

## 6. Repository gates

```bash
python scripts/release_rc_truth_guard.py
python scripts/verify_launch_acceptance.py --mode repository
```

Final structural cutover evidence check must use the accepted executable SHA:

```bash
python scripts/verify_launch_acceptance.py \
  --mode cutover \
  --manifest /secure/path/launch-evidence.json \
  --release-sha 7ae394bbb549bb6200c84e9c46d47ed5cd45499a
```

## 7. Final external sequence

1. verify `main`, the 0.62.2 manifest and merge `b13bacad3f2e923f51354b1839371d07179b2e8c`;
2. verify GitHub protection and Drive integrity gates;
3. run release truth, host and environment preflight;
4. preserve/checksum current legacy rollback and prove restore ownership;
5. create persistent storage and private PostgreSQL;
6. apply all **24** migrations using `prisma migrate deploy`;
7. reconcile the canonical 84-room register to zero diff;
8. build/deploy accepted executable head `7ae394bbb549bb6200c84e9c46d47ed5cd45499a` or its tree-equivalent signed merge to isolated HTTPS/WSS production-like staging;
9. verify Core/Public/Admin/Staff/Kitchen, Marketing/Agents and secure session/realtime boundaries;
10. run external business acceptance and real-device/provider checks;
11. run guarded load baseline with resource monitoring;
12. prove monitoring/restart/self-healing;
13. prove fresh backup, clean restore and off-site evidence;
14. record immutable SHA/image/runtime linkage and DNS rollback;
15. only after explicit owner GO prepare controlled production/DNS switch.

**EXTERNAL PRODUCTION CUTOVER STOP** remains in force.
