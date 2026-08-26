#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE=(-f compose.production.yaml -f compose.production.edge.yaml)
MIGRATION="packages/database/prisma/migrations/20260826_resort_os_baseline/migration.sql"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

fail() { echo "ERROR: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"; }

need docker
need curl
[ -f "$ENV_FILE" ] || fail "Missing $ENV_FILE"
[ -f "$MIGRATION" ] || fail "Missing immutable migration baseline: $MIGRATION"

mkdir -p "$BACKUP_DIR"

# Validate config before touching running services.
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" config >/dev/null

# Snapshot current DB when it exists. Failure is fatal on an existing production volume.
if docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" ps --status running postgres | grep -q postgres; then
  echo "Creating pre-deploy database backup..."
  docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T postgres sh -lc \
    'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
    > "$BACKUP_DIR/predeploy-$TIMESTAMP.dump"
  test -s "$BACKUP_DIR/predeploy-$TIMESTAMP.dump"
fi

# Build first; a failed image build never replaces the running release.
echo "Building production images..."
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" build --pull api web admin staff

# Database starts first; immutable SQL is idempotent only for a fresh baseline.
# For an already initialized production database, future changes must use additive migrations.
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" up -d postgres
for i in {1..60}; do
  if docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T postgres sh -lc \
      'PGPASSWORD="$POSTGRES_PASSWORD" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

# Apply baseline only when Prisma migrations table and application tables are absent.
TABLES=$(docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T postgres sh -lc \
  'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema=\u0027public\u0027 AND table_name IN (\u0027properties\u0027,\u0027rooms\u0027,\u0027reservations\u0027);"')
if [ "$TABLES" = "0" ]; then
  echo "Applying initial immutable database baseline..."
  cat "$MIGRATION" | docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T postgres sh -lc \
    'PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
else
  echo "Existing application schema detected; initial baseline will not be replayed."
fi

# Bring up backend before user-facing surfaces.
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" up -d api
for i in {1..60}; do
  if curl --fail --silent http://127.0.0.1:8000/health/ready >/dev/null; then break; fi
  sleep 2
done
curl --fail --silent http://127.0.0.1:8000/health/ready

# Seed is reconciliation-based and keeps the canonical 84-room/12-category baseline.
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T api python /app/scripts/seed_from_intake.py

# Owner bootstrap is idempotent; remove bootstrap password from host env after first launch.
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T api python /app/scripts/bootstrap_owner.py

docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" up -d web admin staff edge

bash ops/production_smoke.sh "$ENV_FILE"

echo "Production deployment passed smoke checks."
echo "Backup retained at: $BACKUP_DIR/predeploy-$TIMESTAMP.dump (if an existing DB was present)."
