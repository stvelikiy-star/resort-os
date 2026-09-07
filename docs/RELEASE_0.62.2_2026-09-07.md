# Resort OS 0.62.2 — 2026-09-07

Status: **INTERNAL RC FROZEN / EXTERNAL PRODUCTION CUTOVER STOP**

Accepted executable/release-boundary head: `ccf9a7bdca0187ecb712e35d8d0e53bd3d9051cd`.  
Observed tree-equivalent main merge: `7cf4b5a3c4164f7224a2fd70807cecf40cfb42bc`.  
Production source branch: `main`.

## Why the same-version safety refreeze exists

The active application runtime remains 0.62.2. A strict post-freeze operational audit found several non-runtime mutation utilities and CI E2E entrypoints that could fail open when environment targeting was incomplete or overridden. Because `Release RC Truth` correctly treats these safety/control paths as part of the frozen release boundary, the accepted boundary must move even though the product/runtime version does not.

## Safety hardening now included

- synthetic demo and operations scripts require an explicit allowed non-production environment and fail closed on blank/unknown values;
- legacy `release_candidate_check.sh` is retired as a mutating/db-push entrypoint;
- migration baseline generation requires explicit `development|test|ci` and refuses staging/production/unknown environments;
- Owner Control V2 mutating E2E has no credential/service-key fallback and is restricted to `ci|test` with localhost-only Core/PostgreSQL;
- Guest OS Core, Owner Intelligence, Owner Growth and PMS resize mutation workflows run through `scripts/run_local_mutating_ci.py`;
- that runner allowlists exact verifier names, requires explicit `ci|test`, explicit owner credentials, explicit database/Core URLs and localhost-only targets;
- `verify_mutating_utility_safety.py` and Management Final Acceptance enforce these boundaries against regression.

Earlier 0.62.2 Kitchen route/RBAC and active-route uniqueness hardening remains fully in force.

## Evidence

PR #132 exact tested head `ccf9a7bdca0187ecb712e35d8d0e53bd3d9051cd`: **25/25 workflows SUCCESS, 0 failures**.  
Observed main merge `7cf4b5a3c4164f7224a2fd70807cecf40cfb42bc` is tree-equivalent; compare shows zero file changes between tested head and merge.  
Observed main merge: **23/23 applicable non-truth push workflows SUCCESS**.  
One additional `Release RC Truth CI` push run failed closed because the previous frozen manifest correctly detected the safety-boundary drift; this record and manifest are the controlled correction.

The full test contour includes guarded mutating E2E, Management Final Acceptance, clean PostgreSQL migration/seed checks, Core lifecycle, PMS, Kitchen/Dining, automation contracts, backup/restore, Full Staging Gate, Single Server Production Package and the main Release Gate.

## Frozen contracts

- **22 committed migrations**;
- **87 critical constraints**;
- **84 rooms**;
- **12 room categories**;
- **48 rate rows**;
- `ReservationRequest != Reservation`;
- PostgreSQL/Core remain transaction authority;
- public website source remains frozen.

## Scope boundary

PRs #129, #130, #131 and #132 changed no `apps/web/**` product source. The public site was only built/smoke-tested as compatibility evidence. No external Beget/VPS deployment is claimed.

GitHub branch protection and Google Drive permission hardening remain advisory/deferred by owner decision. Beget/VPS and all external staging/rollback/device/provider/monitoring/backup/DNS work remain the final external phase.

**EXTERNAL PRODUCTION CUTOVER STOP** remains active. No production deployment is claimed by this release record.
