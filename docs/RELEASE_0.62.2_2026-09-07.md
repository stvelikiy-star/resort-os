# Resort OS 0.62.2 — 2026-09-07

Refreeze evidence updated: **2026-09-14**.  
Status: **INTERNAL RC REFROZEN / FULL TEST VERIFIED / EXTERNAL PRODUCTION CUTOVER STOP**

Accepted executable/release-boundary head: `7ae394bbb549bb6200c84e9c46d47ed5cd45499a`.  
Observed tree-equivalent main merge: `b13bacad3f2e923f51354b1839371d07179b2e8c`.  
Production source branch: `main`.

## Why the same-version refreeze exists

The active application runtime remains `0.62.2`. Since the 2026-09-08 security refreeze, the repository accepted final public-site Marketing/consent work and the owner-approved PMS operations corrections in PR #157. Those changes alter executable product code and the PostgreSQL release ledger, so the old frozen release truth correctly failed closed after merge. This record is the controlled same-version refreeze; the guard is updated to the new tested executable tree rather than bypassed.

## Accepted product additions

The accepted boundary now includes:
- final **Marketing** surface in Admin and Resort Core, plus marketing consent/attribution migration and automation contracts;
- Agent CRM cards, reservation linkage, period reports, booked amount vs received payments, room nights, interactions and next-contact tracking;
- Reception agent filter;
- dated `MAINTENANCE` and `MANUAL` room holds for owner/staff/guest/service/other use;
- extra-bed server rule: forbidden for `DOUBLE_STANDARD_BASEMENT`, `DOUBLE_IMPROVED`, `TWO_ROOM_STANDARD`; allowed categories recalculate through Resort Core;
- automatic **10% accommodation discount** for a returning guest with a prior `CHECKED_OUT` stay, while alternate manager discounts remain explicit/auditable;
- safe PMS move flow: drag/drop -> Core preview -> explicit `Подтвердить и сохранить график` -> commit;
- public request success state remains server-confirmed.

All prior security, RBAC, Kitchen/Dining, Guest OS, mutation-safety, route-uniqueness, backup/restore and guarded load-test controls remain in force.

## Evidence

PR #157 exact tested head `7ae394bbb549bb6200c84e9c46d47ed5cd45499a`: **52/52 pull-request workflows SUCCESS, 0 failures**.  
Observed main merge `b13bacad3f2e923f51354b1839371d07179b2e8c` is tree-equivalent to the tested head; both resolve to tree `f8991f2f65d837dd16745b43582b5c97292548b6`.  
First main push: **37/39 workflows SUCCESS**. The only two failures were `Release RC Truth CI` and `Launch Acceptance CI`, both failing at the old frozen-truth boundary before this controlled refreeze.

Railway `Three Crowns Full Test` deployed API, Web, Admin and Staff from merge SHA `b13bacad3f2e923f51354b1839371d07179b2e8c`. API successfully found **24 migrations**, applied `z99_marketing_consent_attribution_20260912` and `zz100_owner_ops_corrections_20260914`, verified the 84-room / 12-category / 48-rate seed and returned `/health/ready` HTTP 200.

## Frozen contracts

- **24 committed migrations**;
- **93 critical constraints**;
- **84 rooms**;
- **12 room categories**;
- **48 rate rows**;
- `ReservationRequest != Reservation`;
- PostgreSQL/Core remain transaction authority;
- OWNER/MANAGER retain commercial authority;
- Marketing remains part of the final Admin/Core contour;
- real bank/MKassa/TTLock remain provider-gated until real provider acceptance;
- NFC remains outside active V1;
- release runtime remains `0.62.2`.

The final migrations are:
23. `z99_marketing_consent_attribution_20260912`;
24. `zz100_owner_ops_corrections_20260914`.

## External boundary

Repository and Full Test green status are not real production verification. The following remain launch work: protected GitHub `main`, Google Drive public-writer remediation, authorized production host path, real rollback, target migration/room reconciliation, external HTTPS/WSS, real devices/providers, actual load execution, monitoring/restart evidence, fresh actual-target backup/clean restore/off-site evidence, immutable deployment linkage and DNS rollback.

**EXTERNAL PRODUCTION CUTOVER STOP** remains active. No real production/DNS cutover is claimed by this release record.
