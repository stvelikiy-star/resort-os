# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Version: 6.3  
Date: 2026-09-08  
Status: RESORT OS 0.62.2 INTERNAL RC FROZEN / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

Repository/CI evidence is not external staging or production evidence.

## 1. Frozen release boundary

Repository: `stvelikiy-star/resort-os`.  
Release: `0.62.2`.  
Accepted source PR: `#143` — `audit/request-body-limits-v2-20260907 -> main`.  
Accepted executable/release-boundary head: `ac1a45e4cf3ef0e40a7fea6be75c81999e9af0b4`.  
Observed tree-equivalent main merge: `c931b7e12973ecb62b8f9595d60f0d7947e7ad8e`.  
Production source branch: `main`.

Evidence:
- accepted PR #143 head: **24/24 workflows SUCCESS, 0 failures, 0 cancellations**;
- accepted head and observed merge are tree-equivalent with zero file differences;
- observed main merge: **23/23 applicable non-truth workflows SUCCESS**;
- the additional `Release RC Truth CI` push run failed closed because the prior manifest correctly rejected executable/security drift after the older frozen boundary; this refreeze is the controlled correction.

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

0.62.2 includes PMS/chessboard, Rates/Seasons, Reception, CRM, groups, Guest OS/Services/Offers, housekeeping/maintenance, Finance, Reports/Analytics, Staff/RBAC, Kitchen/Dining, QR/service points, Inbox, automation contracts, backup/restore, production package, staging/release gates, active-route uniqueness, mutating-CI safety and guarded k6 load testing.

The current security boundary additionally includes:
- exact production runtime image pins;
- same-origin Admin/Staff authenticated WebSocket routing;
- production WebSocket Origin enforcement;
- 1 MB Telegram webhook body boundary;
- 2 MB generic public/admin/staff/API edge body boundaries;
- dedicated 8 MB CMS media upload edge boundary aligned with application validation;
- CI guards for runtime pins, WebSocket security/topology and request-body limits.

These are repository-verified controls. Real external HTTPS/WSS, capacity and device behavior remain external evidence.

## 5. Remaining external launch gate

Production cutover remains **STOP** until real evidence exists for:
- protected GitHub `main` with required checks;
- removal/downgrade of public Google Drive writer grants;
- authorized Beget/VPS runtime path;
- actual live legacy rollback package plus restore rehearsal;
- room reconciliation and exact 22 migrations on target;
- external HTTPS/WSS staging;
- real-device and launch-enabled provider checks;
- real k6 load/stress run with resource observations;
- monitoring/restart/self-healing acceptance;
- fresh backup -> clean restore plus off-site copy;
- exact immutable release/image/deployment linkage;
- DNS rollback;
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
  --release-sha ac1a45e4cf3ef0e40a7fea6be75c81999e9af0b4
```

## 7. Final external sequence

1. verify `main` and the 0.62.2 manifest;
2. verify GitHub protection and Drive integrity gates;
3. run release truth, host and environment preflight;
4. preserve/checksum current legacy rollback and prove non-destructive restore;
5. create persistent storage and private PostgreSQL;
6. apply all 22 migrations using `prisma migrate deploy`;
7. reconcile the canonical 84-room register to zero diff;
8. build/deploy exact accepted release-boundary head `ac1a45e4cf3ef0e40a7fea6be75c81999e9af0b4` to isolated HTTPS/WSS staging;
9. verify Core/Public/Admin/Staff/Kitchen and secure network/session/realtime boundaries;
10. run external business acceptance and real-device/provider checks;
11. run guarded load baseline and only then higher pressure with resource monitoring;
12. prove monitoring/restart/self-healing;
13. prove fresh backup, clean restore and off-site evidence;
14. record immutable SHA/image/runtime linkage and DNS rollback;
15. only after explicit owner GO prepare controlled DNS/production switch.

**EXTERNAL PRODUCTION CUTOVER STOP** remains in force.
