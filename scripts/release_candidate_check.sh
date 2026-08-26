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
export RC_MAID_USERNAME="${RC_MAID_USERNAME:-rc-maid}"
export RC_MAID_PASSWORD="${RC_MAID_PASSWORD:-RC-Maid-Local-Only-Password-2026}"
export CORE_API_URL="${CORE_API_URL:-http://127.0.0.1:8000}"

LOG_DIR="${RC_LOG_DIR:-/tmp/three-crowns-rc}"
rm -rf "$LOG_DIR"
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

echo "[1/13] PostgreSQL"
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

echo "[2/13] Prisma validate + development schema"
(
  cd packages/database
  npm install
  npx prisma validate
  npx prisma db push
)

echo "[3/13] Python compile + active release scope guard"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
PY="$ROOT/.venv/bin/python"
"$PY" -m pip install --disable-pip-version-check -r services/api/requirements.txt
"$PY" -m compileall services/api/app scripts
"$PY" scripts/release_scope_guard.py | tee "$LOG_DIR/release-scope.txt"

echo "[4/13] PostgreSQL constraints + evidence-backed seed + synthetic RC staff"
"$PY" scripts/apply_core_constraints.py
"$PY" scripts/seed_from_intake.py
"$PY" scripts/bootstrap_owner.py
STAFF_USERNAME="$RC_MAID_USERNAME" \
STAFF_PASSWORD="$RC_MAID_PASSWORD" \
STAFF_DISPLAY_NAME="RC Synthetic Maid" \
STAFF_ROLE=MAID \
"$PY" scripts/upsert_staff_user.py

echo "[5/13] Admin typecheck/build"
(
  cd apps/admin
  npm install
  CORE_API_URL="$CORE_API_URL" npm run typecheck
  CORE_API_URL="$CORE_API_URL" npm run build
)

echo "[6/13] Public web typecheck/build"
(
  cd apps/web
  npm install
  CORE_API_URL="$CORE_API_URL" npm run typecheck
  CORE_API_URL="$CORE_API_URL" npm run build
)

echo "[7/13] Staff PWA typecheck/build"
(
  cd apps/staff
  npm install
  CORE_API_URL="$CORE_API_URL" npm run typecheck
  CORE_API_URL="$CORE_API_URL" npm run build
)

echo "[8/13] Start Resort Core + health probes"
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
curl --fail --silent --show-error http://127.0.0.1:8000/health/live >"$LOG_DIR/live.json"
curl --fail --silent --show-error http://127.0.0.1:8000/health/ready >"$LOG_DIR/ready.json"
"$PY" - "$LOG_DIR/ready.json" <<'PY'
import json,sys
data=json.load(open(sys.argv[1],encoding='utf-8'))
assert data['status']=='ready'
assert data['room_count']==84, data
assert data['room_type_count']==12, data
print('Readiness invariant: 84 rooms / 12 categories')
PY

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
SEARCH_START=$("$PY" - <<'PY'
from datetime import date,timedelta
print((date.today()+timedelta(days=1)).isoformat())
PY
)
SEARCH_END=$("$PY" - <<'PY'
from datetime import date,timedelta
print((date.today()+timedelta(days=4)).isoformat())
PY
)

echo "[9/13] Auth + PMS 84-room invariant"
UNAUTH_CODE=$(curl --silent --output "$LOG_DIR/unauth-pms.json" --write-out '%{http_code}' \
  "http://127.0.0.1:8000/api/v1/pms/grid?start=$START_DATE&end=$END_DATE")
if [[ "$UNAUTH_CODE" != "401" ]]; then
  echo "ERROR: unauthenticated PMS expected 401, got $UNAUTH_CODE" >&2
  exit 1
fi

curl --fail --silent --show-error -c "$LOG_DIR/cookies.txt" \
  -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$BOOTSTRAP_OWNER_USERNAME\",\"password\":\"$BOOTSTRAP_OWNER_PASSWORD\"}" \
  >"$LOG_DIR/login.json"

curl --fail --silent --show-error -b "$LOG_DIR/cookies.txt" \
  "http://127.0.0.1:8000/api/v1/pms/grid?start=$START_DATE&end=$END_DATE" \
  >"$LOG_DIR/grid.json"

"$PY" - "$LOG_DIR/grid.json" <<'PY'
import json,sys
data=json.load(open(sys.argv[1],encoding='utf-8'))
rooms=data.get('rooms',[])
assert len(rooms)==84, f'expected 84 rooms, got {len(rooms)}'
assert len({room['id'] for room in rooms})==84, 'room ids are not unique'
print('PMS grid invariant: 84 unique rooms')
PY

echo "[10/13] Availability + public ReservationRequest truth"
curl --fail --silent --show-error \
  "http://127.0.0.1:8000/api/v1/booking/check-availability?check_in=$SEARCH_START&check_out=$SEARCH_END&adults=2&children=0" \
  >"$LOG_DIR/availability.json"

"$PY" - "$LOG_DIR/availability.json" "$LOG_DIR/selected-type.txt" <<'PY'
import json,sys
data=json.load(open(sys.argv[1],encoding='utf-8'))
assert data['check_out'] > data['check_in']
results=data.get('results',[])
assert isinstance(results,list)
sellable=[x for x in results if x.get('pricing',{}).get('sellable') and x.get('available_count',0)>0]
assert sellable, 'no sellable availability for RC booking lifecycle'
open(sys.argv[2],'w',encoding='utf-8').write(sellable[0]['room_type_code'])
print(f"Availability contract: {len(results)} category result(s), {len(sellable)} sellable")
PY

TYPE=$(cat "$LOG_DIR/selected-type.txt")
curl --fail --silent --show-error -X POST http://127.0.0.1:8000/api/v1/booking/requests \
  -H 'Content-Type: application/json' \
  -d "{\"guest_name\":\"RC Synthetic Guest\",\"phone\":\"+996700999901\",\"check_in\":\"$SEARCH_START\",\"check_out\":\"$SEARCH_END\",\"adults\":2,\"children\":0,\"room_type_code\":\"$TYPE\",\"source\":\"RC_LOCAL_CHECK\",\"notes\":\"Synthetic local release candidate record\"}" \
  >"$LOG_DIR/request.json"

"$PY" - "$LOG_DIR/request.json" "$LOG_DIR/request-id.txt" <<'PY'
import json,sys
data=json.load(open(sys.argv[1],encoding='utf-8'))
assert data['status']=='NEW'
assert data['is_reservation'] is False
open(sys.argv[2],'w').write(data['id'])
print('ReservationRequest truth: NEW / is_reservation=false')
PY

REQUEST_ID=$(cat "$LOG_DIR/request-id.txt")

echo "[11/13] Manager quote/payment -> reservation -> chessboard schedule"
curl --fail --silent --show-error -b "$LOG_DIR/cookies.txt" \
  -X POST "http://127.0.0.1:8000/api/v1/admin/booking/requests/$REQUEST_ID/quote" \
  -H 'Content-Type: application/json' \
  -d "{\"room_type_code\":\"$TYPE\"}" >"$LOG_DIR/quote.json"

"$PY" - "$LOG_DIR/quote.json" <<'PY'
import json,sys
data=json.load(open(sys.argv[1],encoding='utf-8'))
assert data['status']=='QUOTED'
assert data['quoted_total_kgs'] > 0
assert data.get('required_prepayment_kgs') is None, 'global/system prepayment amount must not be auto-assigned'
assert data.get('prepayment_decided_by_manager') is True
print('Quote truth: stay total calculated; prepayment remains manager-decided')
PY

PAYMENT_KEY="rc-convert-$REQUEST_ID"
curl --fail --silent --show-error -b "$LOG_DIR/cookies.txt" \
  -X POST "http://127.0.0.1:8000/api/v1/admin/booking/requests/$REQUEST_ID/confirm-payment" \
  -H 'Content-Type: application/json' \
  -d "{\"amount_kgs\":777,\"method\":\"RC_MANUAL\",\"provider\":\"MANAGER_MANUAL\",\"external_ref\":\"RC-CONVERT-$REQUEST_ID\",\"idempotency_key\":\"$PAYMENT_KEY\"}" \
  >"$LOG_DIR/reservation.json"

"$PY" - "$LOG_DIR/reservation.json" "$LOG_DIR/reservation-id.txt" <<'PY'
import json,sys
data=json.load(open(sys.argv[1],encoding='utf-8'))
assert data['reservation_status']=='GUARANTEED'
assert data['manager_confirmed_payment_kgs']==777
assert data['payment_collection']=='MANAGER_MANUAL'
open(sys.argv[2],'w').write(data['reservation_id'])
print(f"Guaranteed reservation created: {data['booking_number']} / room {data['room_code']}")
PY

RESERVATION_ID=$(cat "$LOG_DIR/reservation-id.txt")
curl --fail --silent --show-error -b "$LOG_DIR/cookies.txt" \
  "http://127.0.0.1:8000/api/v1/admin/pms/reservations/$RESERVATION_ID/schedule" \
  >"$LOG_DIR/schedule.json"

"$PY" - "$LOG_DIR/schedule.json" <<'PY'
import json,sys
data=json.load(open(sys.argv[1],encoding='utf-8'))
assert data['reservation']['status']=='GUARANTEED'
assert len(data['schedule'])==1
assert data['schedule'][0]['start']==data['reservation']['check_in']
assert data['schedule'][0]['end']==data['reservation']['check_out']
print('Chessboard schedule invariant: one contiguous active reservation segment')
PY

echo "[12/13] Existing-reservation internal payment idempotency"
EXTRA_KEY="rc-extra-$RESERVATION_ID"
cat >"$LOG_DIR/extra-payment-payload.json" <<JSON
{"amount_kgs":321,"method":"RC_MANUAL","external_ref":"RC-EXTRA-$RESERVATION_ID","idempotency_key":"$EXTRA_KEY"}
JSON
curl --fail --silent --show-error -b "$LOG_DIR/cookies.txt" \
  -X POST "http://127.0.0.1:8000/api/v1/admin/booking/reservations/$RESERVATION_ID/payments" \
  -H 'Content-Type: application/json' --data-binary @"$LOG_DIR/extra-payment-payload.json" \
  >"$LOG_DIR/extra-payment-1.json"
curl --fail --silent --show-error -b "$LOG_DIR/cookies.txt" \
  -X POST "http://127.0.0.1:8000/api/v1/admin/booking/reservations/$RESERVATION_ID/payments" \
  -H 'Content-Type: application/json' --data-binary @"$LOG_DIR/extra-payment-payload.json" \
  >"$LOG_DIR/extra-payment-2.json"

"$PY" - "$LOG_DIR/extra-payment-1.json" "$LOG_DIR/extra-payment-2.json" <<'PY'
import json,sys
first=json.load(open(sys.argv[1],encoding='utf-8'))
second=json.load(open(sys.argv[2],encoding='utf-8'))
assert first['idempotent_replay'] is False
assert second['idempotent_replay'] is True
assert first['payment_id']==second['payment_id']
assert first['finance']['paid_kgs']==1098, first['finance']
assert second['finance']['paid_kgs']==1098, second['finance']
print('Internal payment idempotency: replay safe, total not double-counted')
PY

echo "[13/13] Housekeeping inspection/rework lifecycle"
RC_OWNER_USERNAME="$BOOTSTRAP_OWNER_USERNAME" \
RC_OWNER_PASSWORD="$BOOTSTRAP_OWNER_PASSWORD" \
RC_MAID_USERNAME="$RC_MAID_USERNAME" \
RC_MAID_PASSWORD="$RC_MAID_PASSWORD" \
CORE_BASE_URL="http://127.0.0.1:8000" \
"$PY" scripts/release_operations_smoke.py | tee "$LOG_DIR/operations-smoke.txt"

if [[ "${RC_SEED_DEMO:-0}" == "1" ]]; then
  echo "RC_SEED_DEMO=1 -> preparing synthetic showcase bookings"
  DEMO_OWNER_USERNAME="$BOOTSTRAP_OWNER_USERNAME" DEMO_OWNER_PASSWORD="$BOOTSTRAP_OWNER_PASSWORD" \
    CORE_BASE_URL="http://127.0.0.1:8000" "$PY" scripts/prepare_demo_showcase.py
fi

echo
echo "PASS: local release candidate checks completed."
echo "Evidence logs: $LOG_DIR"
echo "Synthetic RC records are marked RC_LOCAL_CHECK / RC_MANUAL and are not real guests or money."
echo "GitHub Actions status is separate; this script does not mark production readiness."
