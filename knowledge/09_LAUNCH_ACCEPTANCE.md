# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Version: 6.2  
Date: 2026-09-07  
Status: RESORT OS 0.62.2 INTERNAL RC FROZEN / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

Repository/CI evidence is not external staging or production evidence.

## 1. Frozen release boundary

Repository: `stvelikiy-star/resort-os`.  
Release: `0.62.2`.  
Accepted safety source PR: `#132` — `hardening/local-mutating-ci-runner-20260907 -> main`.  
Accepted executable/release-boundary head: `ccf9a7bdca0187ecb712e35d8d0e53bd3d9051cd`.  
Observed tree-equivalent main merge: `7cf4b5a3c4164f7224a2fd70807cecf40cfb42bc`.  
Production source branch: `main`.

Evidence:
- accepted PR #132 head: **25/25 workflows SUCCESS, 0 failures**;
- accepted head and observed merge are tree-equivalent with zero file differences;
- observed main merge: **23/23 applicable non-truth workflows SUCCESS**;
- the one additional `Release RC Truth CI` run failed closed because the prior frozen boundary correctly rejected the safety drift; this same-version refreeze is the controlled correction.

Machine truth: `release/current-rc.json`. Guard: `scripts/release_rc_truth_guard.py`.

## 2. Product authority boundary

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`. OWNER/MANAGER retain reservation/payment authority. AI/n8n cannot confirm payment/reservation, invent policy, check guests in/out, refund or bypass Core pricing/availability.

Kitchen menu mutation authority remains structurally single-owner: OWNER/MANAGER canonical routes only. Active API route uniqueness is release-gated. Mutating CI/demo utilities are now fail-closed and localhost-isolated where applicable. Real bank/TTLock remains provider-gated; NFC remains outside active V1.

## 3. Database/property contract

Frozen release boundary: **22 committed migrations / 87 critical domain constraints**.  
Canonical property seed: **84 rooms / 12 categories / 48 rate rows**.

External staging/production migration uses only:

```bash
cd packages/database
npm ci
npx prisma validate
npx prisma migrate deploy
npx prisma migrate status
cd ../..
```

Never use `prisma db push` as staging/production release evidence.

## 4. Repository-verified management contour

0.62.2 includes PMS/chessboard, Rates/Seasons, Reception, CRM, groups, Guest OS/Services/Offers, housekeeping/maintenance, Finance, Reports/Analytics, Staff/RBAC, Kitchen/Dining, QR/service points, Inbox, automation contracts, backup/restore, production package, staging/release gates, Admin demo fail-close, active API route uniqueness enforcement and the final mutating-CI safety boundary.

The public website source remained frozen during PRs #129–#132 (`apps/web/** = 0`). Public Web build/smoke is compatibility evidence only.

## 5. Owner-prioritized external phase

Per owner decision, GitHub branch protection and Google Drive permission hardening are advisory/deferred and are not current internal-RC blockers. Beget/VPS is intentionally the final phase.

Production cutover remains **STOP** until real external evidence exists for the actual target host, legacy rollback, room reconciliation, HTTPS/WSS staging, exact accepted SHA/image linkage, real devices, any launch-enabled providers, monitoring, fresh backup/restore/off-site copy, DNS rollback and explicit owner GO.

No CI result alone authorizes DNS cutover.

## 6. Repository gates

```bash
python scripts/release_rc_truth_guard.py
python scripts/verify_launch_acceptance.py --mode repository
```

Final structural cutover evidence check, only after real evidence exists:

```bash
python scripts/verify_launch_acceptance.py \
  --mode cutover \
  --manifest /secure/path/launch-evidence.json \
  --release-sha ccf9a7bdca0187ecb712e35d8d0e53bd3d9051cd
```

## 7. Final external sequence — deferred until Beget/VPS phase

1. verify `main` and 0.62.2 manifest;
2. run release truth, host and environment preflight;
3. preserve/checksum current legacy rollback;
4. create persistent storage and private PostgreSQL;
5. apply all 22 migrations;
6. reconcile 84-room canonical register to zero diff;
7. build/deploy exact accepted release-boundary head `ccf9a7bdca0187ecb712e35d8d0e53bd3d9051cd` to isolated HTTPS/WSS staging;
8. verify Core/Public/Admin/Staff/Kitchen and secure network boundaries;
9. run full external acceptance plus real-device/provider checks;
10. prove fresh backup and clean restore;
11. only after explicit owner GO prepare controlled DNS/production switch.

**EXTERNAL PRODUCTION CUTOVER STOP** remains in force.
