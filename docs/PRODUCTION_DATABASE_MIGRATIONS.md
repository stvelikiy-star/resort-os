# Three Crowns — production database migration gate

Date: 2026-09-01
Status: **COMMITTED / CLEAN-DEPLOY VERIFIED / BACKUP-RESTORE VERIFIED IN CI / EXTERNAL PRODUCTION NOT EXECUTED**

This document defines the database migration boundary for Three Crowns Resort OS. It does not prove that migrations were run against a real production database.

## Canonical migration ledger

Production/staging schema changes are represented only by committed Prisma migrations.

Exact current ledger:

1. `0_init`
2. `1_site_content`
3. `2_guest_service_tasks`
4. `3_owner_analytics_snapshots`
5. `4_guest_engagements`
6. `5_guest_os_core`
7. `6_service_point_qr_operations`

The exact ledger is maintained in `scripts/release_contract.py` and verified fail-closed by CI.

## Rules

1. `prisma db push` is allowed only for disposable development/test databases.
2. Production/staging uses `npx prisma migrate deploy`.
3. Never use `migrate resolve` to hide schema drift.
4. Never run destructive reset commands against production.
5. Custom PostgreSQL constraints must remain in committed migration history.
6. Any new forward migration must update the shared release contract and all release/backup verification in the same change.
7. Backup -> isolated restore verification is required before cutover.
8. Production requires a fresh real backup even though repository backup/restore is CI-verified.

## Current verified repository state

CI verifies:

- Prisma schema validation;
- clean PostgreSQL migration deploy from empty database;
- exact seven-migration ledger;
- 27 critical domain constraints from the shared release contract;
- 84-room / 12-room-type development intake integrity;
- Resort Core/PMS/business invariant regressions;
- backup creation and clean restore with the current migration/constraint fingerprint;
- Full Staging migration/application startup path.

The development room count is not final owner approval of the physical production register.

## Critical database boundary

The canonical constraint fingerprint is defined by `CRITICAL_CONSTRAINTS` in `scripts/release_contract.py` and currently contains 27 constraints, including:

- valid rate/request/reservation/inventory dates;
- nonnegative/positive financial bounds;
- `no_overlapping_active_room_blocks`;
- Guest Services context/time guards;
- Owner analytics/Growth guards;
- Service Point category/QR/context guards.

Foreign keys and uniqueness are additionally checked by migration/domain tests.

## Fresh staging / production database

Use the exact accepted release and run:

```bash
npx prisma migrate deploy
```

Then run production preflight with real target environment/database evidence:

```bash
python scripts/production_preflight.py
```

Do not disable migration-history verification merely to make preflight pass.

## Existing database previously created outside migrations

If an existing external database was historically created with `db push` or manual SQL:

1. take and verify a backup;
2. compare real schema against the exact committed migration-defined schema;
3. fix drift explicitly;
4. only if baseline equivalence is actually proven, use `migrate resolve` for bookkeeping where appropriate;
5. run `npx prisma migrate status`;
6. run production preflight;
7. preserve evidence of comparison/migration result.

`migrate resolve` never repairs schema.

## Backup / restore gate

Create backup:

```bash
BACKUP_DIR=/secure/path python scripts/database_backup.py
```

Restore into an isolated verification database:

```bash
BACKUP_FILE=/secure/path/three-crowns-....dump \
BACKUP_MANIFEST=/secure/path/three-crowns-....manifest.json \
RESTORE_DATABASE_URL=postgresql://.../resort_os_restore \
python scripts/database_restore_verify.py
```

Repository CI proves this mechanism against the current release contract. Production still needs a new backup from the actual target database with checksum/timestamp/restore ownership evidence.

## Production boundary

Current state is **migration-engineering ready, external production evidence incomplete**.

Do not claim production migration success until the actual target database has:

- fresh backup evidence;
- exact accepted release SHA/image set;
- `migrate deploy` result;
- exact seven-migration ledger;
- critical constraint fingerprint;
- readiness/smoke result;
- tested rollback/restore path.

See `knowledge/09_LAUNCH_ACCEPTANCE.md` for the full cutover gate.
