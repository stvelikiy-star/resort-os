# Three Crowns — production database migration gate

Status: **PROCESS DEFINED / BASELINE SQL NOT YET GENERATED OR VERIFIED**

This document replaces any idea of using `prisma db push` as the permanent production deployment strategy.

The repository currently uses Prisma 6.15.x and custom PostgreSQL constraints under `packages/database/sql/`.

## Rules

1. `prisma db push` is allowed only for disposable development/test databases.
2. Production/staging schema changes must be represented by committed Prisma migrations.
3. The initial migration must be generated from the current canonical schema and reviewed before it is committed.
4. Custom PostgreSQL features not represented by Prisma Schema Language must be included in the migration history as reviewed SQL.
5. Never mark a baseline migration as applied on an existing database until schema equivalence has been checked.
6. Never run destructive reset commands against production.
7. Backup -> restore verification is required before production migration/cutover.

## Initial baseline procedure

Run from `packages/database/` in a controlled development/staging workspace:

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

Then review the generated SQL manually.

The current critical hotel constraints in `packages/database/sql/001_core_constraints.sql` must also be represented in committed migration history. Do not silently rely on a separate production bootstrap script forever.

At minimum the reviewed production migration history must preserve:

- `btree_gist` where required;
- valid reservation/request date checks;
- positive payment constraint;
- nonnegative reservation totals;
- no overlapping active inventory blocks for the same room.

NFC is deferred. Dormant NFC SQL must not drive current V1 migration decisions unless the owner explicitly reactivates that module.

## Existing database baseline

For an existing staging/database that was previously created using `db push`:

1. create a verified backup;
2. compare the real database schema to the generated baseline;
3. fix any drift before declaring equivalence;
4. only then mark the baseline as applied using Prisma `migrate resolve`;
5. run `prisma migrate status` and confirm there are no pending/failed migrations.

Example command after verification:

```bash
npx prisma migrate resolve --applied 0_init
```

This command is a bookkeeping action. It must never be used to hide schema drift.

## New staging / production databases

For a fresh database after the migration history is committed:

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

The baseline SQL itself is **not yet committed**. Until it is generated, reviewed and tested on a clean database, migration status remains `NOT READY FOR PRODUCTION`.
