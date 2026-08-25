#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${APP_ENV:-development}" == "production" || "${APP_ENV:-development}" == "prod" ]]; then
  echo "ERROR: release_candidate_check.sh is a development/staging verifier and refuses APP_ENV=production" >&2
  exit 1
fi

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "ERROR: required command not found: $1" >&2; exit 1; }
}

need docker
need npm
need curl
need python3

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export DATABASE_URL="${DATABASE_URL:-postgresql://resort:resort@127.0.0.1:5432/resort_os?schema=public}"
export PROPERTY_CODE="${PROPERTY_CODE:-THREE_CROWNS}"
export RATE_PLAN_CODE="${RATE_PLAN_CODE:-DIRECT_2026_27}"
export COOKIE_SECURE="${COOKIE_SECURE:-false}"
export BOOTSTRAP_OWNER_USERNAME="${BOOTSTRAP_OWNER_USERNAME:-rc-owner}"
export BOOTSTRAP_OWNER_PASSWORD="${BOOTSTRAP_OWNER_PASSWORD:-RC-Local-Only-Password-2026}"
export BOOTSTRAP_OWNER_DISPLAY_NAME="${BOOTSTRAP_OWNER_DISPLAY_NAME:-Release Check Owner}"
export CORE_API_URL="${CORE_API_URL:-http://127.0.0.1:8000}"

LOG_DIR="${RC_LOG_DIR:-/tmp/three-crowns-rc}"
mkdir -p "$LOG_DIR"
API_PID=""

cleanup() {
  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "== Three Crowns Release Candidate Check =="
echo "Repository: $ROOT"
echo "Logs: $LOG_DIR"

echo "[1/10] PostgreSQL"
docker compose up -d postgres
for attempt in {1..30}; do
  if docker compose exec -T postgres pg_isready -U resort -d resort_os >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" == "30" ]]; then
    echo "ERROR: PostgreSQL did not become ready" >&2
    exit 1
  fi
  sleep 1
done

echo "[2/10] Prisma validate + development schema"
(
  cd packages/database
  npm install
  npx prisma validate
  npx prisma db push
)

echo "[3/10] Python environment"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
PY="$ROOT/.venv/bin/python"
"$PY" -m pip install --disable-pip-version-check -r services/api/requirements.txt
"$PY" -m compileall services/api/app scripts

echo "[4/10] PostgreSQL constraints + evidence-backed seed"
"$PY" scripts/apply_core_constraints.py
"$PY" scripts/seed_from_intake.py
"$PY" scripts/bootstrap_owner.py

echo "[5/10] Admin typecheck/build"
(
  cd apps/admin
  npm install
  CORE_API_URL="$CORE_API_URL" npm run typecheck
  CORE_API_URL="$CORE_API_URL" npm run build
)

echo "[6/10] Public web typecheck/build"
(
  cd apps/web
  npm install
  CORE_API_URL="$CORE_API_URL" npm run typecheck
  CORE_API_URL="$CORE_API_URL" npm run build
)

echo "[7/10] Staff PWA typecheck/build"
(
  cd apps/staff
  npm install
  CORE_API_URL="$CORE_API_URL" npm run typecheck
  CORE_API_URL="$CORE_API_URL" npm run build
)

echo "[8/10] Start Resort Core"
"$PY" -m uvicorn app.app_entry:app --app-dir services/api --host 127.0.0.1 --port 8000 >"$LOG_DIR/core.log" 2>&1 &
API_PID=$!
for attempt in {1..30}; do
  if curl --fail --silent --show-error http://127.0.0.1:8000/health >"$LOG_DIR/health.json" 2>/dev/null; then
    break
  fi
  if [[ "$attempt" == "30" ]]; then
    echo "ERROR: Resort Core did not become healthy" >&2
    cat "$LOG_DIR/core.log" >&2 || true
    exit 1
  fi
  sleep 1
done
curl --fail --silent --show-error http://127.0.0.1:8000/health/ready >"$LOG_DIR/ready.json"

echo "[9/10] Auth + PMS 84-room invariant"
UNAUTH_CODE=$(curl --silent --output "$LOG_DIR/unauth-pms.json" --write-out '%{http_code}' \
  'http://127.0.0.1:8000/api/v1/pms/grid?start=2026-08-26&end=2026-09-09')
if [[ "$UNAUTH_CODE" != "401" ]]; then
  echo "ERROR: unauthenticated PMS expected 401, got $UNAUTH_CODE" >&2
  exit 1
fi

curl --fail --silent --show-error -c "$LOG_DIR/cookies.txt" \
  -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$BOOTSTRAP_OWNER_USERNAME\",\"password\":\"$BOOTSTRAP_OWNER_PASSWORD\"}" \
  >"$LOG_DIR/login.json"

START_DATE=$("$PY" - <<'PY'
from datetime import date
print(date.today().isoformat())
PY
)
END_DATE=$("$PY" - <<'PY'
from datetime import date,timedelta
print((date.today()+timedelta(days=14)).isoformat())
PY
)

curl --fail --silent --show-error -b "$LOG_DIR/cookies.txt" \
  "http://127.0.0.1:8000/api/v1/pms/grid?start=$START_DATE&end=$END_DATE" \
  >"$LOG_DIR/grid.json"

"$PY" - "$LOG_DIR/grid.json" <<'PY'
import json,sys
path=sys.argv[1]
data=json.load(open(path,encoding='utf-8'))
rooms=data.get('rooms',[])
assert len(rooms)==84, f'expected 84 rooms, got {len(rooms)}'
assert len({room['id'] for room in rooms})==84, 'room ids are not unique'
print('PMS grid invariant: 84 unique rooms')
PY

echo "[10/10] Availability + public request truth"
SEARCH_START=$("$PY" - <<'PY'
from datetime import date,timedelta
print((date.today()+timedelta(days=1)).isoformat())
PY
)
SEARCH_END=$("$PY" - <<'PY'
from datetime import date,timedelta
print((date.today()+timedelta(days=3)).isoformat())
PY
)
curl --fail --silent --show-error \
  "http://127.0.0.1:8000/api/v1/booking/check-availability?check_in=$SEARCH_START&check_out=$SEARCH_END&adults=2&children=0" \
  >"$LOG_DIR/availability.json"

"$PY" - "$LOG_DIR/availability.json" <<'PY'
import json,sys
data=json.load(open(sys.argv[1],encoding='utf-8'))
assert data['check_out'] > data['check_in']
assert isinstance(data.get('results'),list)
print(f"Availability contract: {len(data['results'])} category result(s)")
PY

if [[ "${RC_SEED_DEMO:-0}" == "1" ]]; then
  echo "RC_SEED_DEMO=1 -> preparing synthetic showcase bookings"
  DEMO_OWNER_USERNAME="$BOOTSTRAP_OWNER_USERNAME" DEMO_OWNER_PASSWORD="$BOOTSTRAP_OWNER_PASSWORD" \
    CORE_BASE_URL="http://127.0.0.1:8000" "$PY" scripts/prepare_demo_showcase.py
fi

echo
echo "PASS: local release candidate checks completed."
echo "Evidence logs: $LOG_DIR"
echo "GitHub Actions status is separate; this script does not mark production readiness."
