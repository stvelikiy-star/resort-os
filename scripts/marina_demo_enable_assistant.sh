#!/usr/bin/env bash
# Enable the existing assistant in the public demo without updating application code.
set -euo pipefail
cd "${MARINA_DEMO_DIRECTORY:-/home/agent/marina-smart-public-demo}"
test -f .marina-demo.env
test -f compose.marina-demo.yaml
umask 077

base=(docker compose --env-file .marina-demo.env -f compose.marina-demo.yaml)
if [[ -f .marina-demo-tunnel.yaml ]]; then
  base+=(-f .marina-demo-tunnel.yaml)
elif grep -q '^MARINA_DEMO_ADMIN_HOST=' .marina-demo.env; then
  base+=(-f compose.marina-demo-public.yaml)
fi

# Check the running container, not the name of the checkout. Refuse private hotels.
"${base[@]}" exec -T api python - <<'PY'
import os
assert os.environ.get('PROPERTY_CODE') == 'MARINA_DEMO', 'Refusing non-demo property'
from services.api.app import marina_assistant as a
assert a.MANUAL_TEXT.strip(), 'Existing assistant knowledge is missing'
print('DEMO_ASSISTANT_SCOPE_OK')
PY
container=$("${base[@]}" ps -q api)
test -n "$container"
image=$(docker inspect --format '{{.Image}}' "$container")
[[ "$image" =~ ^sha256:[a-f0-9]{64}$ ]]

secret_dir="${XDG_CONFIG_HOME:-$HOME/.config}/marina"
mkdir -p "$secret_dir"
chmod 700 "$secret_dir"
secret="$secret_dir/demo-assistant.env"
overlay=.marina-demo-assistant.yaml
previous=$(mktemp -d)
trap 'rm -rf "$previous"' EXIT
had_secret=false
had_overlay=false
if [[ -f "$secret" ]]; then cp "$secret" "$previous/secret"; had_secret=true; fi
if [[ -f "$overlay" ]]; then cp "$overlay" "$previous/overlay"; had_overlay=true; fi

# Keep the key out of the terminal, shell history, repository and browser.
if [[ ! -f "$secret" ]]; then
  if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    read -r -s -p 'Ключ OpenAI для демо (ввод скрыт): ' OPENAI_API_KEY </dev/tty
    printf '\n' >/dev/tty
  fi
  [[ "$OPENAI_API_KEY" =~ ^sk-[A-Za-z0-9_-]+$ ]] || { echo 'Invalid key format'; exit 1; }
  printf 'OPENAI_API_KEY=%s\n' "$OPENAI_API_KEY" > "$secret"
  unset OPENAI_API_KEY
fi
chmod 600 "$secret"

cat > "$overlay" <<YAML
services:
  api:
    image: $image
    environment:
      OPENAI_API_KEY: \${OPENAI_API_KEY:?Demo assistant key required}
      OPENAI_MARINA_ASSISTANT_MODEL: gpt-4.1-mini
      MARINA_ASSISTANT_RATE_LIMIT_PER_MINUTE: "6"
      MARINA_ASSISTANT_MAX_OUTPUT_TOKENS: "800"
YAML
chmod 600 "$overlay"
compose=("${base[@]}" --env-file "$secret" -f "$overlay")

rollback() {
  trap - ERR
  echo 'Assistant activation failed; restoring the previous demo API configuration.' >&2
  if $had_secret; then cp "$previous/secret" "$secret"; else rm -f "$secret"; fi
  if $had_overlay; then cp "$previous/overlay" "$overlay"; else rm -f "$overlay"; fi
  restore=("${base[@]}")
  if $had_overlay; then restore+=(--env-file "$secret" -f "$overlay"); fi
  "${restore[@]}" up -d --no-deps --no-build --pull never --wait api || true
  exit 1
}
trap rollback ERR
"${compose[@]}" config --quiet
# Reuse the exact running image. Do not rebuild, migrate, seed or touch tunnels.
"${compose[@]}" up -d --no-deps --no-build --pull never --wait api
"${compose[@]}" exec -T api python - <<'PY'
import http.cookiejar, json, os, urllib.request
assert os.environ['PROPERTY_CODE'] == 'MARINA_DEMO'
cookies = http.cookiejar.CookieJar()
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies), NoRedirect())
base = 'http://127.0.0.1:8000/api/v1'
def call(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base+path, data=data, headers={'Content-Type':'application/json'})
    # Production Secure cookies are deliberately omitted on HTTP by CookieJar.
    # This probe runs inside the API container: send its login cookie explicitly
    # to the fixed loopback endpoint, without weakening COOKIE_SECURE or redirects.
    if path != '/auth/login':
        assert cookies, 'Login did not return a session cookie'
        req.add_header('Cookie', '; '.join(f'{c.name}={c.value}' for c in cookies))
    with opener.open(req, timeout=60) as response:
        return json.load(response)
who = call('/auth/login', {'username':os.environ['BOOTSTRAP_OWNER_USERNAME'], 'password':os.environ['BOOTSTRAP_OWNER_PASSWORD']})
assert who['property_code'] == 'MARINA_DEMO'
cap = call('/assistant/capabilities')
assert cap['configured'] and cap['read_only'] and not cap['can_mutate']
answer = call('/assistant/chat', {'locale':'ru', 'current_screen':'PMS', 'messages':[{'role':'user','content':'Объясни новичку, что означает одна клетка Супершахматки. Ничего не изменяй.'}]})
assert isinstance(answer.get('answer'), str) and answer['answer'].strip()
print('DEMO_ASSISTANT_LIVE_PASS: authenticated real response; read-only')
print(answer['answer'][:1000])
PY
trap - ERR
printf '\nВ демо откройте «Помощник» и задайте вопрос.\n'
printf 'При пересоздании API сохраняйте overlay %s и env-файл %s.\n' "$overlay" "$secret"
