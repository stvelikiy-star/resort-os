# Three Crowns Resort OS — Staging Runbook

Status: **deployment contract / not yet externally deployed**.

This runbook creates an isolated full-stack staging environment for the current integration branch. It must never point at the production database or reuse production provider secrets.

## Topology

- PostgreSQL 16: `127.0.0.1:15432`
- Resort Core FastAPI: `127.0.0.1:18000`
- Public site: `127.0.0.1:13000`
- PMS/admin: `127.0.0.1:13001`
- Staff PWA: `127.0.0.1:13002`

Recommended staging hostnames:

- `staging.3korony.com` -> web
- `pms-staging.3korony.com` -> admin
- `staff-staging.3korony.com` -> staff
- `/core/*` on each UI host -> the same Resort Core, with `/core` stripped;
- `/ws/*` on the PMS host -> Resort Core with WebSocket Upgrade preserved.

A ready Caddy template is committed as `deploy/Caddyfile.staging.example`.

## Safety rules

1. Use a separate staging PostgreSQL volume/database.
2. Never reuse production DB, session, n8n, Telegram or provider credentials.
3. Keep direct Telegram/OpenAI/provider credentials empty until a dedicated staging bot/provider account is explicitly connected.
4. Staging synthetic guest/task data must never be copied into production.
5. Google Sheets remain a mirror/control surface; they do not create guaranteed reservations or mutate inventory.
6. A green UI is not sufficient: `scripts/staging_acceptance.py` must pass.
7. Staging schema creation via `prisma db push` is allowed only because the database is disposable. Production still requires a reviewed migration baseline + `prisma migrate deploy`.
8. Localhost acceptance may use `COOKIE_SECURE=false` only because every port is bound to `127.0.0.1`. Any externally reachable HTTPS staging environment must use `COOKIE_SECURE=true`.
9. V9 realtime is mandatory acceptance, not an optional enhancement.

## 1. Checkout the exact integration head

```bash
git fetch origin
git checkout integration/site-pms-cms-20260827
git pull --ff-only
```

Record the SHA before deployment:

```bash
git rev-parse HEAD
```

## 2. Environment

```bash
cp .env.staging.example .env.staging
chmod 600 .env.staging
```

Replace every `CHANGE_ME_*` value with staging-only secrets.

For the first localhost-only gate keep:

```dotenv
COOKIE_SECURE=false
NEXT_PUBLIC_CORE_WS_URL=ws://127.0.0.1:18000
```

Then load environment:

```bash
set -a
source .env.staging
set +a
```

Set a deployment-host database URL for migration/seed scripts:

```bash
export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:15432/${POSTGRES_DB}?schema=public"
```

## 3. Start only PostgreSQL

```bash
docker compose --env-file .env.staging -f compose.staging.yaml up -d postgres
```

Verify:

```bash
docker compose --env-file .env.staging -f compose.staging.yaml ps postgres
```

## 4. Build staging schema on the disposable database

```bash
cd packages/database
npm install
npx prisma validate
npx prisma db push
cd ../..
```

Apply PostgreSQL invariants:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r services/api/requirements.txt
python scripts/apply_core_constraints.py
```

## 5. Seed Three Crowns canonical intake

```bash
python scripts/seed_from_intake.py
```

Seed must stop unless it sees exactly **84 rooms / 12 room types**.

The current `data-intake/rooms.csv` is a reconstructed baseline and still contains owner-confirmation gaps (`UNKNOWN`, explicit `CONFIRM`). It is acceptable for staging mechanics but is **not** owner-approved production physical-room truth. Production physical-room reconciliation must use `scripts/import_physical_rooms.py` after the owner-confirmed 84-room sheet is complete.

## 6. Bootstrap synthetic staging users

```bash
python scripts/bootstrap_owner.py
APP_ENV=staging python scripts/bootstrap_staging_staff.py
```

This creates/rotates only the environment-defined staging OWNER, MAID and TECHNICIAN accounts and revokes their previous sessions.

## 7. Start full stack

```bash
docker compose --env-file .env.staging -f compose.staging.yaml up -d --build api web admin staff
```

`NEXT_PUBLIC_CORE_WS_URL` is a browser-visible build-time value for the admin bundle. When that value changes, rebuild `admin`; a container restart alone is not enough.

Check containers:

```bash
docker compose --env-file .env.staging -f compose.staging.yaml ps
```

Core readiness:

```bash
curl -fsS http://127.0.0.1:18000/health/ready
```

Expected invariant: room count 84 and room type count 12.

## 8. Run localhost full staging acceptance

```bash
export CORE_API_URL=http://127.0.0.1:18000
export CORE_WS_URL=ws://127.0.0.1:18000
python scripts/staging_acceptance.py
```

The gate includes:

1. Core readiness and canonical 84/12.
2. CMS RU/KG/EN draft/publish isolation and restore.
3. Public availability.
4. Website request -> CRM `ReservationRequest`, not automatic reservation.
5. PMS reads the same Core inventory.
6. Authenticated RFC6455 handshake to `/ws/pms/grid`.
7. First realtime message is `pms.grid.snapshot` containing 84 rooms.
8. V9 `control-snapshot` completeness.
9. Analytics report reads 84 rooms / 12 categories from Resort Core.
10. Synthetic MAID login and assigned housekeeping claim.
11. Mandatory housekeeping checklist + audited completion report -> `IN_INSPECTION`.
12. Manager accepts inspection -> room becomes `CLEAN` through canonical operations transition.
13. Synthetic TECHNICIAN login and maintenance claim.
14. Audited maintenance report -> `DONE`.
15. Last active repair releases the room to `DIRTY` and creates/reuses housekeeping.
16. Multiple active repair protection retains `TECH_BLOCK` until the final maintenance task terminates.
17. Audit history contains `COMPLETE_WITH_REPORT`.

If any step fails, staging is rejected.

## 9. Reverse proxy / TLS

Only after localhost acceptance is green, point staging-only DNS names and use the committed Caddy template:

```bash
sudo cp deploy/Caddyfile.staging.example /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Before rebuilding externally exposed staging, change `.env.staging` to:

```dotenv
COOKIE_SECURE=true
NEXT_PUBLIC_CORE_WS_URL=
CORS_ORIGINS=https://staging.3korony.com,https://pms-staging.3korony.com,https://staff-staging.3korony.com
```

An empty `NEXT_PUBLIC_CORE_WS_URL` intentionally makes V9 use same-origin `wss://pms-staging.3korony.com/ws/...`, which Caddy proxies to Resort Core. This keeps the management session cookie and websocket on the same browser origin.

Then rebuild/restart at minimum API + admin:

```bash
docker compose --env-file .env.staging -f compose.staging.yaml up -d --build api admin
```

Run acceptance again through HTTPS. For the direct Core check, either temporarily expose a protected staging Core origin or run the script locally on the host with the localhost Core URL; in addition, manually verify the PMS browser shows realtime `live` through the public PMS hostname.

Do not attach production `3korony.com` DNS during staging.

## 10. Vercel role

Vercel can host the public site and staff/admin previews, but V9 PMS realtime requires special care: HTTP rewrites alone are not treated as a WebSocket guarantee.

Preferred PMS staging shape is the same-origin Caddy/container deployment above. If admin is later hosted on Vercel, use a dedicated Core staging hostname plus a deliberately shared `.3korony.com` cookie policy and verify cross-host WebSocket authentication; do not assume it works because REST `/core` works.

The old `three-crowns-v3-preview` project is not the current full-stack staging environment.

## 11. Mobile acceptance

After HTTPS is available test at minimum:

- iPhone Safari current iOS;
- Android Chrome current;
- Telegram Mini App Android;
- Telegram Mini App iOS where available;
- 360px, 390px, 430px widths;
- landscape once for PMS/staff edge cases.

Mandatory staff checks:

- login/autologin;
- `Мои / Можно взять / Завершено`;
- claim race handling;
- housekeeping checklist;
- report modal keyboard/scroll behavior;
- offline/retry messaging;
- safe-area insets;
- no horizontal page scroll.

Mandatory PMS checks:

- realtime indicator reaches `live`;
- websocket reconnect after Wi-Fi toggle;
- horizontal tape scrolling;
- sticky room/status columns;
- drag/preview/commit never bypasses confirmation;
- 14/30-day views remain usable at tablet widths.

## 12. Rollback / reset

Stop UI/API:

```bash
docker compose --env-file .env.staging -f compose.staging.yaml stop api web admin staff
```

A fully disposable staging reset:

```bash
docker compose --env-file .env.staging -f compose.staging.yaml down -v
```

Then repeat from PostgreSQL/schema/seed.

Never run `down -v` against production compose/volumes.

## Production cutover remains blocked until

- owner-approved physical 84-room register is imported/verified;
- migration baseline is generated, reviewed and clean-db verified;
- backup -> clean restore is verified;
- staging acceptance is green on deployed HTTPS origins;
- mobile acceptance is green;
- provider credentials are connected separately and tested;
- production preflight is green;
- rollback point is recorded immediately before cutover.
