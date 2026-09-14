# Resort OS 0.62.2 — 2026-09-07

Refreeze evidence updated: **2026-09-14**.  
Status: **INTERNAL RC REFROZEN / FULL TEST VERIFIED / EXTERNAL PRODUCTION CUTOVER STOP**

Accepted executable/release-boundary head: `61bd40d7592e842a4d52cfb343483065afb378cb`.  
Observed main merge: `94c849a0833079627b47db1e25869096191424bc`.  
Production source branch: `main`.

## Why this same-version refreeze exists

The active application runtime remains `0.62.2`. PR #164 changed real Public product code to the owner-approved server-confirmed success wording, so the previously frozen PR #157 release truth correctly became stale. The first main push therefore failed closed only at `Release RC Truth CI`. This record accepts the newly tested Public boundary without bypassing the guard or changing database/runtime version.

PR #164 was open while PR #163 landed in `main`, so its tested head and merge are intentionally not tree-equivalent. The only accepted tested-head -> merge drift is the exact already-reviewed operational PR #163 set:
- `.github/workflows/main-pr-merge-guard-ci.yml`;
- `scripts/main_pr_merge_guard.py`;
- `scripts/release_rc_truth_guard.py`.

No other product or executable drift is accepted.

## Accepted product contour

The accepted boundary includes all prior owner-operations and Marketing work plus:
- exact Russian Public success message after a server-accepted booking request: `Заявка отправлена. Номер заявки <id>. Менеджер свяжется с вами для согласования условий и предоплаты.`;
- the existing explicit disclaimer that a request is not yet a confirmed reservation;
- final **Marketing** surface in Admin/Core and consent/attribution contracts;
- Agent CRM/reporting and Reception agent filtering;
- dated `MAINTENANCE` and `MANUAL` room holds;
- extra-bed denial for `DOUBLE_STANDARD_BASEMENT`, `DOUBLE_IMPROVED`, `TWO_ROOM_STANDARD`, with Core recalculation elsewhere;
- automatic **10% accommodation discount** for returning guests with a prior `CHECKED_OUT` stay;
- safe PMS move flow: drag/drop -> Core preview -> explicit `Подтвердить и сохранить график` -> commit.

All security, RBAC, Kitchen/Dining, Guest OS, mutation-safety, route-uniqueness, backup/restore, external monitoring and guarded load-test controls remain in force.

## Evidence

PR #164 exact tested head `61bd40d7592e842a4d52cfb343483065afb378cb`: **26/26 pull-request workflows SUCCESS, 0 failures**.  
Observed main merge: `94c849a0833079627b47db1e25869096191424bc`.  
First main push: **25/26 workflows SUCCESS**; the only failure was `Release RC Truth CI`, correctly rejecting the prior frozen boundary before this controlled refreeze.

Full Test operational evidence already includes external HTTPS/WSS smoke, daily Chromium acceptance, `ON_FAILURE` self-healing and a read-only 50-VU k6 run with **32,229 HTTP requests, 0% HTTP failures, overall p95 38.49 ms and availability p95 42.25 ms**.

## Frozen contracts

- **24 committed migrations**;
- **93 critical constraints**;
- **84 rooms**;
- **12 room categories**;
- **48 rate rows**;
- `ReservationRequest != Reservation`;
- PostgreSQL/Core remain transaction authority;
- OWNER/MANAGER retain commercial authority;
- Marketing remains part of final Admin/Core;
- real MKassa/TTHotel/TTLock remain provider/hardware gated;
- NFC remains outside active V1;
- release runtime remains `0.62.2`.

The final migrations remain:
23. `z99_marketing_consent_attribution_20260912`;
24. `zz100_owner_ops_corrections_20260914`.

## External boundary

Repository and Full Test green status are not real production verification. Remaining launch work is platform-level GitHub branch protection, Google Drive permission remediation if needed, authorized production/VPS path, real legacy rollback, actual-target migration/room reconciliation, final production HTTPS/WSS and real devices, provider/hardware E2E, fresh actual-target backup -> clean restore -> off-site proof, immutable production deployment linkage, DNS rollback and explicit owner GO.

**EXTERNAL PRODUCTION CUTOVER STOP** remains active. No real production/DNS cutover is claimed by this release record.
