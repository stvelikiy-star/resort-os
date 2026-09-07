# Resort OS 0.62.2 — 2026-09-07

Status: **INTERNAL RC FROZEN / EXTERNAL PRODUCTION CUTOVER STOP**

Accepted executable/release-boundary head: `d851c5c64a103ab263b977b3b07c970f29676783`.  
Observed tree-equivalent main merge: `b477e76a32b7fc0fdf8a349cda400c7fa12bc297`.  
Production source branch: `main`.

## Why the same-version refreeze exists

The active application runtime remains 0.62.2. PR #135 added only guarded load/stress testing infrastructure and documentation; it did not change `apps/web/**` or hotel business logic. `Release RC Truth` correctly classified executable test/control paths as release-boundary drift and failed closed after merge, so the accepted boundary is advanced without a runtime version bump.

## Load-test safety now included

- real k6 read-pressure harness using pinned `grafana/k6:0.54.0`;
- explicit `ci|test|staging` environment requirement;
- explicit block for `3korony.com` and `www.3korony.com`;
- non-loopback targets must be clearly staging/test-marked;
- default pressure profile 10→25→50 VUs with failure and p95/p99 thresholds;
- optional authenticated PMS-grid reads require explicit staging credentials;
- no reservation, payment, check-in/out or provider mutations;
- bounded retry protects the CI contract from transient registry 502 errors.

Repository validation of the harness is **not** a claim that the real Beget server has passed load testing. Actual capacity remains external evidence.

## Evidence

PR #135 exact tested head `d851c5c64a103ab263b977b3b07c970f29676783`: **22/22 workflows SUCCESS, 0 failures**.  
Observed main merge `b477e76a32b7fc0fdf8a349cda400c7fa12bc297` is tree-equivalent; compare shows zero changed files between tested head and merge.  
Observed main merge: **20/20 applicable non-truth push workflows SUCCESS**.  
One additional `Release RC Truth CI` push run failed closed because the previous frozen manifest correctly detected the new load-test test/safety boundary; this record and manifest are the controlled correction.

During development the new load-test CI caught and corrected two real harness defects (Docker/k6 environment propagation and unsupported URL parsing), and one external Docker Hub 502 was hardened with bounded retry. The final harness contract is green.

## Frozen contracts

- **22 committed migrations**;
- **87 critical constraints**;
- **84 rooms**;
- **12 room categories**;
- **48 rate rows**;
- `ReservationRequest != Reservation`;
- PostgreSQL/Core remain transaction authority;
- public website source remains frozen;
- release `0.62.2` remains unchanged.

## External boundary

GitHub `main` protection, Google Drive public-writer remediation, Beget/VPS access, external HTTPS/WSS, legacy rollback, real devices/providers, actual load execution, monitoring, fresh backup/restore/off-site evidence, immutable deployment linkage and DNS rollback remain external launch work.

**EXTERNAL PRODUCTION CUTOVER STOP** remains active. No production deployment is claimed by this release record.
