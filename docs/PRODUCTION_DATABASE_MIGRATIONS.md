# Three Crowns — production database migration gate

Date: 2026-09-14  
Release: `0.62.2` owner-operations/marketing/public-confirmation refreeze  
Status: **COMMITTED / CLEAN-DEPLOY + BACKUP-RESTORE VERIFIED IN CI / RAILWAY FULL TEST VERIFIED / EXTERNAL PRODUCTION CUTOVER STOP**

This document defines the current database release boundary. It does not prove real hotel production migration and does not authorize production cutover.

## Release identity

Accepted executable head: `61bd40d7592e842a4d52cfb343483065afb378cb`.  
Observed main merge: `94c849a0833079627b47db1e25869096191424bc`.  
Production source branch: `main`.

PR #164 passed **26/26** pull-request workflows before merge. The first main push produced **25/26** successes; the sole failure was the old frozen Release RC Truth intentionally rejecting the new Public boundary before this controlled refreeze. No database migration changed in PR #164.

## Canonical migration ledger

The current release contains exactly **24 committed migrations**, in this exact deployment order:

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
21. `z20_dining_active_table_unique_20260906`
22. `z21_dining_production_snapshots_20260906`
23. `z99_marketing_consent_attribution_20260912`
24. `zz100_owner_ops_corrections_20260914`

The `zz100_...` prefix is intentional: Prisma migration directories are ordered lexicographically, so the owner-operations migration runs after the existing `z99` Marketing migration.

The shared release contract fingerprints **93 critical domain constraints** through `scripts/release_contract.py`.

## Canonical property baseline

- **84 physical rooms**;
- **12 room categories**;
- **48 rate rows**;
- rooms 501/502 remain owner-approved two-person basement inventory above the laundry.

Physical room intake is closed. Real target reconciliation remains an external evidence step.

## Verified evidence

Repository CI has successfully proved:
- Prisma schema validation/generation;
- clean application of the exact 24-migration chain;
- exact 93-constraint release fingerprint;
- Production Migration Baseline;
- PostgreSQL backup -> clean restore -> migration/constraint comparison;
- Release Gate and Full Staging Gate.

Railway `Three Crowns Full Test` additionally proved all 24 migrations and canonical seed can start together and pass readiness. The later Public confirmation copy does not alter the database boundary.

This Full Test evidence is not actual production migration evidence.

## Production rules

1. External staging/production uses only committed migrations with `npx prisma migrate deploy`.
2. `prisma db push` is not production migration evidence.
3. Never use destructive reset against production.
4. Never use `migrate resolve` to hide schema drift.
5. Every forward migration must update the release contract and backup/restore verification.
6. The Prisma schema must remain synchronized with committed migration truth.
7. A fresh real backup and isolated restore verification are required immediately before cutover.

## Fresh staging / production database

```bash
cd packages/database
npm ci
npx prisma validate
npx prisma migrate deploy
npx prisma migrate status
cd ../..
python scripts/production_preflight.py
```

## Backup / restore gate

Create backup:

```bash
BACKUP_DIR=/secure/path python scripts/database_backup.py
```

Verify isolated restore:

```bash
BACKUP_FILE=/secure/path/three-crowns-....dump \
BACKUP_MANIFEST=/secure/path/three-crowns-....manifest.json \
RESTORE_DATABASE_URL=postgresql://.../resort_os_restore \
python scripts/database_restore_verify.py
```

Repository CI proves the mechanism against the exact **24-migration / 93-constraint** contract. Production still requires a fresh actual-target backup, checksum, timestamp, verified off-site copy and isolated restore evidence.

## Production boundary

Database engineering and Full Test are green, but real production remains **EXTERNAL PRODUCTION CUTOVER STOP** until the actual target has accepted SHA/image linkage, fresh backup, successful `migrate deploy/status`, zero-diff room reconciliation, readiness/smoke, tested rollback/restore and verified off-site copy. No Railway Full Test result by itself authorizes DNS or provider cutover.
