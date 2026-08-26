#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE=(-f compose.production.yaml -f compose.production.edge.yaml)
MIGRATION_DIR="$ROOT/packages/database/prisma/migrations/0_init"
MIGRATION="$MIGRATION_DIR/migration.sql"
MIGRATION_SHA="$MIGRATION.sha256"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

fail() { echo "ERROR: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"; }
reject_placeholder() {
  local name="$1" value="$2"
  [ -n "$value" ] || fail "$name is required"
  case "$value" in CHANGE_ME*) fail "$name still contains a CHANGE_ME placeholder" ;; esac
}
query_postgres() {
  local sql="$1"
  printf '%s\n' "$sql" | docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T postgres sh -lc \
    'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At'
}

need docker
need curl
need sha256sum
need awk
need grep
need date

[ -f "$ENV_FILE" ] || fail "Missing $ENV_FILE"
[ -s "$MIGRATION" ] || fail "Missing immutable migration baseline: $MIGRATION"
[ -s "$MIGRATION_SHA" ] || fail "Missing migration checksum: $MIGRATION_SHA"

EXPECTED_SHA="$(awk 'NR==1 {print $1}' "$MIGRATION_SHA")"
ACTUAL_SHA="$(sha256sum "$MIGRATION" | awk '{print $1}')"
[[ "$EXPECTED_SHA" =~ ^[0-9a-fA-F]{64}$ ]] || fail "Migration checksum file is malformed"
[ "$EXPECTED_SHA" = "$ACTUAL_SHA" ] || fail "Migration checksum mismatch: reviewed baseline changed"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

reject_placeholder POSTGRES_DB "${POSTGRES_DB:-}"
reject_placeholder POSTGRES_USER "${POSTGRES_USER:-}"
reject_placeholder POSTGRES_PASSWORD "${POSTGRES_PASSWORD:-}"
reject_placeholder PROPERTY_CODE "${PROPERTY_CODE:-}"
reject_placeholder RATE_PLAN_CODE "${RATE_PLAN_CODE:-}"
reject_placeholder AUTOMATION_SERVICE_KEY "${AUTOMATION_SERVICE_KEY:-}"
reject_placeholder ACME_EMAIL "${ACME_EMAIL:-}"
reject_placeholder LAST_VERIFIED_BACKUP_AT "${LAST_VERIFIED_BACKUP_AT:-}"

[ "${PRODUCTION_CUTOVER_APPROVED:-false}" = "true" ] || fail "PRODUCTION_CUTOVER_APPROVED must be true after explicit owner cutover approval"
[ "${PUBLIC_DNS_READY:-false}" = "true" ] || fail "PUBLIC_DNS_READY must be true before automatic TLS/public smoke"
[ "${REQUIRE_RECENT_BACKUP:-}" = "true" ] || fail "REQUIRE_RECENT_BACKUP must be true for production deploy"
[ "${REQUIRE_MIGRATION_HISTORY:-}" = "true" ] || fail "REQUIRE_MIGRATION_HISTORY must be true for production deploy"
[ "${COOKIE_SECURE:-}" = "true" ] || fail "COOKIE_SECURE must be true for production deploy"
[ "${REQUIRE_COOKIE_DOMAIN:-false}" = "false" ] || fail "REQUIRE_COOKIE_DOMAIN must be false for host-isolated production sessions"
[ -z "${COOKIE_DOMAIN:-}" ] || fail "COOKIE_DOMAIN must be empty so production sessions remain host-only"

[[ "${MAX_BACKUP_AGE_HOURS:-}" =~ ^[1-9][0-9]*$ ]] || fail "MAX_BACKUP_AGE_HOURS must be a positive integer"
BACKUP_EPOCH="$(date -u -d "$LAST_VERIFIED_BACKUP_AT" +%s 2>/dev/null)" || fail "LAST_VERIFIED_BACKUP_AT must be a valid ISO-8601 timestamp"
NOW_EPOCH="$(date -u +%s)"
[ "$BACKUP_EPOCH" -le "$NOW_EPOCH" ] || fail "LAST_VERIFIED_BACKUP_AT cannot be in the future"
BACKUP_AGE_SECONDS=$((NOW_EPOCH - BACKUP_EPOCH))
MAX_BACKUP_AGE_SECONDS=$((MAX_BACKUP_AGE_HOURS * 3600))
[ "$BACKUP_AGE_SECONDS" -le "$MAX_BACKUP_AGE_SECONDS" ] || fail "LAST_VERIFIED_BACKUP_AT is older than MAX_BACKUP_AGE_HOURS"

mkdir -p "$BACKUP_DIR"

docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" config >/dev/null

echo "Building production images before touching the database..."
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" build --pull migrator api web admin staff

docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" up -d postgres
for _ in {1..60}; do
  if docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T postgres sh -lc \
      'PGPASSWORD="$POSTGRES_PASSWORD" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T postgres sh -lc \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null

APP_TABLE_COUNT="$(query_postgres "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('properties','rooms','reservations');")"
MIGRATION_TABLE="$(query_postgres "SELECT CASE WHEN to_regclass('public._prisma_migrations') IS NULL THEN 0 ELSE 1 END;")"
if [ "$APP_TABLE_COUNT" -gt 0 ] && [ "$MIGRATION_TABLE" != "1" ]; then
  fail "Existing application schema has no Prisma migration history; prove schema equivalence and baseline it outside this deploy script"
fi

STAFF_TABLE="$(query_postgres "SELECT CASE WHEN to_regclass('public.staff_users') IS NULL THEN 0 ELSE 1 END;")"
OWNER_COUNT=0
if [ "$STAFF_TABLE" = "1" ]; then
  OWNER_COUNT="$(query_postgres "SELECT count(*) FROM staff_users WHERE role::text='OWNER' AND \"isActive\"=true;")"
fi

if [ "$OWNER_COUNT" -gt 0 ] && [ -n "${BOOTSTRAP_OWNER_PASSWORD:-}" ]; then
  fail "Active OWNER already exists; clear BOOTSTRAP_OWNER_PASSWORD before deployment"
fi

if [ "$APP_TABLE_COUNT" -gt 0 ]; then
  echo "Creating pre-deploy database backup for existing application schema..."
  docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" exec -T postgres sh -lc \
    'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
    > "$BACKUP_DIR/predeploy-$TIMESTAMP.dump"
  test -s "$BACKUP_DIR/predeploy-$TIMESTAMP.dump"
fi

echo "Applying committed Prisma migration history..."
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" run --rm migrator
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" run --rm migrator npx prisma migrate status

echo "Reconciling canonical Three Crowns intake..."
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" run --rm api python /app/scripts/seed_from_intake.py

OWNER_COUNT="$(query_postgres "SELECT count(*) FROM staff_users WHERE role::text='OWNER' AND \"isActive\"=true;")"
if [ "$OWNER_COUNT" = "0" ]; then
  reject_placeholder BOOTSTRAP_OWNER_USERNAME "${BOOTSTRAP_OWNER_USERNAME:-}"
  reject_placeholder BOOTSTRAP_OWNER_PASSWORD "${BOOTSTRAP_OWNER_PASSWORD:-}"
  echo "No active OWNER exists; running one-time owner bootstrap..."
  docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" run --rm \
    -e BOOTSTRAP_OWNER_USERNAME="$BOOTSTRAP_OWNER_USERNAME" \
    -e BOOTSTRAP_OWNER_PASSWORD="$BOOTSTRAP_OWNER_PASSWORD" \
    -e BOOTSTRAP_OWNER_DISPLAY_NAME="${BOOTSTRAP_OWNER_DISPLAY_NAME:-Owner}" \
    api python /app/scripts/bootstrap_owner.py
fi

echo "Running mandatory production preflight before public services..."
docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" run --rm \
  -e BOOTSTRAP_OWNER_PASSWORD= \
  -e REQUIRE_RECENT_BACKUP=true \
  -e LAST_VERIFIED_BACKUP_AT="$LAST_VERIFIED_BACKUP_AT" \
  -e MAX_BACKUP_AGE_HOURS="${MAX_BACKUP_AGE_HOURS:-24}" \
  -e REQUIRE_MIGRATION_HISTORY=true \
  -e EXPECTED_ROOM_COUNT="${EXPECTED_ROOM_COUNT:-84}" \
  -e EXPECTED_ROOM_TYPE_COUNT="${EXPECTED_ROOM_TYPE_COUNT:-12}" \
  -e REQUIRE_COOKIE_DOMAIN=false \
  api python /app/scripts/production_preflight.py

docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" up -d api
for _ in {1..60}; do
  if curl --fail --silent http://127.0.0.1:8000/health/ready >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
curl --fail --show-error --silent http://127.0.0.1:8000/health/ready >/dev/null

docker compose --env-file "$ENV_FILE" "${COMPOSE[@]}" up -d backup web admin staff edge

bash ops/production_smoke.sh "$ENV_FILE"

echo "Production deployment passed preflight and smoke checks."
if [ -f "$BACKUP_DIR/predeploy-$TIMESTAMP.dump" ]; then
  echo "Pre-deploy backup: $BACKUP_DIR/predeploy-$TIMESTAMP.dump"
fi
if [ -n "${BOOTSTRAP_OWNER_PASSWORD:-}" ]; then
  echo "OWNER ACTION REQUIRED: clear BOOTSTRAP_OWNER_PASSWORD from the production secret store before any subsequent deploy."
fi
