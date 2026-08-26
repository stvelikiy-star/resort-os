#!/usr/bin/env bash
set -euo pipefail

cp scripts/live_client_staging.sh /tmp/live_client_staging_runtime.sh
python - <<'PY'
from pathlib import Path
p = Path('/tmp/live_client_staging_runtime.sh')
s = p.read_text()
old = '''curl --fail -sS "$WEB_URL" >/dev/null
curl --fail -sS "$ADMIN_URL/demo" >/dev/null
curl --fail -sS "$STAFF_URL" >/dev/null
curl --fail -sS "$PUBLIC_CORE_URL/health/live" >/dev/null
'''
new = '''wait_public() {
  local url="$1"
  local label="$2"
  for i in {1..90}; do
    if getent ahosts "$(printf '%s' "$url" | sed -E 's#https?://([^/]+).*#\\1#')" >/dev/null 2>&1 \
       && curl --fail --connect-timeout 5 --max-time 15 -sS "$url" >/dev/null 2>&1; then
      echo "$label reachable: $url"
      return 0
    fi
    sleep 2
  done
  echo "$label did not become reachable: $url" >&2
  return 1
}

wait_public "$WEB_URL" "Public website"
wait_public "$ADMIN_URL/demo" "PMS demo"
wait_public "$STAFF_URL" "Staff PWA"
wait_public "$PUBLIC_CORE_URL/health/live" "Resort Core"
'''
if old not in s:
    raise SystemExit('Expected public tunnel verification block not found')
p.write_text(s.replace(old, new))
PY

exec bash /tmp/live_client_staging_runtime.sh
