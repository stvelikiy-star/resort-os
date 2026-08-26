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

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${BOOTSTRAP_OWNER_USERNAME:?BOOTSTRAP_OWNER_USERNAME is required for first deployment}"
: "${BOOTSTRAP_OWNER_PASSWORD:?BOOTSTRAP_OWNER_PASSWORD is required for first deployment}"

mkdir -p "$BACKUP_DIR"

docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" config >/dev/null

if docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" ps --status running postgres | grep -q postgres; then
  echo "Creating pre-deploy database backup..."
  docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T postgres sh -lc \
    'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
    > "$BACKUP_DIR/predeploy-$TIMESTAMP.dump"
  test -s "$BACKUP_DIR/predeploy-$TIMESTAMP.dump"
fi

echo "Building production images before replacing services..."
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" build --pull api web admin staff

docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" up -d postgres
for i in {1..60}; do
  if docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T postgres sh -lc \
      'PGPASSWORD="$POSTGRES_PASSWORD" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T postgres sh -lc \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null

SCHEMA_PROBE="SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('properties','rooms','reservations');"
TABLES=$(printf '%s\n' "$SCHEMA_PROBE" | docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T postgres sh -lc \
  'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At')

if [ "$TABLES" = "0" ]; then
  echo "Applying initial immutable database baseline..."
  cat "$MIGRATION" | docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T postgres sh -lc \
    'PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
else
  echo "Existing application schema detected; initial baseline will not be replayed."
fi

docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" up -d api
for i in {1..60}; do
  if curl --fail --silent http://127.0.0.1:8000/health/ready >/dev/null 2>&1; then break; fi
  sleep 2
done
curl --fail --show-error --silent http://127.0.0.1:8000/health/ready >/dev/null

docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T api python /app/scripts/seed_from_intake.py
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T api python /app/scripts/bootstrap_owner.py

docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" up -d backup web admin staff edge

bash ops/production_smoke.sh "$ENV_FILE"

echo "Production deployment passed smoke checks."
if [ -f "$BACKUP_DIR/predeploy-$TIMESTAMP.dump" ]; then
  echo "Pre-deploy backup: $BACKUP_DIR/predeploy-$TIMESTAMP.dump"
fi
