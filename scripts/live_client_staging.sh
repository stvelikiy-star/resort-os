#!/usr/bin/env bash
set -euo pipefail

DB_URL="${DATABASE_URL:-postgresql://resort:resort@localhost:5432/resort_os?schema=public}"
CORE_URL="http://127.0.0.1:8000"
DEMO_JSON="/tmp/three-crowns-demo-showcase.json"

log() { printf '\n=== %s ===\n' "$*"; }

log "Create schema"
(
  cd packages/database
  npm install --no-audit --no-fund
  npx prisma validate
  npx prisma db push
)

log "Install Core and seed canonical inventory"
pip install -r services/api/requirements.txt
python scripts/apply_core_constraints.py
python scripts/seed_from_intake.py
python scripts/bootstrap_owner.py

log "Create synthetic staff accounts and clean baseline"
python - <<'PY'
import asyncio, os, uuid
import asyncpg
from argon2 import PasswordHasher

async def main():
    conn = await asyncpg.connect(os.environ['DATABASE_URL'].split('?')[0])
    ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
    try:
        property_id = await conn.fetchval('SELECT id FROM properties WHERE code=$1', os.environ['PROPERTY_CODE'])
        for username, password, display_name, role in [
            ('demo-maid', 'ThreeCrownsMaid!2026', 'Demo Maid', 'MAID'),
            ('demo-tech', 'ThreeCrownsTech!2026', 'Demo Technician', 'TECHNICIAN'),
        ]:
            await conn.execute(
                '''INSERT INTO staff_users (id,"propertyId",username,"displayName","passwordHash",role,"isActive","createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,$5,$6,true,now(),now())
                   ON CONFLICT ("propertyId",username) DO UPDATE SET
                     "displayName"=EXCLUDED."displayName", "passwordHash"=EXCLUDED."passwordHash",
                     role=EXCLUDED.role, "isActive"=true, "updatedAt"=now()''',
                uuid.uuid4(), property_id, username, display_name, ph.hash(password), role,
            )
        await conn.execute('UPDATE rooms SET "operationalState"=\'CLEAN\', "updatedAt"=now() WHERE "propertyId"=$1', property_id)
    finally:
        await conn.close()

asyncio.run(main())
PY

log "Start Resort Core"
python -m uvicorn app.app_entry:app --app-dir services/api --host 127.0.0.1 --port 8000 > /tmp/resort-api.log 2>&1 &
echo $! > /tmp/resort-api.pid
for i in {1..45}; do
  if curl --fail -sS "$CORE_URL/health/ready" >/tmp/ready.json; then break; fi
  sleep 1
done
cat /tmp/ready.json

log "Create real booking flow with synthetic records"
python scripts/prepare_demo_showcase.py
cat "$DEMO_JSON"

log "Shape PMS showcase safely"
curl --fail -sS -c /tmp/demo-cookies.txt -X POST "$CORE_URL/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"client-demo","password":"ThreeCrownsDemo!2026"}' >/tmp/demo-login.json

python - <<'PY'
import asyncio, json, os, uuid
from datetime import date, timedelta
import asyncpg

async def main():
    demo = json.load(open('/tmp/three-crowns-demo-showcase.json', encoding='utf-8'))
    conn = await asyncpg.connect(os.environ['DATABASE_URL'].split('?')[0])
    try:
        today = date.today()
        # First two stays are made valid for check-in. The first will be changed to
        # "departure today" only after Core accepts the check-in transition.
        shapes = [
            (today - timedelta(days=1), today + timedelta(days=1)),
            (today - timedelta(days=1), today + timedelta(days=3)),
            (today, today + timedelta(days=2)),
        ]
        for item, (check_in, check_out) in zip(demo[:3], shapes):
            rid = uuid.UUID(item['reservation_id'])
            await conn.execute('UPDATE reservations SET "checkIn"=$1,"checkOut"=$2,"updatedAt"=now() WHERE id=$3', check_in, check_out, rid)
            await conn.execute(
                '''UPDATE inventory_blocks SET "startDate"=$1,"endDate"=$2,"updatedAt"=now()
                   WHERE "reservationId"=$3 AND active=true AND "blockType"='RESERVATION' ''',
                check_in, check_out, rid,
            )

        reserved = {x.get('room_code') for x in demo if x.get('room_code')}
        rows = await conn.fetch('SELECT id,code FROM rooms ORDER BY code')
        free = [r for r in rows if r['code'] not in reserved]
        for row, state in zip(free[:3], ['DIRTY', 'IN_INSPECTION', 'TECH_BLOCK']):
            await conn.execute('UPDATE rooms SET "operationalState"=$1,"updatedAt"=now() WHERE id=$2', state, row['id'])
    finally:
        await conn.close()

asyncio.run(main())
PY

FIRST=$(python -c "import json; print(json.load(open('$DEMO_JSON'))[0]['reservation_id'])")
SECOND=$(python -c "import json; print(json.load(open('$DEMO_JSON'))[1]['reservation_id'])")
curl --fail -sS -b /tmp/demo-cookies.txt -X POST "$CORE_URL/api/v1/admin/stays/reservations/$FIRST/check-in" >/tmp/checkin-1.json
curl --fail -sS -b /tmp/demo-cookies.txt -X POST "$CORE_URL/api/v1/admin/stays/reservations/$SECOND/check-in" >/tmp/checkin-2.json
cat /tmp/checkin-1.json
cat /tmp/checkin-2.json

# After a valid Core transition, make the first synthetic checked-in stay a
# departure-today example for the PMS quick filter. This is staging-only data.
FIRST="$FIRST" python - <<'PY'
import asyncio, os, uuid
from datetime import date
import asyncpg

async def main():
    rid = uuid.UUID(os.environ['FIRST'])
    conn = await asyncpg.connect(os.environ['DATABASE_URL'].split('?')[0])
    try:
        today = date.today()
        await conn.execute('UPDATE reservations SET "checkOut"=$1,"updatedAt"=now() WHERE id=$2', today, rid)
        await conn.execute(
            '''UPDATE inventory_blocks SET "endDate"=$1,"updatedAt"=now()
               WHERE "reservationId"=$2 AND active=true AND "blockType"='RESERVATION' ''',
            today, rid,
        )
    finally:
        await conn.close()

asyncio.run(main())
PY

log "Build public web"
(cd apps/web && npm install --no-audit --no-fund && npm run typecheck && npm run build)

log "Build PMS admin"
(cd apps/admin && npm install --no-audit --no-fund && npm run typecheck && npm run build)

log "Build Staff PWA"
(cd apps/staff && npm install --no-audit --no-fund && npm run typecheck && npm run build)

log "Start interfaces"
(cd apps/web && CORE_API_URL="$CORE_URL" npm start > /tmp/web.log 2>&1 & echo $! > /tmp/web.pid)
(cd apps/admin && CORE_API_URL="$CORE_URL" npm start > /tmp/admin.log 2>&1 & echo $! > /tmp/admin.pid)
(cd apps/staff && CORE_API_URL="$CORE_URL" npm start > /tmp/staff.log 2>&1 & echo $! > /tmp/staff.pid)
for port in 3000 3001 3002; do
  for i in {1..45}; do
    if curl --fail -sS "http://127.0.0.1:$port" >/dev/null; then break; fi
    sleep 1
  done
  curl --fail -sS "http://127.0.0.1:$port" >/dev/null
done

log "Live smoke tests"
curl --fail -sS "$CORE_URL/api/v1/booking/check-availability?check_in=2026-08-27&check_out=2026-08-29&adults=2&children=0" >/tmp/live-availability.json
curl --fail -sS -b /tmp/demo-cookies.txt "$CORE_URL/api/v1/pms/grid?start=2026-08-25&end=2026-09-05" >/tmp/live-grid.json
python - <<'PY'
import json
availability=json.load(open('/tmp/live-availability.json'))
grid=json.load(open('/tmp/live-grid.json'))
assert len(grid['rooms']) == 84
assert any(x['pricing']['sellable'] for x in availability['results'])
assert any(b.get('reservation_id') for r in grid['rooms'] for b in r['blocks'])
states={r['operational_state'] for r in grid['rooms']}
assert {'CLEAN','DIRTY','IN_INSPECTION','TECH_BLOCK'}.issubset(states)
print('Smoke OK: inventory, pricing, reservations and operational states are present')
PY

log "Install Cloudflare quick tunnel client"
curl -L --fail --retry 3 -o /tmp/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x /tmp/cloudflared
/tmp/cloudflared --version

log "Start HTTPS tunnels"
/tmp/cloudflared tunnel --no-autoupdate --url http://127.0.0.1:3000 > /tmp/tunnel-web.log 2>&1 &
/tmp/cloudflared tunnel --no-autoupdate --url http://127.0.0.1:3001 > /tmp/tunnel-admin.log 2>&1 &
/tmp/cloudflared tunnel --no-autoupdate --url http://127.0.0.1:3002 > /tmp/tunnel-staff.log 2>&1 &
/tmp/cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8000 > /tmp/tunnel-core.log 2>&1 &

find_url() {
  local file="$1" url=""
  for i in {1..90}; do
    url=$(grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' "$file" | head -1 || true)
    if [ -n "$url" ]; then echo "$url"; return 0; fi
    sleep 1
  done
  cat "$file" >&2 || true
  return 1
}

WEB_URL=$(find_url /tmp/tunnel-web.log)
ADMIN_URL=$(find_url /tmp/tunnel-admin.log)
STAFF_URL=$(find_url /tmp/tunnel-staff.log)
PUBLIC_CORE_URL=$(find_url /tmp/tunnel-core.log)

curl --fail -sS "$WEB_URL" >/dev/null
curl --fail -sS "$ADMIN_URL/demo" >/dev/null
curl --fail -sS "$STAFF_URL" >/dev/null
curl --fail -sS "$PUBLIC_CORE_URL/health/live" >/dev/null

log "Publish links"
cat > /tmp/live-links.md <<EOF
## LIVE CLIENT STAGING is online

Exact commit: \`${GITHUB_SHA}\`

- Public website: ${WEB_URL}
- PMS login: ${ADMIN_URL}
- PMS standalone showcase: ${ADMIN_URL}/demo
- Staff PWA: ${STAFF_URL}
- Resort Core readiness: ${PUBLIC_CORE_URL}/health/ready

### Synthetic demo credentials
- OWNER: \`client-demo\` / \`ThreeCrownsDemo!2026\`
- MAID: \`demo-maid\` / \`ThreeCrownsMaid!2026\`
- TECHNICIAN: \`demo-tech\` / \`ThreeCrownsTech!2026\`

Synthetic presentation data only. Temporary staging; do not enter real guest data or real payments.
EOF

gh api "repos/${GITHUB_REPOSITORY}/issues/25/comments" -f body="$(cat /tmp/live-links.md)"
cat /tmp/live-links.md >> "$GITHUB_STEP_SUMMARY"
cat /tmp/live-links.md

log "Keep staging online"
sleep 18000
