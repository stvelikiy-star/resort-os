#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-${ENV_FILE:-.env.production}}"
[ -f "$ENV_FILE" ] || { echo "Missing env file: $ENV_FILE" >&2; exit 1; }

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

PUBLIC_HOST="${PUBLIC_HOST:-3korony.com}"
PMS_HOST="${PMS_HOST:-pms.3korony.com}"
STAFF_HOST="${STAFF_HOST:-staff.3korony.com}"
CORE_HOST="${CORE_HOST:-core.3korony.com}"

check() {
  local name="$1" url="$2"
  echo "Checking $name: $url"
  curl --fail --show-error --silent --location \
    --connect-timeout 10 --max-time 30 "$url" >/dev/null
}

check "public website" "https://${PUBLIC_HOST}/"
check "public room catalog" "https://${PUBLIC_HOST}/rooms"
check "PMS" "https://${PMS_HOST}/"
check "PMS showcase route" "https://${PMS_HOST}/demo"
check "Staff PWA" "https://${STAFF_HOST}/"
check "Core live" "https://${CORE_HOST}/health/live"
check "Core ready" "https://${CORE_HOST}/health/ready"

TODAY=$(date -u +%F)
CHECK_IN=$(date -u -d "$TODAY + 1 day" +%F)
CHECK_OUT=$(date -u -d "$TODAY + 3 days" +%F)
AVAILABILITY=$(curl --fail --show-error --silent \
  "https://${PUBLIC_HOST}/core/api/v1/booking/check-availability?check_in=${CHECK_IN}&check_out=${CHECK_OUT}&adults=2&children=0")
python - "$AVAILABILITY" <<'PY'
import json, sys
payload=json.loads(sys.argv[1])
results=payload.get('results') or []
assert results, 'availability returned no room categories'
assert any((item.get('pricing') or {}).get('sellable') for item in results), 'no sellable category in smoke window'
print(f"Availability smoke OK: {len(results)} categories returned")
PY

echo "Public/Core production smoke checks passed."
