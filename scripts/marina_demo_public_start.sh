#!/usr/bin/env bash
# Dedicated synthetic demo; no fleet stack, working hotel data or DNS writes.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ $# != 4 ]]; then
  echo "Usage: bash scripts/marina_demo_public_start.sh ADMIN_HOST STAFF_HOST WEB_HOST TLS_EMAIL" >&2
  exit 2
fi
command -v docker >/dev/null
command -v python3 >/dev/null
docker compose version >/dev/null
docker info >/dev/null

ENV_FILE=.marina-demo.env
if [[ ! -f "$ENV_FILE" ]] && docker volume inspect marina_demo_db >/dev/null 2>&1; then
  echo "STOP: demo volume exists but its original credentials file is missing. Restore .marina-demo.env first." >&2
  exit 1
fi

# Validate all inputs and preserve the existing demo secrets. Do not source env
# files in the shell or rotate a password underneath a persisted PostgreSQL.
python3 - "$ENV_FILE" "$@" <<'PY'
from pathlib import Path
import os
import re
import secrets
import sys

path = Path(sys.argv[1])
admin, staff, web, email = sys.argv[2:]
hosts = [admin, staff, web]
pattern = r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}"
if len(set(hosts)) != 3 or any(not re.fullmatch(pattern, h) for h in hosts):
    raise SystemExit("STOP: use three distinct lowercase DNS hostnames, without URL schemes, paths or ports.")
if any(h.endswith((".invalid", ".localhost", ".local")) for h in hosts):
    raise SystemExit("STOP: real publicly reachable DNS names are required.")
if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}", email):
    raise SystemExit("STOP: invalid TLS contact email.")
if path.is_symlink():
    raise SystemExit("STOP: refusing a symlink for demo credentials.")
values = {}
if path.exists():
    for line in path.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            key, sep, value = line.partition('=')
            if not sep or not re.fullmatch(r'[A-Z][A-Z0-9_]*', key):
                raise SystemExit("STOP: unsupported credentials file format; original file preserved.")
            values[key] = value
    required = ['MARINA_DEMO_DB_PASSWORD', 'MARINA_DEMO_OWNER_USERNAME', 'MARINA_DEMO_OWNER_PASSWORD']
    if any(not values.get(k) for k in required):
        raise SystemExit("STOP: existing demo credentials are incomplete; original file preserved.")
else:
    values.update(MARINA_DEMO_DB_PASSWORD=secrets.token_hex(24),
                  MARINA_DEMO_OWNER_USERNAME='demo-owner',
                  MARINA_DEMO_OWNER_PASSWORD=secrets.token_urlsafe(24))
if not re.fullmatch(r'[A-Za-z0-9_-]{16,}', values['MARINA_DEMO_DB_PASSWORD']):
    raise SystemExit("STOP: demo database password must be URL-safe; original file preserved.")
if not re.fullmatch(r'[A-Za-z0-9_-]{6,}' if values['MARINA_DEMO_OWNER_USERNAME'] == 'demo' else r'[A-Za-z0-9_-]{8,}', values['MARINA_DEMO_OWNER_PASSWORD']):
    raise SystemExit("STOP: owner password must be URL-safe (6+ for demo, otherwise 8+); original file preserved.")
if not re.fullmatch(r'[A-Za-z0-9_-]{2,80}', values['MARINA_DEMO_OWNER_USERNAME']):
    raise SystemExit("STOP: unsupported demo owner username; original file preserved.")
for key, value in zip(['MARINA_DEMO_ADMIN_HOST', 'MARINA_DEMO_STAFF_HOST', 'MARINA_DEMO_WEB_HOST', 'MARINA_DEMO_TLS_EMAIL'], sys.argv[2:]):
    if key in values and values[key] != value:
        raise SystemExit(f"STOP: {key} differs from the saved demo configuration; review it before changing domains.")
    values[key] = value
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w') as out:
    os.chmod(path, 0o600)
    out.write(''.join(f'{k}={v}\n' for k, v in values.items()))
print('DEMO_ENV_READY: credentials preserved in .marina-demo.env (0600); no secrets printed')
PY

compose=(docker compose --env-file "$ENV_FILE" -f compose.marina-demo.yaml -f compose.marina-demo-public.yaml)
"${compose[@]}" config --quiet

# Refuse conflicts before building or starting anything. An existing demo Caddy
# may own these ports on a rerun; never stop another project's proxy.
python3 - <<'PY'
import json
import socket
import subprocess

ids = subprocess.check_output(['docker', 'ps', '-q'], text=True).split()
demo_proxy = False
if ids:
    for item in json.loads(subprocess.check_output(['docker', 'inspect', *ids], text=True)):
        labels = item.get('Config', {}).get('Labels') or {}
        ports = item.get('NetworkSettings', {}).get('Ports') or {}
        owns = any(x.get('HostPort') in {'80', '443'} for bindings in ports.values() for x in bindings or [])
        ours = labels.get('com.docker.compose.project') == 'marina-smart-demo' and labels.get('com.docker.compose.service') == 'caddy'
        if owns and not ours:
            raise SystemExit('STOP: ports 80/443 belong to another Docker service. Integrate the demo into the existing proxy; no service stopped.')
        demo_proxy = demo_proxy or (owns and ours)
if not demo_proxy:
    for family, address in [(socket.AF_INET, '0.0.0.0')]:
        for kind, port in [(socket.SOCK_STREAM, 80), (socket.SOCK_STREAM, 443), (socket.SOCK_DGRAM, 443)]:
            with socket.socket(family, kind) as sock:
                try:
                    sock.bind((address, port))
                except OSError as exc:
                    raise SystemExit(f'STOP: cannot bind port {port}: {exc}. No service stopped.')
print('DEMO_PORT_CHECK_PASS')
PY

export COMPOSE_PARALLEL_LIMIT=1
"${compose[@]}" build
"${compose[@]}" up -d --wait

# Check the public TLS endpoint, property identity and security of the login
# cookie. Failed TLS or proxy validation never prints a success/demo link.
python3 - "$@" <<'PY'
import http.cookiejar
import json
from pathlib import Path
import sys
import urllib.request

admin, staff, web, _ = sys.argv[1:]
env = dict(line.split('=', 1) for line in Path('.marina-demo.env').read_text().splitlines() if line and not line.startswith('#'))
for host in (admin, staff, web):
    request = urllib.request.Request(f'https://{host}/')
    with urllib.request.urlopen(request, timeout=15) as reply:
        assert reply.status == 200, f'UI failed for {host}'
with urllib.request.urlopen(f'https://{admin}/core/health/ready', timeout=15) as reply:
    ready = json.load(reply)
    assert ready.get('property') == 'MARINA_DEMO', 'Wrong property behind public demo'
payload = json.dumps({'username': env['MARINA_DEMO_OWNER_USERNAME'], 'password': env['MARINA_DEMO_OWNER_PASSWORD']}).encode()
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
with opener.open(urllib.request.Request(f'https://{admin}/core/api/v1/auth/login', data=payload, headers={'Content-Type': 'application/json'}), timeout=15) as reply:
    who = json.load(reply)
    assert who.get('role') == 'OWNER' and who.get('property_code') == 'MARINA_DEMO', 'Wrong demo identity'
assert any(c.name == 'resort_session' and c.secure and c.has_nonstandard_attr('HttpOnly') for c in jar), 'Secure HttpOnly session cookie missing'
with opener.open(f'https://{admin}/core/api/v1/auth/me', timeout=15) as reply:
    assert json.load(reply).get('property_code') == 'MARINA_DEMO', 'Demo session did not survive login'
with opener.open(urllib.request.Request(f'https://{admin}/core/api/v1/auth/logout', data=b'', method='POST'), timeout=15):
    pass
print('DEMO_PUBLIC_HTTPS_LOGIN_PASS')
print(f'Admin: https://{admin}')
print(f'Staff: https://{staff}')
print(f'Guest: https://{web}')
print('Owner credentials: .marina-demo.env on this server. Share privately; use synthetic data only.')
PY
