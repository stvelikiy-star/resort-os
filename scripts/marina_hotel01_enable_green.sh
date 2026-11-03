#!/usr/bin/env bash
# Configure the existing private hotel API. Never update code, DB or public demo.
set -euo pipefail
cd "${MARINA_HOTEL_DIRECTORY:-/home/agent/marina-smart-demo}"
test -f .marina-fleet/hotel01.env
test -f compose.marina-fleet.yaml
umask 077
base=(docker compose --env-file .marina-fleet/hotel01.env -f compose.marina-fleet.yaml)
"${base[@]}" exec -T api python - <<'PY'
import os
assert os.environ.get('PROPERTY_CODE') == 'MARINA_HOTEL01', 'Refusing another property or public demo'
assert os.environ.get('MARINA_TENANT_CONTEXT_ENABLED', 'false').lower() == 'false'
from services.api.app import whatsapp_connection
print('PRIVATE_HOTEL_SCOPE_OK')
PY
# BOOTSTRAP_OWNER_* is an initial seed, not a current account credential.
# Validate the operator's current OWNER login before writing config or restarting.
if [[ -z "${MARINA_GREEN_CHECK_USERNAME:-}" ]]; then
  read -r -p 'Действующий логин собственника основной MARINA: ' MARINA_GREEN_CHECK_USERNAME </dev/tty
fi
if [[ -z "${MARINA_GREEN_CHECK_PASSWORD:-}" ]]; then
  read -r -s -p 'Пароль этого собственника (ввод скрыт): ' MARINA_GREEN_CHECK_PASSWORD </dev/tty
  printf '\n' >/dev/tty
fi
export MARINA_GREEN_CHECK_USERNAME MARINA_GREEN_CHECK_PASSWORD
trap 'unset MARINA_GREEN_CHECK_USERNAME MARINA_GREEN_CHECK_PASSWORD' EXIT
"${base[@]}" exec -T -e MARINA_GREEN_CHECK_USERNAME -e MARINA_GREEN_CHECK_PASSWORD api python - <<'PY'
import json, os, sys, urllib.error, urllib.request
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
payload = {'username': os.environ['MARINA_GREEN_CHECK_USERNAME'], 'password': os.environ['MARINA_GREEN_CHECK_PASSWORD']}
request = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/login', data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
try:
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(request, timeout=20) as response:
        who = json.load(response)
except urllib.error.HTTPError as error:
    print(f'OWNER_LOGIN_FAILED: HTTP {error.code}; configuration unchanged', file=sys.stderr)
    sys.exit(1)
if who.get('role') != 'OWNER' or who.get('property_code') != 'MARINA_HOTEL01':
    sys.exit('OWNER_LOGIN_FAILED: a hotel01 OWNER is required; configuration unchanged')
print('OWNER_LOGIN_OK')
PY
container=$("${base[@]}" ps -q api)
test -n "$container"
image=$(docker inspect --format '{{.Image}}' "$container")
[[ "$image" =~ ^sha256:[a-f0-9]{64}$ ]]

secret_dir="${XDG_CONFIG_HOME:-$HOME/.config}/marina"
mkdir -p "$secret_dir"
chmod 700 "$secret_dir"
secret="$secret_dir/hotel01-green.env"
overlay=.marina-hotel01-green.yaml
previous=$(mktemp -d)
trap 'unset MARINA_GREEN_CHECK_USERNAME MARINA_GREEN_CHECK_PASSWORD; rm -rf "$previous"' EXIT
had_secret=false
had_overlay=false
if [[ -f "$secret" ]]; then cp "$secret" "$previous/secret"; had_secret=true; fi
if [[ -f "$overlay" ]]; then cp "$overlay" "$previous/overlay"; had_overlay=true; fi
if [[ ! -f "$secret" ]]; then
  if [[ -z "${GREEN_API_TOKEN_INSTANCE:-}" ]]; then
    read -r -s -p 'apiTokenInstance из GREEN-API (ввод скрыт): ' GREEN_API_TOKEN_INSTANCE </dev/tty
    printf '\n' >/dev/tty
  fi
  [[ "$GREEN_API_TOKEN_INSTANCE" =~ ^[A-Za-z0-9_-]{16,256}$ ]] || { echo 'Invalid token format'; exit 1; }
  printf 'GREEN_API_URL=https://7107.api.greenapi.com\nGREEN_API_ID_INSTANCE=71072278881\nGREEN_API_TOKEN_INSTANCE=%s\n' "$GREEN_API_TOKEN_INSTANCE" > "$secret"
  unset GREEN_API_TOKEN_INSTANCE
fi
chmod 600 "$secret"
cat > "$overlay" <<YAML
services:
  api:
    image: $image
    environment:
      ENABLE_GREEN_API_CONNECTION: "true"
      GREEN_API_PROPERTY_CODE: MARINA_HOTEL01
      GREEN_API_URL: \${GREEN_API_URL:?Provider URL required}
      GREEN_API_ID_INSTANCE: \${GREEN_API_ID_INSTANCE:?Instance required}
      GREEN_API_TOKEN_INSTANCE: \${GREEN_API_TOKEN_INSTANCE:?Token required}
YAML
chmod 600 "$overlay"
compose=("${base[@]}" --env-file "$secret" -f "$overlay")
rollback() {
  trap - ERR
  echo 'Connection check failed; restoring the previous private hotel API configuration.' >&2
  if $had_secret; then cp "$previous/secret" "$secret"; else rm -f "$secret"; fi
  if $had_overlay; then cp "$previous/overlay" "$overlay"; else rm -f "$overlay"; fi
  restore=("${base[@]}")
  if $had_overlay; then restore+=(--env-file "$secret" -f "$overlay"); fi
  "${restore[@]}" up -d --no-deps --no-build --pull never --wait api || true
  exit 1
}
trap rollback ERR
"${compose[@]}" config --quiet
"${compose[@]}" up -d --no-deps --no-build --pull never --wait api
"${compose[@]}" exec -T -e MARINA_GREEN_CHECK_USERNAME -e MARINA_GREEN_CHECK_PASSWORD api python - <<'PY'
import http.cookiejar, json, os, urllib.request
assert os.environ['PROPERTY_CODE'] == 'MARINA_HOTEL01'
cookies = http.cookiejar.CookieJar()
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies), NoRedirect())
base = 'http://127.0.0.1:8000/api/v1'
def call(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base+path, data=data, headers={'Content-Type':'application/json'})
    if path != '/auth/login':
        assert cookies, 'Login did not return a session cookie'
        req.add_header('Cookie', '; '.join(f'{c.name}={c.value}' for c in cookies))
    with opener.open(req, timeout=45) as response:
        return json.load(response)
who = call('/auth/login', {'username':os.environ['MARINA_GREEN_CHECK_USERNAME'], 'password':os.environ['MARINA_GREEN_CHECK_PASSWORD']})
assert who['property_code'] == 'MARINA_HOTEL01' and who['role'] == 'OWNER'
state = call('/admin/whatsapp/connection')
assert state.get('configured') is True
if state.get('account_authorized') is True:
    print('MARINA_WHATSAPP_AUTHORIZED_PASS')
else:
    print('MARINA_WHATSAPP_CONFIGURED: state='+str(state.get('state'))+'; authorization required')
print('Messaging and AI auto-replies have not been enabled or verified.')
PY
trap - ERR
printf '\nОткройте основную MARINA → WhatsApp / AI → Подключение → Проверить подключение.\n'
printf 'При пересоздании API сохраняйте overlay %s и env-файл %s.\n' "$overlay" "$secret"
