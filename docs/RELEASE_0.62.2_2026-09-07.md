# Resort OS 0.62.2 — 2026-09-07

Status: **INTERNAL RC FROZEN / EXTERNAL PRODUCTION CUTOVER STOP**

Accepted executable head: `b79e22ee56c43e5f9146df7597d4c9e5e4124afa`.  
Observed tree-equivalent main merge: `731e81c2d2a4ccc91fae319b73f0d4b8eb9979b5`.  
Production source branch: `main`.

## Why 0.62.2 exists

A strict post-0.62.1 audit found a structural authorization hazard in Kitchen routing: operational `kitchen.py` still carried duplicate menu mutation endpoints while the canonical manager router carried protected equivalents. Runtime behavior was currently safe only because router registration order selected the manager route first. That is not an acceptable security invariant.

The same audit found stale active FastAPI runtime identity `0.60.0` after the repository had advanced to 0.62.x.

## Fixes

- legacy operational `POST /api/v1/kitchen/menu/bootstrap-draft` is removed from the active application graph before operational Kitchen router composition;
- legacy operational `PATCH /api/v1/kitchen/menu/{item_id}` is likewise removed;
- canonical Kitchen menu mutations remain OWNER/MANAGER-authoritative;
- DINING_STAFF retains operational menu read/order/table capabilities without price/publish mutation authority;
- `scripts/verify_active_route_uniqueness.py` now imports the real FastAPI application and rejects every duplicate API HTTP method/path pair;
- the main Release Gate executes that structural route check after Core installation;
- active FastAPI/OpenAPI runtime identity is `0.62.2`.

Previous 0.62.1 hardening remains active, including Admin demo fail-close and production Kitchen bootstrap fail-close.

## Evidence

PR #127 exact tested head: **41/41 workflows SUCCESS, 0 failures**.  
Observed tree-equivalent main merge: **32/32 eligible product/security/migration/staging workflows SUCCESS**.  
One additional `Release RC Truth CI` push run failed closed exactly because the previous 0.62.1 manifest detected executable drift; 0.62.2 is the controlled refreeze.

The main Release Gate passed clean PostgreSQL migrations, active route uniqueness, schema verification, canonical seed, OWNER bootstrap, Admin/Public/Staff builds, Core start, Site/PMS/CMS smoke, automation truth, full-domain E2E, Dining folio E2E, Chef snapshot E2E, Dining coordination E2E and Root Control Center verification.

## Frozen contracts

- **22 committed migrations**;
- **87 critical constraints**;
- **84 rooms**;
- **12 room categories**;
- **48 rate rows**;
- `ReservationRequest != Reservation`;
- PostgreSQL/Core remain transaction authority.

## Scope boundary

PR #127 changed zero `apps/web/**` files. The public site remained frozen and was only built/smoke-tested for compatibility.

GitHub branch protection and Google Drive permission hardening are advisory/deferred by owner decision. Beget/VPS and all external staging/rollback/device/provider/monitoring/backup/DNS work remain the final external phase.

**EXTERNAL PRODUCTION CUTOVER STOP** remains active. No production deployment is claimed by this release record.
