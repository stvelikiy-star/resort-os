# Three Crowns — production database migration gate

Date: 2026-09-18  
Release: `0.62.2` / `FULL_NO_PAYMENTS`  
Status: **COMMITTED / CLEAN-DEPLOY + BACKUP-RESTORE VERIFIED IN CI / INTERNAL RELEASE GATES GREEN / EXTERNAL PRODUCTION CUTOVER STOP**

This document defines the current database release boundary. It does not prove real hotel production migration and does not authorize production cutover.

## Release identity

Exact tested PR #176 head: `a3ff4c847c66cd64a7cca92ccec613f23917f62d`.  
Accepted executable head: `a53850983d8fc6e1f1997199049a5b071511ed80`.  
Current governance/main head: `b20ea27d9fd7950e0a22f164413156e8b62355ec`.  
Production source branch: `main`.

PR #176 passed **29/29** pull-request workflows before merge. Its first main push produced **25/26** successes; the sole failure was the old frozen Release RC Truth intentionally rejecting the new executable boundary before controlled refreeze. PR #177 then refroze release truth and the resulting main passed **24/24** post-merge workflows.

No database migration changed in PR #176 or PR #177. The database boundary remains unchanged.

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

Historical migration names for Service Point/payment data do not mean payment capabilities are launch-enabled. Runtime composition under `FULL_NO_PAYMENTS` remains authoritative: payment mutations/acquiring/MKassa/NFC wallet are fail-closed for launch.

## Canonical property baseline

- **84 physical rooms**;
- **12 room categories**;
- **48 rate rows**;
- rooms 501/502 remain owner-approved two-person basement inventory above the laundry.

Physical room intake is closed. Real target reconciliation remains an external evidence step.

## Verified internal evidence

Repository CI has proved:
- Prisma schema validation/generation;
- clean application of the exact 24-migration chain;
- exact 93-constraint release fingerprint;
- Production Migration Baseline;
- PostgreSQL backup -> clean restore -> migration/constraint comparison;
- current Release Gate and launch acceptance contracts.

Current accepted executable/release CI also proves the canonical seed and active `FULL_NO_PAYMENTS` route surface. This is not actual production migration evidence.

## Production rules

1. External staging/production uses only committed migrations with `npx prisma migrate deploy`.
2. `prisma db push` is not production migration evidence.
3. Never use destructive reset against production.
4. Never use `migrate resolve` to hide schema drift.
5. Every forward migration must update the release contract and backup/restore verification.
6. The Prisma schema must remain synchronized with committed migration truth.
7. A fresh real backup and isolated restore verification are required immediately before cutover.
8. Runtime capability flags must preserve `FULL_NO_PAYMENTS`; database presence alone never enables dormant financial/provider functions.

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

Create the fresh actual-target backup:

```bash
BACKUP_DIR=/secure/path python scripts/database_backup.py
```

Copy the resulting `.dump` and `.manifest.json` byte-for-byte to a restricted off-site destination before continuing.

Verify a clean isolated restore and emit machine evidence only if the restore succeeds:

```bash
BACKUP_FILE=/secure/path/three-crowns-....dump \
BACKUP_MANIFEST=/secure/path/three-crowns-....manifest.json \
RESTORE_DATABASE_URL=postgresql://.../resort_os_restore \
python scripts/database_restore_evidence.py \
  --output /secure/path/restore-evidence.json
```

Then run the fail-closed pre-cutover gate:

```bash
python scripts/pre_cutover_backup_gate.py \
  --backup-file /secure/path/three-crowns-....dump \
  --manifest /secure/path/three-crowns-....manifest.json \
  --offsite-dir /mounted/restricted-offsite-copy \
  --restore-evidence /secure/path/restore-evidence.json \
  --restore-owner OWNER \
  --max-age-hours 6 \
  --output /secure/path/pre-cutover-backup-evidence.json
```

The gate rejects stale backups, non-v3 manifests, wrong property baseline, migration/constraint drift, local/off-site checksum differences, restore evidence that does not belong to the same backup, or a missing restore owner. `PRE_CUTOVER_BACKUP_GATE_GREEN` is required before the `pre_cutover_backup` launch-evidence item may be marked VERIFIED.

Repository CI proves the mechanism against the exact **24-migration / 93-constraint** contract. Production still requires this procedure on the fresh actual-target backup.

## Production boundary

Database engineering and internal release gates are green, but real production remains **EXTERNAL PRODUCTION CUTOVER STOP** until the actual target has accepted executable SHA/image linkage, fresh backup, successful `migrate deploy/status`, zero-diff room reconciliation, readiness/smoke, tested rollback/restore and verified restricted off-site copy.

No internal CI result by itself authorizes DNS switching or provider activation.
