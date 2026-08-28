#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_DIR="$ROOT/packages/database"
MIGRATION_DIR="$DB_DIR/prisma/migrations/0_init"
MIGRATION_FILE="$MIGRATION_DIR/migration.sql"
CUSTOM_SQL="$DB_DIR/sql/001_core_constraints.sql"

if [[ "${APP_ENV:-development}" == "production" || "${APP_ENV:-development}" == "prod" ]]; then
  echo "ERROR: baseline generation is disabled when APP_ENV=production" >&2
  exit 1
fi

if [[ -e "$DB_DIR/prisma/migrations" && "${ALLOW_REPLACE_MIGRATIONS:-0}" != "1" ]]; then
  echo "ERROR: prisma/migrations already exists. Review it manually; this script will not overwrite migration history." >&2
  echo "Set ALLOW_REPLACE_MIGRATIONS=1 only in a controlled disposable branch/workspace after explicit review." >&2
  exit 1
fi

if [[ ! -f "$DB_DIR/prisma/schema.prisma" || ! -f "$CUSTOM_SQL" ]]; then
  echo "ERROR: canonical Prisma schema or core constraint SQL is missing" >&2
  exit 1
fi

cd "$DB_DIR"
npm install
npx prisma format
npx prisma validate

if [[ -e prisma/migrations ]]; then
  backup="prisma/migrations.prebaseline.$(date +%Y%m%d%H%M%S)"
  mv prisma/migrations "$backup"
  echo "Existing migration directory moved to $backup for explicit review."
fi

mkdir -p "$MIGRATION_DIR"
TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

npx prisma migrate diff \
  --from-empty \
  --to-schema-datamodel prisma/schema.prisma \
  --script > "$TMP_FILE"

if [[ ! -s "$TMP_FILE" ]]; then
  echo "ERROR: Prisma generated an empty baseline" >&2
  exit 1
fi

{
  cat "$TMP_FILE"
  printf '\n\n-- ================================================================\n'
  printf '%s\n' '-- Resort OS custom PostgreSQL invariants reviewed separately from Prisma DSL.'
  printf '%s\n' '-- Source at generation time: packages/database/sql/001_core_constraints.sql'
  printf '%s\n' '-- ================================================================'
  cat "$CUSTOM_SQL"
} > "$MIGRATION_FILE"

required=(
  'CREATE EXTENSION IF NOT EXISTS btree_gist'
  'reservation_request_valid_dates'
  'reservation_valid_dates'
  'reservation_nonnegative_total'
  'inventory_block_valid_dates'
  'no_overlapping_active_room_blocks'
  'payment_positive_amount'
  'payment_has_context'
)
for needle in "${required[@]}"; do
  if ! grep -Fq "$needle" "$MIGRATION_FILE"; then
    echo "ERROR: generated baseline is missing required invariant: $needle" >&2
    exit 1
  fi
done

(
  cd "$MIGRATION_DIR"
  sha256sum migration.sql > migration.sql.sha256
  sha256sum -c migration.sql.sha256
)
cat "$MIGRATION_FILE.sha256"

echo
echo "Baseline generated: $MIGRATION_FILE"
echo "STATUS: GENERATED / NOT YET VERIFIED"
echo
cat <<'NEXT'
Required next steps before committing/using this baseline:
1. Review migration.sql, especially PostgreSQL enums/indexes/FKs and appended custom constraints.
2. Apply it to a clean PostgreSQL database with `npx prisma migrate deploy`.
3. Run seed + Resort Core release checks against that clean migrated database.
4. Compare an existing db-push staging schema with the baseline before any `migrate resolve --applied 0_init`.
5. Never run `migrate resolve` merely to hide schema drift.
NEXT
