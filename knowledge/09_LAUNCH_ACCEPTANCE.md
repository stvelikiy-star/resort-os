# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Version: 6.5  
Date: 2026-09-14  
Status: RESORT OS 0.62.2 INTERNAL RC REFROZEN / FULL TEST VERIFIED / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

Repository/CI and Railway Full Test evidence are not real hotel production evidence.

## 1. Frozen release boundary

Repository: `stvelikiy-star/resort-os`.  
Release: `0.62.2`.  
Accepted source PR: `#164` — `fix/public-request-sent-copy-20260914 -> main`.  
Accepted executable/release-boundary head: `61bd40d7592e842a4d52cfb343483065afb378cb`.  
Observed main merge: `94c849a0833079627b47db1e25869096191424bc`.  
Production source branch: `main`.

Evidence:
- accepted PR #164 head: **26/26 workflows SUCCESS, 0 failures**;
- first main push: **25/26 workflows SUCCESS**;
- the only failed workflow was `Release RC Truth CI`, correctly rejecting the previous frozen boundary before this refreeze;
- PR #164 head and merge are not tree-equivalent only because PR #163 landed in `main` while #164 was open; the exact allowed drift is `.github/workflows/main-pr-merge-guard-ci.yml`, `scripts/main_pr_merge_guard.py`, `scripts/release_rc_truth_guard.py`;
- no other tested-head -> merge drift is accepted.

Machine truth: `release/current-rc.json`. Guard: `scripts/release_rc_truth_guard.py`.

## 2. Product authority boundary

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`. OWNER/MANAGER retain reservation/payment authority. AI/n8n cannot confirm payment/reservation, invent policy, check guests in/out, refund or bypass Core pricing/availability.

The accepted final contour includes Marketing in Admin/Core, Agent CRM/reporting, server-enforced extra-bed rules, returning-guest 10% accommodation discount, dated maintenance/manual room holds, explicit confirmation before schedule commit after drag/drop and the exact public server-confirmed Russian request-sent message.

Real bank/MKassa/TTHotel/TTLock remains provider-gated until real provider/hardware acceptance. NFC remains outside active V1.

## 3. Database/property contract

Frozen release boundary: **24 committed migrations / 93 critical domain constraints**.  
Canonical property seed: **84 rooms / 12 categories / 48 rate rows**.

The final migrations remain:
- `z99_marketing_consent_attribution_20260912`;
- `zz100_owner_ops_corrections_20260914`.

External staging/production migration uses only `npx prisma migrate deploy`; `prisma db push` is never staging/production release evidence.

## 4. Repository and Full Test verification

Repository verification covers PMS/chessboard, Rates/Seasons, Reception, CRM, Agents, Marketing, Guest OS/Services/Offers, housekeeping/maintenance, Finance, Reports/Analytics, Staff/RBAC, Kitchen/Dining, QR/service points, Inbox, automation contracts, backup/restore, production package, release/staging gates, active-route uniqueness, mutating-CI safety and guarded load testing.

Railway `Three Crowns Full Test` verification additionally includes:
- external HTTPS health for API/Public/Admin/Staff and WSS-path reachability;
- scheduled external smoke every 6 hours;
- daily Chromium Public/Admin/Staff acceptance without business mutation;
- API/Web/Admin/Staff `ON_FAILURE` restart policy;
- read-only load baseline through 50 VU: **32,229 requests, 0% HTTP failures, p95 38.49 ms overall and 42.25 ms availability**;
- repository PostgreSQL backup -> isolated restore CI.

These are Full Test results, not production cutover evidence.

## 5. Remaining external launch gate

Production cutover remains **STOP** until real evidence exists for:
- platform-level protected GitHub `main` with required checks;
- removal/downgrade of unsafe public Google Drive writer grants if present;
- authorized real production host/runtime path;
- actual legacy-live rollback package plus restore rehearsal;
- target room reconciliation and exact 24 migrations;
- final production HTTPS/WSS on hotel domains;
- real iPhone/Android/desktop/Staff/Kitchen acceptance against the actual production-like target;
- real launch-enabled MKassa/TTHotel/TTLock provider checks;
- fresh actual-target backup -> clean restore plus verified off-site copy;
- exact immutable release/image/deployment linkage;
- tested DNS rollback;
- explicit owner GO.

Full Test load, monitoring and restart/self-healing are proven and no longer count as open Full Test blockers. They must still be re-observed on the actual production host before cutover.

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
  --release-sha 61bd40d7592e842a4d52cfb343483065afb378cb
```

## 7. Final external sequence

1. verify `main`, release `0.62.2`, accepted head `61bd40d7592e842a4d52cfb343483065afb378cb` and observed merge `94c849a0833079627b47db1e25869096191424bc`;
2. verify GitHub protection and Drive integrity gates;
3. run release truth, host and environment preflight;
4. preserve/checksum current legacy rollback and prove restore ownership;
5. create persistent storage and private PostgreSQL;
6. apply all **24** migrations using `prisma migrate deploy`;
7. reconcile canonical **84 rooms / 12 categories / 48 rates** to zero diff;
8. deploy the accepted executable product boundary plus the exact accepted ops-only merge drift to isolated production-like HTTPS/WSS staging;
9. verify Core/Public/Admin/Staff/Kitchen, Marketing/Agents, secure session and realtime boundaries;
10. run real-device and provider checks;
11. re-run guarded load observation on the actual target;
12. prove target monitoring/restart/self-healing;
13. take fresh backup, prove isolated clean restore and off-site copy;
14. record immutable SHA/image/runtime linkage and tested DNS rollback;
15. only after explicit owner GO prepare controlled production/DNS switch.

**EXTERNAL PRODUCTION CUTOVER STOP** remains in force.
