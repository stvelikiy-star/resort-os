# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Version: 6.2  
Date: 2026-09-07  
Status: RESORT OS 0.62.2 INTERNAL RC FROZEN / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

Repository/CI evidence is not external staging or production evidence.

## 1. Frozen release boundary

Repository: `stvelikiy-star/resort-os`.  
Release: `0.62.2`.  
Accepted source PR: `#135` — `test/load-stress-harness-20260907 -> main`.  
Accepted executable/release-boundary head: `d851c5c64a103ab263b977b3b07c970f29676783`.  
Observed tree-equivalent main merge: `b477e76a32b7fc0fdf8a349cda400c7fa12bc297`.  
Production source branch: `main`.

Evidence:
- accepted PR #135 head: **22/22 workflows SUCCESS, 0 failures**;
- accepted head and observed merge are tree-equivalent with zero file differences;
- observed main merge: **20/20 applicable non-truth workflows SUCCESS**;
- the additional `Release RC Truth CI` run failed closed because the prior manifest correctly rejected the new test/safety boundary; this refreeze is the controlled correction.

Machine truth: `release/current-rc.json`. Guard: `scripts/release_rc_truth_guard.py`.

## 2. Product authority boundary

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`. OWNER/MANAGER retain reservation/payment authority. AI/n8n cannot confirm payment/reservation, invent policy, check guests in/out, refund or bypass Core pricing/availability.

Real bank/TTLock remains provider-gated; NFC remains outside active V1. Public website source remains frozen.

## 3. Database/property contract

Frozen release boundary: **22 committed migrations / 87 critical domain constraints**.  
Canonical property seed: **84 rooms / 12 categories / 48 rate rows**.

External staging/production migration uses only `npx prisma migrate deploy`; `prisma db push` is never staging/production release evidence.

## 4. Repository-verified contour

0.62.2 includes PMS/chessboard, Rates/Seasons, Reception, CRM, groups, Guest OS/Services/Offers, housekeeping/maintenance, Finance, Reports/Analytics, Staff/RBAC, Kitchen/Dining, QR/service points, Inbox, automation contracts, backup/restore, production package, staging/release gates, active-route uniqueness, mutating-CI safety and the new guarded k6 load-test harness.

The load harness is read-only, restricted to `ci|test|staging`, and explicitly blocks the public `3korony.com` host. Its CI contract is green, but **real server load capacity is not yet externally verified**.

## 5. Remaining external launch gate

Production cutover remains **STOP** until real evidence exists for:
- protected GitHub `main` with required checks;
- removal/downgrade of public Google Drive writer grants;
- authorized Beget/VPS runtime path;
- legacy rollback package;
- room reconciliation and exact 22 migrations on target;
- external HTTPS/WSS staging;
- real-device and launch-enabled provider checks;
- real k6 load/stress run with resource observations;
- monitoring and fresh backup→clean restore plus off-site copy;
- exact release/image/deployment linkage and DNS rollback;
- explicit owner GO.

No CI result alone authorizes DNS cutover.

## 6. Repository gates

```bash
python scripts/release_rc_truth_guard.py
python scripts/verify_launch_acceptance.py --mode repository
```

Final structural cutover evidence check must use the accepted SHA:

```bash
python scripts/verify_launch_acceptance.py \
  --mode cutover \
  --manifest /secure/path/launch-evidence.json \
  --release-sha d851c5c64a103ab263b977b3b07c970f29676783
```

## 7. Final external sequence

1. verify `main` and the 0.62.2 manifest;
2. run release truth, host and environment preflight;
3. preserve/checksum current legacy rollback;
4. create persistent storage and private PostgreSQL;
5. apply all 22 migrations;
6. reconcile 84-room canonical register to zero diff;
7. build/deploy exact accepted release-boundary head `d851c5c64a103ab263b977b3b07c970f29676783` to isolated HTTPS/WSS staging;
8. verify Core/Public/Admin/Staff/Kitchen and secure network boundaries;
9. run external acceptance and real-device/provider checks;
10. run guarded load baseline and then higher pressure only with resource monitoring;
11. prove fresh backup and clean restore/off-site evidence;
12. only after explicit owner GO prepare controlled DNS/production switch.

**EXTERNAL PRODUCTION CUTOVER STOP** remains in force.
