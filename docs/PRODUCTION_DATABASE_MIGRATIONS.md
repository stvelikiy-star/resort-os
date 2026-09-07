# Three Crowns — production database migration gate

Date: 2026-09-07  
Release: `0.62.1`  
Status: **COMMITTED / CLEAN-DEPLOY VERIFIED IN REPOSITORY CI / BACKUP-RESTORE VERIFIED IN CI / EXTERNAL PRODUCTION NOT EXECUTED**

This document defines the database migration boundary. It does not prove real production migration.

## Release identity

Accepted executable head: `b3bb0c1be4c522d765509796ddd1d32e8606dc89`.  
Observed tree-equivalent main merge: `7f689458b2cf507d76a8c54fbe164e9492f79aca`.  
Production source branch: `main`.

Repository acceptance on the accepted head is **28/28 workflows SUCCESS**. The observed merge retained the same tree and produced **23 eligible successful product/security/migration/staging workflows**; the previous-manifest Release RC guard failed closed before the 0.62.1 refreeze.

## Canonical migration ledger

Release 0.62.1 retains exactly **22 committed migrations**:

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

The shared release contract fingerprints **87 critical domain constraints** through `scripts/release_contract.py`.

## Canonical property baseline

- 84 physical rooms;
- 12 room categories;
- 48 rate rows;
- rooms 501/502 remain owner-approved two-person basement inventory above the laundry.

Physical room intake is closed. Real target reconciliation remains an external evidence step.

## Production rules

1. External staging/production uses only committed migrations with `npx prisma migrate deploy`.
2. `prisma db push` is not production migration evidence.
3. Never use destructive reset against production.
4. Never use `migrate resolve` to hide schema drift.
5. Every forward migration must update the release contract and backup/restore verification.
6. A fresh real backup and isolated restore verification are required before cutover.

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

Repository CI proves the mechanism against the 22-migration / 87-constraint contract. Production still requires a fresh actual-target backup, checksum, timestamp, off-site copy and restore evidence.

## Production boundary

Database engineering is repository-ready. External production migration remains **EXTERNAL PRODUCTION CUTOVER STOP** until the actual target has exact accepted SHA/image linkage, fresh backup, successful migrate deploy/status, readiness/smoke, tested restore/rollback and verified off-site copy.
