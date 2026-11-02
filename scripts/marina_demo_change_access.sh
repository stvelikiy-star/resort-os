#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export MARINA_DEMO_NEW_USERNAME=demo
: "${MARINA_DEMO_NEW_PASSWORD:?Set the chosen demo password}"
export MARINA_DEMO_NEW_PASSWORD
test -f .marina-demo.env

compose=(docker compose --env-file .marina-demo.env -f compose.marina-demo.yaml)
if [[ -f .marina-demo-tunnel.yaml ]]; then
  compose+=(-f .marina-demo-tunnel.yaml)
elif grep -q '^MARINA_DEMO_ADMIN_HOST=' .marina-demo.env; then
  compose+=(-f compose.marina-demo-public.yaml)
fi
"${compose[@]}" config --quiet

# Build before touching the running owner or credentials file.
export COMPOSE_PARALLEL_LIMIT=1
"${compose[@]}" build api seed staff

umask 077
backup_dir=".marina-backups/demo-access-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_dir"
cp .marina-demo.env "$backup_dir/previous.env"
"${compose[@]}" exec -T postgres pg_dump -U marina_demo -d marina_demo -Fc > "$backup_dir/demo.dump"
"${compose[@]}" exec -T postgres pg_restore --list < "$backup_dir/demo.dump" >/dev/null

# This script also runs in the previous API image: no source copying or live
# code patching is needed. Its own DB/property guards run before any mutation.
"${compose[@]}" exec -T -e MARINA_DEMO_NEW_USERNAME -e MARINA_DEMO_NEW_PASSWORD \
  api python - < scripts/marina_demo_set_access.py

python3 - <<'PY'
import os
from pathlib import Path
p = Path('.marina-demo.env')
values = dict(line.split('=', 1) for line in p.read_text().splitlines() if line and not line.startswith('#'))
values['MARINA_DEMO_OWNER_USERNAME'] = os.environ['MARINA_DEMO_NEW_USERNAME']
values['MARINA_DEMO_OWNER_PASSWORD'] = os.environ['MARINA_DEMO_NEW_PASSWORD']
p.write_text(''.join(f'{k}={v}\n' for k, v in values.items()))
p.chmod(0o600)
PY

"${compose[@]}" up -d --no-deps --wait api staff
"${compose[@]}" exec -T api python - <<'PY'
import json, os, urllib.request
data = json.dumps({'username': os.environ['BOOTSTRAP_OWNER_USERNAME'], 'password': os.environ['BOOTSTRAP_OWNER_PASSWORD']}).encode()
request = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/login', data=data, headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=15) as response:
    who = json.load(response)
    assert who['username'] == 'demo' and who['role'] == 'OWNER' and who['property_code'] == 'MARINA_DEMO'
print('DEMO_LOGIN_PASS: username=demo')
PY
