#!/usr/bin/env bash
# Read-only provider diagnosis in the running private API. Never restart services.
set -euo pipefail
cd "${MARINA_HOTEL_DIRECTORY:-/home/agent/marina-smart-demo}"
compose=(docker compose --env-file .marina-fleet/hotel01.env -f compose.marina-fleet.yaml)
"${compose[@]}" exec -T api python - <<'PY'
import os
assert os.environ.get('PROPERTY_CODE') == 'MARINA_HOTEL01', 'Refusing another property or public demo'
print('PRIVATE_HOTEL_SCOPE_OK; read-only diagnosis')
PY
if [[ -z "${GREEN_API_TOKEN_INSTANCE:-}" ]]; then
  read -r -s -p 'apiTokenInstance из GREEN-API (ввод скрыт): ' GREEN_API_TOKEN_INSTANCE </dev/tty
  printf '\n' >/dev/tty
fi
[[ "$GREEN_API_TOKEN_INSTANCE" =~ ^[A-Za-z0-9_-]{16,256}$ ]] || { echo 'TOKEN_FORMAT_INVALID'; exit 1; }
export GREEN_API_TOKEN_INSTANCE
trap 'unset GREEN_API_TOKEN_INSTANCE' EXIT
"${compose[@]}" exec -T -e GREEN_API_TOKEN_INSTANCE api python - <<'PY'
import logging, os, socket, ssl
logging.disable(logging.CRITICAL)
import httpx
assert os.environ.get('PROPERTY_CODE') == 'MARINA_HOTEL01'
host = '7107.api.greenapi.com'
instance = '71072278881'
try:
    socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
except socket.gaierror:
    print('GREEN_NETWORK=DNS_ERROR')
    raise SystemExit(1) from None
print('GREEN_DNS=OK')
url = f'https://{host}/waInstance{instance}/getStateInstance/'+os.environ['GREEN_API_TOKEN_INSTANCE']
try:
    with httpx.Client(timeout=15, follow_redirects=False) as client:
        response = client.get(url)
except (ImportError, ValueError) as error:
    print('GREEN_CLIENT='+type(error).__name__)
    raise SystemExit(1) from None
except httpx.HTTPError as error:
    cause = error
    causes = set()
    while cause is not None and id(cause) not in causes:
        causes.add(id(cause))
        if isinstance(cause, ssl.SSLError):
            print('GREEN_NETWORK=TLS_ERROR')
            break
        if isinstance(cause, socket.gaierror):
            print('GREEN_NETWORK=DNS_ERROR')
            break
        cause = cause.__cause__ or cause.__context__
    else:
        kind = type(error).__name__
        print('GREEN_NETWORK='+kind)
    raise SystemExit(1) from None
print('GREEN_HTTP='+str(response.status_code))
if response.status_code != 200:
    # Never print the provider body, Location, request URL or exception text.
    raise SystemExit(1)
if len(response.content) > 1_000_000:
    print('GREEN_RESPONSE=TOO_LARGE')
    raise SystemExit(1)
try:
    body = response.json()
except ValueError:
    print('GREEN_RESPONSE=INVALID_JSON')
    raise SystemExit(1) from None
states = {'notAuthorized','authorized','blocked','sleepMode','starting','yellowCard'}
state = body.get('stateInstance') if isinstance(body, dict) else None
if not isinstance(state, str) or state not in states:
    print('GREEN_RESPONSE=UNKNOWN_STATE')
    raise SystemExit(1)
print('GREEN_STATE='+state)
PY
