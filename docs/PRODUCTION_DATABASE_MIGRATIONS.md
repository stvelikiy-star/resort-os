# Three Crowns — production database migration gate

Status: **PROCESS + GENERATOR DEFINED / BASELINE SQL NOT YET EXECUTED OR VERIFIED**

This document replaces any idea of using `prisma db push` as the permanent production deployment strategy.

The repository currently uses Prisma 6.x and custom PostgreSQL constraints under `packages/database/sql/`.

## Rules

1. `prisma db push` is allowed only for disposable development/test databases.
2. Production/staging schema changes must be represented by committed Prisma migrations.
3. The initial migration must be generated from the current canonical schema and reviewed before it is accepted.
4. Custom PostgreSQL features not represented by Prisma Schema Language must be included in migration history as reviewed SQL.
5. Never mark a baseline migration as applied on an existing database until schema equivalence has been checked.
6. Never run destructive reset commands against production.
7. Backup -> clean restore verification is required before production migration/cutover.

## Repository helper

A development-only generator is available:

```bash
bash scripts/generate_migration_baseline.sh
```

Safety behavior:
- refuses `APP_ENV=production`;
- refuses to overwrite an existing `prisma/migrations` directory by default;
- runs Prisma format/validate;
- generates `prisma/migrations/0_init/migration.sql` from empty -> current canonical schema;
- appends `packages/database/sql/001_core_constraints.sql` so critical PostgreSQL invariants are not silently left outside migration history;
- asserts required hotel constraints are present in the generated SQL;
- writes a SHA-256 file;
- **does not** run `migrate resolve`, production deploy or modify a production database.

Generated output is still only `GENERATED / NOT VERIFIED` until the clean-database procedure below succeeds.

## Equivalent manual baseline command

From `packages/database/`:

```bash
npm install
npx prisma format
npx prisma validate
mkdir -p prisma/migrations/0_init
npx prisma migrate diff \
  --from-empty \
  --to-schema prisma/schema.prisma \
  --script \
  > prisma/migrations/0_init/migration.sql
```

Then review/append custom PostgreSQL SQL before accepting the migration.

The current critical hotel constraints in `packages/database/sql/001_core_constraints.sql` include at minimum:
- `btree_gist`;
- valid rate/request/reservation/inventory date checks;
- nonnegative reservation total;
- positive payment amount and payment context;
- `no_overlapping_active_room_blocks` exclusion constraint.

NFC is deferred. Dormant NFC schema may still exist in the canonical Prisma data model for backward compatibility, but NFC must not determine active V1 business behavior or cutover acceptance.

## Clean database verification

After generating/reviewing the baseline, use an isolated clean PostgreSQL database:

```bash
DATABASE_URL=postgresql://.../resort_os_migration_test \
  npx prisma migrate deploy
```

Then from repository root with the same isolated database URL:

```bash
python scripts/seed_from_intake.py
python scripts/production_preflight.py
```

For a development/staging verification environment, also run the Resort Core release acceptance path and prove:
- 84 rooms / 12 categories;
- availability/pricing;
- no overlapping room inventory;
- ReservationRequest != Reservation;
- manager-controlled Reservation creation;
- PMS chessboard schedule reads/mutations;
- auth/RBAC;
- internal payments.

Do not set `REQUIRE_MIGRATION_HISTORY=false` merely to make production preflight pass.

## Existing database baseline

For an existing staging/database previously created using `db push`:

1. create and verify a backup;
2. generate/review the baseline;
3. compare the real database schema to the migration-defined schema;
4. fix any drift first;
5. only after equivalence is proven, mark the baseline as applied:

```bash
npx prisma migrate resolve --applied 0_init
```

6. run:

```bash
npx prisma migrate status
```

7. confirm no pending/failed migrations.

`migrate resolve` is bookkeeping, not schema repair. Never use it to hide drift.

## New staging / production databases

For a fresh database after the migration history is committed and verified:

```bash
npx prisma migrate deploy
```

Then run:

```bash
python scripts/production_preflight.py
```

Production preflight must confirm migration history exists and critical constraints are present.

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

Only a successful restore verification may supply `LAST_VERIFIED_BACKUP_AT` to the production preflight gate.

## Current blocker

The baseline SQL itself is **not yet committed/executed/verified** because this environment has not run the repository command against a clean PostgreSQL target.

Until generation, human review and clean-database verification are captured as evidence, migration status remains `NOT READY FOR PRODUCTION`.
