# Resort OS 0.60.0 — release acceptance evidence

Date: 2026-09-05  
Property: Three Crowns / Три Короны, Cholpon-Ata, Kyrgyzstan  
Release source branch: `feature/owner-corrections-20260905`  
Production source branch: `main`  
Application version: `0.60.0`

## Frozen release state

The final accepted executable release boundary is:

- accepted executable head: `c8db446d367284465853850136c31274c8e39370`;
- Release PR: `#112`;
- exact-head result: **46/46 checks SUCCESS, 0 failures**;
- observed tree-equivalent main merge: `e5efe074abb4a277c032b017ae5fb02c5d0d5039`;
- resulting main merge result: **35/35 triggered checks SUCCESS, 0 failures**;
- post-merge truth-only main head: `00fdb8d1b583cf418e1c39709fb79ca248e462e4`;
- post-merge truth-only result: **4/4 triggered checks SUCCESS, 0 failures**.

The accepted executable head and observed main merge have zero file differences between them. The later truth-only main delta changes canonical documentation only and does not alter executable product behavior.

`release/current-rc.json` is deliberately refrozen to this Resort OS 0.60.0 executable boundary.

The production source branch is `main`, but **EXTERNAL PRODUCTION CUTOVER REMAINS STOP** until branch protection, Drive integrity, real Beget staging, rollback, devices, providers where enabled, monitoring, backups, DNS rollback and explicit owner approval are verified.

## Production-like branch acceptance evidence

Before the final exact-head PR acceptance, production-like Release Gate run `33973604159` passed on clean PostgreSQL 16 for tested code commit:

- commit: `8364f67113edecb4d042906729af0d67d21332b3`;
- workflow: `Resort OS Release Gate`;
- conclusion: `success`.

That run is retained as production-like clean-database evidence. The later PR #112 exact-head 46/46 acceptance is the final frozen repository release authority.

## What 0.60.0 closes

### CMS Media

- real image asset storage for JPEG / PNG / WebP;
- MIME and image-signature validation;
- byte-size limit, SHA-256 identity and deduplication;
- media library archive protection for published assets;
- independent media draft and published slot state;
- public site reads published media only;
- managed slots for Hero, conference, advantages, gallery and room categories;
- audit trail for media mutations.

### Dining Floor

- visual restaurant floor with normalized coordinates;
- zones and table shapes;
- OWNER / MANAGER drag-and-drop layout editing;
- staff read-only operational floor view;
- Stay-linked dining sessions;
- guest, room, party and waiter context on floor;
- kitchen order state visibility including READY;
- PostgreSQL invariant preventing legacy Kitchen transitions from releasing a table with an active Dining Session;
- Dining Session release owns the transition to CLEANING.

### Group booking + folio integration

- atomic multi-room group reservation flow;
- guest folio separates receivable charges from actual Payments;
- kitchen order posting is idempotent and does not fabricate a payment;
- reservation payment timestamp handling normalized across API/audit and PostgreSQL storage boundaries.

### Canonical hotel truth

- 84 physical rooms;
- 12 canonical room categories;
- 48 tariff rows;
- owner-corrected room/category truth preserved;
- current guest/service fact version normalized to 2026-09-05;
- old unpaid-booking rule remains stale/do-not-use;
- launch payment providers remain fail-closed until verified.

## Frozen database release contract

The accepted release contains **20 committed migrations**:

1. `0_init`
2. `1_site_content`
3. `2_guest_service_tasks`
4. `3_owner_analytics_snapshots`
5. `4_guest_engagements`
6. `5_guest_os_core`
7. `6_service_point_qr_operations`
8. `7_kitchen_operations`
9. `8_dining_service_control`
10. `9_guest_offer_campaigns`
11. `z10_service_point_paid_access`
12. `z11_owner_corrections_20260905`
13. `z12_guest_service_settings_20260905`
14. `z13_housekeeping_charges_20260905`
15. `z14_dining_entitlements_20260905`
16. `z15_group_bookings_20260905`
17. `z16_site_media_20260905`
18. `z17_dining_floor_layout_20260905`
19. `z18_site_media_slots_20260905`
20. `z19_dining_table_status_guard_20260905`

The shared release tooling fingerprints **81 critical domain constraints** through `scripts/release_contract.py`.

External staging/production migration mechanism is `npx prisma migrate deploy`; `prisma db push` is not a production migration mechanism.

## Production-like acceptance gate coverage

Clean PostgreSQL 16 acceptance verified:

1. Prisma schema validation.
2. `prisma migrate deploy` for every committed migration.
3. Prisma migration status verification.
4. Python compilation of Resort Core and release scripts.
5. Migrated Dining / Folio / Group / CMS Media tables and invariants.
6. Three Crowns seed: 84 rooms / 12 room categories / 48 rate rows.
7. OWNER bootstrap.
8. Admin TypeScript typecheck and production Next.js build.
9. Public Web TypeScript typecheck and production Next.js build.
10. Staff PWA TypeScript typecheck and production Next.js build.
11. Resort Core startup/readiness.
12. Unified Site / PMS / CRM / CMS smoke.
13. Owner-approved automation truth contract.
14. Release 0.60 full-domain E2E.
15. Root monorepo control-center verification.

## Full-domain E2E path

The release E2E verifies connected business behavior rather than isolated endpoint existence:

`OWNER login -> CMS media upload -> draft invisible publicly -> publish -> atomic group booking -> folio receivable -> actual internal payment fact -> check-in -> Stay -> meal entitlement -> chef production -> Dining Floor table -> Stay-linked seating -> Kitchen order -> folio posting -> ACCEPTED -> COOKING -> READY -> SERVED -> table/session PostgreSQL guard -> Dining Session RELEASED -> table CLEANING`

## Defects discovered by release acceptance and fixed

- duplicate migration drift between Dining migrations;
- duplicate application of baseline PostgreSQL constraints after `migrate deploy`;
- seed loss after owner room corrections;
- invalid PostgreSQL locking on nullable outer-join sides in folio code;
- aware-vs-naive datetime bind failure for payment timestamps;
- competing Kitchen vs Dining sources of truth for table availability;
- stale automation guest-fact assertions;
- frontend compatibility warnings in new Dining / Group / Chef flows.

## Release rule going forward

A version must not be described as stable solely because it builds locally. Minimum repository release evidence is:

- clean-db committed migration deploy;
- seed integrity;
- production builds for all frontends;
- Resort Core smoke/readiness;
- owner-approved automation truth;
- full-domain E2E;
- root monorepo verification;
- exact-head PR acceptance;
- merge tree-equivalence check;
- machine-readable RC refreeze;
- post-merge release-truth check.

External production requires the separate fail-closed launch evidence defined in `knowledge/09_LAUNCH_ACCEPTANCE.md` and `docs/DEPLOYMENT_RUNBOOK.md`.
