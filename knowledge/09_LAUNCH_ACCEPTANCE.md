# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Version: 6.2  
Date: 2026-09-07  
Status: RESORT OS 0.62.2 INTERNAL RC FROZEN / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

Repository/CI evidence is not external staging or production evidence.

## 1. Frozen release boundary

Repository: `stvelikiy-star/resort-os`.  
Release: `0.62.2`.  
Accepted source PR: `#127` — `audit/kitchen-route-canonicalization-20260907 -> main`.  
Accepted executable head: `b79e22ee56c43e5f9146df7597d4c9e5e4124afa`.  
Observed tree-equivalent main merge: `731e81c2d2a4ccc91fae319b73f0d4b8eb9979b5`.  
Production source branch: `main`.

Evidence:
- accepted PR #127 head: **41/41 workflows SUCCESS, 0 failures**;
- accepted head and observed merge share the same tree;
- observed main merge: **32/32 eligible product/security/migration/staging workflows SUCCESS**;
- `Release RC Truth CI` failed closed only because 0.62.1 correctly rejected the new executable; this 0.62.2 refreeze is the controlled correction.

Machine truth: `release/current-rc.json`. Guard: `scripts/release_rc_truth_guard.py`.

## 2. Product authority boundary

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`. OWNER/MANAGER retain reservation/payment authority. AI/n8n cannot confirm payment/reservation, invent policy, check guests in/out, refund or bypass Core pricing/availability.

Kitchen menu mutation authority is now structurally single-owner: OWNER/MANAGER canonical routes only. Active API route uniqueness is release-gated so RBAC cannot depend on duplicate route order. Real bank/TTLock remains provider-gated; NFC remains outside active V1.

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

0.62.2 includes PMS/chessboard, Rates/Seasons, Reception, CRM, groups, Guest OS/Services/Offers, housekeeping/maintenance, Finance, Reports/Analytics, Staff/RBAC, Kitchen/Dining, QR/service points, Inbox, automation contracts, backup/restore, production package, staging/release gates, Admin demo fail-close and active API route uniqueness enforcement.

The public website source remained frozen during PR #127 (`apps/web/** = 0`). Public Web build/smoke is compatibility evidence only.

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
  --release-sha b79e22ee56c43e5f9146df7597d4c9e5e4124afa
```

## 7. Final external sequence — deferred until Beget/VPS phase

1. verify main and 0.62.2 manifest;
2. run release truth, host and environment preflight;
3. preserve/checksum current legacy rollback;
4. create persistent storage and private PostgreSQL;
5. apply all 22 migrations;
6. reconcile 84-room canonical register to zero diff;
7. build/deploy exact accepted executable `b79e22ee56c43e5f9146df7597d4c9e5e4124afa` to isolated HTTPS/WSS staging;
8. verify Core/Public/Admin/Staff/Kitchen and secure network boundaries;
9. run full external acceptance plus real-device/provider checks;
10. prove fresh backup and clean restore;
11. only after explicit owner GO prepare controlled DNS/production switch.

**EXTERNAL PRODUCTION CUTOVER STOP** remains in force.
