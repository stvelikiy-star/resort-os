#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

ENV_FILE=".env.real-admin"
COMPOSE_FILE="compose.staging.yaml"
export COMPOSE_PROJECT_NAME="threecrownsrealadmin"

fail() {
  printf '\nERROR: %s\n' "$1" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "Docker Desktop is not installed."
docker info >/dev/null 2>&1 || fail "Docker Desktop is not running. Start Docker Desktop and run this script again."
[ -f "$ENV_FILE" ] || fail "$ENV_FILE is missing."
[ -f "$COMPOSE_FILE" ] || fail "$COMPOSE_FILE is missing."

printf '\n=== THREE CROWNS REAL ADMIN / Resort OS 0.62.2 ===\n'
printf 'This starts the real apps/admin + FastAPI Resort Core + PostgreSQL.\n'
printf 'No standalone demo UI and no synthetic booking showcase are used.\n\n'

# Keep an existing local review volume unless RESET is explicitly requested.
if [ "${RESET_REAL_ADMIN:-0}" = "1" ]; then
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down -v --remove-orphans || true
else
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down --remove-orphans || true
fi

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d postgres

printf 'Waiting for PostgreSQL...\n'
for i in $(seq 1 60); do
  if docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres pg_isready -U resort_admin_review -d resort_os_real_admin >/dev/null 2>&1; then
    break
  fi
  [ "$i" -lt 60 ] || fail "PostgreSQL did not become ready."
  sleep 2
done

DB_URL='postgresql://resort_admin_review:TC_Local_DB_2026_Review_Only@host.docker.internal:15432/resort_os_real_admin?schema=public'

printf 'Applying the committed Prisma migration ledger...\n'
docker run --rm \
  -v "$PWD/packages/database:/work" \
  -w /work \
  -e DATABASE_URL="$DB_URL" \
  node:22-alpine \
  sh -lc 'npm ci --no-audit --no-fund >/dev/null && npx prisma migrate deploy'

printf 'Loading canonical Three Crowns inventory/rates and local role accounts...\n'
docker run --rm \
  -v "$PWD:/work" \
  -w /work \
  -e DATABASE_URL="$DB_URL" \
  -e PROPERTY_CODE=THREE_CROWNS \
  -e APP_ENV=staging \
  -e BOOTSTRAP_OWNER_USERNAME=owner_local \
  -e BOOTSTRAP_OWNER_PASSWORD=TCReviewOwner2026Safe \
  -e BOOTSTRAP_OWNER_DISPLAY_NAME='Three Crowns Owner' \
  -e STAGING_RECEPTION_USERNAME=reception_local \
  -e STAGING_RECEPTION_PASSWORD=TCReviewReception2026Safe \
  -e STAGING_RECEPTION_DISPLAY_NAME=Reception \
  -e STAGING_DINING_USERNAME=dining_local \
  -e STAGING_DINING_PASSWORD=TCReviewDining2026Safe \
  -e STAGING_DINING_DISPLAY_NAME=Dining \
  -e STAGING_MAID_USERNAME=maid_local \
  -e STAGING_MAID_PASSWORD=TCReviewMaid2026Safe \
  -e STAGING_MAID_DISPLAY_NAME=Housekeeping \
  -e STAGING_TECHNICIAN_USERNAME=tech_local \
  -e STAGING_TECHNICIAN_PASSWORD=TCReviewTech2026Safe \
  -e STAGING_TECHNICIAN_DISPLAY_NAME=Maintenance \
  python:3.12-slim \
  sh -lc 'pip install --disable-pip-version-check --no-cache-dir -q asyncpg argon2-cffi && python scripts/seed_from_intake.py && python scripts/bootstrap_owner.py && python scripts/bootstrap_staging_staff.py'

printf 'Building and starting real Resort Core + Admin/PMS + Staff...\n'
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build api admin staff

printf 'Waiting for Resort Core...\n'
for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:18000/health/ready >/dev/null 2>&1; then
    break
  fi
  [ "$i" -lt 90 ] || {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
    fail "Resort Core did not become ready."
  }
  sleep 2
done

printf 'Waiting for Admin/PMS...\n'
for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:13001/ >/dev/null 2>&1; then
    break
  fi
  [ "$i" -lt 90 ] || {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
    fail "Admin/PMS did not become ready."
  }
  sleep 2
done

COOKIE_JAR="${TMPDIR:-/tmp}/three-crowns-real-admin.cookies"
LOGIN_BODY="${TMPDIR:-/tmp}/three-crowns-real-admin-login.json"
rm -f "$COOKIE_JAR" "$LOGIN_BODY"

printf 'Verifying Admin -> Core -> PostgreSQL authentication path...\n'
curl -fsS \
  -c "$COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -d '{"username":"owner_local","password":"TCReviewOwner2026Safe"}' \
  http://127.0.0.1:13001/core/api/v1/auth/login > "$LOGIN_BODY" \
  || fail "Owner login through the real Admin/Core path failed."

curl -fsS -b "$COOKIE_JAR" http://127.0.0.1:13001/core/api/v1/auth/me >/dev/null \
  || fail "Authenticated /auth/me check failed."

printf '\nREADY: real Three Crowns Admin/PMS is running.\n'
printf 'Admin/PMS:  http://127.0.0.1:13001\n'
printf 'Staff:      http://127.0.0.1:13002\n'
printf 'Core health:http://127.0.0.1:18000/health/ready\n\n'
printf 'OWNER LOGIN\n  user: owner_local\n  pass: TCReviewOwner2026Safe\n\n'
printf 'Reception: reception_local / TCReviewReception2026Safe\n'
printf 'Dining:    dining_local / TCReviewDining2026Safe\n'
printf 'Maid:      maid_local / TCReviewMaid2026Safe\n'
printf 'Tech:      tech_local / TCReviewTech2026Safe\n\n'
printf 'The local database contains canonical hotel inventory/rates only. No fake reservations were pre-created.\n'

if command -v open >/dev/null 2>&1; then
  open http://127.0.0.1:13001 >/dev/null 2>&1 || true
fi
