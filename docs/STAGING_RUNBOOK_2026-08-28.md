# Three Crowns Resort OS — Staging Runbook

Status: **deployment contract / not yet externally deployed**.

This runbook creates an isolated full-stack staging environment for the current integration branch. It must never point at the production database or reuse production provider secrets.

## Topology

- PostgreSQL 16: `127.0.0.1:15432`
- Resort Core FastAPI: `127.0.0.1:18000`
- Public site: `127.0.0.1:13000`
- PMS/admin: `127.0.0.1:13001`
- Staff PWA: `127.0.0.1:13002`

External HTTPS termination/reverse proxy is intentionally outside the compose file. Recommended staging hostnames:

- `staging.3korony.com` -> web
- `pms-staging.3korony.com` -> admin
- `staff-staging.3korony.com` -> staff
- `/core/*` on each UI host must proxy to the same Resort Core.

## Safety rules

1. Use a separate staging PostgreSQL volume/database.
2. Never reuse production DB, session, n8n, Telegram or provider credentials.
3. Keep direct Telegram/OpenAI/provider credentials empty until a dedicated staging bot/provider account is explicitly connected.
4. Staging synthetic guest/task data must never be copied into production.
5. Google Sheets remain a mirror/control surface; they do not create guaranteed reservations or mutate inventory.
6. A green UI is not sufficient: `scripts/staging_acceptance.py` must pass.
7. Staging schema creation via `prisma db push` is allowed only because the database is disposable. Production still requires a reviewed migration baseline + `prisma migrate deploy`.

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

Then load it:

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

Check containers:

```bash
docker compose --env-file .env.staging -f compose.staging.yaml ps
```

Core readiness:

```bash
curl -fsS http://127.0.0.1:18000/health/ready
```

Expected invariant: room count 84 and room type count 12.

## 8. Run full staging acceptance

```bash
export CORE_API_URL=http://127.0.0.1:18000
python scripts/staging_acceptance.py
```

The gate includes:

1. Core readiness and canonical 84/12.
2. CMS RU/KG/EN draft/publish isolation and restore.
3. Public availability.
4. Website request -> CRM `ReservationRequest`, not automatic reservation.
5. PMS reads the same Core inventory.
6. V9 `control-snapshot` completeness.
7. Analytics report reads 84 rooms / 12 categories from Resort Core.
8. Synthetic MAID login and assigned housekeeping claim.
9. Mandatory housekeeping checklist + audited completion report -> `IN_INSPECTION`.
10. Manager accepts inspection -> room becomes `CLEAN` through canonical operations transition.
11. Synthetic TECHNICIAN login and maintenance claim.
12. Audited maintenance report -> `DONE`, room -> `DIRTY`.
13. Maintenance completion creates/reuses a housekeeping task.
14. Audit history contains `COMPLETE_WITH_REPORT`.

If any step fails, staging is rejected.

## 9. Reverse proxy / TLS

Only after local acceptance is green, expose HTTPS staging hostnames. Each Next application already calls `/core/...`; proxy that prefix to the same staging Resort Core.

Do not attach `3korony.com` production DNS during staging.

## 10. Vercel role

Vercel can host the three Next applications as preview/staging frontends, but Resort Core requires a container runtime because the PMS realtime contract includes WebSockets. The old `three-crowns-v3-preview` project is not the current full-stack staging environment.

Preferred end state:

- Vercel: `apps/web`, `apps/admin`, `apps/staff` preview projects.
- Container host: `services/api` FastAPI + WebSockets.
- Staging PostgreSQL: isolated database.
- Each frontend rewrites `/core` to the same staging Core origin.

Until Git integration is connected, do not label an old Vercel deployment as current staging.

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
